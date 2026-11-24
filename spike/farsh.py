"""Day 2: farsh places, found from the letters, and a farsh-only resolver.

    python3 -m spike.farsh            # writes spike/build/farsh.json, prints a summary
    python3 -m spike.farsh --show     # every place with its variants and readers, and each
                                      # rawi's farsh-only differences from Hafs

al-Futuh's colours can't be used to find farsh: its red also marks madd length, silah and
Hamzah's waqf forms (see docs). Instead each word a row gives is classified against the Hafs
word (`spike.diff`): what the uṣūl rules don't explain is a farsh residue. A farsh place is a
word with a residue in some row. Its *variants* are the readings that differ in farsh (two
rows whose words differ only in uṣūl are the same variant); each variant keeps the plainest
word that carries it (fewest uṣūl kinds), and its readers.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field

from .diff import classify
from .rows import BUILD, RUWAT, load_hafs


@dataclass
class Variant:
    text: str  # the plainest word carrying this farsh reading
    kinds: set[str]  # uṣūl kinds that word still has relative to Hafs
    certain: set[str] = field(default_factory=set)
    possible: set[str] = field(default_factory=set)
    words: set[str] = field(default_factory=set)  # every spelling seen (farsh + various uṣūl)
    rows: list[str] = field(default_factory=list)


@dataclass
class Place:
    id: str
    hafs: str
    variants: list[Variant] = field(default_factory=list)

    def variant_of(self, text: str) -> Variant:
        for v in self.variants:
            if not classify(v.text, text)[1]:  # same farsh, maybe different uṣūl
                return v
        k, _ = classify(self.hafs, text)
        v = Variant(text, k)
        self.variants.append(v)
        return v


def load_places() -> tuple[dict[str, Place], dict[str, str]]:
    hafs = load_hafs()
    rows = [json.loads(l) for l in (BUILD / "rows.jsonl").open()]

    def texts(w):
        return w.get("alts") or [w["t"]]

    farsh_ids = {w["id"] for r in rows for w in r["words"] if w["id"] in hafs
                 for t in texts(w) if classify(hafs[w["id"]], t)[1]}
    order = list(hafs)
    places = {i: Place(i, hafs[i]) for i in sorted(farsh_ids, key=order.index)}
    for p in places.values():
        p.variant_of(p.hafs)  # the Hafs reading is always a variant
    for r in rows:
        certain = set(r["ruwat"] or r["ruwat_min"] or [])
        possible = set(r["ruwat_max"] or []) - certain
        for w in r["words"]:
            p = places.get(w["id"])
            if not p:
                continue
            for t in texts(w):
                v = p.variant_of(t)
                v.certain |= certain
                v.possible |= possible
                v.words.add(t)
                v.rows.append(r["id"])
                k, _ = classify(p.hafs, t)
                if len(k - {"style"}) < len(v.kinds - {"style"}):
                    v.text, v.kinds = t, k
    for p in places.values():
        for v in p.variants:
            v.possible -= v.certain
    return places, hafs


def resolve_farsh(rawi: str, places: dict[str, Place], hafs: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    """The passage for one rawi with farsh applied and nothing else: (word id -> text, notes)."""
    text = dict(hafs)
    notes = []
    for pid, p in places.items():
        vs = [v for v in p.variants if rawi in v.certain]
        if len(vs) == 1:
            text[pid] = vs[0].text
        elif len(vs) > 1:
            text[pid] = " / ".join(v.text for v in vs)
            notes.append(f"{pid}: {len(vs)} farsh variants (khulf?)")
        else:
            maybe = [v for v in p.variants if rawi in v.possible]
            if len(maybe) == 1:
                # every row this rawi could be in reads this word the same way
                text[pid] = maybe[0].text
                settled_by_elimination.append((rawi, pid))
            else:
                notes.append(f"{pid}: not named" + (f"; possibly {' / '.join(v.text for v in maybe)}" if maybe else ""))
    return text, notes


settled_by_elimination: list[tuple[str, str]] = []


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    places, hafs = load_places()
    BUILD.mkdir(exist_ok=True)
    out = {pid: {"hafs": p.hafs, "variants": [
        {"text": v.text, "usul_left": sorted(v.kinds - {"style"}), "certain": sorted(v.certain),
         "possible": sorted(v.possible), "spellings": sorted(v.words), "rows": v.rows}
        for v in p.variants]} for pid, p in places.items()}
    (BUILD / "farsh.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    per = {r: resolve_farsh(r, places, hafs) for r in RUWAT}
    if a.show:
        for pid, p in places.items():
            print(f"\n{pid}  (hafs {p.hafs})")
            for v in p.variants:
                left = f" [+{'+'.join(sorted(v.kinds - {'style'}))}]" if v.kinds - {"style"} else ""
                maybe = f"   maybe {','.join(sorted(v.possible))}" if v.possible else ""
                print(f"   {v.text}{left}  <- {','.join(r for r in RUWAT if r in v.certain) or '-'}{maybe}")
        print("\n=== farsh-only: each rawi's differences from Hafs")
        for r in RUWAT:
            text, notes = per[r]
            diffs = [f"{i} {text[i]}" for i in places if text[i] != hafs[i]]
            print(f"{r:17} " + ("; ".join(diffs) or "(same as Hafs)"))
            for n in notes:
                print(f"{'':17}   {n}")
    open_cases = sum(len(per[r][1]) for r in RUWAT)
    print(f"{len(places)} farsh places, {sum(len(p.variants) for p in places.values())} variants; "
          f"{20 * len(places) - open_cases} of {20 * len(places)} rawi/place pairs settled "
          f"({len(settled_by_elimination)} of them by elimination), {open_cases} open", file=sys.stderr)


if __name__ == "__main__":
    main()
