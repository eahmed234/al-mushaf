"""Taḥrīr as data: allowed tuples per rāwī over categories and features (data/constraints.yaml),
each from a page."""
from __future__ import annotations

from pathlib import Path

import yaml

from .paths import DATA
from .ruwat import RUWAT
from .usul import WUJUH

PATH = DATA / "constraints.yaml"


def load(path=PATH) -> list[dict]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []


CONSTRAINTS = load()


def allowed(rawi: str, choice: dict, constraints: list[dict] | None = None) -> bool:
    """False if the choice breaks a taḥrīr constraint for this rāwī. A constraint binds only when
    the choice has every category it names, and only if it is enforced."""
    for c in CONSTRAINTS if constraints is None else constraints:
        if "cats" not in c or c.get("enforced") is False:
            continue
        if rawi in c["rawi"] and all(k in choice for k in c["cats"]):
            if [choice[k] for k in c["cats"]] not in c["allowed"]:
                return False
    return True


def validate(constraints: list[dict] | None = None) -> list[str]:
    """Problems in the constraints: unknown rāwī, a tuple of the wrong length or with a wajh its
    category doesn't have, no page cited."""
    problems = []
    for c in CONSTRAINTS if constraints is None else constraints:
        if "cats" not in c:
            continue
        cid = c.get("id", "?")
        if not str(c.get("cite", "")).strip():
            problems.append(f"{cid}: cites no page")
        for r in c["rawi"]:
            if r not in RUWAT:
                problems.append(f"{cid}: unknown rāwī {r}")
        for t in c["allowed"]:
            if len(t) != len(c["cats"]):
                problems.append(f"{cid}: {t} has {len(t)} wujūh for {len(c['cats'])} categories")
                continue
            for cat, w in zip(c["cats"], t):
                if cat in WUJUH and w not in WUJUH[cat]:
                    problems.append(f"{cid}: {w} is not a wajh of {cat}")
    return problems
