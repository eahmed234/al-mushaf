"""Occurrence tables: which places a category applies to, from the books' per-rubʿ lists.

al-Budūr closes each rubʿ with "الممال": every word of the rubʿ that someone reads with imālah or
taqlīl, and who (for the ten). This module ties each list to its rubʿ (rubʿ starts from the Ḥafṣ
spine's ۞ items and surah starts) by matching its words. A list names words, not places: the
grammatical conditions (ٱلنَّاسِ in the jarr, a kasrah on the rāʾ) stay with the detectors, and the
list decides which words are mumāl at all (it drops عَلَىٰ, إِلَىٰ).

    python3 -m spike.occurrences            build build/imala_table.json and compare with the detectors
    python3 -m spike.occurrences --show 20  list disagreements
"""
import argparse
import json
import re
import sys
from functools import lru_cache
from pathlib import Path

from .rows import SPINE, BUILD
from .usul import detect

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import book  # noqa: E402

OUT = BUILD / "imala_table.json"
# an alif, alif maqṣūrah, dagger alif or tāʾ marbūṭah (al-Kisāʾī's hāʾ al-taʾnīth)
MAYBE = re.compile("[اىٰةآ]")
END = re.compile(r"(المدغم|فوائد|تنبيه|تتمة|فائدة|الإدغام|سورة)")
WORD = re.compile("[ء-يٱً-ْٰ]+")
IMALA_CATS = {"imala_ra", "imala_nas", "imala_kafirin", "imala_ya", "imala_ya_ra", "imala_jaa_shaa",
              "imala_zad", "imala_fiil", "imala_duri_kisai"}


def skel(w: str) -> str:
    """Letters for matching a book word with a Ḥafṣ word: no marks, alifs, hamzah or tatweel."""
    w = book.fold(w).replace("ى", "ي")
    w = re.sub("[أإؤئآ]", "ء", w)  # one hamzah, any seat
    return re.sub("[^ء-ي]|[اـ]", "", w)


def skels(w: str) -> set:
    """A word's skeleton, also without a leading wāw/fāʾ (prose conjunction or the word's own)."""
    k = skel(w)
    return {k, k[1:]} if k[:1] in ("و", "ف") and len(k) >= 3 else {k}


def tokens(text: str) -> set:
    """The list's words as skeletons, each also without a prose wāw/fāʾ (بالكافرين وللكافرين)."""
    return {k for t in WORD.findall(text) for k in skels(t) if len(k) >= 2}


@lru_cache(maxsize=1)
def quarters():
    """Word-id lists in order: a quarter starts at each ۞ of the spine and at each surah."""
    from .waqf_check import hafs_all
    h = hafs_all()
    starts = set()
    for line in SPINE.open():
        it = json.loads(line)
        if it["kind"] == "hizb":
            s, a, _ = it["id"].split(":")
            starts.add((int(s), int(a)))
    out, cur, last_s = [], [], None
    for wid in h:
        s, a, n = map(int, wid.split(":"))
        if cur and n == 1 and ((s, a) in starts or s != last_s):
            out.append(cur)
            cur = []
        cur.append(wid)
        last_s = s
    if cur:
        out.append(cur)
    return out


def lists():
    """al-Budūr's "الممال" sections in order: (page, text)."""
    out, seen = [], set()
    for n, t in enumerate(book.pages("budur")):
        if n < 15:  # the introduction (al-Fātiḥah starts on p. 15)
            continue
        t = re.sub(r"\s+", " ", t)
        for m in re.finditer("الممال", t):
            body = t[m.end(): m.end() + 1500]
            if not re.search("(أمال|قلل|بالإمالة|بالتقليل)", body[:300]):
                continue  # a mention, not a list
            e = END.search(body, 40)  # a heading like "(سورة …)" right after "الممال" isn't its end
            body = body[: e.start()] if e else body
            if (n, body[:40]) not in seen:
                seen.add((n, body[:40]))
                out.append((n, body, t[max(0, m.start() - 1500): m.start()]))
    return out


def build():
    from .waqf_check import hafs_all
    h = hafs_all()
    qs = quarters()
    qskel = [{} for _ in qs]
    for i, q in enumerate(qs):
        for wid in q:
            if MAYBE.search(h[wid]):  # only words that could carry imālah
                for k in skels(h[wid]):
                    qskel[i].setdefault(k, []).append(wid)
    qall = [{k for w in q for k in skels(h[w]) if len(k) >= 3} for q in qs]
    L = lists()
    # score of list j against quarter i: its longer words among the rubʿ's imālah candidates, and
    # the commentary just before it (the end of that rubʿ) among all the rubʿ's words
    S = []
    for page, text, before in L:
        toks = {t for t in tokens(text) if len(t) >= 3}
        ctx = {k for k in tokens(before) if len(k) >= 3}
        S.append([len(toks & set(qskel[i])) + 0.5 * len(ctx & qall[i]) for i in range(len(qs))])
    # monotonic alignment (lists and quarters both in order; either may be skipped), counting a
    # pair only when its score is at least 3
    nL, nQ = len(L), len(qs)
    best = [[0.0] * (nQ + 1) for _ in range(nL + 1)]
    move = [[0] * (nQ + 1) for _ in range(nL + 1)]
    for j in range(1, nL + 1):
        for i in range(1, nQ + 1):
            sc = S[j - 1][i - 1]
            opts = [(best[j - 1][i], 1), (best[j][i - 1], 2)]
            if sc >= 3:
                opts.append((best[j - 1][i - 1] + sc, 3))
            best[j][i], move[j][i] = max(opts)
    tbl, unmatched = {}, []
    j, i = nL, nQ
    while j and i:
        m = move[j][i]
        if m == 3:
            page, text, _ = L[j - 1]
            toks = tokens(text)
            hits = sorted({w for t in toks for w in qskel[i - 1].get(t, [])})
            # "رءوس الآي": the ayah-final alif maqṣūrahs of the rubʿ, named as a class
            ruus = bool(re.search("ر[ءؤو]+وس الا?ي", book.fold(text)))
            tbl[i - 1] = {"page": page, "words": hits, "tokens": sorted(toks), "ruus": ruus}
            j, i = j - 1, i - 1
        elif m == 1:
            unmatched.append(L[j - 1][0])
            j -= 1
        else:
            i -= 1
    unmatched.reverse()
    OUT.write_text(json.dumps({str(k): v for k, v in tbl.items()}, ensure_ascii=False, indent=1))
    table.cache_clear()
    return tbl, unmatched


