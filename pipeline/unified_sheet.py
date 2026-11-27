"""Review sheet for the unified category tables (pipeline/out/unified/*.yaml): each category as one
rule for all twenty ruwāt, in one vocabulary.

    python3 -m pipeline.unified_sheet      → build/unified_review.html (same server as the other sheets)

Per category: its wujūh (the vocabulary), one grid per case (the ten qurrāʾ, both ruwāt, the
Shāṭibiyyah and the Durrah together; hover a cell for its source; ‹أصل› = read as the Durrah rāwī's
aṣl), the listed words, the open questions (each markable), and the reviewed profile rows beside
it. Mark the category, a case or an open question ✓/✗ with a note; "Copy answers" gives JSON.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

import yaml

from mushaf_data.paths import BUILD, ROOT

from .rules_sheet import PAGE, marks

OUT = BUILD / "unified_review.html"
QURRA = [("نافع", "qalun", "warsh"), ("ابن كثير", "bazzi", "qunbul"), ("أبو عمرو", "duri_abuamr", "susi"),
         ("ابن عامر", "hisham", "ibn_dhakwan"), ("عاصم", "shuba", "hafs"), ("حمزة", "khalaf_an_hamzah", "khallad"),
         ("الكسائي", "abul_harith", "duri_kisai"), ("أبو جعفر", "ibn_wardan", "ibn_jammaz"), ("يعقوب", "ruways", "rawh"),
         ("خلف العاشر", "ishaq", "idris")]
NAME = {"qalun": "قالون", "warsh": "ورش", "bazzi": "البزي", "qunbul": "قنبل", "duri_abuamr": "الدوري", "susi": "السوسي",
        "hisham": "هشام", "ibn_dhakwan": "ابن ذكوان", "shuba": "شعبة", "hafs": "حفص", "khalaf_an_hamzah": "خلف",
        "khallad": "خلاد", "abul_harith": "أبو الحارث", "duri_kisai": "الدوري", "ibn_wardan": "ابن وردان",
        "ibn_jammaz": "ابن جماز", "ruways": "رويس", "rawh": "روح", "ishaq": "إسحاق", "idris": "إدريس"}
VIA = {"asl": "أصل", "wasl": "كالوصل", "model_qalun": "كقالون", "model_yaqub": "كيعقوب"}


def esc(s) -> str:
    return html.escape(str(s))


import re

_DOCS: dict = {}
PAGE_REF = re.compile(r"\b(wafi|idah|budur)\s+(\d+)(?:\s*[-–]\s*(\d+))?")


def page_link(book: str, n: int) -> str:
    """build/pages/BOOK-N.jpg, rendered once (needs pymupdf: run with the sheet environment)."""
    from mushaf_data.paths import BOOKS
    f = BUILD / "pages" / f"{book}-{n}.jpg"
    if not f.exists():
        import pymupdf
        doc = _DOCS.setdefault(book, pymupdf.open(BOOKS / f"{book}.pdf"))
        f.parent.mkdir(parents=True, exist_ok=True)
        doc[n - 1].get_pixmap(matrix=pymupdf.Matrix(1.3, 1.3)).save(f, jpg_quality=70)
    return f"pages/{f.name}"


def linked(text: str) -> str:
    out, last = [], 0
    for m in PAGE_REF.finditer(text):
        out.append(esc(text[last:m.start()]))
        book, a, b = m.group(1), int(m.group(2)), m.group(3)
        links = [f'<a href="{page_link(book, n)}" target="_blank">{n}</a>' for n in range(a, (int(b) if b else a) + 1)][:6]
        out.append(f"{book} " + "–".join(links) if b else f'<a href="{page_link(book, a)}" target="_blank">{esc(m.group(0))}</a>')
        last = m.end()
    out.append(esc(text[last:]))
    return "".join(out)


def cell(v: dict | None, label: dict) -> str:
    v = v or {}
    ws = v.get("wujuh") or []
    tip = " · ".join(str(c) for c in (v.get("cite") or [])) + (f" · via {v['via']}" if v.get("via") else "")
    if not ws:
        return '<span class="none">غير مذكور</span>'
    via = f'<span class="via">{esc(VIA.get(v.get("via"), v.get("via")))}</span>' if v.get("via") else ""
    return f'<span class="w" title="{esc(tip)}">{" / ".join(esc(label.get(w, w)) for w in ws)}</span>{via}'


def grid(ruwat: dict, label: dict) -> str:
    rows = "".join(f'<tr><th>{q}</th><td><small>{NAME[a]}</small> {cell(ruwat.get(a), label)}</td>'
                   f'<td><small>{NAME[b]}</small> {cell(ruwat.get(b), label)}</td></tr>' for q, a, b in QURRA)
    return f'<table class="grid">{rows}</table>'


def main():
    sections, n = [], 0
    pol = yaml.safe_load((ROOT / "pipeline/open_sort.yaml").read_text(encoding="utf-8"))["policies"]
    items = "".join(f'<article class="rule open" id="policy-{esc(k)}" data-id="policy:{esc(k)}"><p class="q">{linked(p["q"])}</p>'
                    f'<p class="note">Settles: {esc(", ".join(p["covers"]))}</p><div class="foot">{marks("policy:" + k, "الجواب")}</div></article>'
                    for k, p in pol.items())
    sections.append(f'<details class="family" id="policies" open><summary><span class="fname">policies</span>'
                    f'<span class="ftarget">{len(pol)} أسئلة، كل منها يحسم عدة أبواب</span><span class="fcount"></span></summary>{items}</details>')
    n += len(pol)
    for f in sorted((ROOT / "data/usul").glob("*.yaml")):
        t = yaml.safe_load(f.read_text(encoding="utf-8"))
        cat = t.get("category", f.stem)
        wf = ROOT / "pipeline/work/unify" / f"{f.stem}.json"
        src = json.loads(wf.read_text(encoding="utf-8")) if wf.exists() else {"head": {}}
        label = {w["id"]: w.get("ar") or w["id"] for w in t.get("wujuh") or []}
        vocab = "".join(f'<span class="chip" title="{esc(w.get("en", ""))}">{esc(w.get("ar", w["id"]))} <code>{esc(w["id"])}</code></span>'
                        for w in t.get("wujuh") or [])
        parts = [f'<div class="fbody" data-id="cat:{esc(cat)}"><p class="what">{esc(t.get("what", ""))}</p>'
                 f'<div class="vocab">{vocab}</div><div class="famq">الباب كما هو؟ {marks("cat:" + cat, "ملاحظة على الباب")}</div></div>']
        for i, case in enumerate(t.get("cases") or []):
            cid = f"{cat}#case{i}"
            parts.append(f'<article class="rule" data-id="{esc(cid)}"><div class="head"><span class="who">{esc(case.get("case", ""))}</span></div>'
                         f'{grid(case.get("ruwat") or {}, label)}'
                         + (f'<p class="note">{esc(case["note"])}</p>' if case.get("note") else "")
                         + f'<div class="foot">{marks(cid)}</div></article>')
            n += 1
        listed = t.get("listed") or []
        if listed:
            items = "".join(
                f'<li><b>{esc("، ".join(map(str, x.get("words") or [])))}</b>'
                + (f' <span class="sub">({esc(x["case"])})</span>' if x.get("case") else "")
                + ": " + ("؛ ".join(f'{esc(NAME.get(r, r))} {esc(" / ".join(label.get(w, w) for w in (ws or [])))}' for r, ws in (x.get("ruwat") or {}).items()) or "—")
                + f' <span class="src">{esc(" · ".join(map(str, x.get("cite") or [])))}</span></li>' for x in listed)
            parts.append(f'<details class="listed"><summary>الكلمات المذكورة ({len(listed)})</summary><ul>{items}</ul></details>')
        dis = t.get("disagreements") or []
        if dis:
            items = "".join(f'<li>{esc(NAME.get(d.get("rawi"), d.get("words", "")))}: {esc(d.get("case") or "")} — '
                            f'table {esc("/".join(map(str, d.get("table") or [])) if isinstance(d.get("table"), list) else d.get("table"))}, '
                            f'reviewed {esc("/".join(map(str, d.get("reviewed") or [])))} → kept <b>{esc(d.get("kept"))}</b></li>' for d in dis)
            parts.append(f'<details class="listed"><summary>الخلاف مع الجدول المراجَع ({len(dis)})</summary><ul class="en-list">{items}</ul></details>')
        for q in t.get("questions") or []:
            if q.get("policy"):
                continue  # answered once at the top
            parts.append(f'<article class="rule open" data-id="{esc(q["id"])}"><p class="q">{linked(q["q"])}</p>'
                         f'<details class="was"><summary>the original note</summary><p class="note">{linked(q["from"])}</p></details>'
                         f'<div class="foot">{marks(q["id"], "الجواب")}</div></article>')
            n += 1
        pol = [q for q in t.get("questions") or [] if q.get("policy")]
        if pol:
            parts.append('<p class="note">Settled by a policy question at the top: '
                         + ", ".join(f'<a href="#policy-{esc(q["policy"])}">{esc(q["policy"])}</a>' for q in pol) + "</p>")
        if t.get("gaps"):
            parts.append(f'<details class="listed"><summary>pages being re-read ({len(t["gaps"])})</summary><ul class="en-list">'
                         + "".join(f'<li>{linked(g["reread"])}</li>' for g in t["gaps"]) + "</ul></details>")
        if t.get("notes"):
            parts.append(f'<details class="listed"><summary>notes ({len(t["notes"])})</summary><ul class="en-list">'
                         + "".join(f'<li>{linked(str(x))}</li>' for x in t["notes"]) + "</ul></details>")
        prof = src["head"].get("reviewed_profile_rows") or {}
        if prof:
            rows = "".join(f'<li><code>{esc(p)}</code>: ' + "؛ ".join(
                f'{esc(r["who"] if isinstance(r["who"], str) else "، ".join(NAME.get(x, x) for x in r["who"]))} → {esc("/".join(r.get("wujuh") or []))} ({esc(r.get("cite", ""))})'
                for r in rs) + "</li>" for p, rs in prof.items())
            parts.append(f'<details class="listed"><summary>جدول الأصول المراجَع (للمقارنة)</summary><ul>{rows}</ul></details>')
        n_open = len([q for q in t.get("questions") or [] if not q.get("policy")])
        sections.append(f'<details class="family" id="{esc(cat)}"><summary><span class="fname">{esc(cat)}</span>'
                        f'<span class="ftarget">{len(t.get("cases") or [])} حالات · {len(listed)} كلمات · {n_open} أسئلة</span>'
                        f'<span class="fcount"></span></summary>{"".join(parts)}</details>')
    nav = "".join(f'<a href="#{esc(f.stem)}" data-nav="{esc(f.stem)}">{esc(f.stem)}</a>'
                  for f in sorted((ROOT / "data/usul").glob("*.yaml")))
    css = """<style>
