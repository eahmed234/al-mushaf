"""The review questions as pictures: for each box, the printed box beside the questions about it.

    PYTHONPATH=../mushaf ../mushaf/.venv/bin/python -m spike.review_sheet   # spike/build/review-NN.png

Reads spike/build/review.json (written by `python3 -m spike.review`).
"""

from __future__ import annotations

import html
import json
import sys
from collections import defaultdict

import pymupdf

from .rows import BUILD, FUTUH, PROJECTS, SOURCES

FONT = SOURCES / "kfgqpc/mirror/hafs/hafs.18.ttf"
NAMES = {
    "qalun": "Qālūn", "warsh": "Warsh", "bazzi": "al-Bazzī", "qunbul": "Qunbul", "duri_abuamr": "al-Dūrī (Abū ʿAmr)",
    "susi": "al-Sūsī", "hisham": "Hishām", "ibn_dhakwan": "Ibn Dhakwān", "shuba": "Shuʿbah", "hafs": "Ḥafṣ",
    "khalaf_an_hamzah": "Khalaf (Ḥamzah)", "khallad": "Khallād", "abul_harith": "Abū al-Ḥārith", "duri_kisai": "al-Dūrī (al-Kisāʾī)",
    "ibn_wardan": "Ibn Wardān", "ibn_jammaz": "Ibn Jammāz", "ruways": "Ruways", "rawh": "Rawḥ", "ishaq": "Isḥāq", "idris": "Idrīs",
}
WORDS = {
    "munfasil": "munfaṣil", "silah_mim": "ṣilat al-mīm", "silah_mim_hamza": "ṣilat al-mīm before hamz",
    "imala_ra": "imālah (before rāʾ)", "imala_ya": "imālah (dhawāt al-yāʾ)", "idgham_kabir": "idghām kabīr",
    "naql_word": "naql", "badal": "badal", "hamzatayn": "two hamzas", "hamz_waqf_mid": "waqf on the hamz",
}


# The question each entry asks (neutral: the data can't answer it; Eisa can)
def note_for(it: dict) -> str:
    if it["rawi"] == "qalun":
        return ("Row 1 is 'الجميع عدا أصحاب الصلة'. Does it also cover Qālūn's iskān here, "
                "as 'الجميع عدا من سيأتي' does?")
    if it["rawi"] == "ruways":
        return ("Ruways: idghām kabīr at 2:20 (لَذَهَب بِّسَمۡعِهِمۡ), izhār at 2:2 (فِيهِ هُدٗى). "
                "Is his idghām limited to listed words (so izhār at 2:2 and idghām only at 2:20), or a khulf?")
    return ""


def fmt(ch: dict) -> str:
    return ", ".join(f"{WORDS.get(c, c)}: {w}" for c, w in ch.items())


def main() -> None:
    sys.path.insert(0, str(PROJECTS / "mushaf"))
    from futuh.run import volume_pdf

    doc = pymupdf.open(volume_pdf(1))
    book = [json.loads(l) for l in FUTUH.open() if '"type": "row"' in l]
    items = json.loads((BUILD / "review.json").read_text())
    by_box = defaultdict(list)
    for it in items:
        by_box[it["box"]].append(it)
    arch = pymupdf.Archive(str(FONT.parent))
    css = f"@font-face {{font-family:q; src:url({FONT.name});}}"
    n = 0
    for k, (box, its) in enumerate(sorted(by_box.items(), key=lambda kv: kv[1][0]["from"])):
        rows = [r for r in book if r["group"] == box]
        pages = sorted({r["pdf_page"] for r in rows})
        out = pymupdf.open()
        W = 1100
        crops = []
        for pg in pages:
            ys = [b for r in rows if r["pdf_page"] == pg for w in r["words"] if w.get("bbox") for b in (w["bbox"][1], w["bbox"][3])]
            page = doc[pg - 1]
            crops.append((pg, pymupdf.Rect(page.rect.x0 + 20, min(ys) - 10, page.rect.x1 - 20, max(ys) + 10)))
        heights = [c.height / c.width * 640 for _, c in crops]
        qh = 80 + sum(30 + 18 * (len(it["missing"]) + len(it["shown"])) + 40 for it in its)
        H = max(sum(heights) + 20 * len(crops) + 40, qh)
        p = out.new_page(width=W, height=H)
        y = 30
        p.insert_text((10, 18), f"Box {k + 1}: {its[0]['from']}–{its[0]['to']} (al-Futūḥ vol. 1, pdf p. {', '.join(map(str, pages))})", fontsize=11)
        for (pg, clip), h in zip(crops, heights):
            p.show_pdf_page(pymupdf.Rect(10, y, 650, y + h), doc, pg - 1, clip=clip)
            y += h + 20
        qs = []
        for it in its:
            n += 1
            qs.append(f"<p style='margin:8px 0 2px 0'><b>Q{n}. {html.escape(NAMES[it['rawi']])}</b></p>"
                      + "".join(f"<p style='margin:0 0 0 12px;color:#060'>shown: {html.escape(fmt(c))}</p>" for c in it["shown"])
                      + "".join(f"<p style='margin:0 0 0 12px;color:#a00'>not shown: {html.escape(fmt(c))}</p>" for c in it["missing"])
                      + (f"<p style='margin:2px 0 0 12px;color:#555;font-style:italic'>C: {html.escape(note_for(it))}</p>" if note_for(it) else ""))
        p.insert_htmlbox(pymupdf.Rect(665, 30, W - 10, H - 10),
                         "<div style='font-family:sans-serif;font-size:11px'>" + "".join(qs) + "</div>", css=css, archive=arch)
        p.get_pixmap(dpi=100).save(BUILD / f"review-{k + 1:02d}.png")
    print(f"{len(by_box)} boxes, {n} questions -> {BUILD}/review-NN.png")


if __name__ == "__main__":
    main()
