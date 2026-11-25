"""Side-by-side check of rebuilt rows: the printed rows (this one and the one above) next to the
full text the spike rebuilt. Quoted words black, inherited words grey, alternatives in braces.

    python3 -m checks.sheet ROW_ID [ROW_ID ...]   # writes build/sheet.png
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

import pymupdf

from mushaf_data.paths import BUILD, ROOT, SOURCES
from ..futuh.rows import FUTUH, MUSHAF, RUWAT

FONT = SOURCES / "kfgqpc/mirror/hafs/hafs.18.ttf"
PDF_DIR = MUSHAF


def main(ids: list[str]) -> None:
    sys.path.insert(0, str(PDF_DIR))
    from futuh.run import volume_pdf  # the book PDFs live with the extractor

    doc = pymupdf.open(volume_pdf(1))
    book = {json.loads(l)["id"]: json.loads(l) for l in FUTUH.open() if '"type": "row"' in l}
    rebuilt = {json.loads(l)["id"]: json.loads(l) for l in (BUILD / "rows.jsonl").open()}
    order = list(book)
    W, H = 1100, 260
    out = pymupdf.open()
    page = out.new_page(width=W, height=H * len(ids) + 40)
    page.insert_text((10, 24), "Printed rows (left: the row above, then this row)  |  rebuilt full text (right): quoted = black, inherited = grey", fontsize=11)
    arch = pymupdf.Archive(str(FONT.parent))
    css = f"@font-face {{font-family:q; src:url({FONT.name});}}"
    for n, rid in enumerate(ids):
        y = 40 + n * H
        r, rb = book[rid], rebuilt[rid]
        prev = book[order[order.index(rid) - 1]]
        boxes = [w["bbox"] for x in (prev, r) if x["pdf_page"] == r["pdf_page"] for w in x["words"] if w.get("bbox")]
        y0, y1 = min(b[1] for b in boxes) - 6, max(b[3] for b in boxes) + 6
        pg = doc[r["pdf_page"] - 1]
        page.show_pdf_page(pymupdf.Rect(10, y + 5, 560, y + H - 10), doc, r["pdf_page"] - 1,
                           clip=pymupdf.Rect(pg.rect.x0 + 30, y0, pg.rect.x1 - 30, y1))
        words = []
        for w in rb["words"]:
            t = " | ".join(w["alts"]) if w.get("alts") else w["t"]
            t = "{" + t + "}" if w.get("alts") else t
            col = "#000" if w["src"] == "quote" else "#999"
            words.append(f"<span style='color:{col}'>{html.escape(t)}</span>")
        head = f"{n + 1}. {rid} · row {rb['n']} · {', '.join(rb['ruwat'] or rb['ruwat_min'])}"
        page.insert_htmlbox(pymupdf.Rect(575, y + 5, W - 10, y + H - 10),
            f"<p style='font-family:sans-serif;font-size:10px;color:#a00'>{html.escape(head)}</p>"
            f"<p style='font-family:sans-serif;font-size:10px'>{html.escape(rb['label'])}</p>"
            f"<p dir='rtl' style='font-family:q;font-size:19px;line-height:1.6'>{' '.join(words)}</p>",
            css=css, archive=arch)
        page.draw_line((0, y + H), (W, y + H), color=(0.75, 0.75, 0.75))
    BUILD.mkdir(exist_ok=True)
    page.get_pixmap(dpi=110).save(BUILD / "sheet.png")
    print(BUILD / "sheet.png")


if __name__ == "__main__":
    main(sys.argv[1:])
