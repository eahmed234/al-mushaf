"""Fill the unified tables' unstated slots (Eisa 2026-11-26: unstated reads as Ḥafṣ).

    python3 -m pipeline.unify_fill        rewrites pipeline/unified/*.yaml in place

Per case: a Shāṭibiyyah rāwī no row speaks of gets Ḥafṣ's wujūh in that case (or the vocabulary's
first, Ḥafṣ's reading, when Ḥafṣ is unstated too), `via: as_hafs`. A Durrah rāwī the Durrah is
silent on reads as his aṣl (al-Īḍāḥ pp. 40-43: Abū Jaʿfar as Nāfiʿ, Yaʿqūb as Abū ʿAmr, Khalaf
al-ʿĀshir as Khalaf ʿan Ḥamzah), `via: asl_unstated`; where the aṣl's two ruwāt differ, as Ḥafṣ
and an open line. Open lines that only reported an empty slot move to `filled_notes`.
"""
import re
from pathlib import Path

import yaml

from mushaf_data.paths import ROOT
from mushaf_data.ruwat import RUWAT

DIR = ROOT / "pipeline/unified"
ASL = {"ibn_wardan": ["qalun", "warsh"], "ibn_jammaz": ["qalun", "warsh"], "ruways": ["duri_abuamr", "susi"],
       "rawh": ["duri_abuamr", "susi"], "ishaq": ["khalaf_an_hamzah"], "idris": ["khalaf_an_hamzah"]}
EMPTY = re.compile(r"(?i)\b(empty|no row|not stated|says nothing|left empty|unstated|no reading)\b")


def fill(t: dict) -> int:
    first = [w["id"] for w in (t.get("wujuh") or [])][:1]
    n = 0
    t.setdefault("open", t.get("open") or [])
    for case in t.get("cases") or []:
        rw = case.setdefault("ruwat", {})
        hafs = (rw.get("hafs") or {}).get("wujuh") or first
        for r in RUWAT[:14]:
            if not (rw.get(r) or {}).get("wujuh"):
                rw[r] = {"wujuh": list(hafs), "cite": [], "via": "as_hafs"}
                n += 1
        for r in RUWAT[14:]:
            if (rw.get(r) or {}).get("wujuh"):
                continue
            asl = [tuple((rw.get(a) or {}).get("wujuh") or []) for a in ASL[r]]
            if len(set(asl)) == 1 and asl[0]:
                rw[r] = {"wujuh": list(asl[0]), "cite": ["idah 40-43"], "via": "asl_unstated"}
            else:
                rw[r] = {"wujuh": list(hafs), "cite": [], "via": "as_hafs"}
                t["open"].append(f"{r} in case {case.get('case')!r}: the Durrah is silent and his aṣl's two ruwāt differ "
                                 f"({' / '.join('+'.join(a) for a in asl)}); filled as Ḥafṣ for now")
            n += 1
        case["ruwat"] = {r: rw[r] for r in RUWAT}
    keep, moved = [], []
    for q in t["open"]:
        (moved if EMPTY.search(str(q)) and "filled as Ḥafṣ for now" not in str(q) else keep).append(q)
    t["open"], t["filled_notes"] = keep, (t.get("filled_notes") or []) + moved
    return n


WASL = {"hamzatayn_waqf": ("hamzatayn", 0), "ibdal_sakin_waqf": ("ibdal_sakin", 0)}


def as_wasl() -> int:
    """The waqf parts whose other readers stop as in waṣl (al-Wāfī p. 99): their slots filled as
    Ḥafṣ get their own waṣl reading from the waṣl table instead."""
    f = DIR / "hamz_waqf.yaml"
    t = yaml.safe_load(f.read_text(encoding="utf-8"))
    vocab = {w["id"] for w in t.get("wujuh") or []}
    n = 0
    for case in t.get("cases") or []:
        part = str(case.get("case", "")).split(":")[0]
        if part not in WASL:
            continue
        src, k = WASL[part]
        w = yaml.safe_load((DIR / f"{src}.yaml").read_text(encoding="utf-8"))["cases"][k]["ruwat"]
        for r, v in case["ruwat"].items():
            if v.get("via") in ("as_hafs", "asl_unstated"):
                ws = (w.get(r) or {}).get("wujuh") or v["wujuh"]
                case["ruwat"][r] = {"wujuh": list(ws), "cite": list((w.get(r) or {}).get("cite") or []) + ["wafi 99"], "via": "as_wasl"}
                for x in ws:
                    if x not in vocab:
                        t["wujuh"].append({"id": x, "ar": x, "en": f"as in waṣl ({src})"})
                        vocab.add(x)
                n += 1
    f.write_text(yaml.safe_dump(t, allow_unicode=True, sort_keys=False, width=140), encoding="utf-8")
    return n


def main():
    total = 0
    for f in sorted(DIR.glob("*.yaml")):
        t = yaml.safe_load(f.read_text(encoding="utf-8"))
        n = fill(t)
        total += n
        f.write_text(yaml.safe_dump(t, allow_unicode=True, sort_keys=False, width=140), encoding="utf-8")
    print(f"{total} slots filled; {as_wasl()} waqf slots set as in waṣl")


if __name__ == "__main__":
    main()
