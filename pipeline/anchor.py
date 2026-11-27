"""Anchor the listed words of the word-by-word chapters to places of the Ḥafṣ text.

    python3 -m pipeline.anchor [--show]

The yāʾāt al-iḍāfah, the yāʾāt al-zawāʾid and the idghām ṣaghīr are chapters of single words
(Eisa 2026-11-26: they could be farsh). Their data/usul tables name words, not places. Here each
listed word or phrase is matched to consecutive Ḥafṣ words by skeleton (occurrences.skel; a book
word may lack the Ḥafṣ word's prefix و ف ب ل ك), and data/usul gets, per listed entry:

  places   the word ids of every match (the first word of each phrase match)
  anchor   all: every form matched somewhere; some: some forms matched; none

A sūrah named in brackets in the entry ("بيتي (نوح)") is not resolved yet: all matches are kept.
Run by pipeline.unify_merge.
"""
from __future__ import annotations

import argparse
import re
from collections import defaultdict
from functools import lru_cache

from mushaf_data.occurrences import skel
from mushaf_data.spine import words

TABLES = ("ya_idafa", "ya_zaida", "idgham_saghir")
PREFIX = "وفبلك"


@lru_cache(maxsize=1)
def _index():
    h = words()
    order = list(h)
    sk = [skel(h[w]) for w in order]
    by = defaultdict(list)
    for i, k in enumerate(sk):
        by[k].append(i)
        if len(k) > 2 and k[0] in PREFIX:
            by[k[1:]].append(i)
            if len(k) > 3 and k[1] in PREFIX:
                by[k[2:]].append(i)
    return order, sk, by


def _same(book: str, hafs: str) -> bool:
    return book == hafs or (hafs[:1] in PREFIX and hafs[1:] == book) or (len(hafs) > 2 and all(c in PREFIX for c in hafs[:2]) and hafs[2:] == book)


def same(book: str, hafs: str) -> bool:
    """Equal skeletons, the Ḥafṣ word perhaps with a prefix; a final yāʾ in one and not the other
    is allowed (the Ḥafṣ text drops the yāʾāt al-zawāʾid the book writes: آتاني / ءَاتَىٰنِ)."""
    return any(_same(b, f) for b in {book, book.rstrip("ي")} for f in {hafs, hafs.rstrip("ي")} if b and f)


def find(phrase: str) -> list[str]:
    """Word ids where the phrase starts. Brackets and the book's notes are left out."""
    toks = [skel(t) for t in re.sub(r"\([^)]*\)", " ", phrase).split()]
    toks = [t for t in toks if t]
    while "ي" in toks[:-1]:  # the vocative يا is joined to its word in the Ḥafṣ text (يَٰعِبَادِ)
        i = toks.index("ي")
        toks[i: i + 2] = ["ي" + toks[i + 1]]
    if not toks:
        return []
    order, sk, by = _index()
    out = []
    first = by.get(toks[0], []) + by.get(toks[0].rstrip("ي"), []) + by.get(toks[0] + "ي", [])
    for i in sorted(set(first)):
        if all(i + j < len(sk) and same(t, sk[i + j]) for j, t in enumerate(toks)):
            out.append(order[i])
    return sorted(set(out), key=lambda w: tuple(int(x) for x in w.split(":")))


def anchor(table: dict) -> dict:
    """Adds `places` and `anchor` to each listed entry; returns counts."""
    n = defaultdict(int)
    for x in table.get("listed") or []:
        hits = {str(w): find(str(w)) for w in x.get("words") or []}
        found = [w for w, ps in hits.items() if ps]
        x["places"] = sorted({p for ps in hits.values() for p in ps}, key=lambda w: tuple(int(v) for v in w.split(":")))
        x["anchor"] = "all" if len(found) == len(hits) else "some" if found else "none"
        if x["anchor"] != "all":
            x["unanchored"] = [w for w, ps in hits.items() if not ps]
        n[x["anchor"]] += 1
    return dict(n)


def main():
    import yaml

    from mushaf_data.paths import DATA
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    for c in TABLES:
        t = yaml.safe_load((DATA / "usul" / f"{c}.yaml").read_text(encoding="utf-8"))
        print(c, anchor(t))
        if a.show:
            for x in t["listed"]:
                if x["anchor"] != "all":
                    print("   ", x["anchor"], x.get("unanchored"))


if __name__ == "__main__":
    main()
