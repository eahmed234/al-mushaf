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
import re
from collections import defaultdict

from .diff import classify
from .rows import BUILD, RUWAT, load_hafs
from .usul import FEATURE_ONLY, WUJUH, apply, detect

TEXT_CATS = [c for c in WUJUH if c not in FEATURE_ONLY]


def same(a: str, b: str, pausal_ok: bool, first: bool = False) -> bool:
    """Equal up to style; a pausal final vowel where the quote ends an ayah; and, on a quote's
    first word, the shadda of idgham it gets from the word before (the book drops it there)."""
    if a == b:
        return True
    kinds, residue = classify(a, b)
    allowed = {"style"} | ({"final_vowel"} if pausal_ok else set()) | ({"idgham"} if first else set())
    return not residue and kinds <= allowed


def _madd_groups(rows: list[dict]) -> None:
    """Readers of "أصحاب X" / "الجميع عدا أصحاب X" rows from the book's madd tables (vol. 1
    pp. 52-53), for the madd the row's text contains. al-Futuh's reader parser leaves these
    bounded when a rawi has two wujuh (Qalun: qasr and tawassut)."""
    from .readings import GENERIC_MADD, madd_tables

    tables = madd_tables()
    hafs = load_hafs()
    for r in rows:
        m = re.search(r"(عدا )?أصحاب (\S+)", r["label"])
        wj = GENERIC_MADD.get(m.group(2).rstrip(".،:")) if m else None
        if not wj or (r["ruwat"] and not r["ruwat_max"]):
            continue
        span = [w["id"] for w in r["words"] if w["id"] in hafs]
        cats = {o.cat for o in detect([(i, hafs[i]) for i in span])}
        cat = "munfasil" if cats & {"munfasil", "silah_mim_hamza"} else ("muttasil" if "muttasil" in cats else None)
        if not cat:
            continue
        has = {x for x, ws in tables[cat].items() if wj in ws}
        members = (set(RUWAT) - has) if m.group(1) else has
        members &= set(r["ruwat_max"] or RUWAT)
        r["ruwat"], r["ruwat_min"], r["madd_group"] = sorted(members), sorted(members), f"{cat}:{wj}"


def rows_in(upto: int, start: int = 1) -> list[dict]:
    """Rows whose words all lie in al-Baqarah start..upto."""
    out = []
    for l in (BUILD / "rows.jsonl").open():
        r = json.loads(l)
        ids = [w["id"] for w in r["words"] if w["id"] and w["id"][0].isdigit()]
        if ids and all(i.startswith("2:") and start <= int(i.split(":")[1]) <= upto for i in ids):
            out.append(r)
    _madd_groups(out)
    return out


_FARSH: dict | None = None


def farsh_texts() -> dict[str, dict[str, str]]:
    """rawi -> word id -> text with that rawi's farsh (a row's readers share their farsh)."""
    global _FARSH
    if _FARSH is None:
        from .farsh import load_places, resolve_farsh

        places, hafs = load_places()
        _FARSH = {r: {i: t.split(" / ")[0] for i, t in resolve_farsh(r, places, hafs)[0].items()} for r in RUWAT}
    return _FARSH


def context(span: list[str], hafs: dict[str, str], text: dict[str, str] | None = None):
    """The span's words plus the next word of the mushaf (context only, never compared), and the
    stop: the span's last word if the quote ends an ayah (where the book shows pausal forms),
    else None (the reading goes on: silah, idgham and naql still look ahead)."""
    text = text or hafs
    words = [(i, text[i]) for i in span]
    if not span:
        return words, None
    order = list(hafs)
    k = order.index(span[-1])
    nxt = order[k + 1] if k + 1 < len(order) else None
    # A quote ending on a pause sign still shows the waṣl form (2:7:6 سَمۡعِهِمُۥۖ), so only an
    # ayah end counts as a stop.
    if nxt and nxt.split(":")[:2] == span[-1].split(":")[:2]:
        return words + [(nxt, text[nxt])], None
    return words, span[-1]  # the quote ends an ayah: a stop


_CLAIMED: dict[str, dict[str, set[str]]] | None = None
# a category's claim needs its own colour where al-Futuh's key gives one (vol. 1 p. 12)
CAT_COLOURS = {"silah_mim": {"sila_mim"}, "silah_mim_hamza": {"sila_mim"}, "imala_ra": {"imala_taqlil", "unmapped"},
               "imala_nas": {"imala_taqlil", "unmapped"}, "imala_kafirin": {"imala_taqlil", "unmapped"},
               "imala_ya": {"imala_taqlil", "unmapped"}}  # a second green is unmapped in the extraction


def claimed(segment: str, cat: str | None = None) -> set[str]:
    """Words a box makes a claim about: coloured in some row of the box (with the category's own
    colour, if it has one). Elsewhere the book may leave uṣūl unstated (2:15 has no silah row at
    all), so a plain word there is no evidence."""
    global _CLAIMED
    if _CLAIMED is None:
        _CLAIMED = {}
        for l in (BUILD / "rows.jsonl").open():
            r = json.loads(l)
            seg = _CLAIMED.setdefault(r["segment"], {})
            for w in r["words"]:
                for c in w.get("classes", []):
                    seg.setdefault(c, set()).add(w["id"])
    seg = _CLAIMED.get(segment, {})
    wanted = CAT_COLOURS.get(cat)
    return set().union(*(ws for c, ws in seg.items() if wanted is None or c in wanted)) if seg else set()


def match_row(r: dict, hafs: dict[str, str]):
    """(matching choices, occurrences, words that never match) for one row."""
    span = [w["id"] for w in r["words"] if w["id"] in hafs]
    readers = r["ruwat"] or r["ruwat_min"] or []
    words, stop = context(span, hafs, farsh_texts().get(readers[0]) if readers else None)
    occs = detect(words, stop=stop)
    seen_words = claimed(r["segment"])
    cats = sorted({o.cat for o in occs if o.cat in TEXT_CATS})
    claimed_cats = {o.cat for o in occs if o.word in claimed(r["segment"], o.cat) or o.nxt in claimed(r["segment"], o.cat)}
    if "silah_mim_hamza" in cats and "munfasil" not in cats:
        cats = sorted(cats + ["munfasil"])  # the silah's madd follows the munfasil wajh
    book = {w["id"]: (w.get("alts") or [w["t"]]) for w in r["words"]}
    last = span[-1] if span else None
    ok, misses = [], defaultdict(int)
    for combo in itertools.product(*(WUJUH[c] for c in cats)):
        choice = dict(zip(cats, combo))
        gen = apply(words, occs, choice)
        bad = [i for i in span if i in seen_words and not any(same(gen[i], t, i == last, i == span[0]) for t in book[i])]
        if not bad:
            ok.append(choice)
        for i in bad:
            misses[i] += 1
    n = max(1, len(list(itertools.product(*(WUJUH[c] for c in cats)))))
    never = [i for i, m in misses.items() if m == n]
    return ok, [c for c in cats if c in claimed_cats or c == "munfasil"], occs, never


def learn(upto: int, start: int = 1):
    hafs = load_hafs()
    prof: dict[str, dict[str, dict[str, list[str]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    gaps = []
    for r in rows_in(upto, start):
        ok, cats, occs, never = match_row(r, hafs)
        readers = r["ruwat"] or r["ruwat_min"]
        if not ok:
            gaps.append((r["id"], r["label"], never))
            continue
        for c in cats:
            seen = sorted({ch[c] for ch in ok})
            if len(seen) == len(WUJUH[c]) and len(seen) > 1:
                continue  # the text can't tell this category's wujūh apart here
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
