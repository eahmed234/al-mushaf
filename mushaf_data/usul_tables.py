"""The uṣūl as one rule table per category for all twenty ruwāt (data/usul/, Eisa 2026-11-26).

    tables()      {category: table}
    profiles()    the tables in the shape of mushaf_data.profiles.load, for the engine's categories

Each engine category (mushaf_data.usul.WUJUH) is one case of a table: the case named after it, or
CASE, or the first (data/categories.yaml says which table holds it). Only wujūh ids the engine
knows are kept. The engine still reads data/profiles.yaml; tests hold the two to the same rules.
"""
from __future__ import annotations

import copy
from functools import lru_cache

import yaml

from .paths import DATA
from .ruwat import RUWAT
from .usul import WUJUH

DIR = DATA / "usul"
CASE = {"silah_ha": 1, "tarqiq_ra": 1}  # Ibn Kathīr's ṣilah after a sākin; Warsh's condition for the rāʾ


@lru_cache(maxsize=1)
def tables() -> dict[str, dict]:
    return {f.stem: yaml.safe_load(f.read_text(encoding="utf-8")) for f in sorted(DIR.glob("*.yaml"))}


@lru_cache(maxsize=1)
def where() -> dict[str, tuple[str, int]]:
    cats = yaml.safe_load((DATA / "categories.yaml").read_text(encoding="utf-8"))
    prof_cats = set(yaml.safe_load((DATA / "profiles.yaml").read_text(encoding="utf-8"))["categories"])
    out = {}
    for c, v in cats.items():
        if c not in tables():
            continue
        names = [str(x.get("case", "")) for x in tables()[c].get("cases") or []]
        for old in v.get("rows", []):
            if old in prof_cats:
                out[old] = (c, next((i for i, n in enumerate(names) if n.startswith(old + ":")), CASE.get(old, 0)))
    return out


@lru_cache(maxsize=1)
def _profiles() -> dict:
    out = {r: {} for r in RUWAT}
    for old, (c, k) in where().items():
        case = tables()[c]["cases"][k]
        for r in RUWAT:
            v = case["ruwat"].get(r) or {}
            ws = [w for w in v.get("wujuh") or [] if w in WUJUH.get(old, [w])]
            if ws:
                e = {"wujuh": {w: list(v.get("cite") or [v.get("via", "")]) for w in ws}, "source": f"usul/{c}"}
                if v.get("option"):
                    e["option"] = True
                out[r][old] = e
    return out


def profiles() -> dict:
    return copy.deepcopy(_profiles())
