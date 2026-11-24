"""Day 3: learn each rawi's uṣūl profile from al-Futuh's rows, then generate readings from it
and compare them with the book.

    python3 -m spike.profile [--upto AYAH] [--show]

For every row, every combination of wujūh for the text-changing categories in the row's span is
applied to the Hafs words; the combinations that give exactly the row's text are kept. Each
rawi the row names is then recorded as having those wujūh, with the row as the source. A row
no combination reproduces is a gap in the rules (reported with the words that differ).
Lengths (tawassut / ishba) and other features the text can't show stay ambiguous here.
"""

from __future__ import annotations

import argparse
import itertools
import json
from collections import defaultdict

from .diff import classify
from .rows import BUILD, RUWAT, load_hafs
from .usul import FEATURE_ONLY, WUJUH, apply, detect

TEXT_CATS = [c for c in WUJUH if c not in FEATURE_ONLY]


def same(a: str, b: str, pausal_ok: bool) -> bool:
    if a == b:
        return True
    kinds, residue = classify(a, b)
    allowed = {"style"} | ({"final_vowel"} if pausal_ok else set())
    return not residue and kinds <= allowed


def rows_in(upto: int) -> list[dict]:
    out = []
    for l in (BUILD / "rows.jsonl").open():
        r = json.loads(l)
        ids = [w["id"] for w in r["words"] if w["id"] and w["id"][0].isdigit()]
        if ids and all(i.startswith("2:") and int(i.split(":")[1]) <= upto for i in ids):
            out.append(r)
    return out


def match_row(r: dict, hafs: dict[str, str]):
    """(matching choices, occurrences, words that never match) for one row."""
    span = [w["id"] for w in r["words"] if w["id"] in hafs]
    words = [(i, hafs[i]) for i in span]
    occs = detect(words)
    cats = sorted({o.cat for o in occs if o.cat in TEXT_CATS})
    book = {w["id"]: (w.get("alts") or [w["t"]]) for w in r["words"]}
    last = span[-1] if span else None
    ok, misses = [], defaultdict(int)
    for combo in itertools.product(*(WUJUH[c] for c in cats)):
        choice = dict(zip(cats, combo))
        gen = apply(words, occs, choice)
        bad = [i for i in span if not any(same(gen[i], t, i == last) for t in book[i])]
        if not bad:
            ok.append(choice)
        for i in bad:
            misses[i] += 1
    n = max(1, len(list(itertools.product(*(WUJUH[c] for c in cats)))))
    never = [i for i, m in misses.items() if m == n]
    return ok, cats, occs, never


def learn(upto: int):
    hafs = load_hafs()
    prof: dict[str, dict[str, dict[str, list[str]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    gaps = []
    for r in rows_in(upto):
        ok, cats, occs, never = match_row(r, hafs)
        readers = r["ruwat"] or r["ruwat_min"]
        if not ok:
            gaps.append((r["id"], r["label"], never))
            continue
        for c in cats:
            seen = sorted({ch[c] for ch in ok})
            for rawi in readers:
                for wj in seen:
                    prof[rawi][c][wj].append(r["id"] + ("" if len(seen) == 1 else "?"))
    return prof, gaps


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--upto", type=int, default=5, help="learn from al-Baqarah 1..UPTO")
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    prof, gaps = learn(a.upto)
    out = {r: {c: dict(w) for c, w in cs.items()} for r, cs in prof.items()}
    (BUILD / "profiles.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    if a.show:
        for r in RUWAT:
            cs = prof.get(r, {})
            parts = []
            for c in TEXT_CATS:
                if c in cs:
                    parts.append(f"{c}=" + "/".join(f"{w}{'?' if all(x.endswith('?') for x in src) else ''}" for w, src in cs[c].items()))
            print(f"{r:17} " + "  ".join(parts))
    print(f"rows no rule combination reproduces: {len(gaps)}")
    for g in gaps:
        print("  ", *g)


if __name__ == "__main__":
    main()
