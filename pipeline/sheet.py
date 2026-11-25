"""Review sheet for extracted rows: each page's rows beside the page itself.

    PYTHONPATH=.:../mushaf ../mushaf/.venv/bin/python -m pipeline.sheet DIR [--pages 16-25] [--against GOLD_DIR]

Writes build/extract_review.html. Each row shows the Ḥafṣ words of its place, the ruwāt (khulf
marked), kind and category, the reading, and the words of the page it was read from. With
--against, rows are tagged as agreeing with that set or not, and the other set's rows that have
no match are listed too. Mark each row ✓/✗ with a note; "Copy answers" gives JSON to paste back.
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from checks.sheets.review_profiles import CAT_AR, RAWI_AR, TEMPLATE, page_img
from mushaf_data.paths import BUILD
from mushaf_data.ruwat import RUWAT
from mushaf_data.spine import words

from .pack import parse_pages
from .score import match, rows, units
from .validate import pages as page_texts

OUT = BUILD / "extract_review.html"
# the waqf categories cover more than the profile review's section names say (Eisa, 2026-11-25)
CAT_AR = {**CAT_AR, "hamz_waqf_final": "وقفاً: الهمز المتطرف", "hamz_waqf_mid": "وقفاً: الهمز المتوسط",
          "sakt_al": "السكت على المفصول الخاص (أل وشيء)", "sakt_mafsul": "السكت على المفصول العام"}
KIND_AR = {"farsh": "فرش", "usul": "أصول", "tahrir": "تحرير", "ittifaq": "اتفاق"}
COND_AR = {"wasl": "وصلاً", "waqf": "وقفاً", None: ""}


def esc(s) -> str:
    return html.escape(str(s))


def row_html(rid: str, r: dict, tag: str = "") -> str:
    h = words()
    place = " ".join(esc(h.get(p, p)) for p in r["place"]) or esc(r.get("place_text", "—"))
    ids = esc(", ".join(r["place"]))
    if set(r["readers"]) == set(RUWAT):
        who = "الجميع"
    else:
        who = "، ".join(esc(RAWI_AR[x]) + (" <sup>خلف</sup>" if x in r["khulf"] else "") for x in r["readers"])
    what = KIND_AR[r["kind"]] + (f" · {esc(CAT_AR.get(r['category'], r['category']))}" if r["category"] else "")
    pg, a, b = r["span"]
    quote = page_texts("budur")[pg][a:b]
    return (f'<tr data-id="{esc(rid)}" class="{tag}"><td class="who"><div class="place">{place}</div><div class="en">{ids}</div></td>'
            f'<td class="who">{who}</td><td class="wj">{what} {esc(COND_AR[r["condition"]])}'
            f'{" · كل القرآن" if r["scope"] == "all" else ""}<div class="reading">{esc(r["reading"])}</div>'
            f'<div class="quote">«{esc(quote)}» <span class="en">p. {pg}</span></div>'
            f'{"<div class=tagline>" + esc(tag.replace("-", " ")) + "</div>" if tag else ""}</td>'
            f'<td class="mark"><label><input type="radio" name="{esc(rid)}" value="ok"> ✓</label>'
            f'<label><input type="radio" name="{esc(rid)}" value="wrong"> ✗</label>'
            f'<textarea placeholder="note" rows="1"></textarea></td></tr>')


def build(src: Path, pages: list[int], against: Path | None = None) -> str:
    mine, _ = rows(src, pages)
    other, _ = rows(against, pages) if against else ([], 0)
    agree = set()
    missing = []
    if against:
        gu = units([r for _, r in other])
        mu = units([r for _, r in mine])

        def fits(r, pool):  # every rāwī of the row matches a unit of the other set
            return not match(units([r]), pool)[1]
        agree = {id(r) for _, r in mine if fits(r, gu)}
        missing = [(p, r) for p, r in other if not fits(r, mu)]
    sections, imgs, n = [], {}, 0
    for pg in pages:
        trs = []
        for i, (p, r) in enumerate([x for x in mine if x[0] == pg]):
            tag = ("agrees" if id(r) in agree else "only-in-this-run") if against else ""
            trs.append(row_html(f"p{pg}#{i}", r, tag))
            n += 1
        for i, (p, r) in enumerate([x for x in missing if x[0] == pg]):
            trs.append(row_html(f"p{pg}#missing{i}", r, "only-in-the-gold-set"))
            n += 1
        imgs[f"budur-{pg}"] = page_img("budur", pg)
        body = "".join(trs) or '<tr><td colspan="4" class="en">no rows on this page</td></tr>'
        sections.append(
            f'<section id="p{pg}"><h2>البدور الزاهرة ص {pg}</h2><div class="split"><table><thead><tr><th>الموضع</th>'
            f'<th>الرواة</th><th>القراءة</th><th>review</th></tr></thead><tbody>{body}</tbody></table>'
            f'<div class="pages"><figure><figcaption>p. {pg}</figcaption><img loading="lazy" data-src="budur-{pg}" '
            f'alt="al-Budūr p. {pg}"></figure></div></div></section>')
    nav = "".join(f'<a href="#p{p}">ص {p}</a>' for p in pages)
    intro = (f'<p class="intro">{n} rows from <code>{esc(src)}</code>'
             + (f', compared with <code>{esc(against)}</code>' if against else "") + ". Each row: the place (Ḥafṣ "
             "words), the ruwāt (<sup>خلف</sup>: one of their wujūh), what kind of statement, the reading in the book's "
             "words, and the words of the page it was read from. Mark ✓ or ✗ with a note; marks stay in this "
             "browser; “Copy answers” gives JSON to paste back.</p>")
    extra_css = ("<style>.place{font-size:18px}.reading{margin-top:2px}.quote{font-size:14px;color:var(--muted);margin-top:4px}"
                 "tr.agrees td:first-child{border-inline-start:4px solid var(--ok)}"
                 "tr.only-in-this-run td:first-child,tr.only-in-the-gold-set td:first-child{border-inline-start:4px solid var(--bad)}"
                 ".tagline{font:12px system-ui,sans-serif;color:var(--bad);direction:ltr;text-align:left}</style>")
    page = TEMPLATE.format(nav=nav, intro="", sections=intro + "".join(sections), n_rows=n, n_cats=len(pages),
                           not_read="", imgs=json.dumps(imgs))
    page = page.replace("<title>Profile review</title>", "<title>Extraction review</title>" + extra_css)
    page = page.replace("مراجعة جدول الأصول", "مراجعة الاستخراج").replace('"profile-review-v1"', f'"extract-review-{src.name}"')
    # the profile sheet's fixed intro and Durrah link don't apply here
    start, end = page.index('<p class="intro">'), page.index('<ul></ul>') + len("<ul></ul>")
    page = page[:start] + page[end:]
    page = page.replace('<a href="#durrah_rule">منهج الدرة</a>', "")
    if against:  # a switch to show only the rows the two sets disagree on
        page = page.replace('<button id="copy">', '<label class="en" style="cursor:pointer"><input type="checkbox" id="diff"> '
                            'differences only</label><button id="copy">')
        page = page.replace("count();\n</script>", 'count();\ndocument.getElementById("diff").addEventListener("change", e => '
                            'document.querySelectorAll("tr.agrees").forEach(tr => tr.style.display = e.target.checked ? "none" : ""));\n</script>')
    return page


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--pages", default="16-25")
    ap.add_argument("--against", default=None)
    a = ap.parse_args()
    out = build(Path(a.dir), parse_pages(a.pages), Path(a.against) if a.against else None)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(out, encoding="utf-8")
    print(f"{OUT}: {OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
