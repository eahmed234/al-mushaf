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

import re

from dataclasses import dataclass

from .text import clusters

MADDAH, SHADDA, SUKUN = "ٓ", "ّ", "ۡ"
FATHA, DAMMA, KASRA = "َ", "ُ", "ِ"
TANWIN = {"\u064b", "\u064c", "\u064d", "\u08f0", "\u08f1", "\u08f2", "\u0656", "\u0657", "\u065e"}  # incl. KFGQPC open tanwin
VOWELS = {FATHA, DAMMA, KASRA} | TANWIN
DAGGER, IMALA, TASHIL = "\u0670", "\u065c", "\u06ec"
SMALL_WAW, SMALL_YEH, SMALL_SIN = "ۥ", "ۦ", "ۜ"
HAMZA_START = ("أ", "إ", "ء", "آ")
PAUSE = set("\u06d6\u06d7\u06d8\u06d9\u06da\u06db\u06de\u06e9")  # not U+06DC, the sign of sakt

FEATURE_ONLY = {
    "muttasil": ["tawassut", "ishba"],
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


WAQF_CATS = {"ibdal_sakin", "hamzatayn"}  # hamz categories that a stop changes (Hamzah, Hisham)


def detect(words: list[tuple[str, str]], stop: str | None = None) -> list[Occ]:
    """Occurrences in `words`. `stop` is the word the reader stops on (waqf): a hamz category
    there becomes `<cat>_waqf`, and a hamza in that word gets `hamz_waqf_final` / `hamz_waqf_mid`."""
    out = _detect(words)
    for o in out:
        if o.word == stop and o.cat in WAQF_CATS:
            o.cat += "_waqf"
    if stop:
        w = dict(words).get(stop, "")
        cls = [c for c in (_core(c) for c in clusters(w)) if c]
        if len(cls) >= 3 and cls[0][0] in "\u0648\u0641\u0628\u0644\u0643\u0633" and len(cls[0]) == 2 \
                and cls[1][0] in "\u0623\u0625" and set(cls[1][1:]) & VOWELS:
            out.append(Occ("hamz_waqf_zaid", stop, None))  # وَأَبۡصَٰرِهِمۡ: made mid by a prefix (wafi 122-123)
        elif len(cls) >= 2 and cls[-1][0] == "\u0621" and cls[-2][0] == "\u0627":
            out.append(Occ("hamz_waqf_final", stop, None))  # ٱلسُّفَهَآءُ
        elif any(c[0] == "\u0621" and set(c[1:]) & VOWELS for c in cls[1:-1]):
            out.append(Occ("hamz_waqf_mid", stop, None))  # مُسۡتَهۡزِءُونَ
    return out


def _detect(words: list[tuple[str, str]]) -> list[Occ]:
    out: list[Occ] = []
    for i, (wid, w) in enumerate(words):
        nid, nw = words[i + 1] if i + 1 < len(words) else (None, "")
        cls = [_core(c) for c in clusters(w)]
        cls = [c for c in cls if c]
        if not cls:
            continue
        last = cls[-1]
        # munfasil: maddah on the last letter, next word starts with a hamza
        silent_alif = last[0] == "\u0627" and not set(last[1:]) & VOWELS and len(cls) >= 2
        if nw and nw[0] in HAMZA_START and (
                (MADDAH in last and last[0] in "\u0627\u0648\u064a\u0649")
                or (silent_alif and MADDAH in cls[-2] and cls[-2][0] in "\u0648\u064a")):  # قَالُوٓاْ
            out.append(Occ("munfasil", wid, nid))
        # silah of the plural mim
        bare_or_sakin = last.startswith("\u0645") and (SUKUN in last or not set(last[1:]) & VOWELS)  # هُم بِ (ikhfa')
        if bare_or_sakin and len(cls) >= 2 and cls[-2][0] in "\u0647\u0643\u062a" \
                and nw and not nw.startswith("\u0671"):
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
        # naql across words: a word starting with hamza after a word ending in a sakin consonant or
        # tanwin (عَذَابٌ أَلِيمٌ, خَلَوۡاْ إِلَىٰ); not after a long vowel
        if i and cls[0][0] in "\u0623\u0625" and set(cls[0][1:]) & {FATHA, DAMMA, KASRA}:
            pcl = [c for c in (_core(c) for c in clusters(words[i - 1][1])) if c]
            if pcl:
                plast = pcl[-1]
                if plast[0] == "\u0627" and len(pcl) >= 2 and not set(plast[1:]) & VOWELS:
                    plast = pcl[-2]  # a silent alif after waw (خَلَوۡاْ)
                if (SUKUN in plast or set(plast[1:]) & TANWIN) and MADDAH not in plast:
                    out.append(Occ("naql_word", wid, nid))
        # two hamzas at the start of a word (ءَأَنذَرۡتَهُمۡ)
        if len(cls) >= 2 and cls[0][0] in "\u0621\u0623" and FATHA in cls[0] and cls[1][0] in "\u0623\u0625" \
                and set(cls[1][1:]) & VOWELS:
            out.append(Occ("hamzatayn", wid, nid))
        # idgham of nun sakinah / tanwin into ya' or waw, which Hafs writes without a shadda
        tanwin = set(last[1:]) & TANWIN
        bare_nun = last == "\u0646"
        if nw and (tanwin or bare_nun):
            ncl = [c for c in (_core(c) for c in clusters(nw)) if c]
            if ncl and ncl[0][0] in "\u064a\u0648" and SHADDA not in ncl[0]:
                out.append(Occ("idgham_ghunna", wid, nid))
        # imalah: alif (or dagger alif) before a final ra' with kasra (أَبۡصَٰرِهِمۡ, ٱلنَّارِ)
        for k in range(len(cls) - 1):
            alif_here = DAGGER in cls[k] or (k + 1 < len(cls) and cls[k + 1] == "\u0627")
            ra_at = k + 1 if DAGGER in cls[k] else k + 2
            if alif_here and ra_at < len(cls) and cls[ra_at][0] == "\u0631" and KASRA in cls[ra_at] \
                    and all(c[0] in "\u0647\u0645\u0643\u06e5" for c in cls[ra_at + 1 :]):
                out.append(Occ("imala_ra", wid, nid))
                break
        sk = "".join(c[0] for c in cls)
        if sk.endswith("\u0646\u0627\u0633") and KASRA in cls[-1]:  # ٱلنَّاسِ in the genitive
            out.append(Occ("imala_nas", wid, nid))
        if "\u0643\u0641\u0631\u064a\u0646" in sk and any(DAGGER in c and c[0] == "\u0643" for c in cls):
            out.append(Occ("imala_kafirin", wid, nid))  # كَٰفِرِينَ
        if last[0] == "\u0649" and DAGGER in last and not tanwin:  # dhawat al-ya': ٱلۡهُدَىٰ
            ra = len(cls) >= 2 and cls[-2][0] == "\u0631"  # after rāʾ (ذِكۡرَىٰ): its own rule (wafi 147-148)
            out.append(Occ("imala_ya_ra" if ra else "imala_ya", wid, nid))
        # a maḍmūmah hamzah after a kasrah inside the word (مُسۡتَهۡزِءُونَ): Abū Jaʿfar drops it (idah 110)
        if any(c[0] == "\u0621" and DAMMA in c and KASRA in cls[k - 1] for k, c in enumerate(cls[1:-1], 1)):
            out.append(Occ("hadhf_damm", wid, nid))
        # word-list imālah (the books' lists, not a rule): Ḥamzah's past verbs (wafi 150-151),
        # al-Dūrī ʿan al-Kisāʾī's words (wafi 153-154)
        for cat, rx in WORD_IMALA:
            if rx.match(sk):
                out.append(Occ(cat, wid, nid))
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
    "naql_word": ["none", "naql"],
    "idgham_kabir": ["izhar", "idgham"],
    "sakt_huruf": ["none", "sakt"],
    "badal": ["qasr", "tawassut", "tul"],
    "ibdal_sakin_waqf": ["tahqiq", "ibdal"],
    "hamzatayn_waqf": ["tahqiq", "tashil", "tashil_idkhal", "tahqiq_idkhal", "ibdal"],
    "hamz_waqf_final": ["tahqiq", "ibdal_madd", "ibdal_qasr", "tashil_rawm_madd", "tashil_rawm_qasr"],
    "hamz_waqf_mid": ["tahqiq", "tashil", "hadhf", "ibdal_ya"],
    "hamzatayn": ["tahqiq", "tashil", "tashil_idkhal", "tahqiq_idkhal", "ibdal"],
    "idgham_ghunna": ["ghunna", "bila_ghunna"],
    "imala_ra": ["fath", "taqlil", "imala"],
    "imala_nas": ["fath", "imala"],
    "imala_kafirin": ["fath", "taqlil", "imala"],
    "imala_ya": ["fath", "taqlil", "imala"],
    "hadhf_damm": ["tahqiq", "hadhf"],
    "hamz_waqf_zaid": ["tahqiq", "tashil"],
    "imala_ya_ra": ["fath", "taqlil", "imala"],
    "imala_jaa_shaa": ["fath", "imala"],
    "imala_zad": ["fath", "imala"],
    "imala_fiil": ["fath", "imala"],
    "imala_duri_kisai": ["fath", "imala"],
    **FEATURE_ONLY,
}


