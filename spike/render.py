"""A tiny preview renderer: HarfBuzz shaping, glyph outlines drawn as SVG paths.

It exists so display choices (like the standalone tas-hil dot) can be made in the drawing,
not by abusing characters. Stored text uses tatweel + U+06EC for the book's standalone dot (its
own letter); here it is shaped as ZWNJ tatweel U+06EC ZWNJ (so neighbours keep their
non-joining forms), the tatweel is not drawn, and it gets the width `dot_advance`; the dot is
centred in that width at mid-letter height.

    ../mushaf/.venv/bin/python -m spike.render "TEXT" out.png
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pymupdf
import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen

from .rows import PROJECTS

DK = PROJECTS / "mushaflab/fonts/digitalkhatt/hb-madina.otf"
STANDALONE_DOT = "ـ۬"  # internal encoding of the book's standalone tas-hil dot
_DOT_LETTER = re.compile("\u0640[\u064b-\u065f\u0670\u06d6-\u06ed]*\u06ec[\u064b-\u065f\u0670\u06d6-\u06ed]*")


class Renderer:
    def __init__(self, font_path: Path = DK):
        blob = hb.Blob.from_file_path(str(font_path))
        self.face = hb.Face(blob)
        self.font = hb.Font(self.face)
        self.upem = self.face.upem
        self.tatweel = self.font.get_nominal_glyph(0x0640)
        self.dot = self.font.get_nominal_glyph(0x06EC)
        self._paths: dict[int, str] = {}
        self._ink: dict = {}

    def _path(self, gid: int) -> str:
        if gid not in self._paths:
            pen = SVGPathPen(None)
            self.font.draw_glyph_with_pen(gid, pen)
            self._paths[gid] = pen.getCommands()
        return self._paths[gid]

    def shape(self, text: str):
        # wrap the whole standalone-dot letter (tatweel and all its marks, in any order) in ZWNJs
        text = _DOT_LETTER.sub(lambda m: "\u200c" + m.group(0) + "\u200c", text)
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.font, buf, {})
        return buf.glyph_infos, buf.glyph_positions

    def _bounds(self, gid: int) -> tuple[float, float, float, float]:
        from fontTools.pens.boundsPen import BoundsPen

        pen = BoundsPen(None)
        self.font.draw_glyph_with_pen(gid, pen)
        return pen.bounds or (0, 0, 0, 0)

    def _ink_x(self, gid: int, y0: float, y1: float) -> tuple[float, float] | None:
        """Leftmost and rightmost ink of a glyph between heights y0 and y1 (outline sampled)."""
        key = (gid, round(y0), round(y1))
        if key not in self._ink:
            pen = _SamplePen()
            self.font.draw_glyph_with_pen(gid, pen)
            xs = [x for x, y in pen.points if y0 <= y <= y1]
            self._ink[key] = (min(xs), max(xs)) if xs else None
        return self._ink[key]

    def svg(self, text: str, size: float = 60, gap: int = 40, dot_scale: float = 0.85,
            dot_mid: int = 230, vowel_gap: int = 50, min_open: int = 0) -> tuple[str, float, float]:
        """The standalone dot stands after the whole of the letter before it, `gap` font units
        from its ink; on the other side it is `gap` units from the next letter's ink at the
        dot's own height. It takes the width it needs, but at least `min_open` units. The
        softened hamza's vowel goes above it."""
        infos, poss = self.shape(text)
        dx0, dy0, dx1, dy1 = self._bounds(self.dot)
        dot_w, dot_h = (dx1 - dx0) * dot_scale, (dy1 - dy0) * dot_scale
        dot_bottom, dot_top = dot_mid - dot_h / 2, dot_mid + dot_h / 2
        dot_clusters = {i.cluster for i in infos if i.codepoint == self.tatweel}
        vowels = {i.cluster: i.codepoint for i in infos
                  if i.cluster in dot_clusters and i.codepoint not in (self.tatweel, self.dot)}
        # pass 1: lay out with zero-width slots; pieces are (gid, x, y, cluster, advance)
        pieces, slot_at, x = [], {}, 0
        for info, pos in zip(infos, poss):
            if info.codepoint == self.tatweel and info.cluster in dot_clusters:
                slot_at[info.cluster] = len(pieces)
                continue
            pieces.append([info.codepoint, x + pos.x_offset, pos.y_offset, info.cluster, pos.x_advance])
            x += pos.x_advance
        # pass 2: open each slot just enough, from the neighbours' ink in the dot's band
        dot_x: dict[int, float] = {}
        for cl, k in sorted(slot_at.items(), key=lambda kv: kv[1]):
            top = dot_top + vowel_gap
            if cl in vowels:
                vb = self._bounds(vowels[cl])
                top += vb[3] - vb[1]
            band = (dot_bottom - gap, top + gap)
            slot_x = pieces[k][1] if k < len(pieces) else x
            left = next((p for p in reversed(pieces[:k]) if p[4] > 0), None)
            right = next((p for p in pieces[k:] if p[4] > 0), None)
            ink_l = self._ink_x(left[0], *band) if left else None
            L = left[1] + ink_l[1] if ink_l else slot_x
            # The letter before the dot (on its right) keeps all its ink to itself: the dot never
            # tucks under a tail (zay), it stands after the whole letter, as in KFGQPC's fonts.
            # The letter after it (on the left) is measured at the dot's height only.
            R = right[1] + self._bounds(right[0])[0] if right else slot_x
            need = max(float(min_open), dot_w + 2 * gap - (R - L))
            for p in pieces[k:]:
                p[1] += need
            x += need
            dot_x[cl] = (L + R + need - dot_w) / 2
        out = []
        for gid, gx, gy, cl, _ in pieces:
            sc = 1.0
            if gid == self.dot and cl in dot_x:
                sc = dot_scale
                gx, gy = dot_x[cl] - dx0 * sc, dot_bottom - dy0 * sc
            elif cl in dot_x:
                vx0, vy0, vx1, _ = self._bounds(gid)
                gx = dot_x[cl] + dot_w / 2 - (vx0 + vx1) / 2
                gy = dot_top + vowel_gap - vy0
            p = self._path(gid)
            if p:
                tf = f"translate({gx:.1f},{gy:.1f})" + (f" scale({sc})" if sc != 1.0 else "")
                out.append(f'<path transform="{tf}" d="{p}"/>')
        width = x
        asc, desc = 1100, 600
        scale = size / self.upem
        w, h = width * scale + 20, (asc + desc) * scale + 10
        body = "".join(out)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}">'
               f'<g transform="translate(10,{asc * scale + 5:.1f}) scale({scale},{-scale})">{body}</g></svg>')
        return svg, w, h


