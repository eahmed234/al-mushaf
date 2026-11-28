"""The farsh table (data/farsh/) against KFGQPC's eight riwāyāt.

    python3 -m checks.farsh [--surah 2] [--upto AYAH] [--show N]

For each of KFGQPC's riwāyāt other than Ḥafṣ, its words are aligned with the spine (as in
checks.kfgqpc) and each is compared with the Ḥafṣ word (mushaf_data.diff): a difference the uṣūl
kinds don't explain is a farsh difference. The table says a rāwī may differ from Ḥafṣ at a place
when one of his options there doesn't include Ḥafṣ. The two should agree:

  both          KFGQPC differs, and the table has the rāwī in a non-Ḥafṣ option
  kfgqpc only   KFGQPC differs, the table doesn't say so (farsh missed, or an uṣūl difference
                mushaf_data.diff doesn't recognise)
  table only    the table says he differs, KFGQPC's text doesn't (a difference the text can't
                show, like ishmām, or KFGQPC's wajh is the Ḥafṣ one)
"""
from __future__ import annotations

import argparse
import difflib
from collections import defaultdict

import yaml

from mushaf_data.diff import classify
from mushaf_data.paths import DATA
from mushaf_data.spine import words
from mushaf_data.text import normalize

from .kfgqpc import FILES, kwords, skel

import re

TANWIN_F = "\u064b\u0657\u08f0"
SUKUNS = "\u0652\u06e1\u06df"


def knorm(w: str) -> str:
    """KFGQPC's spelling conventions → the spine's, as far as a farsh comparison needs (not
    kfgqpc.norm, which also folds letters for its letter key)."""
    w = w.replace("\u0652", "\u06e1").replace("\u06d2", "\u064a").replace("\u064a\u0654", "\u0626")
    # the waṣl alif written with a vowel and a mark: اَ۬لْكِتَٰبُ, اُ۟عۡبُدُوا
    w = re.sub("^([\u0648\u0641\u0628\u0644\u0643]?[\u064e\u0650]?)\u0627[\u064e\u064f\u0650]?[\u06ec\u06ea\u06df]", "\\1\u0671", w)
    w = w.replace("\u0670\u06ea", "\u065c").replace("\u06ea", "\u065c")  # imālah mark
    w = re.sub("(?<=[\u0621-\u064a])\u06ed", "\u064e", w)  # al-Dūrī's text: a low mark in place of the fatḥah (imālah)
    w = w.replace("\u0635\u0650\u06dc", "\u0633\u0650").replace("\u0635\u06dc", "\u0633")  # صۜ is read with sīn
    w = re.sub(f"([\u0627\u0649])([{TANWIN_F}])", "\\2\\1", w)  # tanwīn written after the alif
    w = re.sub("\u0627([\u064e\u064b\u08f0\u0657]\u06e2?)(?=[\u06d6-\u06dc]*$)", "\\1\u0627", w)  # أَمَداَۢ: the same before iqlāb
    w = re.sub("^((?:[\u0648\u0641\u0628\u0643\u0644][\u064e\u0650]?){1,2})\u0627\u064e?\u0644", "\\1\u0671\u0644", w)  # وَالسَّمَآءَ، وَبِالَّذِي: the waṣl alif unmarked
    return w


def prep(w: str) -> str:
    """Both sides: no sukūn on a silent alif, no shadda on the lām after al- or in لله."""
    w = re.sub(f"\u0627[{SUKUNS}]", "\u0627", w)
    w = re.sub("(\u0671|\u0644\u0651?\u0650)\u0644\u0651\u064e?", "\\1\u0644", w)  # ٱلَّذِينَ، لِلَّهِ، لِّلَّذِينَ
    # Maghribi and Madinan spelling, not reading: the small yāʾ of إبراهيم, dagger and full alif,
    # the iqlāb marks and KFGQPC's imālah mark, alif maqṣūrah, pause signs
    w = w.replace("\u0640\u06e7", "\u064a").replace("\u06e7", "\u064a").replace("\u0670", "\u0627")
    w = re.sub("[\u06e2\u06ed\u06d6-\u06dc]", "", w)
    w = w.replace("\u0649", "\u064a")
    w = re.sub("\u064e(?=\u064a[^\u064e\u064f\u0650\u0651\u06e1\u064b-\u064d\u08f0-\u08f2])", "", w)  # the fatḥah before an imālah yāʾ
    w = re.sub("\u0621\u064e\u0627|\u0627\u0627", "\u0622", w)  # ءَالِ / اٰلِ
    w = re.sub("((?:\u0671|\u0627|\u0644)[\u064e\u0650\u064f]?\u0644[\u064e\u0650\u064f\u06e1]?)\u0644\u0651", "\\1\u0644", w)
    w = re.sub("(\u0671\u0644)([\u0628-\u064a])\u0651", "\\1\\2", w)  # ٱلَّذِينَ: the shadda of lām al-shamsiyyah
    return w


