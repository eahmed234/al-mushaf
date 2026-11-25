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
    w = re.sub("^([\u0648\u0641\u0628\u0643][\u064e\u0650]?)\u0627\u064e?\u0644", "\\1\u0671\u0644", w)  # وَالسَّمَآءَ: the waṣl alif unmarked
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


def table(surah: int) -> dict[str, set[str]]:
    """word id → ruwāt the table lets differ from Ḥafṣ there."""
    f = DATA / "farsh" / f"{surah:03d}.yaml"
    out: dict[str, set[str]] = defaultdict(set)
    for e in yaml.safe_load(f.read_text(encoding="utf-8")) or []:
        for o in e["options"]:
            if "hafs" in o["readers"]:
                continue
            for w in e["place"] + e.get("also", []):
                out[w] |= set(o["readers"]) | set(o.get("implied", []))
    return out


def kfgqpc_farsh(rawi: str, ids: list[str]) -> set[str]:
    h = words()
    kw = kwords(rawi)
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
                if differs(prep(h[w]), b, final=final):
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


def check(surah: int = 2, upto: int | None = None, source: str = "kfgqpc") -> dict:
    h = words()
    ids = [w for w in h if w.split(":")[0] in ("1", "2")]  # kwords gives al-Fātiḥah and al-Baqarah
    scope = [w for w in ids if int(w.split(":")[0]) == surah and (upto is None or int(w.split(":")[1]) <= upto)]
    tab = table(surah)
    res = {"both": [], "kfgqpc_only": [], "table_only": []}
    fu = futuh_farsh(surah) if source == "futuh" else None
    from mushaf_data.ruwat import RUWAT
    for rawi in (RUWAT if fu is not None else FILES):
        if rawi == "hafs":
            continue
        kf = (fu.get(rawi, set()) if fu is not None else kfgqpc_farsh(rawi, ids)) & set(scope)
        tb = {w for w in scope if rawi in tab.get(w, ())}
        res["both"] += [(w, rawi) for w in sorted(kf & tb)]
        res["kfgqpc_only"] += [(w, rawi) for w in sorted(kf - tb)]
        res["table_only"] += [(w, rawi) for w in sorted(tb - kf)]
    return res


def report(surah: int, r: dict, who: str) -> None:
    """Markdown list of the disagreements: per word, which ruwāt, and (for KFGQPC) their text."""
    from mushaf_data.paths import BUILD

    h = words()
    lines = [f"# Farsh of surah {surah} against {who}", "",
             f"{len(r['both'])} (word, rāwī) pairs agree. Below: the rest, by word.", ""]
    ent = {w: e for e in yaml.safe_load((DATA / "farsh" / f"{surah:03d}.yaml").read_text(encoding="utf-8")) or []
           for w in e["place"] + e.get("also", [])}
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
    a = ap.parse_args()
    r = check(a.surah, a.upto, a.source)
    h = words()
    who = "seven KFGQPC riwāyāt" if a.source == "kfgqpc" else "al-Futūḥ's rows, all twenty"
    if a.report:
        report(a.surah, r, who)
    print(f"surah {a.surah}{f' to ayah {a.upto}' if a.upto else ''}, {who}: "
          f"{len(r['both'])} agree, {len(r['kfgqpc_only'])} {a.source} only, {len(r['table_only'])} table only")
    for k in ("kfgqpc_only", "table_only"):
        by = defaultdict(list)
        for w, rawi in r[k]:
            by[w].append(rawi)
        print(f"  {k}: {len(by)} words")
        for w in list(by)[: a.show]:
            print(f"    {w} {h[w]} {' '.join(by[w])}")


if __name__ == "__main__":
    main()
