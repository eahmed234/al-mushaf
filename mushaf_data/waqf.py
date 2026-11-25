"""Ḥamzah's and Hishām's waqf on hamz: every form a stop allows, by rule.

Source: al-Qāḍī, al-Wāfī, bāb waqf Ḥamzah wa-Hishām ʿalā al-hamz, pp. 110-127 (books/wafi.txt),
with al-Budūr and Ghayth al-Nafʿ per place. Each rule below cites its page. Ḥamzah changes a
hamzah in the middle or at the end of the word he stops on (never one that starts it, unless a
prefix makes it mid, pp. 122-123); Hishām only the final one (pp. 116-117).

    forms(word, rawi) -> [(label, text), ...]   all forms for that rāwī at a stop, Ḥafṣ text in

Text encoding follows al-Futūḥ's prints: the tas-hīl dot is tatweel + U+06EC; with rawm the
vowel sits on the tatweel (ـِ۬). Features the text can't show (madd length beyond qaṣr against
not-qaṣr, ishmām) are labels only.
"""
from __future__ import annotations

import itertools

from .text import clusters

FATHA, DAMMA, KASRA = "َ", "ُ", "ِ"
SUKUN, SHADDA, MADDAH, DAGGER = "ۡ", "ّ", "ٓ", "ٰ"
TASHIL, TATWEEL = "۬", "ـ"
HAMZA_ABOVE, HAMZA_BELOW = "ٔ", "ٕ"
# KFGQPC writes open tanwīn as U+0657 (fatḥ, خَطَـٔٗا), U+0656 (kasr, شَيۡءٖ), U+065E (ḍamm, أَلِيمٞ)
TANWIN_OF = {"ً": FATHA, "ٌ": DAMMA, "ٍ": KASRA, "ࣰ": FATHA, "ࣱ": DAMMA,
             "ࣲ": KASRA, "ٗ": FATHA, "ٖ": KASRA, "ٞ": DAMMA}
FATH_TANWIN = ("ً", "ࣰ", "ٗ")
VOWEL_LETTER = {FATHA: "ا", DAMMA: "و", KASRA: "ي"}
PAUSE = set("ۖۗۘۙۚۛ۞۩")
PREFIXES = set("وفبلكس")  # و ف ب ل ك س (p. 123)
SILENT = {"ا", "ۥ", "ۦ"}  # a rasm alif after a final hamzah (يَبۡدَؤُاْ), small waw/yeh


def is_hamza(cl: str) -> bool:
    return cl[0] in "ءأإؤئ" or HAMZA_ABOVE in cl or HAMZA_BELOW in cl


def vowel(cl: str) -> str | None:
    if is_hamza(cl) and MADDAH in cl and not any(m in cl for m in (DAMMA, KASRA)):
        return FATHA  # ءَا written أٓ (ٱلۡأٓخِرَةِ)
    for m in cl[1:]:
        if m in (FATHA, DAMMA, KASRA):
            return m
        if m in TANWIN_OF:
            return TANWIN_OF[m]
    return None


def bare(cl: str) -> str:
    """The letter without vowels, sukūn, tanwīn or the hamza mark (keeps shadda, dagger)."""
    return cl[0] + "".join(m for m in cl[1:] if m not in (FATHA, DAMMA, KASRA, SUKUN, MADDAH,
                                                       HAMZA_ABOVE, HAMZA_BELOW) and m not in TANWIN_OF)


def _last_real(cls: list[str]) -> int:
    """Index of the last cluster that is pronounced (skips a rasm alif, ۥ, ۦ, pause signs)."""
    k = len(cls) - 1
    while k > 0 and (cls[k][0] in SILENT and not vowel(cls[k]) and MADDAH not in cls[k]
                     and SHADDA not in cls[k] or cls[k][0] in PAUSE):
        k -= 1
    return k


