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

from checks.sheets.review_profiles import RAWI_AR
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
        target = "تصنيف جديد" if spec.get("proposed") else f"يُضم إلى <code>{esc(spec['into'])}</code>"
        cards = []
        for i, (book, pg, r) in enumerate(rs):
            span = locate(book, pg, r["quote"])
            quote = pages(book)[span[0]][span[1]:span[2]] if span else r["quote"]
            src = render(book, span[0] if span else pg, docs)
            watch = (book, pg) in WATCH
            rid = f"{fam}#{book}-{pg}-{i}"
            facts = []
            if r.get("applies"):
                facts.append(f"<dt>حيث</dt><dd>{esc(r['applies'])}</dd>")
            if r.get("words"):
                facts.append("<dt>الكلمات</dt><dd>" + esc("، ".join(r["words"][:14])) + (" …" if len(r["words"]) > 14 else "") + "</dd>")
            if r.get("except"):
                facts.append("<dt>يستثنى</dt><dd>" + esc("، ".join(r["except"][:10])) + "</dd>")
            cond = {"waqf": "وقفاً", "wasl": "وصلاً"}.get(r["condition"], "")
            cards.append(
                f'<article class="rule{" watch" if watch else ""}" data-id="{esc(rid)}">'
                f'<div class="head"><span class="who">{who(r["readers"], r["khulf"])}</span>'
                f'<a class="src" href="{src}" target="_blank">{esc(NAMES[book])} ص {pg}</a></div>'
                f'<p class="reading">{esc(r["reading"])}{f" <span class=cond>{cond}</span>" if cond else ""}</p>'
                + (f'<dl>{"".join(facts)}</dl>' if facts else "")
                + f'<blockquote>{esc(quote)}</blockquote>'
                f'<div class="foot"><span class="meta">{esc(r["category"][4:])} · {esc(r["scope"])}{" · <b>راجِع</b>" if watch else ""}</span>'
                f'{marks(rid)}</div></article>')
            n += 1
        sections.append(
            f'<details class="family" id="{esc(fam)}"><summary><span class="fname">{esc(fam)}</span>'
            f'<span class="ftarget">{target}</span><span class="fcount" data-fam="{esc(fam)}">{len(rs)}</span></summary>'
            f'<div class="fbody" data-id="family:{esc(fam)}"><p class="what">{esc(spec["what"])}</p>'
            f'<p class="merges">يجمع: {esc("، ".join(spec["from"]))}</p>'
            f'<div class="famq">هل هذا باب واحد، واسمه ونطاقه صحيحان؟ {marks("family:" + fam, "ملاحظة على الباب")}</div></div>'
            f'{"".join(cards)}</details>')
    nav = "".join(f'<a href="#{esc(f)}" data-nav="{esc(f)}">{esc(f)}</a>' for f in prop)
    OUT.write_text(PAGE.replace("{NAV}", nav).replace("{SECTIONS}", "".join(sections)).replace("{N}", str(n))
                   .replace("{F}", str(len(prop))), encoding="utf-8")
    print(f"{OUT}: {len(prop)} families, {n} rules, {len(list(IMG.glob('*.jpg')))} page images")


def marks(rid: str, placeholder: str = "ملاحظة") -> str:
    return (f'<span class="marks"><label class="ok"><input type="radio" name="{esc(rid)}" value="ok">✓</label>'
            f'<label class="no"><input type="radio" name="{esc(rid)}" value="wrong">✗</label>'
            f'<textarea rows="1" placeholder="{placeholder}"></textarea></span>')


