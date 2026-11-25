"""Pack book pages for extraction: each page's text, the start of the next page (a statement may
run on), and the Ḥafṣ words the page speaks about, with their ids.

    python3 -m pipeline.pack budur 15-25        writes pipeline/work/budur/p015.txt ...

al-Budūr goes through each rubʿ in order and closes it with its "الممال" list, and those lists are
tied to the spine's quarters (mushaf_data.occurrences). A page's words are the quarters from the
one after the last list before it to the one its next list closes (and, on a page that has a
list, the quarter after it, where the page goes on).
"""
from __future__ import annotations

import argparse

from mushaf_data import occurrences
from mushaf_data.paths import ROOT
from mushaf_data.spine import words
from tools import book

WORK = ROOT / "pipeline" / "work"


def quarter_span(slug: str, n: int) -> tuple[int, int]:
    if slug != "budur":
        raise NotImplementedError("page ranges come from al-Budūr's lists; other books need their own anchors")
    tied = {rec["page"]: q for q, rec in occurrences.build(write=False)[0].items()}
    before = [q for pg, q in tied.items() if pg < n]
    after = sorted((pg, q) for pg, q in tied.items() if pg >= n)
    lo = max(before) + 1 if before else 0
    if not after:
        return lo, len(occurrences.quarters()) - 1
    pg, hi = after[0]
    return lo, hi + (1 if pg == n else 0)


def pack(slug: str, pages: list[int]) -> list[dict]:
    qs = occurrences.quarters()
    allp = book.pages(slug)
    h = words()
    out = []
    for n in pages:
        lo, hi = quarter_span(slug, n)
        ids = [w for q in qs[lo:hi + 1] for w in q]
        nxt = allp[n + 1][:600] if n + 1 < len(allp) else ""
        out.append({"page": n, "text": allp[n], "next": nxt, "first": ids[0], "last": ids[-1],
                    "words": [f"{w}\t{h[w]}" for w in ids]})
    return out


def write(slug: str, packed: list[dict]) -> None:
    d = WORK / slug
    d.mkdir(parents=True, exist_ok=True)
    for p in packed:
        (d / f"p{p['page']:03d}.txt").write_text(
            f"# {slug} page {p['page']}; Ḥafṣ words {p['first']} to {p['last']}\n\n"
            f"## PAGE\n{p['text']}\n\n## NEXT PAGE BEGINS (context only)\n{p['next']}\n\n"
            "## HAFS WORDS (id<TAB>text)\n" + "\n".join(p["words"]) + "\n", encoding="utf-8")


def parse_pages(spec: str) -> list[int]:
    out = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("pages")
    a = ap.parse_args()
    packed = pack(a.slug, parse_pages(a.pages))
    write(a.slug, packed)
    for p in packed:
        print(p["page"], p["first"], p["last"], len(p["words"]), "words")


if __name__ == "__main__":
    main()
