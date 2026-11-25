"""Check extraction output against the page and the data, and turn quotes into offsets.

    python3 -m pipeline.validate pipeline/out/RUN/budur        report per page

A row is rejected when its quote isn't on the page (or the start of the next), a rāwī isn't one
of the twenty, `khulf` isn't within `readers`, a place id isn't among the page's Ḥafṣ words, or
a field is missing or out of its set. Kept rows store the quote as offsets into the page's text
(spaces collapsed): `span: [page, start, end]`. Book text is never stored.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from functools import lru_cache
from pathlib import Path

import yaml

from mushaf_data.paths import DATA
from mushaf_data.ruwat import RUWAT
from tools import book

from .pack import WORK

KINDS = {"farsh", "usul", "tahrir", "ittifaq"}
CATS = set(yaml.safe_load((DATA / "profiles.yaml").read_text(encoding="utf-8"))["categories"])
FIELDS = ["place", "kind", "category", "readers", "khulf", "reading", "condition", "scope", "quote"]


def squash(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


@lru_cache(maxsize=4)
def pages(slug: str) -> list[str]:
    return [squash(p) for p in book.pages(slug)]


def page_words(slug: str, page: int) -> set[str]:
    f = WORK / slug / f"p{page:03d}.txt"
    if not f.exists():
        return set()
    body = f.read_text(encoding="utf-8").split("## HAFS WORDS", 1)[1]
    return {line.split("\t")[0] for line in body.splitlines()[1:] if "\t" in line}


def locate(slug: str, page: int, quote: str):
    """[page, start, end] of the quote on the page (or the next page's start), or None."""
    q = squash(quote)
    if not q:
        return None
    ps = pages(slug)
    k = ps[page].find(q)
    if k >= 0:
        if ps[page].find(q, k + 1) >= 0:
            return None  # on the page twice: which place it reads from is unclear
        return [page, k, k + len(q)]
    if page + 1 < len(ps):
        k = ps[page + 1].find(q)
        if 0 <= k < 700:
            return [page + 1, k, k + len(q)]
    return None


def check_row(r: dict, slug: str, page: int, words: set[str]) -> list[str]:
    bad = [f"missing {k}" for k in FIELDS if k not in r]
    if bad:
        return bad
    if r["kind"] not in KINDS:
        bad.append(f"kind {r['kind']}")
    if r["category"] is not None and r["category"] not in CATS:
        bad.append(f"category {r['category']}")
    if not r["readers"]:
        bad.append("no readers")
    bad += [f"rāwī {x}" for x in r["readers"] + r["khulf"] if x not in RUWAT]
    if not set(r["khulf"]) <= set(r["readers"]):
        bad.append("khulf not within readers")
    if len(set(r["readers"])) != len(r["readers"]):
        bad.append("a rāwī twice")
    if words:
        bad += [f"place {p}" for p in r["place"] if p not in words]
    if r["condition"] not in ("wasl", "waqf", None):
        bad.append(f"condition {r['condition']}")
    if r["scope"] not in ("here", "all"):
        bad.append(f"scope {r['scope']}")
    if locate(slug, page, r["quote"]) is None:
        q = squash(r["quote"])
        bad.append("quote on the page more than once" if q and pages(slug)[page].count(q) > 1 else "quote not on the page")
    return bad


def validate(path: Path, slug: str | None = None):
    """(kept rows with spans, rejected rows with reasons) for one output file."""
    d = json.loads(path.read_text(encoding="utf-8"))
    slug = slug or d.get("book", "budur")
    page = d["page"]
    words = page_words(slug, page)
    kept, rejected = [], []
    for r in d.get("rows", []):
        bad = check_row(r, slug, page, words)
        if bad:
            rejected.append((r, bad))
            continue
        row = {k: r[k] for k in FIELDS if k != "quote"}
        if r.get("place_text"):
            row["place_text"] = r["place_text"]
        row["span"] = locate(slug, page, r["quote"])
        kept.append(row)
    return page, kept, rejected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    total = rej = 0
    for f in sorted(Path(a.dir).glob("p*.json")):
        try:
            page, kept, rejected = validate(f)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"{f.name}: not readable ({e})")
            continue
        total += len(kept) + len(rejected)
        rej += len(rejected)
        print(f"p{page}: {len(kept)} rows kept, {len(rejected)} rejected")
        if a.show:
            for r, bad in rejected:
                print("    ", "; ".join(bad), "|", r.get("quote", "")[:80])
    print(f"{total} rows, {rej} rejected", file=sys.stderr)


if __name__ == "__main__":
    main()
