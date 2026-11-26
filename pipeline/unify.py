"""Check the unified category tables (pipeline/prompt_unify.md).

    python3 -m pipeline.unify [CATEGORY ...]     check pipeline/out/unified/*.yaml

Every case must list all twenty ruwāt; every wajh used must be in the table's vocabulary; every
cite must be a page some row of that category came from ("wafi 51", "idah 57"); a rāwī with no
wujūh must have a line in `open`. Prints per table: cases, listed words, open questions, problems.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

from mushaf_data.paths import ROOT
from mushaf_data.ruwat import RUWAT

OUT = ROOT / "pipeline/out/unified"
WORK = ROOT / "pipeline/work/unify"


def check(path: Path) -> tuple[dict, list[str]]:
    t = yaml.safe_load(path.read_text(encoding="utf-8"))
    src = json.loads((WORK / f"{path.stem}.json").read_text(encoding="utf-8"))
    pages = {f"{r['book']} {r['page']}" for r in src["rows"]}
    vocab = {w["id"] for w in t.get("wujuh", [])}
    bad = []

    def cites(cs, where):
        for c in cs or []:
            if str(c) not in pages and src["rows"]:
                bad.append(f"{where}: cite {c} is not a page of this category's rows")

    for case in t.get("cases", []) or []:
        rw = case.get("ruwat", {}) or {}
        miss = [r for r in RUWAT if r not in rw]
        if miss:
            bad.append(f"case {case.get('case')!r}: missing {', '.join(miss)}")
        for r, v in rw.items():
            if r not in RUWAT:
                bad.append(f"case {case.get('case')!r}: unknown rāwī {r}")
                continue
            for w in v.get("wujuh", []) or []:
                if w not in vocab:
                    bad.append(f"case {case.get('case')!r}: {r} wajh {w} not in the vocabulary")
            cites(v.get("cite"), f"{r}")
    for item in t.get("listed", []) or []:
        for r, ws in (item.get("ruwat") or {}).items():
            if r not in RUWAT:
                bad.append(f"listed {item.get('words')}: unknown rāwī {r}")
            for w in ws or []:
                if w not in vocab:
                    bad.append(f"listed {item.get('words')}: {r} wajh {w} not in the vocabulary")
        cites(item.get("cite"), f"listed {item.get('words')}")
    n_empty = sum(1 for case in t.get("cases", []) or [] for v in (case.get("ruwat") or {}).values() if not v.get("wujuh"))
    if n_empty and not t.get("open"):
        bad.append(f"{n_empty} ruwāt with no wujūh and nothing in open")
    stats = {"cases": len(t.get("cases") or []), "listed": len(t.get("listed") or []), "open": len(t.get("open") or []),
             "wujuh": len(vocab), "empty": n_empty}
    return stats, bad


def main():
    names = sys.argv[1:] or [p.stem for p in sorted(OUT.glob("*.yaml"))]
    total = 0
    for n in names:
        p = OUT / f"{n}.yaml"
        if not p.exists():
            print(f"{n}: not written")
            continue
        try:
            stats, bad = check(p)
        except Exception as e:  # noqa: BLE001
            print(f"{n}: unreadable ({e})")
            total += 1
            continue
        total += len(bad)
        print(f"{n}: {stats}" + (f"  {len(bad)} problems" if bad else ""))
        for b in bad[:12]:
            print("    ", b)
    print(f"{total} problems", file=sys.stderr)


if __name__ == "__main__":
    main()
