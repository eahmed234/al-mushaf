"""Day 3: uṣūl as rules. Detectors find where a category applies in the Hafs text; each wajh is
a transform of the word (and sometimes its neighbour). Profiles (which wujūh a rawi has) are not
written here: they are learned from al-Futuh's rows (`spike.profile`).

Categories that change the written text (the ones a text comparison can check):

  munfasil      a madd letter with maddah at a word's end, before a hamza starting the next word.
                qasr drops the maddah; tawassut and ishba keep it (they differ only in length).
  silah_mim     a mim of the plural with sukun at a word's end, before a moving letter: sukun or
                silah (mim takes damma + small waw; before a hamza the waw gets a maddah unless
                munfasil is qasr). Split by what follows: `silah_mim` (no hamza next) and
                `silah_mim_hamza` (hamza next), since some ruwat differ there.
  silah_ha      the ha' of the pronoun after a sakin, before a moving letter: none or silah
                (small yeh after kasra, small waw after damma).
  ibdal_sakin   a hamza with sukun inside a word: kept, or replaced by its carrier letter.
  naql          ٱلۡ + a hamza starting the rest of the word: kept, or the hamza's vowel moves to the
                lam and the hamza is dropped (a maddah on it stays: that is a badal madd).
  idgham_kabir  a word ending in the letter the next word starts with: none, or the first
                loses its vowel and the second takes a shadda.
  sakt_huruf    the separate letters of a muqatta'ah (الٓمٓ): none, or a small sin (U+06DC) after
                each letter but the last.

Categories that leave the text alone (length, pause, tone) are listed in FEATURE_ONLY; Day 3
reads them from the row labels.
"""

from __future__ import annotations

from dataclasses import dataclass

from .text import clusters

MADDAH, SHADDA, SUKUN = "ٓ", "ّ", "ۡ"
FATHA, DAMMA, KASRA = "َ", "ُ", "ِ"
VOWELS = {FATHA, DAMMA, KASRA, "ً", "ٌ", "ٍ", "ࣰ", "ࣱ", "ࣲ"}
SMALL_WAW, SMALL_YEH, SMALL_SIN = "ۥ", "ۦ", "ۜ"
HAMZA_START = ("أ", "إ", "ء", "آ")
PAUSE = set("\u06d6\u06d7\u06d8\u06d9\u06da\u06db\u06de\u06e9")  # not U+06DC, the sign of sakt

FEATURE_ONLY = {
    "muttasil": ["tawassut", "ishba"],
    "badal": ["qasr", "tawassut", "tul"],
    "sakt_al": ["none", "sakt"],
    "sakt_mafsul": ["none", "sakt"],
    "tarqiq_ra": ["tafkhim", "tarqiq"],
    "taghliz_lam": ["tarqiq", "taghliz"],
}


def _core(cl: str) -> str:
    """A cluster without pause signs."""
    return "".join(c for c in cl if c not in PAUSE)


@dataclass
class Occ:
    cat: str
    word: str  # word id
    nxt: str | None  # next word id (for transforms that touch it)


# ---------------------------------------------------------------------------------------------
# Detectors: (words: list of (id, text)) -> occurrences