PAGE = """<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Category review</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Noto+Naskh+Arabic:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{--bg:#f6f3ec;--card:#fffdf8;--fg:#24211c;--muted:#7a7366;--line:#e6dfd1;--accent:#2f6b5a;--ok:#2e7d4f;--bad:#b4472f;--quote:#f1ece1}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#1b1a17;--card:#24221e;--fg:#ece6da;--muted:#9c9485;--line:#38342d;--accent:#8cc4b1;--ok:#73c495;--bad:#e08a72;--quote:#2c2a25}}
:root[data-theme=dark]{--bg:#1b1a17;--card:#24221e;--fg:#ece6da;--muted:#9c9485;--line:#38342d;--accent:#8cc4b1;--ok:#73c495;--bad:#e08a72;--quote:#2c2a25}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:18px/1.9 "Noto Naskh Arabic","Amiri",serif}
header{position:sticky;top:0;z-index:3;background:var(--bg);border-bottom:1px solid var(--line);padding:10px 20px;display:flex;gap:14px;align-items:center;flex-wrap:wrap}
header h1{font-size:19px;margin:0;font-weight:600}.sub{font:13px system-ui,sans-serif;color:var(--muted)}
header .tools{margin-inline-start:auto;display:flex;gap:10px;align-items:center;font:13px system-ui,sans-serif}
button{font:13px system-ui,sans-serif;padding:6px 12px;border-radius:7px;border:1px solid var(--accent);background:var(--accent);color:var(--bg);cursor:pointer}
button.ghost{background:transparent;color:var(--accent)}
nav{padding:8px 20px 12px;display:flex;flex-wrap:wrap;gap:6px;font:13px system-ui,sans-serif;direction:ltr;border-bottom:1px solid var(--line)}
nav a{color:var(--muted);text-decoration:none;padding:2px 8px;border-radius:12px;border:1px solid var(--line)}nav a.done{color:var(--ok);border-color:var(--ok)}
main{max-width:860px;margin:0 auto;padding:16px 16px 80px}
.family{background:var(--card);border:1px solid var(--line);border-radius:12px;margin:14px 0;overflow:hidden}
summary{cursor:pointer;padding:14px 18px;display:flex;gap:12px;align-items:baseline;list-style:none}summary::-webkit-details-marker{display:none}
summary::before{content:"◂";color:var(--muted);font-size:14px}details[open] summary::before{content:"▾"}
.fname{font:600 16px system-ui,sans-serif;direction:ltr}.ftarget{color:var(--muted);font-size:15px}.ftarget code{font-size:13px}
.fcount{margin-inline-start:auto;font:12px system-ui,sans-serif;color:var(--muted)}
.fbody{padding:4px 18px 14px;border-bottom:1px solid var(--line)}.what{font:15px/1.6 system-ui,sans-serif;direction:ltr;text-align:left;margin:4px 0}
.merges{font:12px system-ui,sans-serif;color:var(--muted);direction:ltr;text-align:left;margin:0 0 8px}
.famq{display:flex;gap:10px;align-items:center;flex-wrap:wrap;font-size:16px}
.rule{padding:14px 18px;border-bottom:1px solid var(--line)}.rule:last-child{border-bottom:0}
.rule.watch{border-inline-start:4px solid var(--bad)}.rule.ok{background:color-mix(in srgb,var(--ok) 7%,transparent)}.rule.wrong{background:color-mix(in srgb,var(--bad) 9%,transparent)}
.head{display:flex;gap:12px;align-items:baseline}.who{font-weight:600;color:var(--accent)}.who sup{font-weight:400;color:var(--muted);font-size:11px}
.src{margin-inline-start:auto;font:13px system-ui,sans-serif;color:var(--muted);white-space:nowrap}
.reading{font-size:21px;margin:4px 0 6px}.cond{font-size:14px;color:var(--muted);border:1px solid var(--line);border-radius:10px;padding:0 8px}
dl{display:grid;grid-template-columns:auto 1fr;gap:2px 12px;margin:0 0 8px;font-size:16px}dt{color:var(--muted)}dd{margin:0}
blockquote{margin:6px 0 8px;padding:8px 14px;background:var(--quote);border-radius:8px;font-size:16px;color:var(--muted);line-height:1.8}
.foot{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.meta{font:11px system-ui,sans-serif;color:var(--muted);direction:ltr}
.marks{margin-inline-start:auto;display:flex;gap:6px;align-items:center}
.marks label{cursor:pointer;font:15px system-ui,sans-serif;border:1px solid var(--line);border-radius:8px;padding:2px 10px}
.marks input{display:none}.marks label.ok:has(input:checked){background:var(--ok);color:var(--bg);border-color:var(--ok)}
.marks label.no:has(input:checked){background:var(--bad);color:var(--bg);border-color:var(--bad)}
.marks textarea{font:13px system-ui,sans-serif;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:6px;width:190px;padding:4px}
@media (max-width:600px){.marks{margin-inline-start:0;width:100%}.marks textarea{flex:1}}
</style></head><body>
<header><h1>مراجعة أبواب الأصول</h1><span class="sub">{F} أبواب مقترحة · {N} قاعدة</span>
<span class="tools"><span class="sub" id="count"></span><label><input type="checkbox" id="watchonly"> «راجِع» فقط</label>
<button class="ghost" id="theme">☾/☀</button><button id="copy">Copy answers</button></span></header>
<nav>{NAV}</nav><main>{SECTIONS}</main>
<script>
const KEY="category-review-v1";let state={};try{state=JSON.parse(localStorage.getItem(KEY)||"{}")}catch(e){}
function save(){try{localStorage.setItem(KEY,JSON.stringify(state))}catch(e){}count()}
function count(){const all=document.querySelectorAll("[data-id]").length;const done=Object.values(state).filter(v=>v.mark).length;
 document.getElementById("count").textContent=done+" / "+all;
 document.querySelectorAll("nav a").forEach(a=>{const f=a.dataset.nav;a.classList.toggle("done",!!(state["family:"+f]||{}).mark)})}
document.querySelectorAll("[data-id]").forEach(el=>{const id=el.dataset.id,s=state[id]||{},ta=el.querySelector("textarea");
 const own=[...el.querySelectorAll("input")].filter(i=>i.name===id);
 if(s.mark){el.classList.add(s.mark);own.forEach(i=>{if(i.value===s.mark)i.checked=true})}if(s.note&&ta)ta.value=s.note;
 own.forEach(i=>i.addEventListener("change",()=>{state[id]={...(state[id]||{}),mark:i.value};el.classList.remove("ok","wrong");el.classList.add(i.value);save()}));
 if(ta)ta.addEventListener("input",()=>{state[id]={...(state[id]||{}),note:ta.value};save()})});
document.getElementById("watchonly").addEventListener("change",e=>{document.querySelectorAll(".rule").forEach(r=>r.style.display=e.target.checked&&!r.classList.contains("watch")?"none":"");
 if(e.target.checked)document.querySelectorAll("details").forEach(d=>{if(d.querySelector(".rule.watch"))d.open=true})});
document.querySelectorAll("nav a").forEach(a=>a.addEventListener("click",()=>{const d=document.getElementById(a.dataset.nav);if(d)d.open=true}));
if(location.hash){const d=document.getElementById(location.hash.slice(1));if(d)d.open=true}
document.getElementById("theme").addEventListener("click",()=>{const r=document.documentElement;const dark=r.dataset.theme?r.dataset.theme==="dark":matchMedia("(prefers-color-scheme: dark)").matches;r.dataset.theme=dark?"light":"dark";try{localStorage.setItem(KEY+"-theme",r.dataset.theme)}catch(e){}});
try{const t=localStorage.getItem(KEY+"-theme");if(t)document.documentElement.dataset.theme=t}catch(e){}
document.getElementById("copy").addEventListener("click",async()=>{const out=JSON.stringify(state,null,1);try{await navigator.clipboard.writeText(out);document.getElementById("copy").textContent="Copied"}catch(e){prompt("Copy:",out)}});
count();
</script></body></html>"""


if __name__ == "__main__":
    main()
