"""Check spike.waqf against every waqf form al-Futūḥ prints for Ḥamzah's ruwāt and Hishām.

    python3 -m spike.waqf_check [--show N] [--rawi hisham]

Test set: rows of out/vol1-6.jsonl naming khalaf_an_hamzah, khallad or hisham whose label says
waqf, with words coloured as waqf (#c00000); the first such word's spine id is the Ḥafṣ word.
A row's forms are 'covered' when every form it prints is one spike.waqf generates.
"""
import argparse
import collections
import json
import re
from functools import lru_cache
from pathlib import Path

from .rows import SPINE
from .text import normalize, clusters
from .waqf import forms, forms_initial, is_hamza, PAUSE, TATWEEL, SUKUN

OUT = Path("/home/eahmed/Projects/mushaf/out")


@lru_cache(maxsize=1)
def hafs_all() -> dict[str, str]:
    out = {}
    for line in SPINE.open():
        it = json.loads(line)
        if it["kind"] == "word":
            cps = " ".join(cl["cps"] for cl in it["clusters"]).split()
            out[it["id"]] = normalize("".join(chr(int(c[2:], 16)) for c in cps))
    return out


def key(w: str) -> str:
    """Comparison form: normalised; no pause signs, stretch tatweel or a final sukūn; the
    final letter's vowel kept (rawm forms differ by it)."""
    w = normalize(w)
    w = "".join(c for c in w if c not in PAUSE)
    # the tas-hīl dot: above (U+06EC) or, for a kasrah hamzah, below (U+065C) its seat; the prints
    # give the seat as alif, dotless yāʾ or tatweel, sometimes none. One form here: the dot (with
    # its rawm vowel) after the letter before; a dotless-yāʾ or tatweel seat dropped.
    w = w.replace("\u200d", "")
    w = w.replace("\u066e", "\u0649")  # a dotless-beh seat (لَذَآٮٜقُونَ)
    w = w.replace("\u0640\u0670", "\u0627")  # ibdāl written as a dagger alif on tatweel (يَسۡتَـٰخِرُونَ)
    # Ḥamzah's imālah printed in the same word (ٱلۡأَعۡلَىٰ → ٱلَاعۡـلٜىٰ): the dot under a consonant
    # stands for its fatḥah here (imālah is checked elsewhere)
    w = re.sub("(?<=[\u0628-\u063a\u0641-\u0646\u0647\u0648])\u065c", "\u064e", w)
    w = re.sub("(?<=[\u0627\u0649\u0640])([\u064e\u064f\u0650]?)\u065c", "\\1\u06ec", w)
    w = re.sub("[\u0649\u0640]+(?=[\u064e\u064f\u0650]?\u06ec)", "", w)
    w = re.sub("[\u0648\u0649]\u0640*(?=[\u064e\u064f\u0650]?\u06ec)", "", w)  # وَأَحِبَّٰٓوـ۬هُۥ, جَزَٰٓو۬هُۥ
    w = re.sub("\u064e(?=\u0651?\u0627)", "", w)  # a fatḥah before an alif, often unprinted
    cl0 = clusters(w)
    if cl0:  # the shadda the first letter gets from the word before (يُّومِنُونَ)
        cl0[0] = cl0[0].replace("\u0651", "")
        w = "".join(cl0)
    w = re.sub("\u06ec+", "\u06ec", w)
    w = re.sub("^\u0627[\u064e\u064f\u0650]", "\u0627", w)  # naql into the word before: vowel often unprinted
    w = re.sub(TATWEEL + "(?![َُِ۬])", "", w)
    cl = clusters(w)
    if cl:
        # a final sukūn or maddah isn't pronounced at a stop; a rawm vowel prints as ḍamm, fatḥ or
        # kasr in the extraction, so rawm counts as one mark
        cl[-1] = re.sub("[\u064e\u064f\u0650]", "\u064f", cl[-1].replace(SUKUN, "").replace("\u0653", ""))
    return "".join(cl)


