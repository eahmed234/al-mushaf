"""The unified uṣūl tables against al-Budūr's statements at each place of al-Baqarah.

    python3 -m pipeline.crosscheck_budur [--show N]

al-Budūr's uṣūl rows (the reviewed gold pp. 16-25, the run pp. 26-58) name readers at a word. For
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
    "idgham_ghunna": [("بلا غنة", "bila_ghunna"), ("بغير غنة", "bila_ghunna"), ("غير غنة", "bila_ghunna"), ("بلاغنة", "bila_ghunna"), ("الغنة", "ghunna"), ("بغنة", "ghunna")],
    "silah_mim": [("إسكان", "sukun"), ("الإسكان", "sukun"), ("بالإسكان", "sukun"), ("صلة", "silah"), ("وصل", "silah")],
    "silah_mim_hamza": [("إسكان", "sukun"), ("صلة", "silah"), ("وصل", "silah")],
    "silah_ha": [("صلة", "silah"), ("وصل", "silah"), ("بغير صلة", "none")],
    "ibdal_sakin": [("حقق", "tahqiq"), ("تحقيق", "tahqiq"), ("ولا إبدال", "tahqiq"), ("أبدل", "ibdal"), ("إبدال", "ibdal")],
    "tarqiq_ra": [("لا ترقيق", "tafkhim"), ("فخم", "tafkhim"), ("تفخيم", "tafkhim"), ("كغيره", "tafkhim"), ("لا ترفق", "tafkhim"), ("لا ترقق", "tafkhim"), ("رقق", "tarqiq"), ("ترقيق", "tarqiq"), ("رفق", "tarqiq")],
    "hamz_waqf_mid": [("إلا التحقيق", "tahqiq"), ("لا شيء فيه", "tahqiq")],
    "taghliz_lam": [("ترقيق", "tarqiq"), ("غلظ", "taghliz"), ("تغليظ", "taghliz"), ("تفخيم", "taghliz")],
}
IMALA = [("قلل", "taqlil"), ("تقليل", "taqlil"), ("أمال", "imala"), ("إمالة", "imala"), ("بالإمالة", "imala"), ("فتح", "fath")]


def check(show: int = 0) -> dict:
    gold, _ = rows(GOLD / "budur", list(range(16, 26)))
    run, _ = rows(Path("pipeline/out/baqarah/budur"), list(range(26, 59)))
    h = words()
    tables, res, out = {}, Counter(), []
    for p, r in gold + run:
        cat = r.get("category")
        if r["kind"] != "usul" or cat not in where() or cat in SKIP or not r["place"]:
            continue
        if r["condition"] == "waqf" and not cat.startswith(("hamz_waqf", "ibdal_sakin_waqf", "hamzatayn_waqf")):
            continue  # a stop's wajh belongs to the waqf tables, not this waṣl case
        tname, k = where()[cat]
        t = tables.setdefault(tname, yaml.safe_load((DIR / f"{tname}.yaml").read_text(encoding="utf-8")))
        case = t["cases"][k]
        vocab = [w["id"] for w in t.get("wujuh") or []]
        sk = {skel(h[w]) for w in r["place"] if w in h}
        entry = next((x for x in t.get("listed") or [] if {skel(str(w)) for w in x.get("words") or []} & sk), None)
        kws = IMALA if cat.startswith("imala") else KEYWORDS.get(cat)
        want = next((w for kw, w in kws if kw in r["reading"]), None) if kws else None
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
            ws = (entry.get("ruwat") or {}).get(x) if entry and x in (entry.get("ruwat") or {}) else (case["ruwat"].get(x) or {}).get("wujuh") or []
            fine = ok_set(ws) and (x not in r["khulf"] or len(ws) > 1)
            res["agree" if fine else "differ"] += 1
            if not fine:
                out.append((p, cat, ",".join(r["place"]), " ".join(h.get(w, "") for w in r["place"]), x, "/".join(ws), r["reading"][:40],
                            "khulf" if x in r["khulf"] else "", "listed" if entry else ""))
    return {"agree": res["agree"], "differ": res["differ"], "rows": out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int, default=0)
    a = ap.parse_args()
    r = check()
    print(f"al-Budūr pp. 16-58 against the unified tables: {r['agree']} rāwī statements agree, {r['differ']} differ")
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
