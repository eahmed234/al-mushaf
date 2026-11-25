"""Write a gold set: rows with quotes (kept outside the repo) → pipeline/gold/BOOK/pNNN.json with
offsets instead of quotes, checked by the same validator as the extraction.

    python3 -m pipeline.gold SOURCE.json BOOK
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

from mushaf_data.paths import ROOT

from .validate import FIELDS, check_row, locate, page_words

GOLD = ROOT / "pipeline" / "gold"


def write(rows: list[dict], slug: str) -> list[str]:
    by_page, problems = defaultdict(list), []
    for r in rows:
        bad = check_row(r, slug, r["page"], page_words(slug, r["page"]))
        if bad:
            problems.append(f"p{r['page']} {'; '.join(bad)} | {r['quote'][:60]}")
            continue
        row = {k: r[k] for k in FIELDS if k != "quote"}
        if r.get("place_text"):
            row["place_text"] = r["place_text"]
        row["span"] = locate(slug, r["page"], r["quote"])
        by_page[r["page"]].append(row)
    if not problems:
        d = GOLD / slug
        d.mkdir(parents=True, exist_ok=True)
        for page, rs in by_page.items():
            (d / f"p{page:03d}.json").write_text(json.dumps({"book": slug, "page": page, "rows": rs},
                                                            ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("book")
    a = ap.parse_args()
    problems = write(json.loads(Path(a.source).read_text(encoding="utf-8")), a.book)
    print("\n".join(problems) or "ok")


if __name__ == "__main__":
    main()