_SUF = "(?:وا|ت|تا)?(?:هم|هما|كم|كما|نا|ه|ها|ك|ني|هن|كن)?$"
WORD_IMALA = [(c, re.compile(r)) for c, r in [
    ("imala_jaa_shaa", "^[وف]?(?:ل)?(?:جا|شا)ء" + _SUF),          # جَآءَ, شَآءَ (past)
    ("imala_zad", "^[وف]?زاد" + _SUF),                            # زَادَ
    ("imala_fiil", "^[وف]?(?:خاب|خاف|طاب|ضاق|حاق|زاغ)" + _SUF),  # Ḥamzah's other past verbs
    ("imala_duri_kisai", "^[وف]?(?:ب|ل)?(?:(?:ء?ا)ذان(?:هم|نا)|طغين(?:هم|ه)|انصاري|سارعوا|نسارع|يسرعون|يسارعون|الباري|بارئكم|الجوار)$"),
]]


def _imala(cat: str, cls: list[str]) -> list[str]:
    """The dot below (U+065C) replaces the fatha of the letter before the alif (taqlil and imala
    are written the same way; the label tells them apart)."""
    def dot(k):
        cls[k] = cls[k][0] + "".join(m for m in cls[k][1:] if m != FATHA) + IMALA

    if cat in ("imala_ya", "imala_ya_ra"):
        dot(len(cls) - 2)
    elif cat in ("imala_jaa_shaa", "imala_zad", "imala_fiil"):  # the verb's alif (شَآءَ: with maddah)
        k = next((k for k in range(len(cls) - 1) if cls[k + 1][0] == "\u0627"), None)
        if k is not None:
            dot(k)
    elif cat == "imala_duri_kisai":  # the last alif or dagger alif (ءَاذَٰنِهِمۡ: after the dhāl)
        ks = [k for k in range(len(cls) - 1) if DAGGER in cls[k] or cls[k + 1] == "\u0627"]
        if ks:
            dot(ks[-1])
    elif cat == "imala_nas":
        dot(len(cls) - 3)
    else:
        for k in range(len(cls) - 1):
            if DAGGER in cls[k] or cls[k + 1] == "\u0627":
                if cat == "imala_ra":
                    ra_at = k + 1 if DAGGER in cls[k] else k + 2
                    if not (ra_at < len(cls) and cls[ra_at][0] == "\u0631"):
                        continue
                dot(k)
                break
    return cls


