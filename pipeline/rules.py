"""Rules read from uṣūl chapters (al-Wāfī, al-Īḍāḥ; pipeline/prompt_rules.md): validated, then
checked against the profile table.

    python3 -m pipeline.rules pipeline/out/RUN/wafi [--show]

A row is rejected when its quote isn't on the page (once), a rāwī is unknown, khulf isn't
within the readers, or the category / wajh isn't one of ours (`new:...` categories pass). Kept
rows are compared with data/profiles.yaml: the wajh should be among the rāwī's wujūh there, and
a rāwī given it with khulf should have more than one. New categories are listed apart.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from mushaf_data.profiles import load
from mushaf_data.ruwat import RUWAT
from mushaf_data.usul import WUJUH

from .validate import CATS, locate, squash, pages

FIELDS = ["category", "wajh", "readers", "khulf", "reading", "applies", "words", "except", "scope", "condition", "quote"]


def check_row(r: dict, slug: str, page: int) -> list[str]:
    bad = [f"missing {k}" for k in FIELDS if k not in r]
    if bad:
        return bad
    cat = r["category"]
    if not (cat in CATS or str(cat).startswith("new:")):
        bad.append(f"category {cat}")
    elif cat in WUJUH and r["wajh"] is not None and r["wajh"] not in WUJUH[cat]:
        bad.append(f"wajh {r['wajh']} not in {cat}")
    bad += [f"rāwī {x}" for x in r["readers"] + r["khulf"] if x not in RUWAT]
    if not r["readers"]:
        bad.append("no readers")
    if not set(r["khulf"]) <= set(r["readers"]):
        bad.append("khulf not within readers")
    if r["scope"] not in ("all", "listed", "place"):
        bad.append(f"scope {r['scope']}")
    if locate(slug, page, r["quote"]) is None:
        q = squash(r["quote"])
        bad.append("quote on the page more than once" if q and pages(slug)[page].count(q) > 1 else "quote not on the page")
    return bad


def against_profiles(rows: list[dict]) -> dict:
    prof = load()
    agree, conflict, new = [], [], Counter()
    for r in rows:
        cat = r["category"]
        if str(cat).startswith("new:"):
            new[cat] += 1
            continue
        if r["wajh"] is None or cat not in WUJUH or r["condition"] == "waqf" or r["scope"] != "all":
            continue  # the profile is a rāwī's general waṣl rule: listed words and single places are its exceptions
        for x in r["readers"]:
            p = prof[x].get(cat, {}).get("wujuh", {})
            if r["wajh"] not in p:
                conflict.append((r["_page"], cat, x, r["wajh"], "not in profile " + "/".join(p)))
            elif x in r["khulf"] and len(p) < 2:
                conflict.append((r["_page"], cat, x, r["wajh"], "khulf, profile has one wajh"))
            else:
                agree.append((cat, x, r["wajh"]))
    return {"agree": agree, "conflict": conflict, "new": new}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    kept, rejected = [], []
    for f in sorted(Path(a.dir).glob("p*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        for r in d["rows"]:
            bad = check_row(r, d["book"], d["page"])
            (rejected.append((d["page"], r, bad)) if bad else kept.append({**r, "_page": d["page"]}))
    res = against_profiles(kept)
    pairs = len(res["agree"]) + len(res["conflict"])
    print(f"{a.dir}: {len(kept)} rules kept, {len(rejected)} rejected; against the profile table: "
          f"{len(res['agree'])}/{pairs} rāwī-wajh pairs agree; new categories: {dict(res['new'])}")
    if a.show:
        for p, r, bad in rejected:
            print("  rejected", p, "; ".join(bad), "|", r.get("quote", "")[:70])
        for c in res["conflict"]:
            print("  conflict", *c)


if __name__ == "__main__":
    main()
