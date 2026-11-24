"""Print crops beside the preview renderer's standalone dot at a few side bearings.

    PYTHONPATH=../mushaf ../mushaf/.venv/bin/python -m spike.dot_sheet
"""

from __future__ import annotations

import json
import sys

import pymupdf

from .render import Renderer
from .rows import BUILD, FUTUH, PROJECTS

SIDES = [30]


def main() -> None:
    sys.path.insert(0, str(PROJECTS / "mushaf"))
    from futuh.run import volume_pdf

    doc = pymupdf.open(volume_pdf(1))
    words = []
    for line in FUTUH.open():
        r = json.loads(line)
        if r.get("type") != "row":
            continue
        for w in r["words"]:
            if "۬" in w["t"] and w.get("spine") in ("2:14:16", "2:13:16") and w["t"] not in [x[1]["t"] for x in words]:
                words.append((r, w))
    words = words[:3]
    R = Renderer()
    out = pymupdf.open()
    W, H = 600, 150
    page = out.new_page(width=W, height=40 + H * len(words))
    page.insert_text((10, 20), "print (left)  |  stored text drawn by the preview renderer (right)", fontsize=10)
    for n, (r, w) in enumerate(words):
        y = 40 + n * H
        b = w["bbox"]
        page.show_pdf_page(pymupdf.Rect(10, y, 260, y + H - 20), doc, r["pdf_page"] - 1,
                           clip=pymupdf.Rect(b[0] - 3, b[1] - 3, b[2] + 3, b[3] + 3))
        # stored form: the dot as its own letter (tatweel + U+06EC), in place of "letter + U+06EC"
        stored = w["t"]  # already the stored form: tatweel + U+06EC (+ the hamza's vowel)
        x = 280
        for side, vy in ((30, -200),):
            svg, sw, sh = R.svg(stored, size=56, dot_side=side, vowel_y=vy)
            sdoc = pymupdf.open(stream=svg.encode(), filetype="svg")
            pdfbytes = sdoc.convert_to_pdf()
            src = pymupdf.open("pdf", pdfbytes)
            page.show_pdf_page(pymupdf.Rect(x, y, x + 270, y + H - 20), src, 0)
            page.insert_text((x + 5, y + H - 8), "preview renderer, DigitalKhatt", fontsize=8, color=(0.5, 0.5, 0.5))
            x += 290
    BUILD.mkdir(exist_ok=True)
    page.get_pixmap(dpi=110).save(BUILD / "dot-sheet.png")
    print(BUILD / "dot-sheet.png")


if __name__ == "__main__":
    main()
