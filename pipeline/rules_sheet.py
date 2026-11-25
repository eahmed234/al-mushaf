"""Review sheet for the uṣūl run's proposed categories (pipeline/categories_proposal.yaml).

    PYTHONPATH=.:../mushaf ../mushaf/.venv/bin/python -m pipeline.rules_sheet

Writes build/category_review.html and the cited pages as build/pages/BOOK-N.jpg (served beside
it). One section per proposed family: what it is, the names merged into it, and every rule in it
(book, page, readers, reading, where it applies, the words named, the page's own words); each
row opens its page. Mark the family (first row) and any rule ✓/✗ with a note; "Copy answers"
gives JSON. Rows to look at first are tagged: readers the page may not name, and pages that
seem to disagree.
"""
from __future__ import annotations

import html
import json
from collections import defaultdict
from pathlib import Path

import pymupdf
import yaml

from checks.sheets.review_profiles import RAWI_AR, TEMPLATE
from mushaf_data.paths import BOOKS, BUILD, ROOT
from mushaf_data.ruwat import RUWAT

from .validate import locate, pages

OUT = BUILD / "category_review.html"
IMG = BUILD / "pages"
NAMES = {"wafi": "الوافي", "idah": "الإيضاح"}
# rows the run's reports asked to look at (pipeline/PILOT.md, "The full uṣūl run")
WATCH = {("wafi", p) for p in (113, 124, 178)} | {("idah", 50), ("idah", 52), ("wafi", 146), ("wafi", 147), ("wafi", 82)}


def esc(s) -> str:
    return html.escape(str(s))


def render(book: str, n: int, docs: dict) -> str:
    f = IMG / f"{book}-{n}.jpg"
    if not f.exists():
        doc = docs.setdefault(book, pymupdf.open(BOOKS / f"{book}.pdf"))
        IMG.mkdir(parents=True, exist_ok=True)
        doc[n - 1].get_pixmap(matrix=pymupdf.Matrix(1.3, 1.3)).save(f, jpg_quality=70)
    return f"pages/{f.name}"


def who(rs: list[str], khulf: list[str]) -> str:
    if len(rs) >= 14 and set(rs) >= set(RUWAT[:14]):
        return "الجميع" + (" (والدرة)" if set(rs) == set(RUWAT) else "")
    return "، ".join(esc(RAWI_AR[x]) + (" <sup>خلف</sup>" if x in khulf else "") for x in rs)


