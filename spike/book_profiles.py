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
                for k in ("cond", "place", "note", "inherited"):
                    if k in row:
                        entry[k] = row[k]
                out[r][cat] = entry
        missing = [r for r in RUWAT if r not in seen]
        if missing:
            problems.append(f"{cat}: no row for {', '.join(missing)}")
    if problems:
        raise ValueError("profiles.yaml:\n  " + "\n  ".join(problems))
    # waqf on hamz: the same as waṣl for everyone but Ḥamzah and Hishām (their bāb isn't read yet,
    # so they're left to the rows); Khalaf al-ʿĀshir: "وحقق همز الوقف" (idah 121)
    for r in RUWAT:
        if r in WAQF_OWN:
            continue
        for waqf, wasl in WAQF_OF.items():
            if r in ("ishaq", "idris"):
                out[r][waqf] = {"wujuh": {"tahqiq": ["idah 117, 121"]}, "source": "book"}
            elif wasl in out[r]:
                e = out[r][wasl]
                out[r][waqf] = {**e, "note": f"waqf as waṣl ({wasl})"}
            else:
                out[r][waqf] = {"wujuh": {"tahqiq": ["waqf as waṣl"]}, "source": "book"}
    return out


WAQF_OWN = {"khalaf_an_hamzah", "khallad", "hisham"}
WAQF_OF = {"ibdal_sakin_waqf": "ibdal_sakin", "hamzatayn_waqf": "hamzatayn",
           "hamz_waqf_final": None, "hamz_waqf_mid": None}


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
            got = set(learned[r][cat]["wujuh"])
            allowed = set(e["wujuh"])
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
