"""Review sheet for the book profile table: each category's rows beside the book pages they cite.

    PYTHONPATH=../mushaf ../mushaf/.venv/bin/python -m spike.review_profiles

Writes build/profile_review.html (one file, pages embedded as JPEG). Each row can be marked
right / wrong with a note; "Copy answers" gives JSON to paste back.
"""
import base64
import html
import json
import re
from pathlib import Path

import pymupdf
import yaml

from .rows import RUWAT

ROOT = Path(__file__).resolve().parent.parent
BOOKS = ROOT / "books"
OUT = Path(__file__).parent / "build" / "profile_review.html"
TABLE = Path(__file__).parent / "data" / "profiles.yaml"

BOOK_NAMES = {"wafi": "الوافي", "idah": "الإيضاح", "budur": "البدور الزاهرة", "ghayth-1": "غيث النفع"}
RAWI_AR = dict(zip(RUWAT, ["قالون", "ورش", "البزي", "قنبل", "الدوري (أبو عمرو)", "السوسي", "هشام",
                           "ابن ذكوان", "شعبة", "حفص", "خلف (عن حمزة)", "خلاد", "أبو الحارث",
                           "الدوري (الكسائي)", "ابن وردان", "ابن جماز", "رويس", "روح", "إسحاق", "إدريس"]))
WAJH_AR = {
    "qasr": "قصر", "tawassut": "توسط", "ishba": "إشباع", "tul": "طول", "silah": "صلة", "sukun": "إسكان",
    "none": "ترك", "ibdal": "إبدال", "tahqiq": "تحقيق", "naql": "نقل", "sakt": "سكت", "idgham": "إدغام",
    "izhar": "إظهار", "ghunna": "بغنة", "bila_ghunna": "بلا غنة", "tashil": "تسهيل",
    "tashil_idkhal": "تسهيل مع الإدخال", "tahqiq_idkhal": "تحقيق مع الإدخال", "fath": "فتح",
    "taqlil": "تقليل", "imala": "إمالة", "tafkhim": "تفخيم", "tarqiq": "ترقيق", "taghliz": "تغليظ",
    "hadhf": "حذف", "ibdal_ya": "إبدال ياء", "isqat_ula": "إسقاط الأولى", "tashil_thaniya": "تسهيل الثانية",
    "ibdal_thaniya": "إبدال الثانية", "taghyir_thaniya": "تغيير الثانية", "ibdal_madd": "إبدال مع المد",
    "ibdal_qasr": "إبدال مع القصر", "tashil_rawm_madd": "تسهيل بالروم مع المد",
    "tashil_rawm_qasr": "تسهيل بالروم مع القصر",
}
CAT_AR = {
    "munfasil": "المد المنفصل", "muttasil": "المد المتصل", "badal": "مد البدل", "lin_hamz": "مد اللين المهموز",
    "silah_mim": "صلة ميم الجمع قبل متحرك", "silah_mim_hamza": "صلة ميم الجمع قبل همز القطع",
    "silah_ha": "صلة هاء الكناية", "ibdal_sakin": "إبدال الهمز الساكن", "naql": "النقل",
    "sakt_al": "السكت على أل وشيء", "sakt_mafsul": "السكت على المفصول", "idgham_kabir": "الإدغام الكبير",
    "idgham_ghunna": "الغنة في الواو والياء", "hamzatayn": "الهمزتان من كلمة",
    "hamzatayn_kalimatayn_muttafiq": "الهمزتان من كلمتين: المتفقتان",
    "hamzatayn_kalimatayn_mukhtalif": "الهمزتان من كلمتين: المختلفتان",
    "imala_ra": "الألف قبل راء متطرفة مكسورة", "imala_kafirin": "كافرين", "imala_nas": "الناس المجرور",
    "imala_ya": "ذوات الياء", "imala_jaa_shaa": "جاء وشاء", "imala_zad": "زاد",
    "imala_fiil": "خاب خاف طاب ضاق حاق زاغ", "imala_duri_kisai": "ما انفرد بإمالته الدوري عن الكسائي",
    "hadhf_damm": "حذف الهمزة المضمومة بعد كسر", "sakt_huruf": "السكت على حروف الهجاء",
    "tarqiq_ra": "ترقيق الراءات", "taghliz_lam": "تغليظ اللامات",
    "ibdal_sakin_waqf": "وقفاً: الهمز الساكن", "hamzatayn_waqf": "وقفاً: الهمزتان من كلمة",
    "hamz_waqf_zaid": "وقفاً: المتوسط بزائد", "hamz_waqf_final": "وقفاً: المتطرف بعد ألف",
    "hamz_waqf_mid": "وقفاً: المتوسط المتحرك بعد متحرك",
}
SKIP_PAGES = {("idah", p) for p in range(40, 44)}  # the Durrah rule, shown once at the top


