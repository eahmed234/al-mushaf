"""Classify how a reading's word differs from the Hafs word (spike, Day 2).

The idea under test: uṣūl differences are regular enough to be recognised by rule from the
letters alone, and whatever is left over is farsh. `classify(hafs, other)` returns the uṣūl
kinds it found and whether a farsh residue remains.

Rules (each removes one uṣūl kind from both words before comparing):
  madd     maddah U+0653 (length is a feature, not a letter)
  silah    small waw/yeh U+06E5/U+06E6 after mim or ha' (with any maddah on them); the mim or
           ha' takes a vowel
  (imala's dot replaces the fatha of its letter)
  imala    the imalah/taqlil dot below U+065C
  idgham   a shaddah on the first letter (assimilation from the word before)
  sakt     the small sin U+06DC after a letter (a pause without breath)
  final_vowel  the last letter's vowel dropped: a pausal form where a quote stops, or the
           first word of an idgham kabir
  hamz     hamza in any form (incl. idkhal: a dagger alef on a hamza), the tas-hil dot U+06EC on or after a hamza place, the
           standalone-dot letter (tatweel + U+06EC): hamza letters are reduced to their carrier
           or dropped, and the vowels on a hamza place and the letter before it are ignored
           (naql moves the vowel back; ibdal and hadhf change the vowel before)
Style only, always ignored: pause signs, sukun forms, open tanwin forms.
"""

from __future__ import annotations

import unicodedata

from .text import clusters

PAUSE = set("\u06d6\u06d7\u06d8\u06d9\u06da\u06db\u06de\u06e9")  # not U+06DC, the sign of sakt
SUKUN = {"ْ", "ۡ"}
OPEN_TANWIN = {"ࣰ": "ً", "ࣱ": "ٌ", "ࣲ": "ٍ"}
HAMZA_BASE = {"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",
              "ؤ": "و", "ئ": "ي", "ء": ""}
HAMZA_MARKS = {"ٔ", "ٕ"}
VOWELS = set("ًٌٍَُِ")


def _letters(word: str) -> list[dict]:
    """Clusters as {base, marks, hamza}: with style differences removed (pause signs, sukun
    forms, open tanwin, alef maksura vs yeh, and a tatweel that only carries a dagger alef)."""
    out = []
    for cl in clusters(word):
        base, marks = cl[0], [m for m in cl[1:]]
        if base == "\u0640" and "\u06ec" not in marks and out:
            out[-1]["marks"] += [OPEN_TANWIN.get(m, m) for m in marks if m not in PAUSE and m not in SUKUN]
            continue
        base = "\u064a" if base == "\u0649" else base
        marks = [OPEN_TANWIN.get(m, m) for m in marks if m not in PAUSE and m not in SUKUN]
        out.append({"base": base, "marks": marks, "hamza": False})
    return out


def _strip(word: str) -> tuple[list[dict], set[str]]:
    """Remove the uṣūl kinds; return the letters left and the kinds that were present."""
    kinds: set[str] = set()
    ls = _letters(word)
    res: list[dict] = []
    for k, c in enumerate(ls):
        b, ms = c["base"], c["marks"]
        if "ٓ" in ms:
            kinds.add("madd")
            ms = [m for m in ms if m != "ٓ"]
        if "\u06dc" in ms:
            kinds.add("sakt")  # the small sin after a letter: a pause without breath
            ms = [m for m in ms if m != "\u06dc"]
        imala_here = "ٜ" in ms
        if imala_here:
            kinds.add("imala")  # the dot replaces the fatha
            ms = [m for m in ms if m not in ("ٜ", "َ")]
        if k == 0 and "ّ" in ms:
            kinds.add("idgham")  # recorded; removed only if the other word lacks it (see classify)
        if b in ("ۥ", "ۦ") and res and res[-1]["base"] in ("م", "ه"):
            kinds.add("silah")  # and the mim/ha' before it takes a vowel
            res[-1]["silah"] = True
            continue
        hamza = False
        if b == "ـ" and "۬" in ms:  # the standalone tas-hil dot: a softened hamza
            kinds.add("hamz")
            hamza, b = True, ""
        if "۬" in ms and (b in "اوي" or (res and res[-1]["hamza"])):
            kinds.add("hamz")
            hamza = True
            ms = [m for m in ms if m != "۬"]
        if b in HAMZA_BASE or HAMZA_MARKS & set(ms):
            hamza = True
            b = HAMZA_BASE.get(b, b)
            ms = [m for m in ms if m not in HAMZA_MARKS]
        if hamza and res:
            res[-1]["hamza_next"] = True
        if b == "" and not [m for m in ms if m not in VOWELS]:
            if res:
                res[-1]["hamza_next"] = True
            continue
        if hamza and "\u0670" in ms:  # idkhal: an alif between two hamzas
            kinds.add("hamz")
            ms = [m for m in ms if m != "\u0670"]
        res.append({"base": b, "marks": ms, "hamza": hamza, "imala": imala_here})
    return res, kinds


