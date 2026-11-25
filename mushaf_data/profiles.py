"""Uṣūl profiles from the books (data/profiles.yaml), expanded to every rāwī; wujūh tied to a
place (data/place_wujuh.yaml).

    python3 -m mushaf_data.profiles   check coverage and print the table
"""
from pathlib import Path

import yaml

from .paths import DATA
from .ruwat import RUWAT, SEVEN

PATH = DATA / "profiles.yaml"
PLACES = DATA / "place_wujuh.yaml"


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
            if not str(row.get("cite", "")).strip():
                problems.append(f"{cat}: a row for {', '.join(who)} cites no page")
            for r in who:
                if r not in out:
                    problems.append(f"{cat}: unknown rāwī {r}")
                    continue
                if r in seen:
                    problems.append(f"{cat}: {r} named twice")
                seen.append(r)
                entry = {"wujuh": {w: [row.get("cite")] for w in row["wujuh"]}, "source": "book"}
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



def place_wujuh(path=PLACES) -> list[dict]:
    """Wujūh tied to one place: at `word` the entry's `wujuh`, elsewhere its `elsewhere`."""
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []


def main():
    book = load()
    cats = list(next(iter(book.values())).keys())
    print(f"{len(cats)} categories × {len(RUWAT)} ruwāt, all covered")
    for cat in cats:
        groups = {}
        for r in RUWAT:
            groups.setdefault("/".join(book[r][cat]["wujuh"]), []).append(r)
        print(f"{cat}: " + "; ".join(f"{w} ← {', '.join(rs)}" for w, rs in groups.items()))


if __name__ == "__main__":
    main()
