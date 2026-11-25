"""Ways to write the book's standalone tas-hil dot, rendered beside the print.

    PYTHONPATH=../mushaf ../mushaf/.venv/bin/python -m spike.dot_options
"""

from __future__ import annotations

import html
import json
import sys

import pymupdf

from .rows import BUILD, FUTUH, PROJECTS, SOURCES

FONTS = {
    "KFGQPC Hafs v18": SOURCES / "kfgqpc/mirror/hafs/hafs.18.ttf",
    "DigitalKhatt Madina": SOURCES / "digitalkhatt/digitalkhatt-js/hb-madina.otf",
}
DOT = "۬"
OPTIONS = [
    ("a  dot on the letter before (now)", lambda pre, post: pre + DOT + post),
    ("b  dot on a tatweel", lambda pre, post: pre + "ـ" + DOT + post),
    ("c  dot on a no-break space", lambda pre, post: pre + " " + DOT + post),
    ("d  dot on a narrow no-break space", lambda pre, post: pre + " " + DOT + post),
    ("e  dot on a hamza", lambda pre, post: pre + "ء" + DOT + post),
]


def main() -> None:
    sys.path.insert(0, str(PROJECTS / "mushaf"))
    from futuh.run import volume_pdf

    doc = pymupdf.open(volume_pdf(1))
    # two book words with the standalone dot: 2:14:16 (between zay and waw), 2:13 (after alif)
    samples = []
    for line in FUTUH.open():
        r = json.loads(line)
        if r.get("type") != "row":
            continue
        for w in r["words"]:
            if DOT in w["t"] and w.get("spine") in ("2:14:16", "2:13:16") and len(samples) < 2:
                if not any(s[1].get("spine") == w.get("spine") for s in samples):
                    samples.append((r, w))
    out = pymupdf.open()
    W = 1150
    H = 70
    page = out.new_page(width=W, height=110 + H * len(OPTIONS) * len(samples))
    y = 10
    for r, w in samples:
        i = w["t"].index(DOT)
        pre, post = w["t"][:i], w["t"][i + 1 :]
        b = w["bbox"]
        page.insert_text((10, y + 14), f"print, vol 1 p. {r['pdf_page']} ({w['spine']})", fontsize=9)
        page.show_pdf_page(pymupdf.Rect(10, y + 18, 260, y + 18 + 45), doc, r["pdf_page"] - 1,
                           clip=pymupdf.Rect(b[0] - 4, b[1] - 3, b[2] + 4, b[3] + 3))
        y += 70
        for label, make in OPTIONS:
            page.insert_text((10, y + 30), label, fontsize=10)
            x = 260
            for fname, fpath in FONTS.items():
                text = make(pre, post)
                css = f"@font-face {{font-family:q; src:url({fpath.name});}}"
                page.insert_htmlbox(pymupdf.Rect(x, y, x + 420, y + H),
                    f"<p dir='rtl' style='font-family:q;font-size:34px;text-align:center'>{html.escape(text)}</p>",
                    css=css, archive=pymupdf.Archive(str(fpath.parent)))
                page.insert_text((x + 5, y + H - 4), fname, fontsize=7, color=(0.5, 0.5, 0.5))
                x += 440
            page.draw_line((0, y + H), (W, y + H), color=(0.85, 0.85, 0.85))
            y += H
        y += 20
    BUILD.mkdir(exist_ok=True)
    page.get_pixmap(dpi=100).save(BUILD / "dot-options.png")
    print(BUILD / "dot-options.png")


if __name__ == "__main__":
    main()
