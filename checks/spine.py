"""KFGQPC's eight riwāyāt against the spine's projections (milestone 3: "Ḥafṣ is one projection;
KFGQPC's eight align without gaps").

    python3 -m checks.spine [--show]

Per sūrah (the riwāyāt count āyāt differently, so āyah numbers aren't used), each riwāyah's KFGQPC
words are aligned by skeleton with the slots of its projection (mushaf_data.spine.projection). Where
they don't pair one to one, a block of slots and words is still aligned when it is KFGQPC writing the
same rasm in more or fewer tokens: أَوَ لَمۡ for أَوَلَمۡ, مَا لِي for مَالِيَ, وَنَـَٔابِجَانِبِهِۦ for
وَنَـَٔا بِجَانِبِهِۦ (the joined letters agree). Anything else is a gap: a slot the spine lacks or has
in excess for that riwāyah.

The basmalah of al-Fātiḥah is left out of the files whose count doesn't number it (Qālūn, Warsh,
al-Dūrī, al-Sūsī): an āyah count, not a word they don't read (data/usul basmalah: obligatory at a
sūrah's start, wafi 49). Counts are milestone 7.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
from collections import defaultdict
from functools import lru_cache

from mushaf_data.spine import projection, slot_data, words

from mushaf_data.occurrences import skel  # letters, wāw kept (kfgqpc.skel drops it: أَوَ would vanish)

from .kfgqpc import FILES, MIRROR

UNNUMBERED_BASMALAH = {"qalun", "warsh", "duri_abuamr", "susi"}
BASMALAH = ["1:1:1", "1:1:2", "1:1:3", "1:1:4"]


@lru_cache(maxsize=None)
def kwords(rawi: str) -> dict[int, list[str]]:
    """KFGQPC's words per sūrah (āyah numbers and pause signs dropped)."""
    d = json.loads((MIRROR / FILES[rawi]).read_text(encoding="utf-8"))
    sk = "sura_no" if "sura_no" in d[0] else "sora"
    out: dict[int, list[str]] = defaultdict(list)
    for a in d:
        for w in a["aya_text"].replace("\xa0", " ").split():
            if not re.fullmatch("[٠-٩۰-۹]+|[ۖ-۞]", w):
                out[int(a[sk])].append(w)
    return out


def added_text(rawi: str, slot: str) -> str | None:
    """An added slot's word, read from the KFGQPC file the slot data names (the word after
    `after`'s word in that āyah)."""
    a = next(x for x in slot_data().get("added") or [] if x["id"] == slot)
    src = a["text"]["source"].split()[-1]
    kw = kwords(src)[int(slot.split(":")[0])]
    prev = skel(words()[a["after"]])
    for i, w in enumerate(kw[:-1]):
        if skel(w) == prev:
            return kw[i + 1]
    return None


MARKS = re.compile("[\u064b-\u065f\u0670\u06d6-\u06ed\u08f0-\u08f2\u0640]")


def letters(w: str) -> str:
    """A word's letters for comparing a block: marks dropped, alif kept (أَوۡ أَن ≠ وَأَن), hamzah
    seats folded to their letter (al-Sūsī's تُومِن for تُؤۡمِن), KFGQPC's ے as yāʾ."""
    w = MARKS.sub("", w).replace("\u06d2", "ي").replace("ى", "ي")
    return w.translate(str.maketrans("أإآٱؤئ", "ااااوي")).replace("ء", "")


def same_rasm(a: list[str], b: list[str]) -> bool:
    """The block's slots and KFGQPC words carry the same letters, cut differently. The nūn of أن /
    من written apart before لا لو لن ما (maqṭūʿ in KFGQPC, mawṣūl in Ḥafṣ: وَأَن لَّوِ / وَأَلَّوِ)
    is ignored."""
    x, y = ("".join(letters(w) for w in ws) for ws in (a, b))
    fold = lambda k: re.sub("ن(?=[لم])", "", k)  # noqa: E731
    return bool(x) and fold(x) == fold(y)


def align(rawi: str, surah: int) -> list[dict]:
    """The gaps of one riwāyah in one sūrah: blocks that don't align."""
    h = words()
    proj = [s for s in projection(rawi) if int(s.split(":")[0]) == surah]
    if surah == 1 and rawi in UNNUMBERED_BASMALAH:
        proj = [s for s in proj if s not in BASMALAH]
    text = {s: h.get(s) or added_text(rawi, s) or "" for s in proj}
    A = [skel(text[s]) for s in proj]
    kw = kwords(rawi)[surah]
    B = [skel(w) for w in kw]
    ops = [o for o in difflib.SequenceMatcher(None, A, B, autojunk=False).get_opcodes()]
    # neighbouring non-equal opcodes are one block
    blocks, cur = [], None
    for tag, i1, i2, j1, j2 in ops:
        if tag == "equal":
            if cur:
                blocks.append(cur)
                cur = None
            continue
        cur = [cur[0], i2, cur[2], j2] if cur else [i1, i2, j1, j2]
    if cur:
        blocks.append(cur)
    gaps = []
    T = [text[s] for s in proj]
    for i1, i2, j1, j2 in blocks:
        if i2 - i1 == j2 - j1 or same_rasm(T[i1:i2], kw[j1:j2]):
            continue
        # one side empty: the block may be joined to the word beside it (أَن لَّن written أَلَّن)
        if (i1 == i2 or j1 == j2) and any(
                same_rasm(T[a1:a2], kw[b1:b2]) for a1, a2, b1, b2 in
                ((i1 - 1, i2, j1 - 1, j2), (i1, i2 + 1, j1, j2 + 1)) if a1 >= 0 and b1 >= 0):
            continue
        gaps.append({"rawi": rawi, "surah": surah, "slots": proj[i1:i2], "spine": [text[s] for s in proj[i1:i2]],
                     "kfgqpc": kw[j1:j2]})
    return gaps


def check() -> dict:
    out = {"gaps": [], "riwayat": 0}
    for rawi in FILES:
        out["riwayat"] += 1
        for s in range(1, 115):
            out["gaps"] += align(rawi, s)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    r = check()
    print(f"KFGQPC's {r['riwayat']} riwāyāt against the spine's projections: {len(r['gaps'])} gaps")
    if a.show:
        for g in r["gaps"]:
            print("  ", g["rawi"], g["surah"], g["slots"], " ".join(g["spine"]), "|", " ".join(g["kfgqpc"]))


if __name__ == "__main__":
    main()
