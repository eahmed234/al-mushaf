"""The Ḥafṣ word spine (sources/spine/hafs.jsonl, built by tools/build_spine.py): word id → text,
in the encoding of `text.normalize`."""
from __future__ import annotations

import json
from functools import lru_cache

from .paths import SPINE
from .text import normalize


def wid(s: str) -> tuple[int, int, int]:
    a, b, c = s.split(":")
    return int(a), int(b), int(c)


def _text(item: dict) -> str:
    cps = " ".join(cl["cps"] for cl in item["clusters"]).split()
    return "".join(chr(int(c[2:], 16)) for c in cps)


def items(path=SPINE):
    """Every item of the spine (word, hizb sign, ayah end), in Qurʾān order."""
    if not path.exists():
        raise FileNotFoundError(f"{path}: run python3 -I tools/fetch_sources.py and python3 tools/build_spine.py")
    with open(path, encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)


@lru_cache(maxsize=1)
def words() -> dict[str, str]:
    """Word id → normalised Ḥafṣ text, the whole Qurʾān (cached: treat as read-only)."""
    return {it["id"]: normalize(_text(it)) for it in items() if it["kind"] == "word"}


def in_passage(surah: int, ayah: int) -> bool:
    """The spike's passage: al-Fātiḥah and al-Baqarah 1–20."""
    return surah == 1 or (surah == 2 and ayah <= 20)


@lru_cache(maxsize=1)
def passage() -> dict[str, str]:
    """The passage's words in order, with the basmalah recited at the junction before al-Baqarah
    (ids B:2:1-4, same text as 1:1) between 1:7 and 2:1."""
    out: dict[str, str] = {}
    for k, v in words().items():
        s, a, _ = wid(k)
        if not in_passage(s, a):
            continue
        if k == "2:1:1":
            for n in range(1, 5):
                out[f"B:2:{n}"] = out[f"1:1:{n}"]
        out[k] = v
    return out


# The spine across the twenty (docs/04 §3): Ḥafṣ's words plus the slots of data/spine/slots.yaml.

@lru_cache(maxsize=1)
def slot_data() -> dict:
    import yaml

    from .paths import DATA
    return yaml.safe_load((DATA / "spine" / "slots.yaml").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def slots() -> tuple[str, ...]:
    """Every slot id in order: Ḥafṣ's word ids with each added slot after its `after`."""
    after: dict[str, list[str]] = {}
    for a in slot_data().get("added") or []:
        after.setdefault(a["after"], []).append(a["id"])
    out = []
    for w in words():
        out.append(w)
        out += after.get(w, [])
    return tuple(out)


def projection(rawi: str) -> list[str]:
    """The slots the rāwī reads, in order: Ḥafṣ's words but the ones empty for him, plus the added
    slots he reads. Ḥafṣ's projection is his word list."""
    from .ruwat import RUWAT

    if rawi not in RUWAT:
        raise ValueError(f"unknown rāwī {rawi}")
    d = slot_data()
    empty = {e["slot"] for e in d.get("empty") or [] if rawi in e["readers"]}
    added = {a["id"] for a in d.get("added") or []}
    mine = {a["id"] for a in d.get("added") or [] if rawi in a["readers"]}
    return [s for s in slots() if s not in empty and (s not in added or s in mine)]
