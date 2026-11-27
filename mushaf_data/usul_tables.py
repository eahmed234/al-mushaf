"""The uṣūl as one rule table per category for all twenty ruwāt (data/usul/, Eisa 2026-11-26).

    tables()      {category: table}
    profiles(edition="sughra", options=())
                  the tables in the shape of mushaf_data.profiles.load, for the engine's categories
    extras()      every `options` entry (ahl al-adāʾ views, off by default) and `kubra` entry (other
                  ṭuruq), keyed `<table>:<id>`
    active(edition, options)
                  the extras switched on: options by id; with edition "kubra", every kubrā entry too

An extra with `adds` ({category, wujuh}) adds those wujūh to that engine category for its ruwāt;
one without is recorded but not modelled yet, and `active` says so (`modelled: False`).

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


EDITIONS = ("sughra", "kubra")


@lru_cache(maxsize=1)
def extras() -> dict[str, dict]:
    out = {}
    for c, t in tables().items():
        for kind in ("options", "kubra"):
            for e in t.get(kind) or []:
                key = f"{c}:{e['id']}"
                if key in out:
                    raise ValueError(f"two extras named {key}")
                add = e.get("adds")
                if add and not set(add["wujuh"]) <= set(WUJUH.get(add["category"], [])):
                    raise ValueError(f"{key}: adds {add} outside the engine's {add['category']} wujūh")
                if not set(e["ruwat"]) <= set(RUWAT):
                    raise ValueError(f"{key}: unknown ruwāt {set(e['ruwat']) - set(RUWAT)}")
                out[key] = {**e, "kind": kind, "table": c, "modelled": bool(add)}
    return out


def active(edition: str = "sughra", options=()) -> list[dict]:
    """The extras switched on. Options are named `<table>:<id>`; kubrā entries come with the
    kubrā edition (the sughrā leaves them out)."""
    if edition not in EDITIONS:
        raise ValueError(f"edition {edition!r} is not one of {EDITIONS}")
    ex = extras()
    unknown = [o for o in options if o not in ex or ex[o]["kind"] != "options"]
    if unknown:
        raise ValueError(f"unknown options {unknown}; offered: {sorted(k for k, e in ex.items() if e['kind'] == 'options')}")
    return [e for k, e in ex.items() if k in options or (edition == "kubra" and e["kind"] == "kubra")]


def profiles(edition: str = "sughra", options=()) -> dict:
    out = copy.deepcopy(_profiles())
    for e in active(edition, options):
        if not e["modelled"]:
            continue
        cat = e["adds"]["category"]
        for r in e["ruwat"]:
            slot = out[r].setdefault(cat, {"wujuh": {WUJUH[cat][0]: []}, "source": f"usul/{e['table']}"})
            for w in e["adds"]["wujuh"]:
                slot["wujuh"].setdefault(w, list(e["cite"]))
            slot.setdefault("extras", []).append(f"{e['table']}:{e['id']}")
    return out
