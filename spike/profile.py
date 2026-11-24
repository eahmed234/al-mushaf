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
    for r in out:
        extra = EXTRA_READERS.get(r["id"])
        if extra:
            r["ruwat"] = sorted(set(r["ruwat"] or r["ruwat_min"] or []) | extra)
            r["ruwat_min"] = r["ruwat"]
            r["khulf_added"] = sorted(extra)
    return out


# "الجميع عدا من سيأتي" still covers a rawi named in a following row for his *other* wajh
# (Eisa, 2026-11-24: at 2:3 row 1 includes Qalun's iskan, though row 2 names him for silah).
# Filled by `khulf_convention` from a first pass of the profiles: row id -> rawis to add.
EXTRA_READERS: dict[str, set[str]] = {}


def khulf_convention(prof, upto: int, start: int = 1) -> dict[str, set[str]]:
    """For each "الجميع عدا من سيأتي" row: the rawis its following rows (same sub-segment) name
    who also have, in their own profile, the wajh row 1 shows for every category where the two
    rows differ. Those rawis read row 1 too."""
    hafs = load_hafs()
    rows = rows_in(upto, start)
    # khulf evidence: categories where some box shows the rawi with two different wujūh
    # (Qalun's iskan and silah in the 2:4 box); a wajh seen only in other boxes is not enough
    # (Ruways's izhar at 2:2 says nothing about his idgham at 2:20)
    per_box: dict[tuple, set] = defaultdict(set)
    matches = {r["id"]: match_row(r, hafs)[0] for r in rows}
    for r in rows:
        ok = matches[r["id"]]
        for c in {c for ch in ok for c in ch}:
            vals = {ch.get(c) for ch in ok}
            if len(vals) == 1:
                for rawi in (r["ruwat"] or r["ruwat_min"] or []):
                    per_box[(rawi, r["segment"], c)] |= vals
    khulf = {(rawi, c) for (rawi, _, c), v in per_box.items() if len(v) > 1}
    # and the book's madd tables, which state two wujūh outright (al-Duri: qasr and tawassut, v1 p. 52)
    from .readings import madd_tables

    for cat, per in madd_tables().items():
        khulf |= {(rawi, cat) for rawi, ws in per.items() if len(ws) > 1}
    # and place entries that give two wujuh (a footnote's "بخلاف عنه")
    from .readings import PLACE_WUJUH

    khulf |= {(e["rawi"], e["category"]) for e in PLACE_WUJUH if len(e["wujuh"]) > 1}
    out: dict[str, set[str]] = {}
    for k, r in enumerate(rows):
        if "الجميع عدا" not in r["label"]:
            continue  # "الجميع عدا من سيأتي", and "الجميع عدا أصحاب X" (Eisa: 2:18 includes Qalun)
        ok1 = matches[r["id"]]
        if not ok1:
            continue
        add = set()
        # the other rows of the same sub-segment
        sub = []
        for later in rows[k + 1 :]:
            if later["segment"] != r["segment"] or later["n"] == "1":
                break
            sub.append(later)
        for later in sub:
            okl = matches[later["id"]]
            for rawi in (later["ruwat"] or later["ruwat_min"] or []):
                if rawi in (r["ruwat"] or []):
                    continue
                # a choice of row 1 that the rawi's profile has, wherever the two rows differ
                for c1 in ok1:
                    if any(all(c1.get(c) == cl.get(c) or c1.get(c) in prof.get(rawi, {}).get(c, {})
                               for c in set(c1) | set(cl)) for cl in okl):
                        diff = [c for c in c1 if any(c1.get(c) != cl.get(c) for cl in okl)]
                        if diff and all(c1[c] in prof.get(rawi, {}).get(c, {}) and (rawi, c) in khulf for c in diff):
                            add.add(rawi)
                            break
        if add:
            out[r["id"]] = add
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
    if nxt and nxt.split(":")[:2] == span[-1].split(":")[:2]:
        return words + [(nxt, text[nxt])], None
    return words, span[-1]  # the quote ends an ayah: a stop


PAUSE_SIGNS = set("\u06d6\u06d7\u06d8\u06d9\u06da\u06db")


def contexts(span: list[str], hafs: dict[str, str], text: dict[str, str] | None = None):
    """Every way the span can be read: at a pause sign the reader may stop or go on, and the book
    shows either (2:7:6 سَمۡعِهِمُۥۖ goes on; 2:20:19 وَأَبۡصَٰرِهِمۡۚ stops)."""
    words, stop = context(span, hafs, text)
    out = [(words, stop)]
    if span and stop is None and PAUSE_SIGNS & set(hafs[span[-1]]):
        out.append((words[: len(span)], span[-1]))
    return out


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


