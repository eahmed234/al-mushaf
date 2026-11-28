"""Which case of an uṣūl table a word belongs to, where the category alone doesn't say.

    case_for(cat, word, k, nxt="")   the table case for the word (k when the word doesn't decide)
    refine(occs, words, stop)        the engine's occurrences, each moved to the category of its case

The tables (data/usul) have finer cases than the engine's categories: the hamzatayn's second hamzah
maftūḥah / maksūrah / maḍmūmah, the sākin hamzah as fāʾ / ʿayn / lām of the word, imālah after a
rāʾ, on the faʿlā words, or before a sākin in waṣl. The engine detects a category (usul.detect),
and `refine` gives the occurrence the sub-category of its case (SUBCATS), keeping the detector's
category as `base` (the transform). The al-Budūr crosscheck (pipeline.crosscheck_budur) reads the
same `case_for`, so the check and the engine can't drift apart.

Moved here from pipeline/crosscheck_budur (2026-11-28, docs/06 §3 item 2).
"""
from __future__ import annotations

import re

# al-Wāfī p. 150: the words on fuʿlā, faʿlā and fiʿlā (alif al-taʾnīth), Abū ʿAmr's taqlīl
FAALA = """موسى أنثى الدنيا قربى الوسطى القصوى العزى الوثقى الحسنى الأولى السفلى العليا الرؤيا طوبى المثلى
السوأى زلفى سقيا الرجعى عقبى السلوى الموتى التقوى النجوى القتلى مرضى دعوى شتى صرعى طغوى يحيى سيما إحدى
ضيزى عيسى""".split()
SUFFIX = re.compile(r"(?:هما|هم|ها|ه|كم)$")

# imālah table cases (data/usul/imala.yaml; tests hold the names to these numbers)
IMALA_YA_RA, ALIF_TANITH = 4, 9
WASL_SAKIN = 11  # the alif before a sākin in the next word, in waṣl (wafi 156); +1 after a rāʾ

# sub-category → (table, case, the category a taḥrīr constraint written for the base reads it as).
# A sub-category's wujūh are its base's (usul.WUJUH); `refine` names the base per occurrence.
SUBCATS = {
    "hamzatayn_maksurah": ("hamzatayn", 1, "hamzatayn"),        # أَئِنَّكُمۡ
    "hamzatayn_madmumah": ("hamzatayn", 2, "hamzatayn"),        # أَؤُنَبِّئُكُم (wafi 90-91)
    "ibdal_sakin_ayn": ("ibdal_sakin", 1, "ibdal_sakin"),       # بِئۡسَ, ٱلذِّئۡبُ
    "ibdal_sakin_lam": ("ibdal_sakin", 2, "ibdal_sakin"),       # جِئۡتَ, نَشَأۡ
    "imala_alif_tanith": ("imala", ALIF_TANITH, "imala_ya"),    # مُوسَىٰ (wafi 150)
    # waṣl before a sākin: the alif goes, so a constraint on the stop's imālah doesn't bind it
    "imala_wasl_sakin": ("imala", WASL_SAKIN, None),
    "imala_wasl_sakin_ra": ("imala", WASL_SAKIN + 1, None),
}
# (detector category, case) → the engine category of that case
_TO = {("imala_ya", IMALA_YA_RA): "imala_ya_ra", ("imala_ya", ALIF_TANITH): "imala_alif_tanith",
       ("hamzatayn", 1): "hamzatayn_maksurah", ("hamzatayn", 2): "hamzatayn_madmumah",
       ("ibdal_sakin", 1): "ibdal_sakin_ayn", ("ibdal_sakin", 2): "ibdal_sakin_lam"}


def skel(word: str) -> str:
    from .occurrences import skel as _skel  # (occurrences imports the engine)
    return _skel(word)


# what may follow a hamzah that is the word's lām: a verb's ending, then pronouns (alifs kept; no
# bare yāʾ or nūn: رِءۡيٗا, شَأۡنٞ, شَأۡنِهِمۡ are ʿayn)
LAM_TAIL = re.compile("(?:تموا|تمو|تما|تم|تن|ت|نا|وا|و)?(?:هما|هم|هن|ها|ه|كما|كم|كن|ك|نا|ني|ون|ين)*ا?")
PREP = {"ب": {"\u0650"}, "ل": {"\u064e", "\u0650"}, "ك": {"\u064e"}}
MUDARI = "يتنمأ"