def classify(hafs: str, other: str) -> tuple[set[str], bool]:
    """(uṣūl kinds seen in either word that differ, farsh residue?)"""
    if hafs == other:
        return set(), False
    a, ka = _strip(hafs)
    b, kb = _strip(other)
    kinds = ka ^ kb  # a kind present in one word only
    # kinds present in both but different in detail (e.g. madd on different letters) count too
    if len(a) != len(b):
        # a hamza dropped with its carrier, or turned into a letter (ibdal to yeh/waw):
        # drop one letter next to a hamza place from the longer word
        longer, shorter = (a, b) if len(a) > len(b) else (b, a)
        fixed = None
        if len(longer) == len(shorter) + 1:
            for k, x in enumerate(longer):
                near = (x["hamza"] or x.get("hamza_next") or (k and longer[k - 1].get("hamza_next"))
                        or (0 < k <= len(shorter) and shorter[k - 1].get("hamza_next")))
                if near and x["base"] in "\u0627\u0648\u064a":
                    cand = longer[:k] + longer[k + 1 :]
                    if [c["base"] for c in cand] == [c["base"] for c in shorter]:
                        fixed = cand
                        break
        if fixed is None:
            return kinds, True
        a, b = (fixed, b) if len(a) > len(b) else (a, fixed)
        kinds.add("hamz")
    residue = False
    for k, (x, y) in enumerate(zip(a, b)):
        if x["base"] != y["base"]:
            residue = True
            continue
        near_hamza = x["hamza"] or y["hamza"] or x.get("hamza_next") or y.get("hamza_next")
        if x["hamza"] != y["hamza"]:
            kinds.add("hamz")  # a hamza on one side only: ibdal (يُؤۡمِنُونَ / يُومِنُونَ)
        mx, my = list(x["marks"]), list(y["marks"])
        if k == 0 and ("ّ" in mx) != ("ّ" in my):
            kinds.add("idgham")
            mx = [m for m in mx if m != "ّ"]
            my = [m for m in my if m != "ّ"]
        last = k == len(a) - 1
        if last and (set(mx) & VOWELS) != (set(my) & VOWELS) and not (set(mx) & VOWELS and set(my) & VOWELS):
            kinds.add("final_vowel")  # pausal form where a quote stops, or idgham kabir
            mx = [m for m in mx if m not in VOWELS]
            my = [m for m in my if m not in VOWELS]
        if x.get("imala") or y.get("imala"):
            mx = [m for m in mx if m != "َ"]
            my = [m for m in my if m != "َ"]
        if x.get("silah") or y.get("silah"):
            mx = [m for m in mx if m not in VOWELS]
            my = [m for m in my if m not in VOWELS]
        if near_hamza:
            mx = [m for m in mx if m not in VOWELS]
            my = [m for m in my if m not in VOWELS]
            if x["marks"] != y["marks"]:
                kinds.add("hamz")
        if sorted(mx) != sorted(my):
            residue = True
    if not residue and not kinds:
        kinds.add("style")
    return kinds, residue


def describe(hafs: str, other: str) -> str:
    kinds, residue = classify(hafs, other)
    parts = sorted(kinds) + (["FARSH"] if residue else [])
    return "+".join(parts) or "same"


if __name__ == "__main__":
    import sys

    print(describe(sys.argv[1], sys.argv[2]))
