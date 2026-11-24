"""Uṣūl profiles from the books (data/profiles.yaml), expanded to every rāwī.

    python3 -m spike.book_profiles            check coverage and print the table
    python3 -m spike.book_profiles --vs-rows  compare with the profiles learned from al-Futūḥ's rows
"""
import argparse
from pathlib import Path

import yaml

from .rows import RUWAT

PATH = Path(__file__).parent / "data" / "profiles.yaml"
SEVEN = RUWAT[:14]


def load(path=PATH):
    """{rawi: {cat: {"wujuh": {wajh: [cite]}, "source": "book", "cond"/"place"/"note": ...}}}.
    Raises if a category leaves a rāwī out or names one twice."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    out = {r: {} for r in RUWAT}
    problems = []
    for cat, rows in data["categories"].items():
        seen = []
        for row in rows:
            who = row["who"]
            if who == "rest_as_wasl":  # waqf categories: everyone not named reads as in waṣl
                for r in RUWAT:
                    if r in seen:
                        continue
                    src = out[r].get(row.get("wasl")) if row.get("wasl") else None
                    out[r][cat] = ({**src, "note": f"waqf as waṣl ({row['wasl']})"} if src else
                                   {"wujuh": {w: ["waqf as waṣl"] for w in row.get("wujuh", ["tahqiq"])}, "source": "book"})
                    seen.append(r)
                continue
            if who == "rest7":
                who = [r for r in SEVEN if r not in seen]
            for r in who:
                if r not in out:
                    problems.append(f"{cat}: unknown rāwī {r}")
                    continue
                if r in seen:
                    problems.append(f"{cat}: {r} named twice")
                seen.append(r)
                entry = {"wujuh": {w: [row["cite"]] for w in row["wujuh"]}, "source": "book"}
                for k in ("cond", "place", "note", "inherited", "option"):
                    if k in row:
                        entry[k] = row[k]
                out[r][cat] = entry
        missing = [r for r in RUWAT if r not in seen]
        if missing:
            problems.append(f"{cat}: no row for {', '.join(missing)}")
    if problems:
        raise ValueError("profiles.yaml:\n  " + "\n  ".join(problems))
    return out



def vs_rows(book, upto=20):
    """Where the rows of al-Futūḥ (2:1-upto) show a wajh the book profile doesn't allow, or the
    book allows wujūh the rows never show (expected: the passage is short)."""
    from .readings import full_profiles

    learned, _, _, _ = full_profiles(upto)
    conflicts, unseen = [], []
    for r in RUWAT:
        for cat, e in book[r].items():
            if cat not in learned[r]:
                continue
            allowed = set(e["wujuh"])
            lw = learned[r][cat]["wujuh"]
            # a learned wajh counts only if some row behind it isn't also behind an allowed wajh
            # (a quote ending at a pause sign matches both the waṣl and the waqf form)
            ok_rows = {x for w in allowed & set(lw) for x in lw[w]}
            got = {w for w, src in lw.items() if w in allowed or set(src) - ok_rows}
            if got - allowed:
                conflicts.append((r, cat, sorted(got - allowed), sorted(allowed), learned[r][cat]["source"]))
            elif allowed - got:
                unseen.append((r, cat, sorted(allowed - got)))
    return conflicts, unseen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vs-rows", action="store_true")
    a = ap.parse_args()
    book = load()
    if a.vs_rows:
        conflicts, unseen = vs_rows(book)
        print(f"{len(conflicts)} conflicts (rows show a wajh the book doesn't give):")
        for c in conflicts:
            print("  ", *c)
        print(f"{len(unseen)} book wujūh the passage's rows don't show:")
        for u in unseen:
            print("  ", *u)
        return
    cats = list(next(iter(book.values())).keys())
    print(f"{len(cats)} categories × {len(RUWAT)} ruwāt, all covered")
    for cat in cats:
        groups = {}
        for r in RUWAT:
            groups.setdefault("/".join(book[r][cat]["wujuh"]), []).append(r)
        print(f"{cat}: " + "; ".join(f"{w} ← {', '.join(rs)}" for w, rs in groups.items()))


if __name__ == "__main__":
    main()