@lru_cache(maxsize=1)
def rub_starts() -> set:
    """Quarters that start at a ۞ (or al-Fātiḥah / al-Baqarah): a rubʿ's list covers the quarters
    from there to the one it is tied to (in juzʾ ʿAmma a rubʿ spans several surahs)."""
    starts = set()
    for line in SPINE.open():
        it = json.loads(line)
        if it["kind"] == "hizb":
            s, a, _ = it["id"].split(":")
            starts.add(f"{s}:{a}:1")
    return {i for i, q in enumerate(quarters()) if q[0] in starts or q[0] in ("1:1:1", "2:1:1")}


@lru_cache(maxsize=1)
def table() -> dict:
    if not OUT.exists():
        build()
    tbl = {int(k): v for k, v in json.loads(OUT.read_text()).items()}
    out = dict(tbl)
    rs = rub_starts()
    for i, rec in tbl.items():
        j = i
        while j not in rs and j - 1 >= 0 and j - 1 not in tbl:
            j -= 1
            out[j] = rec
    return out


@lru_cache(maxsize=1)
def quarter_of() -> dict:
    return {w: i for i, q in enumerate(quarters()) for w in q}


def listed(word_id: str, hafs_word: str):
    """True/False: al-Budūr's list for the word's rubʿ names it (any of its places);
    None: that rubʿ's list isn't tied yet."""
    rec = table().get(quarter_of().get(word_id, -1))
    if rec is None:
        return None
    return bool(skels(hafs_word) & set(rec["tokens"])) or (rec.get("ruus", False) and ruus_word(word_id, hafs_word))


@lru_cache(maxsize=1)
def ayah_last() -> set:
    from .waqf_check import hafs_all
    last = {}
    for w in hafs_all():
        s, a, n = w.split(":")
        last[(s, a)] = w
    return set(last.values())


def ruus_word(word_id: str, hafs_word: str) -> bool:
    return word_id in ayah_last() and re.search("\u0649[\u0670\u0653\u06d6-\u06db]*$", hafs_word) is not None


# the five words written with yāʾ whose alif is never mumāl (al-Wāfī pp. 142-143): لَدَى (Ghāfir),
# زَكَىٰ (al-Nūr), and the particles حَتَّىٰ, إِلَىٰ, عَلَىٰ; matched with any prefix (وَعَلَىٰ, فَإِلَىٰ)
NEVER_MUMAL = {"لدي", "زكي", "حتي", "لي", "علي"}


def imala_excluded(hafs_word: str, word_id: str = "") -> bool:
    k = skel(hafs_word)
    if k == "زكي":  # only مَا زَكَىٰ مِنكُم (al-Nūr 21); زَكَّىٰ elsewhere is mumāl
        return word_id.startswith("24:21:")
    return k in NEVER_MUMAL or (k[:1] in ("\u0648", "\u0641") and k[1:] in NEVER_MUMAL)


def compare(tbl, show=0):
    from .waqf_check import hafs_all
    h = hafs_all()
    qs = quarters()
    named_n = dropped = unseen = 0
    drops, misses = [], []
    for i, rec in tbl.items():
        words = [(w, h[w]) for w in qs[i]]
        det = set()
        for k in range(0, len(words), 40):
            det |= {o.word for o in detect(words[k:k + 41]) if o.cat in IMALA_CATS}
        for w in words:  # at a stop too (هُدٗى with tanwīn)
            det |= {o.word for o in detect([w], stop=w[0]) if o.cat in IMALA_CATS}
        toks = set(rec["tokens"])
        named = {w for w, t in words if skels(t) & toks and MAYBE.search(t) or rec.get("ruus") and ruus_word(w, t)}
        named_n += len(det & named)
        dropped += len(det - named)
        drops += [(w, h[w], rec["page"]) for w in sorted(det - named)]
        # a word the list names that no detector finds anywhere in the rubʿ
        found = {skel(h[w]) for w in det}
        miss = sorted({skel(h[w]) for w in named if len(skel(h[w])) >= 3} - found)
        unseen += len(miss)
        misses += [(m, rec["page"]) for m in miss]
    print(f"{len(tbl)} quarters tied. Detector hits: {named_n} on words the list names, {dropped} on "
          f"words it doesn't (the gate drops them). Words the list names that no detector finds in "
          f"the rubʿ: {unseen}")
    for x in drops[:show]:
        print("  dropped:", *x)
    for x in misses[:show]:
        print("  named, not detected:", *x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int, default=0)
    a = ap.parse_args()
    tbl, unmatched = build()
    print(f"{len(lists())} lists in al-Budūr; {len(tbl)} tied to a quarter of {len(quarters())}; "
          f"{len(unmatched)} not tied (pages {unmatched[:10]}…)")
    table.cache_clear()
    compare(table(), a.show)


if __name__ == "__main__":
    main()