.grid{border-collapse:collapse;width:100%;margin:6px 0;font-size:16px}.grid th{font-weight:600;color:var(--muted);text-align:right;padding:3px 8px;width:7em;font-size:15px}
.grid td{padding:3px 8px;border-top:1px solid var(--line)}.grid small{color:var(--muted);font:12px system-ui,sans-serif;display:inline-block;min-width:5.5em}
.w{color:var(--fg)}.none{color:var(--line);font-size:14px}.via{font:11px system-ui,sans-serif;color:var(--accent);border:1px solid var(--accent);border-radius:8px;padding:0 5px;margin-inline-start:6px}
.vocab{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 10px}.chip{background:var(--quote);border-radius:12px;padding:1px 10px;font-size:15px}.chip code{font-size:11px;color:var(--muted)}
.listed{padding:6px 18px;border-bottom:1px solid var(--line)}.listed summary{padding:4px 0;font-size:16px;color:var(--accent)}.listed ul{margin:4px 0 8px;padding-inline-start:20px;font-size:16px}
.listed .src,.listed .sub{font:12px system-ui,sans-serif;color:var(--muted)}.en-list{direction:ltr;text-align:left;font:13px system-ui,sans-serif}.rule.open .q a{color:var(--accent)}.rule.open .q{font:15px/1.6 system-ui,sans-serif;direction:ltr;text-align:left;margin:0 0 6px}
.rule.open{background:color-mix(in srgb,var(--accent) 4%,transparent)}.note{font:13px system-ui,sans-serif;color:var(--muted);direction:ltr;text-align:left}
</style>"""
    page = (PAGE.replace("{NAV}", nav).replace("{SECTIONS}", "".join(sections)).replace("{N}", str(n)).replace("{F}", str(len(sections)))
            .replace("<title>Category review</title>", "<title>Unified uṣūl</title>" + css)
            .replace("مراجعة أبواب الأصول", "الأصول موحّدة: الشاطبية والدرة").replace("أبواب مقترحة", "باباً")
            .replace('"category-review-v1"', '"usul-open-v1"')
            .replace('<label><input type="checkbox" id="watchonly"> «راجِع» فقط</label>', '<label><input type="checkbox" id="watchonly"> الأسئلة فقط</label>'))
    page = page.replace('r.style.display=e.target.checked&&!r.classList.contains("watch")?"none":""', 'r.style.display=e.target.checked&&!r.classList.contains("open")?"none":""')
    page = page.replace('if(d.querySelector(".rule.watch"))d.open=true', 'if(d.querySelector(".rule.open"))d.open=true')
    OUT.write_text(page, encoding="utf-8")
    print(f"{OUT}: {len(sections)} categories, {n} markable items")


if __name__ == "__main__":
    main()