def sakin_hamzah(word: str) -> tuple[bool, str | None]:
    """(the word's sākin hamzah comes right after its prefixes, i.e. is its fāʾ; the letters after
    it, alifs kept). Prefixes, in order: the istifhām أَ, a conjunction وَ فَ, a preposition بِ لِ
    كَ or the future سَ or the command لۡ, the article, an imperfect or participle letter (يتنمأ),
    the istafʿala سۡتَ. A preposition is one only if three letters are left (بِئۡسَ's bāʾ is the
    word's). skel drops a hamzah on an alif (نَشَأۡ), and the first hamzah isn't always the sākin
    one (أَنۢبِئۡهُم). (False, None) when there is no sākin hamzah."""
    from .text import clusters
    raw = [c for c in clusters(word) if c]
    ham = lambda c: c[0] in "أإؤئء" or "\u0654" in c  # noqa: E731
    pos = next((i for i, c in enumerate(raw) if i and ham(c) and "\u06e1" in c), None)
    if pos is None:
        return False, None
    letters = lambda cs: sum(1 for c in cs if c[0] not in "اٱـ" or ham(c))  # noqa: E731
    k = 0
    if raw[k][0] == "أ" and "\u064e" in raw[k] and k + 1 < pos and raw[k + 1][0] in MUDARI + "وف":
        k += 1  # أَتَأۡمُرُونَ
    if k < pos and raw[k][0] in "وف" and len(raw) - k > 2 and "\u064e" in raw[k]:
        k += 1
    if k + 1 < pos and raw[k][0] in PREP and set(raw[k][1:]) - {"\u0651"} <= PREP[raw[k][0]] and letters(raw[k + 1:]) >= 3:
        k += 1  # (not right before the hamzah: بِئۡسَ, بِئۡرٖ)
    elif k < pos and raw[k][0] == "س" and "\u064e" in raw[k] and raw[k + 1][0] in MUDARI:
        k += 1  # سَيُؤۡتِينَا
    elif k < pos and raw[k][0] == "ل" and "\u06e1" in raw[k] and raw[k + 1][0] in MUDARI:
        k += 1  # وَلۡيُؤۡمِنُواْ
    while k < pos and raw[k][0] in "اٱ":
        k += 1
    if k < pos and raw[k][0] == "ل" and ("\u06e1" in raw[k] or len(raw[k]) == 1) and \
            any(c[0] == "ٱ" for c in raw[:k]) or (k and k < pos and raw[k][0] == "ل" and raw[k - 1][0] == "ل"):
        k += 1  # the article (ٱلۡ, ٱل before a sun letter, لِلۡ)
    if k < pos and raw[k][0] in MUDARI and set(raw[k][1:]) & {"\u064e", "\u064f"}:
        k += 1
    if k + 1 < pos and raw[k][0] == "س" and "\u06e1" in raw[k] and raw[k + 1][0] == "ت":
        k += 2  # تَسۡتَأۡنِسُواْ, ٱسۡتَـٔۡذَنَكَ
    tail = "".join("\u064a" if c[0] == "\u0649" else c[0] + ("ا" if "\u0670" in c else "")
                   for c in raw[pos + 1:] if c[0] not in "ـ")
    return k == pos, re.sub("[^ء-ي]", "", tail)


def key(word: str) -> tuple[str, bool]:
    """Skeleton plus whether the word starts with an alif or hamzah (skel drops both: أزكى ≠ زكى)."""
    from tools import book
    return skel(word), book.fold(word).lstrip("وفبل")[:1] in ("ا", "ء")


def hskel(word: str) -> str:
    """skel with every hamzah kept as ء (skel drops one on an alif: أَدۡنَىٰ would be دنيا's)."""
    from tools import book
    w = re.sub("آ(?=[\u064b-\u065f\u06d6-\u06ed]*$)", "ا", word)  # a final آ is a madd alif (ٱلدُّنۡيَآ إِلَّا)
    w = re.sub("[أإؤئ\u0654]", "ء", w).replace("آ", "ء")
    return re.sub("[^ء-ي]|[اـ]", "", book.fold(w).replace("ى", "ي"))


def stem(word: str) -> str:
    """The skeleton without a pronoun suffix (prefixes are left: matching is by the word's end)."""
    return SUFFIX.sub("", skel(word))


_FAALA_SK = None


