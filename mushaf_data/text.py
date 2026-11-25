"""One internal encoding for Qur'anic text (spike, Day 1).

Sources write the same thing with different codepoints. Everything the spike reads goes through
`normalize`, so later comparisons are about readings, not encodings. The target is the KFGQPC
v2.0 Hafs encoding the spine uses. Each rule says what it changes and why; nothing here changes
what a word says.
"""

from __future__ import annotations

import unicodedata

TATWEEL = "ـ"
SHADDA = "ّ"

# Mark order inside one letter: KFGQPC writes shadda before the vowel (U+0651 U+064E), which
# is the reverse of Unicode canonical order, so NFC/NFD can't be used. We sort marks into
# these ranks, keeping the source order within a rank.
_RANK = {SHADDA: 0}
for c in "ًࣰٌࣱٍࣲَُِْۡ":
    _RANK[c] = 1  # vowels, tanwin (incl. open tanwin), sukun (both forms)
_RANK["ٓ"] = 2  # maddah


def _is_mark(c: str) -> bool:
    return unicodedata.category(c) == "Mn"


def clusters(word: str) -> list[str]:
    """Split a word into letters: one base character plus the marks after it.

    Small waw/yeh (U+06E5/U+06E6, category Lm) count as bases: they are written letters of
    silah. A leading mark with no base (rare in quotes) forms its own cluster."""
    out: list[str] = []
    for c in word:
        if _is_mark(c) and out:
            out[-1] += c
        else:
            out.append(c)
    return out


def _sort_marks(cl: str) -> str:
    base, marks = cl[0], cl[1:]
    if _is_mark(base):
        return cl
    return base + "".join(sorted(marks, key=lambda m: _RANK.get(m, 3)))


def normalize(word: str) -> str:
    """Internal encoding of one word.

    1. Precomposed alef with maddah (U+0622) -> alef + maddah (U+0627 U+0653), as in the spine.
       (al-Futuh glyph 60.)
    2. Tatweel used as a stretch between letters is dropped; tatweel that carries a mark
       (e.g. before a dagger alef in أُوْلَـٰٓئِكَ) is kept, since the spine has it.
    3. Marks inside a letter are put in one order (shadda, vowel/sukun/tanwin, maddah, rest).
    """
    w = word.replace("آ", "آ")
    kept = []
    for i, c in enumerate(w):
        if c == TATWEEL:
            nxt = w[i + 1] if i + 1 < len(w) else ""
            if not (nxt and _is_mark(nxt)):
                continue
        kept.append(c)
    return "".join(_sort_marks(cl) for cl in clusters("".join(kept)))


def drop_shadda_first(word: str) -> str:
    """The word without a shadda on its first letter (for quote-boundary comparison)."""
    cls = clusters(word)
    if cls:
        cls[0] = cls[0].replace(SHADDA, "")
    return "".join(cls)