def _options(cls: list[str], k: int, final: bool, rawi: str) -> list[tuple[str, list[str]]]:
    h = cls[k]
    if final and any(m in h for m in FATH_TANWIN):
        # fatḥ tanwīn: at a stop it becomes an alif, so the hamzah is mid (وَنِدَآءٗ → وَنِدَآـ۬ا)
        cls = cls[:k] + [h[0] + FATHA] + cls[k + 1:]
        add = [] if k + 1 < len(cls) and cls[k + 1][0] == "\u0627" else ["\u0627"]  # خَطَـٔٗا has its alif
        return [(lab, rep + add) for lab, rep in _options_(cls, k, False, rawi)]
    return _options_(cls, k, final, rawi)


def _options_(cls: list[str], k: int, final: bool, rawi: str) -> list[tuple[str, list[str]]]:
    """Ways to read the hamzah at cls[k] at a stop: [(label, new clusters for cls[k-1:k+1])]."""
    h, p = cls[k], cls[k - 1]
    hv = vowel(h)  # its own vowel (None: sākin)
    silent = p[0] == "\u0627" and "\u0652" in p and k >= 2  # مِاْئَةٗ: a rasm alif, not read
    pv = vowel(cls[k - 2]) if silent else vowel(p)
    rawm_ok = final and hv in (DAMMA, KASRA)  # rawm only for marfūʿ / majrūr (p. 126)
    out: list[tuple[str, list[str]]] = []

    alif_seat = h[0] in "\u0623\u0625"

    def tashil(v=""):
        # on an alif seat the book keeps the alif (وَا۬بۡصَٰرِهِمۡ); otherwise tatweel + dot
        return ("\u0627" if alif_seat and not v else TATWEEL) + v + TASHIL

    p_is_alif = not silent and (p[0] == "\u0627" and not pv and SUKUN not in p or DAGGER in p)
    p_sakin = not silent and (SUKUN in p or (p[0] in "\u0648\u064a" and not pv and SHADDA not in p))

    if hv is None or final:
        # sākin, or made sākin by the stop
        if p_is_alif and final:
            # after an alif at the end: ibdāl alif with qaṣr / tawassuṭ / madd (pp. 114-115),
            # tas-hīl with rawm, madd or qaṣr, for marfūʿ and majrūr (pp. 125-127)
            pa = p if MADDAH in p else p + MADDAH
            # a dagger alif left at the end is written in full (شُرَكَٰٓؤُاْ → شُرَكَا, شُرَكَآ)
            fa = ([p.replace(DAGGER, "").replace(MADDAH, ""), "\u0627" + MADDAH] if DAGGER in p else [pa])
            fq = ([p.replace(DAGGER, "").replace(MADDAH, ""), "\u0627"] if DAGGER in p else [p.replace(MADDAH, "")])
            out += [("ibdal_madd", fa), ("ibdal_qasr", fq)]
            if rawm_ok:
                out += [("tashil_rawm_madd", fa + [tashil(hv)]),
                        ("tashil_rawm_qasr", fq + [tashil(hv)])]
            # rasm: the hamzah written on a wāw (جَزَٰٓؤُاْ) or a yāʾ (تِلۡقَآيِٕ) is read as that
            # letter: wāw with the three lengths, sukūn or ishmām, and rawm with qaṣr ("سبعة الرسم",
            # al-Budūr pp. 91-92); yāʾ with the three lengths and rawm with qaṣr ("أربعة الرسم",
            # al-Budūr p. 209); only the listed words, which are the ones the rasm writes so
            # (al-Wāfī pp. 119-120)
            seat = "\u0648" if h[0] == "\u0624" else "\u064a" if h[0] == "\u064a" and HAMZA_BELOW in h else None
            if seat:
                pq = p.replace(MADDAH, "")
                out += [("rasm_madd", [pa, seat]), ("rasm_qasr", [pq, seat])]
                if rawm_ok:
                    out.append(("rasm_rawm_qasr", [pq, seat + hv]))
                if seat == "\u0648":
                    out += [("rasm_ishmam_madd", [pa, seat + DAMMA]), ("rasm_ishmam_qasr", [pq, seat + DAMMA])]
            return out
        if pv and not p_sakin:
            # after a ḥarakah: ibdāl to the madd letter of that ḥarakah (pp. 110-112)
            out.append(("ibdal", [p, VOWEL_LETTER[pv]]))
            if rawm_ok:
                out.append(("tashil_rawm", [p, tashil(hv)]))  # p. 126
            if final and h[0] == "\u0624":
                # rasm wāw after a ḥarakah (يَبۡدَؤُاْ, ٱلۡمَلَؤُاْ): wāw with sukūn, ishmām or rawm
                # (al-Budūr pp. 142, 171, 218)
                out += [("rasm", [p, "\u0648"]), ("rasm_rawm", [p, "\u0648" + (hv or DAMMA)])]
            return out
    if p_sakin or p_is_alif:
        if p_is_alif:
            # mid, after an alif: tas-hīl with madd or qaṣr (p. 114)
            pa = p if MADDAH in p else p + MADDAH
            return [("tashil_madd", [pa, tashil()]), ("tashil_qasr", [p.replace(MADDAH, ""), tashil()])]
        # after a sākin letter: naql and ḥadhf (pp. 112-113); after wāw/yāʾ also ibdāl + idghām
        # (zāʾid: p. 115; aṣlī, by some: p. 125)
        nv = ((hv or "") if not final else "") + (DAGGER if DAGGER in h else "")  # سَوۡءَٰتِ → سَوَٰتِ
        seat = ["\u0627"] if alif_seat else []  # ٱلۡأَرۡضِ → ٱلَارۡضِ: the alif stays, bare
        out.append(("naql", [bare(p) + nv] + seat))
        if rawm_ok:
            out.append(("naql_rawm", [bare(p) + hv] + seat))
        if p[0] in "وي":
            out.append(("idgham", [bare(p) + SHADDA + nv] + seat))
            if rawm_ok:
                out.append(("idgham_rawm", [bare(p) + SHADDA + hv] + seat))
        return out
    # mutaḥarrik after mutaḥarrik, mid (p. 116; al-Akhfash p. 120; rasm ḥadhf p. 121)
    if hv == FATHA and pv == KASRA:
        return [("ibdal_ya", [p, "ي" + FATHA])]
    if hv == FATHA and pv == DAMMA:
        return [("ibdal_waw", [p, "و" + FATHA])]
    out.append(("tashil", [p, tashil()]))
    if hv == DAMMA and pv == KASRA:
        out.append(("ibdal_ya", [p, "ي" + DAMMA]))  # al-Akhfash
        if h[0] in "ء" + TATWEEL:  # no seat in the rasm: ḥadhf, the letter before takes ḍamm
            out.append(("hadhf", [bare(p) + DAMMA]))
    if hv == KASRA and pv == KASRA and h[0] in "\u0621" + TATWEEL and k + 1 < len(cls) and cls[k + 1][0] == "\u064a":
        out.append(("hadhf", [bare(p) + KASRA]))  # خَٰسِـِٔينَ, ٱلصَّٰبِـِٔينَ (al-Budūr p. 34)
    if hv == KASRA and pv == DAMMA:
        out.append(("ibdal_waw", [p, "و" + KASRA]))  # al-Akhfash
    return out