# which kind of difference (spike.diff) each category makes in a word's text
CAT_KIND = {"munfasil": "madd", "silah_mim": "silah", "silah_mim_hamza": "silah", "silah_ha": "silah",
            "ibdal_sakin": "hamz", "ibdal_sakin_waqf": "hamz", "naql": "hamz", "naql_word": "hamz",
            "hamzatayn": "hamz", "hamzatayn_waqf": "hamz", "hamz_waqf_final": "hamz", "hamz_waqf_mid": "hamz",
            "idgham_kabir": "idgham", "idgham_ghunna": "idgham", "sakt_huruf": "sakt", "badal": "madd",
            "imala_ra": "imala", "imala_nas": "imala", "imala_kafirin": "imala", "imala_ya": "imala"}
_REVIEWED: set | None = None


def reviewed(cat: str, word: str, nxt: str | None = None) -> bool:
    """A detector's place counts once some row of the book writes that word (or, for idgham, the
    next word) with the category's kind of difference from Hafs. Stands in for the reviewed
    occurrence tables of the real model: عَلَىٰ / إِلَىٰ never get an imala dot, so they drop out."""
    global _REVIEWED
    if _REVIEWED is None:
        hafs = load_hafs()
        _REVIEWED = set()
        for l in (BUILD / "rows.jsonl").open():
            for w in json.loads(l)["words"]:
                if w["id"] in hafs:
                    for t in w.get("alts") or [w["t"]]:
                        if t != hafs[w["id"]]:
                            _REVIEWED |= {(k, w["id"]) for k in classify(hafs[w["id"]], t)[0]}
    kind = CAT_KIND.get(cat)
    if kind is None or cat == "munfasil":
        return True
    return (kind, word) in _REVIEWED or (cat.startswith("idgham") and (kind, nxt) in _REVIEWED)


def quote_starts(r: dict) -> set[str]:
    """Words where a quote begins: the row's first word, and in a "..." row the first word it
    quotes itself. The book drops the idgham shadda a word gets from the word before there."""
    ids = [w["id"] for w in r["words"] if w["id"]]
    first_quoted = next((w["id"] for w in r["words"] if w["src"] == "quote" and w["id"]), None)
    return {x for x in (ids[0] if ids else None, first_quoted) if x}


def match_row(r: dict, hafs: dict[str, str]):
    """(matching choices, claimed categories, occurrences, words that never match) for one row,
    over every way the span can be read (stop or not at a pause sign)."""
    span = [w["id"] for w in r["words"] if w["id"] in hafs]
    readers = r["ruwat"] or r["ruwat_min"] or []
    book = {w["id"]: (w.get("alts") or [w["t"]]) for w in r["words"]}
    seen_words = claimed(r["segment"])
    last = span[-1] if span else None
    starts = quote_starts(r)
    ok, all_cats, all_occs, never_sets = [], set(), [], []
    # if the print fits a stop at a pause sign, it is a stop: don't also learn the waṣl reading
    ctxs = contexts(span, hafs, farsh_texts().get(readers[0]) if readers else None)
    for words, stop in sorted(ctxs, key=lambda c: c[1] is None):
        if ok:
            break
        occs = [o for o in detect(words, stop=stop) if reviewed(o.cat, o.word, o.nxt)]
        cats = sorted({o.cat for o in occs if o.cat in TEXT_CATS})
        claimed_cats = {o.cat for o in occs if o.word in claimed(r["segment"], o.cat) or o.nxt in claimed(r["segment"], o.cat)}
        if "silah_mim_hamza" in cats and "munfasil" not in cats:
            cats = sorted(cats + ["munfasil"])  # the silah's madd follows the munfasil wajh
        misses = defaultdict(int)
        combos = list(itertools.product(*(WUJUH[c] for c in cats)))
        for combo in combos:
            choice = dict(zip(cats, combo))
            gen = apply(words, occs, choice)
            bad = [i for i in span if i in seen_words and not any(same(gen[i], t, i == last, i in starts) for t in book[i])]
            if not bad:
                ok.append({c: choice[c] for c in cats if c in claimed_cats or c == "munfasil"})
            for i in bad:
                misses[i] += 1
        all_cats |= {c for c in cats if c in claimed_cats or c == "munfasil"}
        all_occs += occs
        never_sets.append({i for i, m in misses.items() if m == len(combos)})
    never = sorted(set.intersection(*never_sets)) if never_sets else []
    return ok, sorted(all_cats), all_occs, never


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
            seen = sorted({ch[c] for ch in ok if c in ch})
            if not seen:
                continue
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