def parse_cite(cite):
    """'wafi 84, 89; budur 22' -> [('wafi', 84), ('wafi', 89), ('budur', 22)]."""
    out = []
    for part in str(cite).split(";"):
        part = re.sub(r"\bn\. ?\d+", "", part).strip()
        m = re.match(r"([a-z\-0-9]+?)\s+(.*)", part)
        if not m or m.group(1) not in BOOK_NAMES:
            continue
        for rng in m.group(2).split(","):
            nums = [int(x) for x in re.findall(r"\d+", rng)]
            if len(nums) == 1:
                out.append((m.group(1), nums[0]))
            elif len(nums) == 2:
                out += [(m.group(1), p) for p in range(nums[0], nums[1] + 1)]
    return out


_DOCS = {}


def page_img(book, n, zoom=1.35):
    doc = _DOCS.setdefault(book, pymupdf.open(BOOKS / f"{book}.pdf"))
    pix = doc[n - 1].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
    return base64.b64encode(pix.tobytes("jpg", jpg_quality=72)).decode()


def esc(s):
    return html.escape(str(s))


def main():
    data = yaml.safe_load(TABLE.read_text(encoding="utf-8"))
    seven = RUWAT[:14]
    sections, imgs, n_rows = [], {}, 0

    def figure(book, p):
        key = f"{book}-{p}"
        if key not in imgs:
            imgs[key] = page_img(book, p)
        return (f'<figure><figcaption>{esc(BOOK_NAMES[book])} ص {p}</figcaption>'
                f'<img loading="lazy" data-src="{key}" alt="{esc(book)} p. {p}"></figure>')

    for cat, rows in data["categories"].items():
        seen, trs, pages = [], [], []
        for i, row in enumerate(rows):
            who = row["who"]
            if who == "rest7":
                who = [r for r in seven if r not in seen]
            elif who == "rest_as_wasl":
                who = [r for r in RUWAT if r not in seen]
            seen += who
            rid = f"{cat}#{i}"
            n_rows += 1
            wujuh = row.get("wujuh") or ([f"as waṣl ({row['wasl']})"] if row.get("wasl") else [])
            wj = " / ".join(f'{esc(WAJH_AR.get(w, w))} <span class="en">{esc(w)}</span>' for w in wujuh)
            extra = []
            for k in ("cond", "place", "note"):
                if row.get(k):
                    extra.append(f'<div class="{k}"><b>{k}</b> {esc(row[k])}</div>')
            flags = []
            if row.get("option"):
                flags.append('<span class="tag opt">option</span>')
            if row.get("inherited"):
                flags.append('<span class="tag inh">inherited from aṣl</span>')
            cite = row.get("cite", "")
            for bp in parse_cite(cite):
                if bp not in SKIP_PAGES and bp not in pages:
                    pages.append(bp)
            trs.append(
                f'<tr data-id="{esc(rid)}"><td class="who">{"، ".join(esc(RAWI_AR[r]) for r in who)}'
                f'<div class="en">{esc(", ".join(who))}</div></td>'
                f'<td class="wj">{wj} {"".join(flags)}<div class="cite">{esc(cite)}</div>{"".join(extra)}</td>'
                f'<td class="mark"><label><input type="radio" name="{esc(rid)}" value="ok"> ✓</label>'
                f'<label><input type="radio" name="{esc(rid)}" value="wrong"> ✗</label>'
                f'<textarea placeholder="note" rows="1"></textarea></td></tr>')
        figs = "".join(figure(b, p) for b, p in pages)
        sections.append(
            f'<section id="{esc(cat)}"><h2>{esc(CAT_AR.get(cat, cat))} <span class="en">{esc(cat)}</span></h2>'
            f'<div class="split"><table><thead><tr><th>الرواة</th><th>الأوجه</th><th>review</th></tr></thead>'
            f'<tbody>{"".join(trs)}</tbody></table><div class="pages">{figs}</div></div></section>')

    rule = data["durrah_rule"]
    intro = (f'<section id="durrah_rule"><h2>منهج الدرة <span class="en">the Durrah rule, rows marked '
             f'"inherited"</span></h2><div class="split"><div class="rule">{esc(json.dumps(rule["aṣl"], ensure_ascii=False))}'
             f'<div class="en">cite: {esc(rule["cite"])}</div></div><div class="pages">'
             f'{"".join(figure("idah", p) for p in range(40, 44))}</div></div></section>')
    nav = "".join(f'<a href="#{esc(c)}">{esc(CAT_AR.get(c, c))}</a>' for c in data["categories"])
    not_read = "".join(f"<li>{esc(x)}</li>" for x in data.get("not_read_yet", []))
    page = TEMPLATE.format(nav=nav, intro=intro, sections="".join(sections), n_rows=n_rows,
                           n_cats=len(data["categories"]), not_read=not_read,
                           imgs=json.dumps(imgs))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"{OUT}: {n_rows} rows, {len(data['categories'])} categories, {len(imgs)} pages, "
          f"{OUT.stat().st_size / 1e6:.1f} MB")