def _prefix_end(cls: list[str]) -> int:
    """Index of the first letter after the zāʾid prefixes (p. 123): و ف ب ل ك س with a vowel,
    then lām al-taʿrīf (ٱلۡ). -1 if none."""
    i = 0
    if len(cls) > 2 and cls[0][0] in "\u0647\u064a" and DAGGER in cls[0]:  # هَٰٓؤُلَآءِ, يَٰٓـَٔادَمُ (p. 123)
        return 1
    while i < len(cls) - 1 and cls[i][0] in PREFIXES and vowel(cls[i]) and (i == 0 or SHADDA not in cls[i]):
        i += 1
    if i + 1 < len(cls) and cls[i][0] == "\u0671" and cls[i + 1][0] == "\u0644" and SUKUN in cls[i + 1]:
        i += 2
    elif i and cls[i][0] == "\u0644" and SUKUN in cls[i]:  # لِلۡأَبۡرَارِ: li- + lām al-taʿrīf, no alif
        i += 1
    return i if i else -1


def _idh(cls: list[str], k: int) -> bool:
    """The hamzah of ـئِذٖ in يَوۡمَئِذٖ, حِينَئِذٖ."""
    return k + 1 < len(cls) and cls[k][0] == "\u0626" and cls[k + 1][0] == "\u0630" and k + 1 == len(cls) - 1


