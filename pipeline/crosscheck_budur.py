"""The unified uṣūl tables against al-Budūr's statements at each place of al-Baqarah and Āl ʿImrān.

    python3 -m pipeline.crosscheck_budur [--show N]

al-Budūr's uṣūl rows (the reviewed gold pp. 16-25, the run pp. 26-75) name readers at a word. For
each rāwī a row names, the unified table (its case for the row's category, or the listed entry
for that word) should allow the reading: a row that includes Ḥafṣ states the case's first wajh
(Ḥafṣ's); one that doesn't, another; for imālah the row's words decide (قلل → taqlīl, أمال →
imālah, فتح → fatḥ). A khulf row needs the rāwī to have two wujūh. Madd lengths are left out
(al-Budūr speaks in degrees).
"""
from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path

import yaml

from mushaf_data.occurrences import skel
from mushaf_data.spine import words

from .gold import GOLD
from .score import rows
from .unify_profiles import DIR, where

SKIP = {"munfasil", "muttasil", "badal", "lin_hamz", "madd_arid",
        "hamzatayn_kalimatayn_muttafiq", "hamzatayn_kalimatayn_mukhtalif"}  # degrees; the case depends on the vowels
# the row's own words name the wajh where they can (first match wins)
KEYWORDS = {
    "sakt_al": [("ترك", "none"), ("بلا سكت", "none"), ("غير سكت", "none"), ("تحقيق", "none"), ("سكت", "sakt")],
    "sakt_mafsul": [("ترك", "none"), ("بلا سكت", "none"), ("غير سكت", "none"), ("تحقيق", "none"), ("سكت", "sakt")],
    "naql": [("نقل", "naql"), ("تحقيق", "none"), ("ترك", "none")],
    "idgham_ghunna": [("أظهر", None), ("بلا غنة", "bila_ghunna"), ("بغير غنة", "bila_ghunna"), ("غير غنة", "bila_ghunna"), ("بلاغنة", "bila_ghunna"), ("الغنة", "ghunna"), ("بغنة", "ghunna")],
    "silah_mim": [("إسكان", "sukun"), ("الإسكان", "sukun"), ("بالإسكان", "sukun"), ("صلة", "silah"), ("وصل", "silah")],
    "silah_mim_hamza": [("إسكان", "sukun"), ("صلة", "silah"), ("وصل", "silah")],
    "silah_ha": [("حذف الصلة", "none"), ("غير صلة", "none"), ("بغير صلة", "none"), ("إسكان", "sukun"), ("بالقصر", "none"), ("الإشباع", "silah"), ("بلا صلة", "none"), ("صلة", "silah"), ("وصل", "silah")],
    "ibdal_sakin": [("حقق", "tahqiq"), ("تحقيق", "tahqiq"), ("ولا إبدال", "tahqiq"), ("أبدل", "ibdal"), ("إبدال", "ibdal")],
    "tarqiq_ra": [("لا ترقيق", "tafkhim"), ("فخم", "tafkhim"), ("تفخيم", "tafkhim"), ("كغيره", "tafkhim"), ("لا ترفق", "tafkhim"), ("لا ترقق", "tafkhim"), ("رقق", "tarqiq"), ("ترقيق", "tarqiq"), ("رفق", "tarqiq")],
    "hamz_waqf_mid": [("إلا التحقيق", "tahqiq"), ("لا شيء فيه", "tahqiq")],
    "taghliz_lam": [("ترقيق", "tarqiq"), ("غلظ", "taghliz"), ("تغليظ", "taghliz"), ("تفخيم", "taghliz")],
}
# al-Wāfī p. 150: the words on fuʿlā, faʿlā and fiʿlā (alif al-taʾnīth), Abū ʿAmr's taqlīl
FAALA = """موسى أنثى الدنيا قربى الوسطى القصوى العزى الوثقى الحسنى الأولى السفلى العليا الرؤيا طوبى المثلى
السوأى زلفى سقيا الرجعى عقبى السلوى الموتى التقوى النجوى القتلى مرضى دعوى شتى صرعى طغوى يحيى سيما إحدى
ضيزى عيسى""".split()
SUFFIX = re.compile(r"(?:هما|هم|ها|ه|كم)$")
REFERENCE = ("كحكم", "حكمها", "ومثله", "مثله", "مثل ", "وكذلك")  # a row pointing at another word's rule