def fold_idgham(w: str) -> str:
    """A letter that loses its vowel into a doubled next letter (idghām: خَلَقكُّمۡ): both folded."""
    return re.sub("([\u0621-\u064a])[\u064e\u064f\u0650\u06e1]?(?=[\u0621-\u064a]\u0651)", "\\1", w).replace("\u0651", "")


def differs(a: str, b: str, final: bool = False) -> bool:
    """A farsh difference: one mushaf_data.diff can't explain, even with idghām folded. With
    `final` (KFGQPC prints waṣl, so a word inside an ayah keeps its last vowel), a different last
    vowel counts too: yāʾ al-iḍāfah, jazm against rafʿ."""
    k1, r1 = classify(a, b)
    if r1 and classify(fold_idgham(a), fold_idgham(b))[1]:
        return True
    return final and "final_vowel" in k1 and not ({"silah", "idgham"} & k1)


def entries(surah: int) -> dict[str, list[dict]]:
    """word id → every farsh entry at it (its own place or `also`, and each recurring one)."""
    out: dict[str, list[dict]] = defaultdict(list)
    for f in sorted((FARSH).glob("*.yaml")):
        for e in yaml.safe_load(f.read_text(encoding="utf-8")) or []:
            ws = set(e["place"] + e.get("also", []))
            ws |= set((e.get("recurs") or {}).get("slots") or [])  # stored slots, not forms
            for w in ws:
                if int(w.split(":")[0]) == surah and e not in out[w]:
                    out[w].append(e)
    return out


def places(surah: int) -> dict[str, dict]:
    """word id → its farsh entry: the surah's places and `also`, then the occurrences of every
    entry (any surah) that `recurs` (the book's "حيث وقع") not already a place of its own."""
    out: dict[str, dict] = {}
    for e in yaml.safe_load((FARSH / f"{surah:03d}.yaml").read_text(encoding="utf-8")) or []:
        for w in e["place"] + e.get("also", []):
            out.setdefault(w, e)
    for f in sorted((FARSH).glob("*.yaml")):
        for e in yaml.safe_load(f.read_text(encoding="utf-8")) or []:
            for w in (e.get("recurs") or {}).get("slots") or []:
                if int(w.split(":")[0]) == surah:
                    out.setdefault(w, e)
    return out


FARSH = DATA / "farsh"  # --books: data/farsh_books (al-Wāfī and al-Īḍāḥ, from Āl ʿImrān on)


def waqf_only(o: dict) -> bool:
    """An option read only at a stop (hāʾ al-sakt, hāʾ for a tāʾ, a stop on the yāʾ): KFGQPC's
    waṣl text can't show it."""
    return o.get("condition") == "waqf" or bool(re.match("^\\s*(?:و)?(?:وقف|يقف|إذا وقف|في الوقف)", o["reading"])) \
        or "وقف" in o["reading"][:12]


def table(surah: int) -> dict[str, set[str]]:
    """word id → ruwāt the table lets differ from Ḥafṣ there: every entry at the word, its own and
    a recurring one (وهو at 2:91: Yaʿqūb's hāʾ al-sakt there, and the hāʾ's sukūn from 2:29)."""
    out: dict[str, set[str]] = defaultdict(set)
    for w, es in entries(surah).items():
        for e in es:
            for o in e["options"]:
                if "hafs" not in o["readers"] and not o.get("base") and not waqf_only(o):
                    out[w] |= set(o["readers"]) | set(o.get("implied", []))
    return out


ALIGNED: dict[tuple[str, str], str] = {}  # (rāwī, word id) → KFGQPC's word, from the last alignment