def forms_initial(word: str, rawi: str = "khalaf_an_hamzah") -> list[tuple[str, str]]:
    """Ḥamzah stopping on a word that starts with a hamzah after a word ending in a sākin
    (مَنۡ ءَامَنَ, عَذَابٌ أَلِيمٌ): taḥqīq or naql (wafi 105-106). The changed end of the word
    before isn't modelled here."""
    cls = clusters(word)
    if not cls or not is_hamza(cls[0]):
        return [("tahqiq", word)]
    v = vowel(cls[0]) or ""
    out = []
    for lab, w in forms(word, rawi):  # its own mid/final hamzahs as at any stop
        c = clusters(w)
        rest = c[1:]
        if rest and rest[0][0] == "\u0627":  # ءَاخَرِينَ: the alif after the hamzah carries on
            naql = "".join(rest)
        else:
            naql = "".join(["\u0627" + v] + rest)
        out += [(lab, w), ("naql+" + lab, naql)]
    return out


def forms(word: str, rawi: str) -> list[tuple[str, str]]:
    """All forms of `word` (Ḥafṣ, normalised) at a stop for Ḥamzah's ruwāt or Hishām."""
    cls = [c for c in clusters(word) if c[0] not in PAUSE]
    last = _last_real(cls)
    spots = []  # (index, final, prefixed)
    for k, cl in enumerate(cls):
        if k == 0 or not is_hamza(cl):
            continue
        final = k == last
        if rawi == "hisham" and not final:
            continue
        prefixed = k == _prefix_end(cls)
        spots.append((k, final, prefixed))
    if not spots:
        return [("tahqiq", word)]
    choices = []
    for k, final, prefixed in spots:
        opts = _options(cls, k, final, rawi)
        if prefixed or _idh(cls, k):
            # made mid by a prefix (incl. lām al-taʿrīf): taḥqīq or takhfīf (pp. 122-123); also
            # يَوۡمَئِذٖ, حِينَئِذٖ, where al-Jaʿbarī takes only takhfīf and others both (p. 122 n. 1)
            opts = [("tahqiq", None)] + opts
        choices.append([(k, lab, rep) for lab, rep in opts])
    out = []
    for combo in itertools.product(*choices):
        # two tas-hīls after an alif go with the same length (هَٰٓؤُلَآءِ: al-Budūr p. 65)
        lens = {lab.rsplit("_", 1)[-1] for _, lab, _ in combo if lab.startswith("tashil") and lab.rsplit("_", 1)[-1] in ("madd", "qasr")}
        if len(lens) > 1:
            continue
        new = list(cls)
        labels = []
        for k, lab, rep in sorted(combo, key=lambda c: -c[0]):
            labels.append(lab)
            if rep is not None:
                tail = 1
                while k + tail < len(new) and new[k + tail][0] == "\u0627" and "\u0652" in new[k + tail]:
                    tail += 1  # جَزَٰٓؤُاْ: the rasm alif after the hamzah goes with it
                new[k - 1:k + tail] = rep
        text = "".join(new)
        out.append(("+".join(reversed(labels)), text))
    return out
