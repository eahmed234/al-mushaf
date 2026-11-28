"""Day 5: generate 1:1-2:20 for the eight riwāyāt KFGQPC publishes and compare with their texts.

An independent source (not al-Futūḥ) and whole text (not per-box rows). KFGQPC numbers ayahs by
each riwāyah's count and writes in its own conventions, so the comparison aligns word by word on
letters and compares what a reading changes:

  letters (hamzah as a letter, ṣilah's small wāw/yāʾ included), maddahs (madd), shaddas (idghām),
  imālah marks (our U+065C dot; KFGQPC's U+06EA under a dagger alif), tas-hīl dots.

For each ayah the engine's readings for the rāwī are tried and the closest kept (KFGQPC prints one
wajh per place); what still differs is listed by kind.

    python3 -m checks.kfgqpc [--show N]
"""
import argparse
import collections
import difflib
import json
import re
from pathlib import Path

from .futuh.readings import full_profiles, generate, confirmed_occurrences
from mushaf_data.paths import SOURCES

from .futuh.rows import load_hafs

MIRROR = SOURCES / "kfgqpc/mirror"
FILES = {"hafs": "hafs/hafsData_v18.json", "shuba": "shouba/ShoubaData08.json",
         "warsh": "warsh/warshData_v10.json", "qalun": "qaloon/QaloonData_v10.json",
         "bazzi": "bazzi/BazziData_v07.json", "qunbul": "qumbul/QumbulData_v07.json",
         "duri_abuamr": "doori/DooriData_v09.json", "susi": "soosi/SoosiData09.json"}
MARKS = re.compile("[\u064b-\u0652\u0653-\u065f\u0670\u06d6-\u06ed\u08f0-\u08f2]")


def kwords(rawi: str) -> list[str]:
    """KFGQPC's words for al-Fātiḥah and al-Baqarah (ayah numbers dropped)."""
    d = json.loads((MIRROR / FILES[rawi]).read_text(encoding="utf-8"))
    sk = "sura_no" if "sura_no" in d[0] else "sora"
    out = []
    for a in d:
        if a[sk] in (1, 2):
            for w in a["aya_text"].replace("\xa0", " ").split():
                if not re.fullmatch("[\u0660-\u0669\u06f0-\u06f9]+|[\u06d6-\u06de]", w):
                    out.append(w)
    return out


def norm(w: str) -> str:
    """KFGQPC conventions to ours, as far as a reading is concerned."""
    w = w.replace("\u0652", "\u06e1").replace("\u06d2", "\u064a").replace("\u0649", "\u064a")
    w = re.sub("^([\u0648\u0641\u0628\u0644\u0643]?[\u064e\u0650]?)\u0627[\u064e\u064f\u0650]?[\u06ec\u06ea]", "\\1\u0671", w)  # اَ۬لْكِتَٰبُ
    w = w.replace("\u0670\u06ea", "\u065c").replace("\u06ea", "\u065c")  # KFGQPC's imālah mark
    # al-Dūrī's and al-Sūsī's taqlīl: a small low mīm on the letter before the alif (مُوسۭيٰ, ٱلدُّنۡيۭا);
    # elsewhere U+06ED is the iqlāb of a kasr tanwīn, which isn't before an alif
    w = re.sub("\u06ed(?=[\u0670]?[\u064a\u0649\u0627\u0670])|(?<=\u0670)\u06ed", "\u065c", w)  # (بِسِيمٰۭهُمۡ)
    w = w.replace("\u0635\u0650\u06dc", "\u0633\u0650").replace("\u0635\u06dc", "\u0633")  # صۜ: read with sīn
    w = w.replace("\u064a\u0654", "\u0626")
    return w


def letters(w: str) -> str:
    w = w.replace("\u0649", "\u064a").replace("\u06d2", "\u064a")
    w = re.sub("[\u0623\u0625\u0624\u0626\u0621]", "\u0621", w)
    w = re.sub("[\u0671\u0622]", "\u0627", w)
    w = w.replace("\u0670", "\u0627")  # dagger alif is an alif
    w = w.replace("\u0654", "\u0621")
    return re.sub("[^\u0621-\u064a\u06e5\u06e6]", "", MARKS.sub(lambda m: m.group(0) if m.group(0) == "\u0654" else "", w)).replace("\u0640", "")