def kfgqpc_farsh(rawi: str, ids: list[str], listed: set[str] = frozenset(), surah: int | None = None) -> set[str]:
    """Word ids where the rāwī's KFGQPC text differs from Ḥafṣ by farsh. At a word where the farsh
    table has this rāwī differ (`listed`), any difference mushaf_data.diff sees counts: a farsh word's change can look
    like hamz, madd or a last vowel (ٱلنَّبِيٓـِٕۧنَ, بَارِئۡكُمۡ, إِنِّيَ)."""
    h = words()
    if surah is None:
        kw = kwords(rawi)
    else:  # one sūrah, the rāwī's projection of the spine (an added slot has no Ḥafṣ word: left out)
        from mushaf_data.spine import projection

        from .spine import kwords as kw_surah
        kw = kw_surah(rawi)[surah]
        if surah == 1 and rawi in ("qalun", "warsh", "duri_abuamr", "susi"):
            ids = [w for w in ids if not w.startswith("1:1:")]  # the basmalah: not numbered in their count
        mine = set(projection(rawi))
        ids = [w for w in ids if w in mine]
    sm = difflib.SequenceMatcher(None, [skel(h[w]) for w in ids], [skel(x) for x in kw], autojunk=False)
    out = set()
    nxt = {a: b for a, b in zip(ids, ids[1:])}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("equal", "replace") and i2 - i1 == j2 - j1:
            for k in range(i2 - i1):
                w = ids[i1 + k]
                n = nxt.get(w, "")
                inside = n.split(":")[:2] == w.split(":")[:2]  # not the ayah's last word
                b = prep(normalize(knorm(kw[j1 + k])))
                # not a naql from the next word (Warsh: أَلَمَ أقل), not al-Sūsī's idghām kabīr (a last
                # vowel dropped into the next word)
                final = inside and h.get(n, "")[:1] not in "أإءآؤئ" and not (
                    rawi == "susi" and b[-1:] not in "\u064e\u064f\u0650\u064b\u064c\u064d")
                ALIGNED[(rawi, w)] = kw[j1 + k]
                if differs(prep(h[w]), b, final=final) or (w in listed and any(classify(prep(h[w]), b))):
                    out.add(w)
        elif tag in ("replace", "insert", "delete"):
            out |= set(ids[i1:i2])  # unaligned: a word added, dropped or changed beyond recognition
    return out


def futuh_farsh(surah: int) -> dict[str, set[str]]:
    """rāwī → word ids where some al-Futūḥ row (vol. 1) gives him a reading that differs from
    Ḥafṣ in a way the uṣūl kinds don't explain. Quoted words only (no rebuilding of elided rows)."""
    from .futuh.rows import load_rows

    h = words()
    out: dict[str, set[str]] = defaultdict(set)
    for r in load_rows(lambda s, a: s == surah):
        readers = r.ruwat or r.ruwat_min
        for w in r.quoted:
            if not w.id or w.id not in h or int(w.id.split(":")[0]) != surah:
                continue
            if any(differs(prep(h[w.id]), prep(t)) for t in (w.alts or [w.t])):
                for x in readers:
                    out[x].add(w.id)
    return out


# Disagreements read word by word (2026-11-27) and found not to be farsh disagreements:
# (word id, kfgqpc_only | table_only) → why. The report lists them apart; a new one is unexplained.
USUL = "an uṣūl difference mushaf_data.diff doesn't recognise"
KNOWN = {
    **{(w, "kfgqpc_only"): f"{USUL}: hamzatayn" for w in ("2:6:6", "2:140:14", "2:31:12")},
    **{(w, "kfgqpc_only"): f"{USUL}: Warsh's naql shows as a kasrah on the wāw (خلوِا إلى، تولوِا إلا)" for w in ("2:14:8", "2:246:48")},
    **{(w, "kfgqpc_only"): f"{USUL}: al-Sūsī's idghām kabīr" for w in ("2:21:6", "2:200:3", "2:249:33")},
    **{(w, "kfgqpc_only"): f"{USUL}: Abū ʿAmr's kasr of the mīm al-jamʿ (wafi 52)" for w in ("2:93:17", "2:142:8", "2:166:11", "2:167:14", "2:246:46")},
    ("2:1:1", "kfgqpc_only"): "KFGQPC's marks on the opening letters (أَلَٓمِّٓ)",
    **{(f"1:1:{i}", "kfgqpc_only"): "the basmalah: KFGQPC doesn't number it as an āyah for Qālūn, Warsh and Abū ʿAmr"
       for i in range(1, 5)},
    **{(w, "kfgqpc_only"): "KFGQPC writes the tanwīn after the alif (أَبَداَۢ)" for w in ("2:95:3", "2:213:31", "2:236:21")},
    **{(w, "kfgqpc_only"): "KFGQPC splits أَوَ off as its own token: an alignment slip" for w in ("2:77:1", "2:100:1", "2:260:10")},
    ("2:245:14", "kfgqpc_only"): "the ṣād with a small sīn: KFGQPC and the table agree on who reads sīn",
    ("2:245:14", "table_only"): "the ṣād with a small sīn (read sīn by Ḥafṣ): KFGQPC's plain ṣād is the table's ṣād",
    **{(w, "table_only"): "a stop's reading: waṣl text can't show it" for w in ("2:91:22", "2:218:12")},
    **{(w, "table_only"): "Qālūn's khulf: KFGQPC prints his other wajh (dropped)" for w in ("2:186:9", "2:186:11")},
    ("2:173:14", "table_only"): "a two-word place: the difference is on فَمَنُ (2:173:13)",
    ("2:177:1", "table_only"): "a two-word place: the difference is on ٱلۡبِرُّ (2:177:2)",
    ("3:143:3", "table_only"): "al-Bazzī: \"المقروء به من طريقه إنما هو التخفيف\" (budur 70), the same as Ḥafṣ",
}