# ---------------------------------------------------------------------------------------------
# Transforms: apply a choice (category -> wajh) to every occurrence in a list of words


def apply(words: list[tuple[str, str]], occs: list[Occ], choice: dict[str, str]) -> dict[str, str]:
    text = {wid: w for wid, w in words}
    by_word: dict[str, list[Occ]] = {}
    for o in occs:
        by_word.setdefault(o.word, []).append(o)
    prev = None
    for wid, w in words:
        cls = clusters(text[wid])
        for o in by_word.get(wid, []):
            wj = choice.get(o.cat)
            base_cat = o.cat[: -len("_waqf")] if o.cat.endswith("_waqf") and o.cat[: -len("_waqf")] in WAQF_CATS else o.cat
            if o.cat == "munfasil" and wj == "qasr":
                k = len(cls) - 1 if MADDAH in cls[-1] else len(cls) - 2
                cls[k] = cls[k].replace(MADDAH, "")
            elif o.cat in ("silah_mim", "silah_mim_hamza") and wj == "silah":
                madd = o.cat == "silah_mim_hamza" and choice.get("munfasil") != "qasr"
                cls[-1] = "\u0645" + DAMMA
                cls.append(SMALL_WAW + (MADDAH if madd else ""))
                if o.nxt:  # the mim no longer merges into a following mim (قُلُوبِهِمُۥ مَرَضٞ)
                    ncl = clusters(text[o.nxt])
                    if ncl[0][0] == "\u0645" and SHADDA in ncl[0]:
                        ncl[0] = ncl[0].replace(SHADDA, "")
                        text[o.nxt] = "".join(ncl)
            elif o.cat == "silah_ha" and wj == "silah":
                cls.append(SMALL_YEH if KASRA in cls[-1] else SMALL_WAW)
            elif base_cat == "ibdal_sakin" and wj == "ibdal":
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
                        if choice.get("badal") == "qasr":
                            rest = rest.replace(MADDAH, "")  # the badal's qasr shows once the hamza is gone
                        cls[k + 1] = "ا" + rest  # otherwise the maddah stays (badal)
                        break
            elif o.cat == "idgham_kabir" and wj == "idgham" and o.nxt:
                cls[-1] = "".join(c for c in cls[-1] if c not in VOWELS)
                ncl = clusters(text[o.nxt])
                ncl[0] = ncl[0][0] + SHADDA + ncl[0][1:]
                text[o.nxt] = "".join(ncl)
            elif o.cat == "naql_word" and wj == "naql" and not (prev and text[prev].rstrip("\u0653").endswith((SMALL_WAW, SMALL_YEH))):
                # (no naql after a word that now ends in a silah madd: ءَأَنذَرۡتَهُمُۥٓ أَمۡ)
                vowel = "".join(m for m in cls[0][1:] if m in (FATHA, DAMMA, KASRA))
                rest = "".join(m for m in cls[0][1:] if m not in (FATHA, DAMMA, KASRA))
                cls[0] = "\u0627" + vowel + rest  # the hamza goes; the word before takes its vowel
            elif base_cat == "hamzatayn" and wj not in (None, "tahqiq"):
                first, second = cls[0], cls[1]
                if wj in ("tashil_idkhal", "tahqiq_idkhal"):
                    first = first + DAGGER  # idkhal: an alif between the two hamzas
                if wj in ("tashil", "tashil_idkhal"):
                    second = "\u0627" + TASHIL  # the second hamza softened
                elif wj == "ibdal":
                    second = "\u0627" + MADDAH  # the second hamza turned into a long alif
                cls[0], cls[1] = first, second
            elif o.cat == "hamz_waqf_final" and wj not in (None, "tahqiq"):
                h = cls[-1]
                vowel = "".join(m for m in h[1:] if m in VOWELS)
                cls = cls[:-1]
                if wj.endswith("qasr"):
                    cls[-1] = cls[-1].replace(MADDAH, "")
                if wj.startswith("tashil"):
                    cls.append("\u0640" + vowel + TASHIL)  # the softened hamza with rawm of its vowel
            elif o.cat in ("hamz_waqf_mid", "hadhf_damm") and wj not in (None, "tahqiq") and \
                    (k := next((k for k, c in enumerate(cls) if k and c[0] == "\u0621" and set(c[1:]) & VOWELS), None)):
                # (None once another category has already dropped the hamza)
                vowel = "".join(m for m in cls[k][1:] if m in VOWELS)
                if wj == "tashil":
                    cls[k] = "\u0640" + TASHIL
                elif wj == "hadhf":  # the hamza goes, its vowel moves back
                    cls[k - 1] = cls[k - 1][0] + "".join(m for m in cls[k - 1][1:] if m not in VOWELS) + vowel
                    del cls[k]
                elif wj == "ibdal_ya":
                    cls[k] = "\u064a" + vowel
            elif o.cat == "hamz_waqf_zaid" and wj == "tashil":
                cls[1] = "\u0627" + TASHIL + "".join(m for m in cls[1][1:] if m not in VOWELS)
            elif o.cat == "idgham_ghunna" and wj == "bila_ghunna" and o.nxt:
                ncl = clusters(text[o.nxt])
                ncl[0] = ncl[0][0] + SHADDA + ncl[0][1:]
                text[o.nxt] = "".join(ncl)
            elif o.cat.startswith("imala_") and wj in ("taqlil", "imala"):
                cls = _imala(o.cat, cls)
            elif o.cat == "sakt_huruf" and wj == "sakt":
                cls = [c + SMALL_SIN if k < len(cls) - 1 else c for k, c in enumerate(cls)]
        text[wid] = "".join(cls)
        prev = wid
    return text
