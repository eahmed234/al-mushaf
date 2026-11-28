"""Review sheet for option text (data/farsh_text): each farsh word's texts beside the book's pages.

    PYTHONPATH=.:../mushaf ../mushaf/.venv/bin/python -m pipeline.farsh_text_sheet [--all]

Writes build/farsh_text_review.html. Each case shows the Ḥafṣ word in context, then one line per
text: the text, its ruwāt (khulf marked), the options it realises (the book's words, page), and what
KFGQPC says for the ruwāt it has a file for (✓ agree / ✗ differ, with KFGQPC's word). By default
only the texts no KFGQPC file confirms are listed (no reader with a file, or a reader that differs);
--all lists every case. Mark ✓/✗ with a note; "Copy answers" gives JSON to paste back.
"""
from __future__ import annotations

import argparse
import html
import json
import re

from checks.api import check
from checks.kfgqpc import FILES
from checks.sheets.review_profiles import RAWI_AR, TEMPLATE, page_img
from mushaf_data.api import Mushaf
from mushaf_data.paths import BUILD

from .farsh_text import WORK

OUT = BUILD / "farsh_text_review.html"


def esc(s) -> str:
    return html.escape(str(s))


def verdicts(suras) -> dict[tuple[str, str], tuple[str, str]]:
    m = Mushaf()
    out = {}
    for s in suras:
        for r in FILES:
            for slot, v in check(r, s, m)["status"].items():
                out[(slot, r)] = v
    return out


def build(show_all: bool = False) -> tuple[str, int]:
    import yaml
    from mushaf_data.paths import DATA
    cases = {c["key"]: c for c in json.loads((WORK / "keys.json").read_text(encoding="utf-8"))}
    texts = {}
    for f in sorted((DATA / "farsh_text").glob("*.yaml")):
        texts.update(yaml.safe_load(f.read_text(encoding="utf-8")) or {})
    suras = sorted({int(s.split(":")[0]) for s in texts})
    v = verdicts(suras)
    imgs, sections, n = {}, [], 0
    done = set()
    for slot, e in texts.items():
        if e["case"] in done:
            continue
        done.add(e["case"])
        c = cases[e["case"]]
        trs, need = [], False
        for i, g in enumerate(e["groups"]):
            checked = [(r, v.get((s, r))) for r in g["readers"] if r in FILES for s in c["slots"] if v.get((s, r))]
            ok = [r for r, x in checked if x[0] == "agree"]
            bad = [(r, x[1]) for r, x in checked if x[0] == "differ"]
            if g.get("text") is None or bad or (not ok and not g.get("base")):
                need = True
            who = "، ".join(esc(RAWI_AR[r]) + ("<sup>خلف</sup>" if r in (g.get("khulf") or []) else "") for r in g["readers"])
            kf = (" ".join(f'<span class="ok">✓ {esc(RAWI_AR[r])}</span>' for r in dict.fromkeys(ok))
                  + " ".join(f'<span class="bad">✗ {esc(RAWI_AR[r])}: {esc(k)}</span>' for r, k in bad)) \
                or '<span class="en">no KFGQPC file for these ruwāt</span>'
            frm = "<br>".join(esc(x) for x in g.get("from") or []) or ('<span class="en">the muṣḥaf\'s own</span>' if g.get("base") else "")
            note = f'<div class="quote">{esc(g["note"])}</div>' if g.get("note") else ""
            text = esc(g["text"]) if g.get("text") else '<span class="bad">no text</span>'
            trs.append(f'<tr data-id="{esc(e["case"])}#{i}"><td class="place">{text}</td><td class="who">{who}</td>'
                       f'<td class="reading">{frm}{note}<div class="quote">{kf}</div></td>'
                       f'<td class="rv"><button class="b-ok">✓</button><button class="b-bad">✗</button>'
                       f'<input class="note" placeholder="note"></td></tr>')
        if not (need or show_all):
            continue
        pages = []
        for o in c["options"]:
            m = re.match(r"(wafi|idah) (\d+)", o.get("cite") or "")
            if m and (m[1], int(m[2])) not in pages:
                pages.append((m[1], int(m[2])))
        figs = []
        for b, p in pages[:3]:
            k = f"{b}-{p}"
            if k not in imgs:
                imgs[k] = page_img(b, p)
            figs.append(f'<figure><figcaption>{"الوافي" if b == "wafi" else "الإيضاح"} ص {p}</figcaption>'
                        f'<img loading="lazy" data-src="{k}" alt="{b} p. {p}"></figure>')
        n += len(trs)
        sections.append(
            f'<section id="{esc(e["case"])}"><h2>{esc(c["hafs"])} <span class="en">{esc(", ".join(c["slots"][:6]))}'
            f'{" …" if len(c["slots"]) > 6 else ""}</span></h2><div class="quote">{esc(c["context"])}</div>'
            f'<div class="split"><table><thead><tr><th>النص</th><th>الرواة</th><th>القراءة</th><th>review</th></tr></thead>'
            f'<tbody>{"".join(trs)}</tbody></table><div class="pages">{"".join(figs)}</div></div></section>')
    nav = "".join(f'<a href="#{s.split(" id=")[1].split(chr(34))[1]}">{i + 1}</a>' for i, s in enumerate(sections))
    intro = (f'<p class="intro">{len(sections)} words, {n} texts. Each text is the word as those ruwāt read it, the farsh '
             "only (their uṣūl are added by the engine). ✓/✗ beside a rāwī: KFGQPC's text for him agrees or not "
             "(after his uṣūl). Listed: texts no KFGQPC file confirms. Mark ✓ or ✗ with a note; “Copy answers” gives "
             "JSON to paste back.</p>")
    css = ("<style>.place{font-size:22px}.quote{font-size:14px;color:var(--muted);margin-top:4px}"
           ".ok{color:var(--ok)}.bad{color:var(--bad)}</style>")
    page = TEMPLATE.format(nav=nav, intro="", sections=intro + "".join(sections), n_rows=n, n_cats=len(sections),
                           not_read="", imgs=json.dumps(imgs))
    page = page.replace("<title>Profile review</title>", "<title>Farsh text review</title>" + css)
    page = page.replace("مراجعة جدول الأصول", "مراجعة نصوص الفرش").replace('"profile-review-v1"', '"farsh-text-review-v1"')
    start, end = page.index('<p class="intro">'), page.index('<ul></ul>') + len("<ul></ul>")
    page = page[:start] + page[end:]
    page = page.replace('<a href="#durrah_rule">منهج الدرة</a>', "")
    return page, len(sections)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    page, n = build(a.all)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"{OUT}: {n} words, {OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