HAMZAS = "\u0621\u0623\u0625\u0622\u0624\u0626"
MARKS_RE = re.compile("[\u064b-\u065f\u0670\u06d6-\u06ed\u08f0-\u08f2]")


def explain(w: str, rawi: str, k: str, kf_word: str | None) -> str | None:
    """Why a disagreement isn't a farsh one, by pattern (2026-11-27, from al-Baqarah and Āl ʿImrān):
    uṣūl the diff doesn't recognise, or a mark KFGQPC leaves out. None: unexplained."""
    h = words()
    a = h[w]
    ids = list(h)
    nxt = h.get(ids[ids.index(w) + 1], "") if k == "kfgqpc_only" else ""
    s, ay, n = map(int, w.split(":"))
    if k != "kfgqpc_only" or kf_word is None:
        return None
    b = kf_word
    if ay == 1 and n == 1 and "\u0653" in a:
        return "KFGQPC's marks on the opening letters"
    if re.match(f"^[\u0648\u0641]?[\u064e]?[{HAMZAS}][\u064e\u064f\u0650]?[{HAMZAS}]", a):
        return f"{USUL}: hamzatayn"
    if rawi in ("duri_abuamr", "susi") and a.endswith("\u0645\u064f") and b.rstrip("\u06d6\u06d7\u06d8\u06d9\u06da\u06db").endswith("\u0645\u0650"):
        return f"{USUL}: Abū ʿAmr's kasr of the mīm al-jamʿ (wafi 52)"
    pa, pb = prep(a), prep(normalize(knorm(b)))
    bare = lambda x: MARKS_RE.sub("", x).replace("\u0671", "\u0627")  # noqa: E731  (ٱ as KFGQPC's plain ا)
    if rawi == "warsh" and nxt[:1] in HAMZAS and bare(pa) == bare(pb):
        return f"{USUL}: Warsh's naql (the hamzah's vowel on the last letter)"
    if rawi == "susi" and pb.count("\u0651") > pa.count("\u0651") and bare(fold_idgham(pa)) == bare(fold_idgham(pb)):
        return f"{USUL}: al-Sūsī's idghām kabīr"
    if "\u06e0" in a and nxt[:1] not in HAMZAS and pa.replace("\u06e0", "") == pb:
        return "أنا before a word without a hamzah: all drop its alif in waṣl (wafi 222); KFGQPC doesn't mark it"
    if bare(pa) == bare(pb) and set(MARKS_RE.findall(pb)) <= set(MARKS_RE.findall(pa)) \
            and len(MARKS_RE.findall(pb)) <= len(MARKS_RE.findall(pa)):
        return "a mark KFGQPC leaves out (same letters, fewer marks)"
    return None