def detect(words: list[tuple[str, str]]) -> list[Occ]:
    out: list[Occ] = []
    for i, (wid, w) in enumerate(words):
        nid, nw = words[i + 1] if i + 1 < len(words) else (None, "")
        cls = [_core(c) for c in clusters(w)]
        cls = [c for c in cls if c]
        if not cls:
            continue
        last = cls[-1]
        # munfasil: maddah on the last letter, next word starts with a hamza
        if MADDAH in last and last[0] in "اويى" and nw and nw[0] in HAMZA_START:
            out.append(Occ("munfasil", wid, nid))
        # silah of the plural mim
        if last.startswith("م") and SUKUN in last and len(cls) >= 2 and cls[-2][0] in "هكت" \
                and nw and not nw.startswith("ٱ"):
            out.append(Occ("silah_mim_hamza" if nw[0] in HAMZA_START else "silah_mim", wid, nid))
        # silah of the pronoun ha' after a sakin (here: after a long vowel letter)
        if last[0] == "ه" and (KASRA in last or DAMMA in last) and len(cls) >= 2 and cls[-2][0] in "يوا" \
                and not set(cls[-2][1:]) & VOWELS and nw and not nw.startswith("ٱ"):
            out.append(Occ("silah_ha", wid, nid))
        # hamza with sukun inside a word
        for k, c in enumerate(cls):
            if k and c[0] in "أؤئ" and SUKUN in c:
                out.append(Occ("ibdal_sakin", wid, nid))
                break
        # naql on the article: (prefix) ٱلۡ + hamza
        for k in range(len(cls) - 1):
            if cls[k][0] == "ل" and k and cls[k - 1][0] == "ٱ" and SUKUN in cls[k] and cls[k + 1][0] in HAMZA_START:
                out.append(Occ("naql", wid, nid))
                out.append(Occ("sakt_al", wid, nid))
                break
        # idgham kabir: same letter at the end of this word and the start of the next, both moving
        if nw:
            ncl = [c for c in (_core(c) for c in clusters(nw)) if c]
            if ncl and last[0] == ncl[0][0] and set(last[1:]) & VOWELS and last[0] not in "اويى":
                out.append(Occ("idgham_kabir", wid, nid))
        # separate letters of a muqatta'ah: every letter carries a maddah or is a bare alif
        if len(cls) >= 2 and all(MADDAH in c or c == "ا" for c in cls) and wid.endswith(":1:1"):
            out.append(Occ("sakt_huruf", wid, nid))
        # badal: a hamza followed by a madd (أٓ, or ءَا)
        for k, c in enumerate(cls):
            if c[0] in "\u0621\u0623" and (MADDAH in c or (FATHA in c and k + 1 < len(cls) and cls[k + 1] == "\u0627")):
                out.append(Occ("badal", wid, nid))
                break
        # muttasil: maddah on a madd letter followed by a hamza in the same word
        for k in range(len(cls) - 1):
            if MADDAH in cls[k] and cls[k + 1][0] in "ءئؤأ":
                out.append(Occ("muttasil", wid, nid))
                break
    return out


WUJUH = {
    "munfasil": ["qasr", "tawassut", "ishba"],
    "silah_mim": ["sukun", "silah"],
    "silah_mim_hamza": ["sukun", "silah"],
    "silah_ha": ["none", "silah"],
    "ibdal_sakin": ["tahqiq", "ibdal"],
    "naql": ["none", "naql"],
    "idgham_kabir": ["izhar", "idgham"],
    "sakt_huruf": ["none", "sakt"],
    **FEATURE_ONLY,
}


# ---------------------------------------------------------------------------------------------
# Transforms: apply a choice (category -> wajh) to every occurrence in a list of words


def apply(words: list[tuple[str, str]], occs: list[Occ], choice: dict[str, str]) -> dict[str, str]:
    text = {wid: w for wid, w in words}
    by_word: dict[str, list[Occ]] = {}
    for o in occs:
        by_word.setdefault(o.word, []).append(o)
    for wid, w in words:
        cls = clusters(text[wid])
        for o in by_word.get(wid, []):
            wj = choice.get(o.cat)
            if o.cat == "munfasil" and wj == "qasr":
                cls[-1] = cls[-1].replace(MADDAH, "")
            elif o.cat in ("silah_mim", "silah_mim_hamza") and wj == "silah":
                madd = o.cat == "silah_mim_hamza" and choice.get("munfasil") != "qasr"
                cls[-1] = "م" + DAMMA
                cls.append(SMALL_WAW + (MADDAH if madd else ""))
            elif o.cat == "silah_ha" and wj == "silah":
                cls.append(SMALL_YEH if KASRA in cls[-1] else SMALL_WAW)
            elif o.cat == "ibdal_sakin" and wj == "ibdal":
                carrier = {"أ": "ا", "ؤ": "و", "ئ": "ي"}
                for k, c in enumerate(cls):
                    if k and c[0] in carrier and SUKUN in c:
                        cls[k] = carrier[c[0]] + "".join(m for m in c[1:] if m != SUKUN)
                        break
            elif o.cat == "naql" and wj == "naql":
                for k in range(len(cls) - 1):
                    if cls[k][0] == "ل" and cls[k + 1][0] in HAMZA_START:
                        h = cls[k + 1]
                        vowel = next((m for m in h[1:] if m in (FATHA, DAMMA, KASRA)), FATHA)
                        cls[k] = "ل" + vowel
                        rest = "".join(m for m in h[1:] if m not in (FATHA, DAMMA, KASRA))
                        cls[k + 1] = "ا" + rest  # a maddah on the hamza stays (badal)
                        break
            elif o.cat == "idgham_kabir" and wj == "idgham" and o.nxt:
                cls[-1] = "".join(c for c in cls[-1] if c not in VOWELS)
                ncl = clusters(text[o.nxt])
                ncl[0] = ncl[0][0] + SHADDA + ncl[0][1:]
                text[o.nxt] = "".join(ncl)
            elif o.cat == "sakt_huruf" and wj == "sakt":
                cls = [c + SMALL_SIN if k < len(cls) - 1 else c for k, c in enumerate(cls)]
        text[wid] = "".join(cls)
    return text