def main():
    prop = yaml.safe_load((ROOT / "pipeline/categories_proposal.yaml").read_text(encoding="utf-8"))
    fam_of = {n: k for k, v in prop.items() for n in v["from"]}
    rows = defaultdict(list)
    for f in sorted((ROOT / "pipeline/out/rules").glob("*/p*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        for r in d["rows"]:
            c = str(r["category"])
            if c.startswith("new:") and c[4:] in fam_of:
                rows[fam_of[c[4:]]].append((d["book"], d["page"], r))
    docs, sections, n = {}, [], 0
    for fam, spec in prop.items():
        rs = sorted(rows[fam], key=lambda x: (x[0] != "wafi", x[1]))
        target = "new category" if spec.get("proposed") else f"into <code>{esc(spec['into'])}</code>"
        trs = [f'<tr data-id="family:{esc(fam)}" class="fam"><td colspan="3"><b>{esc(fam)}</b> — {target}<div class="en">'
               f'{esc(spec["what"])}</div><div class="en">merges: {esc(", ".join(spec["from"]))} · {len(rs)} rules</div></td>'
               f'<td class="mark"><label><input type="radio" name="family:{esc(fam)}" value="ok"> ✓</label>'
               f'<label><input type="radio" name="family:{esc(fam)}" value="wrong"> ✗</label>'
               f'<textarea placeholder="note on the family" rows="1"></textarea></td></tr>']
        for i, (book, pg, r) in enumerate(rs):
            span = locate(book, pg, r["quote"])
            quote = pages(book)[span[0]][span[1]:span[2]] if span else r["quote"]
            src = render(book, span[0] if span else pg, docs)
            tag = " watch" if (book, pg) in WATCH else ""
            rid = f"{fam}#{book}-{pg}-{i}"
            extra = []
            if r.get("applies"):
                extra.append(f"حيث: {esc(r['applies'])}")
            if r.get("words"):
                extra.append("الكلمات: " + esc("، ".join(r["words"][:12])) + (" …" if len(r["words"]) > 12 else ""))
            if r.get("except"):
                extra.append("يستثنى: " + esc("، ".join(r["except"][:8])))
            cond = {"waqf": " · وقفاً", "wasl": " · وصلاً"}.get(r["condition"], "")
            trs.append(
                f'<tr data-id="{esc(rid)}" class="{tag.strip()}"><td class="who">{esc(NAMES[book])} <a href="{src}" target="_blank">ص {pg}</a>'
                f'<div class="en">{esc(r["category"][4:])} · {esc(r["scope"])}{" · watch" if tag else ""}</div></td>'
                f'<td class="who">{who(r["readers"], r["khulf"])}</td>'
                f'<td class="wj"><div class="reading">{esc(r["reading"])}{cond}</div>'
                + "".join(f'<div class="ap">{x}</div>' for x in extra)
                + f'<div class="quote">«{esc(quote)}»</div></td>'
                f'<td class="mark"><label><input type="radio" name="{esc(rid)}" value="ok"> ✓</label>'
                f'<label><input type="radio" name="{esc(rid)}" value="wrong"> ✗</label>'
                f'<textarea placeholder="note" rows="1"></textarea></td></tr>')
            n += 1
        sections.append(f'<section id="{esc(fam)}"><h2>{esc(fam)} <span class="en">{len(rs)} rules</span></h2>'
                        f'<table><thead><tr><th>المصدر</th><th>الرواة</th><th>القاعدة</th><th>review</th></tr></thead>'
                        f'<tbody>{"".join(trs)}</tbody></table></section>')
    nav = "".join(f'<a href="#{esc(f)}">{esc(f)}</a>' for f in prop)
    intro = (f'<p class="intro">{len(prop)} proposed families for the {n} rules the uṣūl run of al-Wāfī and al-Īḍāḥ put in new '
             'categories (<code>pipeline/categories_proposal.yaml</code>). For each family: is it one rule, and is its name and '
             'scope right (mark the first row)? Mark any rule that is misread. Each rule links to its page. Rows tagged '
             '<span class="watchtag">watch</span> are the ones the run itself flagged: readers the page may not name, and pages '
             'that seem to disagree. Marks stay in this browser; “Copy answers” gives JSON to paste back.</p>')
    css = ("<style>.reading{font-size:17px}.ap{font:13px system-ui,sans-serif;color:var(--muted)}"
           ".quote{font-size:14px;color:var(--muted);margin-top:3px}tr.fam td{background:var(--tag)}"
           "tr.watch td:first-child{border-inline-start:4px solid var(--bad)}.watchtag{border-inline-start:4px solid var(--bad);padding:0 4px}"
           "section table{max-width:1200px}</style>")
    page = TEMPLATE.format(nav=nav, intro="", sections=intro + "".join(sections), n_rows=n, n_cats=len(prop), not_read="", imgs="{}")
    page = page.replace("<title>Profile review</title>", "<title>Category review</title>" + css)
    page = page.replace("مراجعة جدول الأصول", "مراجعة أبواب الأصول").replace('"profile-review-v1"', '"category-review-v1"')
    a, b = page.index('<p class="intro">'), page.index("<ul></ul>") + len("<ul></ul>")
    page = page[:a] + page[b:]
    page = page.replace('<a href="#durrah_rule">منهج الدرة</a>', "").replace('<div class="split">', "<div>")
    OUT.write_text(page, encoding="utf-8")
    print(f"{OUT}: {len(prop)} families, {n} rules, {len(list(IMG.glob('*.jpg')))} page images")


if __name__ == "__main__":
    main()