def key(word: str) -> tuple[str, bool]:
    """Skeleton plus whether the word starts with an alif or hamzah (skel drops both: أزكى ≠ زكى)."""
    from tools import book
    return skel(word), book.fold(word).lstrip("وفبل")[:1] in ("ا", "ء")


def stem(word: str) -> str:
    """The skeleton without a pronoun suffix (prefixes are left: matching is by the word's end)."""
    return SUFFIX.sub("", skel(word))


FAALA_SK = {skel(w[2:] if w.startswith("ال") else w) for w in FAALA}


def faala(word: str) -> bool:
    st = stem(word)
    return any(st.endswith(f) and len(st) - len(f) <= 3 for f in FAALA_SK)


WASL_SAKIN = 11  # imala: the alif before a sākin in the next word, in waṣl (wafi 156)


def case_for(cat: str, word: str, k: int, nxt: str = "") -> int:
    """The table case the word belongs to, where the category alone doesn't say: imālah (after a
    rāʾ: ذوات الراء; on fuʿlā/faʿlā/fiʿlā: alif al-taʾnīth, wafi 150), the sākin hamzah (fāʾ, ʿayn,
    lām of the word), the second hamzah of two in a word (its vowel)."""
    if cat.startswith("imala") and nxt.startswith("ٱ") and re.search("[ىا][\u0670]?[\u064b-\u065f\u06d6-\u06ed]*$", word):
        return WASL_SAKIN + (stem(word)[-2:-1] == "ر")  # a final alif; after a rāʾ, al-Sūsī's khulf
    if cat == "imala_ya":
        st = stem(word)
        if st[-2:-1] == "ر":
            return 4
        if faala(word):
            return 9
    if cat == "ibdal_sakin":
        st = re.sub(r"^(?:[وفبل]*ل(?=.{3})|[وفب])?[يتنم]?", "", stem(word))  # article, conjunction, imperfect or participle prefix
        i = st.find("ء")
        if i == 0:
            return 0
        if i == len(st) - 1 or (i >= 0 and i == len(st) - 2 and st[-1] in "تن"):
            return 2
        if i > 0:
            return 1
    if cat == "hamzatayn":
        m = re.search("[ءأ][\u064e]?[\u0670]?[ءأإؤئ]([\u064e\u064f\u0650])?", word)
        second = m.group(0)[-2:] if m else ""
        if "إ" in second or "ئ" in second or "\u0650" in second:
            return 1
        if "ؤ" in second or "\u064f" in second:
            return 2
    return k


IMALA = [("لا إمالة", "fath"), ("لا تقليل", "fath"), ("قلل", "taqlil"), ("تقليل", "taqlil"), ("أمال", "imala"), ("إمالة", "imala"), ("بالإمالة", "imala"), ("فتح", "fath")]


def farsh_words() -> set[str]:
    """Slots the farsh tables (al-Budūr's and the books') cover: their reading is farsh, not a
    table case (التوراة, wafi 230)."""
    out = set()
    for d in ("farsh", "farsh_books"):
        for f in (Path("data") / d).glob("*.yaml"):
            for pl in yaml.safe_load(f.read_text(encoding="utf-8")) or []:
                if pl.get("class", "farsh") != "rule":
                    out.update(pl.get("place") or [])
    return out