def _bare(word: str) -> str:
    """Letters only, a dagger alif as an alif (سِيمَٰهُمۡ), but not the one on an alif maqṣūrah (مُوسَىٰ)."""
    w = re.sub("[\u064b-\u065f\u06d6-\u06ed]", "", word)  # (marks first: the spine may put the maddah before the dagger, 2:51:3)
    return w.replace("\u0649\u0670", "\u0649").replace("\u0670", "ا")


def _ends_alif(word: str) -> bool:
    return _bare(word)[-1:] in ("ا", "آ")


def faala(word: str) -> bool:
    """A word on fuʿlā/faʿlā/fiʿlā of al-Wāfī p. 150's list: its skeleton ends in one of the list's,
    after prefixes only, and it ends as that word does (ٱلدُّنۡيَا in an alif, مُوسَىٰ in ى: العليا
    is not عَلَىٰ)."""
    global _FAALA_SK
    if _FAALA_SK is None:
        _FAALA_SK = {(hskel(w[2:] if w.startswith("ال") else w), _ends_alif(w)) for w in FAALA}
    st = SUFFIX.sub("", hskel(word))
    alif = _ends_alif(SUFFIX.sub("", _bare(word)))
    # what comes before the word is prefixes only (وَٱلسَّلۡوَىٰ, يَٰمُوسَىٰ), not a verb's letters (ٱسۡتَسۡقَىٰ ≠ سقيا)
    return any(st.endswith(f) and a == alif and len(st) - len(f) <= 3 and set(st[: len(st) - len(f)]) <= set("وفبلكي")
               for f, a in _FAALA_SK)


def case_for(cat: str, word: str, k: int, nxt: str = "") -> int:
    """The table case the word belongs to, where the category alone doesn't say: imālah (after a
    rāʾ: ذوات الراء; on fuʿlā/faʿlā/fiʿlā: alif al-taʾnīth, wafi 150; a final alif before a sākin
    in waṣl, wafi 155-156), the sākin hamzah (fāʾ, ʿayn, lām of the word), the second hamzah of two
    in a word (its vowel). `nxt` is the next word in waṣl ("" at a stop)."""
    if cat.startswith("imala") and nxt.startswith("ٱ") and re.search("[ىا][ٰ]?[ً-ٟۖ-ۭ]*$", word):
        return WASL_SAKIN + (stem(word)[-2:-1] == "ر")  # a final alif; after a rāʾ, al-Sūsī's khulf
    if cat == "imala_ya":
        st = stem(word)
        if st[-2:-1] == "ر":
            return IMALA_YA_RA
        if faala(word):
            return ALIF_TANITH
    if cat == "ibdal_sakin":
        fa, tail = sakin_hamzah(word)
        if fa:
            return 0  # fāʾ: يُؤۡمِنُونَ, ٱلۡمَأۡوَىٰ, فَأۡتُواْ
        if tail is not None and LAM_TAIL.fullmatch(tail):
            return 2  # lām: only endings after it (نَشَأۡ, جِئۡتُمُونَا, تَسُؤۡهُمۡ, أَنۢبِئۡهُم)
        if tail is not None:
            return 1  # ʿayn: بِئۡسَ, ٱلذِّئۡبُ, رِءۡيٗا, شَأۡنٞ
    if cat == "hamzatayn":
        m = re.search("[ءأ][َ]?[ٰ]?[ءأإؤئ]([َُِ])?", word)
        second = m.group(0)[-2:] if m else ""
        if "إ" in second or "ئ" in second or "ِ" in second:
            return 1
        if "ؤ" in second or "ُ" in second:
            return 2
    return k


def refine(occs: list, words: list[tuple[str, str]], stop: str | None = None) -> list:
    """Each occurrence of a category with finer table cases moved to its case's engine category
    (`o.cat`), the detector's kept as `o.base` (the transform reads it). In place; returns occs."""
    text = dict(words)
    for o in occs:
        if not (o.cat.startswith("imala") or o.cat in ("hamzatayn", "ibdal_sakin")):
            continue
        w = text.get(o.word, "")
        nxt = "" if o.word == stop or not o.nxt else text.get(o.nxt, "")
        k = case_for(o.cat, w, -1, nxt)
        if k < 0:
            continue
        new = ("imala_wasl_sakin" if k == WASL_SAKIN else "imala_wasl_sakin_ra") if k >= WASL_SAKIN else _TO.get((o.cat, k))
        if new and new != o.cat:
            o.base, o.cat = o.base or o.cat, new
    return occs