class _SamplePen:
    """Collects points along a glyph outline (curves sampled), for ink-profile checks."""

    def __init__(self):
        self.points: list[tuple[float, float]] = []
        self._cur = (0.0, 0.0)

    def moveTo(self, p):
        self._cur = p
        self.points.append(p)

    def lineTo(self, p):
        (x0, y0), (x1, y1) = self._cur, p
        for t in range(1, 9):
            self.points.append((x0 + (x1 - x0) * t / 8, y0 + (y1 - y0) * t / 8))
        self._cur = p

    def curveTo(self, *ps):
        pts = [self._cur, *ps]
        for t in range(1, 17):
            u = t / 16
            if len(pts) == 4:
                (a, b, c, d) = pts
                f = lambda i: (1 - u) ** 3 * a[i] + 3 * (1 - u) ** 2 * u * b[i] + 3 * (1 - u) * u ** 2 * c[i] + u ** 3 * d[i]
            else:
                (a, b, c) = pts[0], pts[1], pts[-1]
                f = lambda i: (1 - u) ** 2 * a[i] + 2 * (1 - u) * u * b[i] + u ** 2 * c[i]
            self.points.append((f(0), f(1)))
        self._cur = ps[-1]

    def qCurveTo(self, *ps):
        self.curveTo(*ps)

    def closePath(self):
        pass

    def endPath(self):
        pass


def to_png(svg: str, out: Path, zoom: float = 2.0) -> None:
    doc = pymupdf.open(stream=svg.encode(), filetype="svg")
    doc[0].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).save(out)


if __name__ == "__main__":
    s, _, _ = Renderer().svg(sys.argv[1])
    to_png(s, Path(sys.argv[2]))