def check(show: int = 0, last: int = 75) -> dict:
    gold, _ = rows(GOLD / "budur", list(range(16, 26)))
    run, _ = rows(Path("pipeline/out/baqarah/budur"), list(range(26, last + 1)))
    farsh = farsh_words()
    h = words()
    order = list(h)
    pos = {w: i for i, w in enumerate(order)}
    tables, res, out = {}, Counter(), []
    for p, r in gold + run:
        cat = r.get("category")
        if r["kind"] != "usul" or cat not in where() or cat in SKIP or not r["place"]:
            continue
        if r["condition"] == "waqf" and not cat.startswith(("hamz_waqf", "ibdal_sakin_waqf", "hamzatayn_waqf")):
            continue  # a stop's wajh belongs to the waqf tables, not this waṣl case
        if set(r["place"]) & farsh:
            res["farsh"] += 1
            continue
        if any(x in r["reading"] for x in REFERENCE):
            res["reference"] += 1
            continue
        tname, k = where()[cat]
        first = r["place"][0]
        nxt = h[order[pos[first] + 1]] if first in pos and pos[first] + 1 < len(order) else ""
        nxt = "" if r["condition"] == "waqf" or (first in h and any(c in h[first] for c in "ۖۗۚۛۘۙ")) else nxt
        k = case_for(cat, h.get(first, ""), k, nxt)
        t = tables.setdefault(tname, yaml.safe_load((DIR / f"{tname}.yaml").read_text(encoding="utf-8")))
        case = t["cases"][k]
        vocab = [w["id"] for w in t.get("wujuh") or []]
        sk = {key(h[w]) for w in r["place"] if w in h}
        sk |= {(k[1:], False) for k, _ in sk if k[:1] in "وفبل" and len(k) > 3}  # وَبِئۡسَ, وَمَأۡوَىٰهُمُ
        entries = [x for x in t.get("listed") or []
                   if {k for w in x.get("words") or [] for k in (key(str(w)), key(str(w).split()[0]))} & sk]
        kws = IMALA if cat.startswith("imala") else KEYWORDS.get(cat)
        hit = next(((kw, w) for kw, w in kws if kw in r["reading"]), None) if kws else None
        if hit and hit[1] is None:
            res["other_rule"] += 1  # the row speaks of another rule (iẓhār at مِنۡ خَيۡرٖ is nūn sākinah)
            continue
        want = hit[1] if hit else None
        if want is not None:
            ok_set = lambda ws, want=want: want in ws  # noqa: E731
        elif cat.startswith("imala"):
            continue
        else:
            default = (case["ruwat"].get("hafs") or {}).get("wujuh") or vocab[:1]
            if "hafs" in r["readers"]:
                ok_set = lambda ws, d=set(default): bool(set(ws) & d)  # noqa: E731
            else:
                ok_set = lambda ws, d=set(default): bool(set(ws) - d)  # noqa: E731
        for x in r["readers"]:
            entry = next((e for e in entries if x in (e.get("ruwat") or {})), None)  # the entry that names him
            ws = entry["ruwat"][x] if entry else (case["ruwat"].get(x) or {}).get("wujuh") or []
            fine = ok_set(ws) and (x not in r["khulf"] or len(ws) > 1)
            res["agree" if fine else "differ"] += 1
            if not fine:
                out.append((p, cat, ",".join(r["place"]), " ".join(h.get(w, "") for w in r["place"]), x, "/".join(ws), r["reading"][:40],
                            "khulf" if x in r["khulf"] else "", "listed" if entry else ""))
    return {"agree": res["agree"], "differ": res["differ"], "reference": res["reference"], "farsh": res["farsh"],
            "rows": out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int, default=0)
    a = ap.parse_args()
    r = check()
    print(f"al-Budūr pp. 16-75 against the unified tables: {r['agree']} rāwī statements agree, {r['differ']} differ"
          f" ({r['reference']} rows that point at another word's rule left out)")
    by = Counter((x[1]) for x in r["rows"])
    print("  by category:", dict(by.most_common()))
    for x in r["rows"][: a.show]:
        print("   ", *x)
    from mushaf_data.paths import BUILD
    lines = ["# al-Budūr's statements against the unified uṣūl tables", "",
             f"{r['agree']} rāwī statements agree, {r['differ']} differ. page | category | place | words | rāwī | table | al-Budūr | khulf | listed", ""]
    lines += ["- " + " | ".join(map(str, x)) for x in r["rows"]]
    (BUILD / "crosscheck_budur.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
