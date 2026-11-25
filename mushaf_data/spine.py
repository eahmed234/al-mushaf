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