def check(surah: int = 2, upto: int | None = None, source: str = "kfgqpc") -> dict:
    h = words()
    ids = [w for w in h if int(w.split(":")[0]) == surah]
    scope = [w for w in ids if upto is None or int(w.split(":")[1]) <= upto]
    tab = table(surah)
    res = {"both": [], "kfgqpc_only": [], "table_only": []}
    fu = futuh_farsh(surah) if source == "futuh" else None
    from mushaf_data.ruwat import RUWAT
    for rawi in (RUWAT if fu is not None else FILES):
        if rawi == "hafs":
            continue
        mine = {w for w, rs in tab.items() if rawi in rs}
        kf = (fu.get(rawi, set()) if fu is not None else kfgqpc_farsh(rawi, ids, mine, surah)) & set(scope)
        tb = {w for w in scope if rawi in tab.get(w, ())}
        res["both"] += [(w, rawi) for w in sorted(kf & tb)]
        res["kfgqpc_only"] += [(w, rawi) for w in sorted(kf - tb)]
        res["table_only"] += [(w, rawi) for w in sorted(tb - kf)]
    if fu is None:
        kf_of = defaultdict(set)
        for w, r in res["both"] + res["kfgqpc_only"]:
            kf_of[r].add(w)
        ent = entries(surah)
        why = {}
        for k in ("kfgqpc_only", "table_only"):
            for w, r in res[k]:
                if (w, k) in KNOWN:
                    why[(w, r, k)] = KNOWN[(w, k)]
                elif k == "table_only" and any(o in kf_of[r] for e in ent.get(w, []) for o in e["place"] if o != w):
                    why[(w, r, k)] = "a place of several words: the difference shows on another of them"
                elif k == "table_only" and any(r in o["readers"] and (o.get("base") or "hafs" in o["readers"])
                                               for e in ent.get(w, []) for o in e["options"]):
                    why[(w, r, k)] = "a khulf whose other wajh reads as Ḥafṣ: KFGQPC prints that one"
                else:
                    x = explain(w, r, k, ALIGNED.get((r, w)))
                    if x:
                        why[(w, r, k)] = x
        res["explained"] = [(w, r, k) for (w, r, k) in why]
        res["why"] = why
        for k in ("kfgqpc_only", "table_only"):
            res[k] = [(w, r) for w, r in res[k] if (w, r, k) not in why]
    return res


def report(surah: int, r: dict, who: str) -> None:
    """Markdown list of the disagreements: per word, which ruwāt, and (for KFGQPC) their text."""
    from mushaf_data.paths import BUILD

    h = words()
    lines = [f"# Farsh of surah {surah} against {who}", "",
             f"{len(r['both'])} (word, rāwī) pairs agree. Below: the rest, by word.", ""]
    ent = places(surah)
    for k, title in (("kfgqpc_only", "KFGQPC differs from Ḥafṣ here; the table doesn't say so"),
                     ("table_only", "The table says these differ from Ḥafṣ; KFGQPC's text doesn't")):
        by = defaultdict(list)
        for w, rawi in r[k]:
            by[w].append(rawi)
        lines += [f"## {title} ({len(by)} words)", ""]
        for w in sorted(by, key=lambda x: tuple(int(n) for n in x.split(":"))):
            e = ent.get(w)
            opts = "; ".join(f"{', '.join(o['readers'])}: {o['reading']} ({o['cite']})" for o in e["options"]) if e else "no entry"
            lines.append(f"- **{w}** {h[w]} — {', '.join(by[w])}. Table: {opts}")
        lines.append("")
    if r.get("explained"):
        by = defaultdict(list)
        for w, rawi, k in r["explained"]:
            by[(w, k)].append(rawi)
        lines += [f"## Read and explained, not farsh disagreements ({len(by)} words)", ""]
        for (w, k), rs in sorted(by.items(), key=lambda x: tuple(int(n) for n in x[0][0].split(":"))):
            lines.append(f"- **{w}** {h[w]} — {', '.join(rs)} ({k.replace('_', ' ')}): {r['why'][(w, rs[0], k)]}")
        lines.append("")
    out = BUILD / f"farsh_check_{surah:03d}.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--surah", type=int, default=2)
    ap.add_argument("--upto", type=int, default=None)
    ap.add_argument("--show", type=int, default=0)
    ap.add_argument("--source", choices=["kfgqpc", "futuh"], default="kfgqpc")
    ap.add_argument("--report", action="store_true", help="write build/farsh_check_SSS.md")
    ap.add_argument("--books", action="store_true", help="check data/farsh_books (al-Wāfī, al-Īḍāḥ)")
    a = ap.parse_args()
    if a.books:
        global FARSH
        FARSH = DATA / "farsh_books"
    r = check(a.surah, a.upto, a.source)
    h = words()
    who = "seven KFGQPC riwāyāt" if a.source == "kfgqpc" else "al-Futūḥ's rows, all twenty"
    if a.report:
        report(a.surah, r, who)
    print(f"surah {a.surah}{f' to ayah {a.upto}' if a.upto else ''}, {who}: "
          f"{len(r['both'])} agree, {len(r['kfgqpc_only'])} {a.source} only, {len(r['table_only'])} table only"
          + (f", {len(r['explained'])} explained" if "explained" in r else ""))
    for k in ("kfgqpc_only", "table_only"):
        by = defaultdict(list)
        for w, rawi in r[k]:
            by[w].append(rawi)
        print(f"  {k}: {len(by)} words")
        for w in list(by)[: a.show]:
            print(f"    {w} {h[w]} {' '.join(by[w])}")


if __name__ == "__main__":
    main()