def skel(w: str) -> str:
    """Letters only, without hamzah seats or alifs: to tell which word a printed form is."""
    return re.sub("[^\u0628-\u064a]|[\u0627\u0623\u0625\u0624\u0626\u0621\u0649]", "", normalize(w))


def test_set():
    h = hafs_all()
    for v in range(1, 7):
        for line in (OUT / f"vol{v}.jsonl").open():
            r = json.loads(line)
            if r["type"] != "row" or "وقف" not in r["readers"]:
                continue
            ru = set(r.get("ruwat") or r.get("ruwat_min") or [])
            who = [x for x in ("khalaf_an_hamzah", "khallad", "hisham") if x in ru]
            if not who:
                continue
            ws = [w for w in r.get("words", []) if any(c.get("class") == "waqf" for c in w.get("colors", []))]
            if not ws or ws[0].get("spine") not in h:
                continue
            texts = [w["t"] for w in ws]
            # which Ḥafṣ word the forms belong to: in the row's ayah(s), the one with the same
            # letters as the first form (the coloured word's own spine id is often off by one)
            sp = ws[0]["spine"]
            a, b, c = sp.split(":")
            near = [f"{a}:{b}:{n}" for n in range(max(1, int(c) - 3), int(c) + 4)]
            near = [x for x in near if x in h]
            match = [x for x in near if skel(h[x]) == skel(texts[0])]
            if not match:
                continue
            target = min(match, key=lambda x: abs(int(x.split(":")[2]) - int(c)))
            texts = [t for t in texts if skel(t) == skel(h[target])]
            cl = clusters(h[target])
            initial = bool(cl) and is_hamza(cl[0]) and any(t[:1] == "\u0627" and not is_hamza(clusters(t)[0]) for t in texts) \
                or (bool(cl) and is_hamza(cl[0]) and not any(is_hamza(x) for x in cl[1:]))
            yield r["id"], who, target, h[target], texts, r["readers"], initial
            continue
            yield r["id"], who, target, h[target], texts, r["readers"], False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int, default=0)
    ap.add_argument("--rawi", default=None)
    a = ap.parse_args()
    n = covered = 0
    misses = []
    by_label = collections.Counter()
    skipped = dot_lost = end_before = 0
    for rid, who, target, hafs, book, label, initial in test_set():
        if not any(is_hamza(c) for c in clusters(hafs)):
            skipped += 1  # the Ḥafṣ word has no hamzah: a farsh difference or a misaligned row
            continue
        rawi = a.rawi if a.rawi in who else who[0]
        if a.rawi and a.rawi not in who:
            continue
        gen = {key(t): lab for lab, t in (forms_initial(hafs, rawi) if initial else forms(hafs, rawi))}
        n += 1
        miss = [b for b in book if key(b) not in gen]
        hk = key(hafs)
        if miss and all(len(clusters(key(b))) == len(clusters(hk)) and key(b)[:-2] == hk[:-1] for b in miss):
            end_before += 1  # only a vowel on the last letter: naql from the next word (أَنظُرِ ٱ…)
            continue
        nodot = {k.replace("\u06ec", "") for k in gen}
        if miss and all(key(b).replace("\u06ec", "") in nodot for b in miss):
            dot_lost += 1  # the same but for a tas-hīl dot the extraction didn't keep
            continue
        if not miss:
            covered += 1
            for b in book:
                by_label[gen[key(b)]] += 1
        else:
            misses.append((rid, rawi, target, hafs, miss, sorted(gen), re.sub(r"\s+", " ", label)[:90]))
    print(f"{n} rows; all printed forms generated in {covered} ({covered / max(n, 1):.0%}); "
          f"{skipped} skipped (Ḥafṣ word without a hamzah); {dot_lost} differ only by a tas-hīl dot not extracted; "
          f"{end_before} only add a vowel to the last letter (naql from the next word, not this word's waqf)")
    print("forms matched, by rule:", dict(by_label.most_common()))
    for m in misses[: a.show]:
        print("  ", m[0], m[1], m[2], m[3], "book:", " ، ".join(m[4]), "| gen:", " ، ".join(m[5]), "|", m[6])


if __name__ == "__main__":
    main()