def key(w: str) -> tuple:
    """What a reading changes. Shaddas that are writing conventions don't count: lām al-shamsiyyah
    (Warsh/Qālūn's texts leave it out) and the first letter's (KFGQPC puts the shadda of idghām
    from the word before on it; the spine doesn't)."""
    w = norm(w)
    cl = re.findall(".[\u064b-\u065f\u0670\u06d6-\u06ed]*", w)
    shad = 0
    for i, c in enumerate(cl):
        if "\u0651" not in c or i == 0:
            continue
        after_al = i >= 2 and cl[i - 1][0] == "\u0644" and cl[i - 2][0] in "\u0671\u0627"
        lam_of_al = c[0] == "\u0644" and cl[i - 1][0] in "\u0671\u0627"  # ٱلَّذِينَ
        if after_al or lam_of_al or (i == 1 and cl[0][0] == "\u0644"):
            continue  # ٱلَّذِينَ, لِلَّهِ
        shad += 1
    return (letters(w), w.count("\u0653"), shad, w.count("\u065c"), w.count("\u06ec"))


def kind(a: tuple, b: tuple) -> str:
    names = ["letters", "madd", "shadda", "imala", "tashil"]
    return "+".join(n for n, x, y in zip(names, a, b) if x != y)


def skel(w: str) -> str:
    return re.sub("[\u0621\u0627\u06e5\u06e6\u0648\u064a]", "", letters(norm(w)))


def run(show: int = 0, out=print) -> dict:
    """{rawi: (words that agree, words compared)} and "all": the total."""
    hafs = load_hafs()
    ids = [w for w in hafs if not w.startswith("B:")]
    full, _, _, _ = full_profiles(20, book=True)
    conf = confirmed_occurrences()
    ayahs = collections.OrderedDict()
    for w in ids:
        s, ay, _ = w.split(":")
        ayahs.setdefault((s, ay), []).append(w)
    total = collections.Counter()
    res = {}
    for rawi in FILES:
        kw = kwords(rawi)
        # align the spine's words with KFGQPC's on letters
        sm = difflib.SequenceMatcher(None, [skel(hafs[w]) for w in ids], [skel(x) for x in kw], autojunk=False)
        pair = {}
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag in ("equal", "replace") and i2 - i1 == j2 - j1:
                for k in range(i2 - i1):
                    pair[ids[i1 + k]] = kw[j1 + k]
        same = diff = unaligned = 0
        kinds = collections.Counter()
        shown = []
        for (s, ay), span in ayahs.items():
            gens = generate(rawi, span, full, conf) if rawi != "hafs" else [({}, {w: hafs[w] for w in span})]

            def cost(g):
                return sum(key(g[w]) != key(pair[w]) for w in span if w in pair)
            ch, g = min(gens, key=lambda cg: cost(cg[1]))
            for w in span:
                if w not in pair:
                    unaligned += 1
                    continue
                if key(g[w]) == key(pair[w]):
                    same += 1
                else:
                    diff += 1
                    kd = kind(key(g[w]), key(pair[w]))
                    kinds[kd] += 1
                    shown.append((w, g[w], pair[w], kd))
        n = same + diff
        res[rawi] = (same, n)
        out(f"{rawi:12} {same}/{n} words agree ({same / n:.1%}); {unaligned} unaligned; differences: {dict(kinds)}")
        for x in shown[:show]:
            out("     ", *x)
        total.update({"same": same, "diff": diff})
    res["all"] = (total["same"], total["same"] + total["diff"])
    out(f"all eight: {res['all'][0]}/{res['all'][1]} words agree")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int, default=0)
    a = ap.parse_args()
    run(a.show)


if __name__ == "__main__":
    main()
