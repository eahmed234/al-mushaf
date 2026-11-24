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

    def svg(self, text: str, size: float = 60, dot_side: int = 30, dot_mid: int = 230, vowel_room: int = 150, vowel_y: int = -200) -> tuple[str, float, float]:
        infos, poss = self.shape(text)
        dot_advance = 180 + 2 * dot_side  # the dot glyph is 180 units wide in DigitalKhatt
        # clusters holding a standalone-dot tatweel, and those that also carry the hamza's vowel
        dot_clusters = {i.cluster for i in infos if i.codepoint == self.tatweel}
        voweled = {i.cluster for i in infos if i.cluster in dot_clusters and i.codepoint not in (self.tatweel, self.dot)}
        # HarfBuzz gives glyphs in visual order (left to right) for RTL text.
        pieces, slots, x = [], {}, 0
        for info, pos in zip(infos, poss):
            gid = info.codepoint
            if gid == self.tatweel and info.cluster in dot_clusters:
                # reserve the dot's slot (plus room on its left for the vowel); the tatweel isn't drawn
                room = vowel_room if info.cluster in voweled else 0
                slots[info.cluster] = x + room
                x += dot_advance + room
                continue
            pieces.append((gid, x + pos.x_offset, pos.y_offset, info.cluster))
            x += pos.x_advance
        width = x
        out = []
        for gid, gx, gy, cl in pieces:
            if gid == self.dot and cl in slots:
                gx, gy = slots[cl] + dot_side, dot_mid - 90
            elif cl in slots:
                # the softened hamza's vowel: below and to the left of the dot, as al-Futuh prints it
                gx, gy = slots[cl] - vowel_room, vowel_y
            p = self._path(gid)
            if p:
                out.append(f'<path transform="translate({gx},{gy})" d="{p}"/>')
        asc, desc = 1100, 600
        scale = size / self.upem
        w, h = width * scale + 20, (asc + desc) * scale + 10
        body = "".join(out)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}">'
               f'<g transform="translate(10,{asc * scale + 5:.1f}) scale({scale},{-scale})">{body}</g></svg>')
        return svg, w, h


def to_png(svg: str, out: Path, zoom: float = 2.0) -> None:
    doc = pymupdf.open(stream=svg.encode(), filetype="svg")
    doc[0].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).save(out)


if __name__ == "__main__":
    s, _, _ = Renderer().svg(sys.argv[1])
    to_png(s, Path(sys.argv[2]))
