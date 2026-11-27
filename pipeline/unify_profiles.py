"""The unified tables (pipeline/unified/) as engine profiles, compared with the reviewed table.

    python3 -m pipeline.unify_profiles [--show]

Each old category's general rule is one case of its unified table: the case named after it
(imālah, Ḥamzah's waqf), else the case that is its condition (CASE below), else the first.
`load()` gives {rāwī: {category: {"wujuh": {wajh: cites}, "source": "unified"}}} in the shape of
mushaf_data.profiles.load, with only the wujūh ids the engine knows (mushaf_data.usul.WUJUH).
"""
from __future__ import annotations

import argparse
from functools import lru_cache

import yaml

from mushaf_data.paths import DATA, ROOT
from mushaf_data.profiles import load as reviewed
from mushaf_data.ruwat import RUWAT
from mushaf_data.usul import WUJUH

DIR = ROOT / "pipeline/unified"
CASE = {"silah_ha": 1, "tarqiq_ra": 1}  # Ibn Kathīr's ṣilah after a sākin; Warsh's condition for the rāʾ


@lru_cache(maxsize=1)
def where() -> dict[str, tuple[str, int]]:
    cats = yaml.safe_load((DATA / "categories.yaml").read_text(encoding="utf-8"))
    prof_cats = set(next(iter(reviewed().values())))
    out = {}
    for c, v in cats.items():
        for old in v.get("rows", []):
            if old not in prof_cats:
                continue
            t = yaml.safe_load((DIR / f"{c}.yaml").read_text(encoding="utf-8"))
            names = [str(x.get("case", "")) for x in t.get("cases") or []]
            k = next((i for i, n in enumerate(names) if n.startswith(old + ":")), CASE.get(old, 0))
            out[old] = (c, k)
    return out


@lru_cache(maxsize=1)
def _load() -> dict:
    out = {r: {} for r in RUWAT}
    tables = {}
    for old, (c, k) in where().items():
        t = tables.setdefault(c, yaml.safe_load((DIR / f"{c}.yaml").read_text(encoding="utf-8")))
        case = (t.get("cases") or [])[k]
        for r in RUWAT:
            v = case["ruwat"].get(r) or {}
            ws = [w for w in v.get("wujuh") or [] if w in WUJUH.get(old, [w])]
            if ws:
                out[r][old] = {"wujuh": {w: list(v.get("cite") or [v.get("via", "")]) for w in ws}, "source": "unified"}
    return out


def load() -> dict:
    """A fresh copy (callers may change it)."""
    import copy
    return copy.deepcopy(_load())


def diff() -> list[tuple]:
    rev, uni = reviewed(), load()
    out = []
    for r in RUWAT:
        for cat, e in rev[r].items():
            if cat not in uni[r]:
                continue
            a, b = list(e["wujuh"]), list(uni[r][cat]["wujuh"])
            if set(a) != set(b):
                out.append((cat, r, "/".join(a), "/".join(b)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    d = diff()
    rev, uni = reviewed(), load()
    pairs = sum(1 for r in RUWAT for c in rev[r] if c in uni[r])
    print(f"unified vs reviewed profile: {pairs - len(d)}/{pairs} rāwī-category pairs give the same wujūh; {len(d)} differ")
    if a.show:
        for x in sorted(d):
            print("  ", *x)


if __name__ == "__main__":
    main()