TEMPLATE = """<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Profile review</title>
<style>
:root {{ --bg:#fbfaf7; --fg:#1d1c1a; --muted:#6b675f; --line:#e2ded5; --card:#ffffff; --accent:#2f5d50;
        --ok:#2e7d4f; --bad:#b3412e; --tag:#efe9dc; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#171614; --fg:#ece9e2; --muted:#a29d93; --line:#34312c;
        --card:#1f1d1a; --accent:#7fb8a6; --ok:#6cc391; --bad:#e07a63; --tag:#2c2924; }} }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:16px/1.6 "Noto Naskh Arabic","Amiri",serif; }}
header {{ position:sticky; top:0; z-index:2; background:var(--bg); border-bottom:1px solid var(--line);
         padding:10px 16px; display:flex; gap:12px; align-items:center; flex-wrap:wrap; }}
header h1 {{ font-size:18px; margin:0; }}
header .count {{ color:var(--muted); font:13px system-ui,sans-serif; }}
header button {{ margin-inline-start:auto; font:14px system-ui,sans-serif; padding:6px 12px; border-radius:6px;
                border:1px solid var(--accent); background:var(--accent); color:var(--bg); cursor:pointer; }}
nav {{ padding:8px 16px; display:flex; flex-wrap:wrap; gap:6px 14px; font-size:14px; border-bottom:1px solid var(--line); }}
nav a {{ color:var(--accent); text-decoration:none; }}
main {{ padding:0 16px 40px; }}
.intro {{ font:14px/1.6 system-ui,sans-serif; color:var(--muted); direction:ltr; text-align:left; max-width:900px; }}
section {{ border-bottom:1px solid var(--line); padding:18px 0; scroll-margin-top:64px; }}
h2 {{ font-size:20px; margin:0 0 10px; }}
.en {{ font:12px system-ui,sans-serif; color:var(--muted); direction:ltr; unicode-bidi:isolate; }}
.split {{ display:grid; grid-template-columns:minmax(0,1.1fr) minmax(0,1fr); gap:16px; align-items:start; }}
@media (max-width:1100px) {{ .split {{ grid-template-columns:1fr; }} .pages {{ position:static; max-height:none; }} }}
table {{ border-collapse:collapse; width:100%; background:var(--card); }}
th, td {{ border:1px solid var(--line); padding:6px 8px; vertical-align:top; text-align:right; }}
td.who {{ width:22%; }}
th {{ font:13px system-ui,sans-serif; color:var(--muted); }}
td.wj .cite {{ font:12px system-ui,sans-serif; direction:ltr; text-align:left; color:var(--accent); margin-top:2px; }}
td.wj > div {{ font:12.5px/1.5 system-ui,sans-serif; direction:ltr; text-align:left; color:var(--muted); margin-top:4px; }}
td.wj b {{ color:var(--fg); font-weight:600; }}
.tag {{ font:11px system-ui,sans-serif; background:var(--tag); border-radius:4px; padding:1px 6px; margin-inline-start:4px; }}
.tag.opt {{ color:var(--accent); }}
td.mark {{ width:120px; font:13px system-ui,sans-serif; }}
td.mark label {{ margin-inline-end:8px; cursor:pointer; }}
td.mark textarea {{ width:100%; margin-top:4px; font:12px system-ui,sans-serif; background:var(--bg); color:var(--fg);
                    border:1px solid var(--line); border-radius:4px; }}
tr.ok td {{ background:color-mix(in srgb, var(--ok) 10%, transparent); }}
tr.wrong td {{ background:color-mix(in srgb, var(--bad) 12%, transparent); }}
.pages {{ display:flex; flex-direction:column; gap:10px; max-height:85vh; overflow:auto; position:sticky; top:64px; }}
figure {{ margin:0; background:var(--card); border:1px solid var(--line); }}
figcaption {{ font:12px system-ui,sans-serif; color:var(--muted); padding:4px 8px; }}
figure img {{ width:100%; display:block; min-height:200px; }}
.rule {{ font:13px system-ui,sans-serif; direction:ltr; text-align:left; }}
ul {{ font:13px system-ui,sans-serif; direction:ltr; text-align:left; color:var(--muted); }}
</style></head><body>
<header><h1>مراجعة جدول الأصول</h1><span class="count" id="count"></span>
<button id="copy">Copy answers</button></header>
<nav><a href="#durrah_rule">منهج الدرة</a>{nav}</nav>
<main>
<p class="intro">{n_cats} categories, {n_rows} rows from <code>spike/data/profiles.yaml</code>, each beside the
pages it cites (file page = printed page). Mark each row ✓ or ✗ and add a note where needed; marks are kept in
this browser. "Copy answers" puts them on the clipboard as JSON to paste back to Claude.
Pages from al-Īḍāḥ pp. 40–43 (the Durrah rule) are shown once, below.</p>
<p class="intro">Not in the table yet:</p><ul>{not_read}</ul>
{intro}{sections}
</main>
<script>
const IMGS = {imgs};
const KEY = "profile-review-v1";
let state = {{}};
try {{ state = JSON.parse(localStorage.getItem(KEY) || "{{}}"); }} catch (e) {{}}
function save() {{ try {{ localStorage.setItem(KEY, JSON.stringify(state)); }} catch (e) {{}} count(); }}
function count() {{
  const rows = document.querySelectorAll("tr[data-id]");
  const done = Object.values(state).filter(v => v.mark).length;
  document.getElementById("count").textContent = done + " / " + rows.length + " reviewed";
}}
document.querySelectorAll("tr[data-id]").forEach(tr => {{
  const id = tr.dataset.id, s = state[id] || {{}};
  const ta = tr.querySelector("textarea");
  if (s.mark) {{ tr.classList.add(s.mark); const r = tr.querySelector(`input[value="${{s.mark}}"]`); if (r) r.checked = true; }}
  if (s.note) ta.value = s.note;
  tr.querySelectorAll("input").forEach(inp => inp.addEventListener("change", () => {{
    state[id] = {{...(state[id] || {{}}), mark: inp.value}};
    tr.classList.remove("ok", "wrong"); tr.classList.add(inp.value); save();
  }}));
  ta.addEventListener("input", () => {{ state[id] = {{...(state[id] || {{}}), note: ta.value}}; save(); }});
}});
const io = new IntersectionObserver(es => es.forEach(e => {{
  if (e.isIntersecting) {{ const img = e.target; img.src = "data:image/jpeg;base64," + IMGS[img.dataset.src]; io.unobserve(img); }}
}}), {{rootMargin: "600px"}});
document.querySelectorAll("img[data-src]").forEach(i => io.observe(i));
document.getElementById("copy").addEventListener("click", async () => {{
  const out = JSON.stringify(state, null, 1);
  try {{ await navigator.clipboard.writeText(out); document.getElementById("copy").textContent = "Copied"; }}
  catch (e) {{ prompt("Copy:", out); }}
}});
count();
</script></body></html>
"""

if __name__ == "__main__":
    main()
