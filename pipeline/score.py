"""Score an extraction run against the gold set.

    python3 -m pipeline.score pipeline/out/RUN/budur [--pages 16-25] [--show]

The unit is one rāwī at one place: (places, category for uṣūl rows / kind otherwise, rāwī, khulf
or not, the words of the page it was read from), each counted once, pooled over the pages (a statement may be put on the page it starts
or ends on). So splitting a statement into rows, or merging rows, doesn't change the score; who
reads what, with or without khulf, does. A gold unit is found when a run unit has the same
category/kind, rāwī and khulf, shares a place (or both have none), and is the same reading: read
from words of the page that overlap, or given in a row with exactly the same readers. Recall: gold units found;
precision: run units that match one (a restatement counts once; rows about a word or passage
elsewhere, `place: []`, are counted apart). Khulf is compared on farsh and uṣūl rows only. "Loose" ignores category/kind. Rows the validator rejects
count as not there. Row-level keys (whole reader sets) are reported too, as a stricter view.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .gold import GOLD
from .pack import parse_pages
from .validate import validate


def what(r: dict):
    return r["category"] if r["kind"] == "usul" else r["kind"]


def key(r: dict) -> tuple:
    return (frozenset(r["place"]), frozenset(r["readers"]), frozenset(r["khulf"]), what(r))


def units(rs: list[dict]) -> list[tuple]:
    """One per rāwī and fact: (places, rāwī, khulf, category/kind, spans), where spans are every
    place on the page the fact was read from (which reading of the place it is). A fact stated
    twice (a restatement, a summary) is one unit with two spans."""
    out: dict[tuple, tuple[set, set]] = {}
    for r in rs:
        for x in r["readers"]:
            khulf = x in r["khulf"] and r["kind"] == "usul" or x in r["khulf"] and r["kind"] == "farsh"
            k = (frozenset(r["place"]), frozenset([x]), frozenset([x] if khulf else []), what(r))
            spans, groups = out.setdefault(k, (set(), set()))
            spans.add(tuple(r["span"]))
            groups.add(frozenset(r["readers"]))
    return [k + (frozenset(v[0]), frozenset(v[1])) for k, v in out.items()]


def overlap(a: tuple, b: tuple) -> bool:
    return a[0] == b[0] and a[1] < b[2] and b[1] < a[2]


def rows(dirpath: Path, pages: list[int]) -> tuple[list[tuple], int]:
    out, rejected = [], 0
    for p in pages:
        f = dirpath / f"p{p:03d}.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        if d["rows"] and "span" in d["rows"][0]:  # already validated (the gold set)
            kept, rej = d["rows"], []
        else:
            _, kept, rej = validate(f)
        rejected += len(rej)
        out += [(p, r) for r in kept]
    return out, rejected


def match(gold: list, run: list, strict: bool = True):
    """(gold units found, gold units missed, run units matching no gold unit). Not one-to-one: a
    fact the run states twice (a restatement) isn't counted against it."""
    def same(g, m):
        return (((g[0] & m[0]) or (not g[0] and not m[0])) and g[1] == m[1] and g[2] == m[2]
                and (not strict or g[3] == m[3]) and (len(g) < 5 or any(overlap(a, b) for a in g[4] for b in m[4]) or bool(g[5] & m[5])))
    found = [g for g in gold if any(same(g, m) for m in run)]
    missed = [g for g in gold if g not in found]
    extra = [m for m in run if not any(same(g, m) for g in gold)]
    return found, missed, extra


def score(run_dir: Path, pages: list[int], slug: str = "budur") -> dict:
    g_rows, _ = rows(GOLD / slug, pages)
    r_rows, rejected = rows(run_dir, pages)
    gk = list(dict.fromkeys(key(r) for _, r in g_rows))
    rk = list(dict.fromkeys(key(r) for _, r in r_rows))
    kfound, _, kextra = match(gk, rk)
    gu = units([r for _, r in g_rows])
    ru = units([r for _, r in r_rows])
    found, missed, extra = match(gu, ru)
    # rows about a word or passage outside the page's places (place []): not wrong, but outside
    # what the gold set covers; reported apart, not counted in precision
    elsewhere = [u for u in extra if not u[0]]
    extra = [u for u in extra if u[0]]
    ru_scored = [u for u in ru if u[0] or u not in elsewhere]
    lfound, _, _ = match(gu, ru, strict=False)
    where = {}
    for p, r in g_rows + r_rows:
        for u in units([r]):
            where.setdefault(u[:4], (p, r["reading"]))
    return {"gold": len(gu), "run": len(ru_scored), "found": len(found), "rejected": rejected, "elsewhere": elsewhere,
            "recall": len(found) / max(len(gu), 1), "precision": 1 - len(extra) / max(len(ru_scored), 1),
            "loose_recall": len(lfound) / max(len(gu), 1), "missed": missed, "extra": extra, "where": where,
            "rows": len(r_rows), "key_recall": len(kfound) / max(len(gk), 1), "key_precision": 1 - len(kextra) / max(len(rk), 1)}


def fmt(k, where) -> str:
    k = k[:4]
    p, reading = where.get(k, ("?", ""))
    return f"p{p} {','.join(sorted(k[0])) or '-'} {k[3]} [{','.join(sorted(k[1]))}] khulf[{','.join(sorted(k[2]))}] {reading}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--pages", default="16-25")
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    s = score(Path(a.run), parse_pages(a.pages))
    print(f"{a.run}: {s['rows']} rows, {s['rejected']} rejected. Per rāwī: recall {s['recall']:.1%} "
          f"({s['found']}/{s['gold']}), precision {s['precision']:.1%} ({s['run'] - len(s['extra'])}/{s['run']}), loose recall "
          f"{s['loose_recall']:.1%}; {len(s['elsewhere'])} units about words outside the passage. Per row: recall {s['key_recall']:.1%}, precision {s['key_precision']:.1%}")
    if a.show:
        for k in s["missed"]:
            print("  missed ", fmt(k, s["where"]))
        for k in s["extra"]:
            print("  extra  ", fmt(k, s["where"]))


if __name__ == "__main__":
    main()
