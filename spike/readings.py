"""Day 3: full profiles (text wujūh from the rows, features from the labels and the book's madd
tables) and generated readings, compared with every row of the passage part.

    python3 -m spike.readings [--upto AYAH] [--show]

A Reading here is the text of a span plus a set of features (madd lengths, sakt, tarqiq ...):
what the text alone can't show (Q5).

Sources:
- text wujūh: learned from the rows (`spike.profile`), each with its row ids;
- munfasil / muttasil lengths: al-Futuh's own tables, vol. 1 pp. 52-53, as recorded with their
  citation in ../mushaf/futuh/readers.yaml (`madd_tables`);
- other features: the row labels, read with the small vocabulary below (book usage), with
  "كالسابق" taking the features of the row above.
"""

from __future__ import annotations

import argparse
import itertools
from functools import lru_cache
import json
import re
from collections import defaultdict

import yaml
from pathlib import Path

from .profile import TEXT_CATS, claimed, context, learn, match_row, quote_starts, reviewed, rows_in, same
from .rows import BUILD, PROJECTS, RUWAT, load_hafs
from .usul import WUJUH, apply, detect

QARI = {
    "nafi": ["qalun", "warsh"], "ibn_kathir": ["bazzi", "qunbul"], "abu_amr": ["duri_abuamr", "susi"],
    "ibn_amir": ["hisham", "ibn_dhakwan"], "asim": ["shuba", "hafs"], "hamzah": ["khalaf_an_hamzah", "khallad"],
    "kisai": ["abul_harith", "duri_kisai"], "abu_jafar": ["ibn_wardan", "ibn_jammaz"], "yaqub": ["ruways", "rawh"],
    "khalaf_ashir": ["ishaq", "idris"],
}
READERS_YAML = PROJECTS / "mushaf/futuh/readers.yaml"

# label phrase -> (category, wujuh); first match per category wins, longest phrases first
LABEL = [
    ("ثلاثة البدل", "badal", ["qasr", "tawassut", "tul"]),
    ("توسط ومد البدل", "badal", ["tawassut", "tul"]),
    ("قصر البدل", "badal", ["qasr"]),
    ("وإشباع البدل", "badal", ["tul"]),
    ("إشباع البدل", "badal", ["tul"]),
    ("بتوسط وإشباع البدل", "badal", ["tawassut", "tul"]),
    ("بتوسط الصلة", "munfasil", ["tawassut"]),
    ("السكت على «أل»", "sakt_al", ["sakt"]),
    ("السكت على المفصول", "sakt_mafsul", ["sakt"]),
    ("ترك السكت", "sakt_mafsul", ["none"]),
    ("عدم السكت", "sakt_mafsul", ["none"]),
    ("ترقيق الراء", "tarqiq_ra", ["tarqiq"]),
    ("تفخيم الراء", "tarqiq_ra", ["tafkhim"]),
    ("تغليظ اللام", "taghliz_lam", ["taghliz"]),
    ("ترقيق اللام", "taghliz_lam", ["tarqiq"]),
    ("ترك الغنة", "idgham_ghunna", ["bila_ghunna"]),
    ("القصر", "munfasil", ["qasr"]),
    ("التوسط", "munfasil", ["tawassut"]),
    ("بتوسط", "munfasil", ["tawassut"]),
    ("الإشباع", "munfasil", ["ishba"]),
    ("إشباع المد", "munfasil", ["ishba"]),
]


def madd_tables() -> dict[str, dict[str, set[str]]]:
    """category -> rawi -> wujuh, from the book's madd tables."""
    t = yaml.safe_load(READERS_YAML.read_text())["madd_tables"]
    out: dict[str, dict[str, set[str]]] = {}
    for cat, spec in t.items():
        per: dict[str, set[str]] = defaultdict(set)
        for wajh, who in spec.items():
            if wajh == "cite":
                continue
            if "all_except" in who:
                ex = set(who["all_except"].get("ruwat", [])) | {r for q in who["all_except"].get("qurra", []) for r in QARI[q]}
                members = set(RUWAT) - ex
            else:
                members = set(who.get("ruwat", [])) | {r for q in who.get("qurra", []) for r in QARI[q]}
            for r in members:
                per[r].add(wajh)
        out[cat] = per
    return out


GENERIC_MADD = {"القصر": "qasr", "التوسط": "tawassut", "بتوسط": "tawassut", "الإشباع": "ishba", "إشباع المد": "ishba"}


def label_features(label: str, madd_cat: str | None) -> dict[str, list[str]]:
    """Features a row label states. A bare madd word (القصر, التوسط, الإشباع) is about the madd
    the row's text contains (`madd_cat`: munfasil if there is one, else muttasil); after "عدا"
    it is an exception ("الجميع عدا أصحاب الإشباع": the other wujūh)."""
    body = label.split(":", 1)[1] if ":" in label else label
    body = re.sub(r"\s+", " ", body)
    out: dict[str, list[str]] = {}
    m = re.search(r"عدا أصحاب (\S+)", label)
    if m and madd_cat:
        ex = GENERIC_MADD.get(m.group(1).rstrip(".،"))
        if ex:
            out[madd_cat] = [w for w in WUJUH[madd_cat] if w != ex]
        body = body.replace(m.group(0), "")
    for phrase, cat, wj in sorted(LABEL, key=lambda x: -len(x[0])):
        if phrase in GENERIC_MADD:
            continue
        if phrase in body and cat not in out:
            out[cat] = wj
    if "القياس" in body or "وقفاً" in body and "مع القصر" in body:
        madd_cat = None  # "خمسة القياس ... الإبدال مع القصر": the madd of the waqf form, not the munfasil
    if madd_cat and madd_cat not in out:
        rest = body.replace("قصر البدل", "").replace("توسط ومد البدل", "").replace("بتوسط وإشباع البدل", "").replace("إشباع البدل", "")
        for phrase, wj in GENERIC_MADD.items():
            if phrase in rest:
                out[madd_cat] = [wj]
                break
    return out


def _skel(word: str) -> str:
    """Letters only (for matching a word a label names against the Hafs word)."""
    import unicodedata

    return "".join(c for c in word if unicodedata.category(c) != "Mn" and c not in "\u0640\u0671").replace("\u0627", "")


def row_features(rows: list[dict]) -> dict[str, dict[str, list[str]]]:
    """row id -> features, with كالسابق inheriting from the row above in the segment."""
    hafs = load_hafs()
    out, prev = {}, {}
    for r in rows:
        span = [w["id"] for w in r["words"] if w["id"] in hafs]
        occs = detect([(i, hafs[i]) for i in span])
        cats = {o.cat for o in occs}
        madd_cat = "munfasil" if cats & {"munfasil", "silah_mim_hamza"} else ("muttasil" if "muttasil" in cats else None)
        f = label_features(r["label"], madd_cat)
        imala_occs = [o for o in occs if o.cat.startswith("imala_")]
        for phrase, wj in (("التقليل", "taqlil"), ("تقليل", "taqlil"), ("الإمالة", "imala"), ("إمالة", "imala"),
                           ("الفتح", "fath"), ("وفتح", "fath")):
            k = r["label"].find(phrase)
            if k < 0:
                continue
            # "إمالة (شَآءَ)": the label names its word; it counts only for an occurrence on that word
            named = re.match(r"\s*\(([^)]+)\)", r["label"][k + len(phrase):])
            if named:
                target = _skel(named.group(1))
                hits = [o for o in imala_occs if _skel(hafs[o.word]) == target]
            else:
                hits = imala_occs if len({o.cat for o in imala_occs}) == 1 else []
            for o in hits:
                f[o.cat] = [wj]
            break
        if "كالسابق" in r["label"] and r["segment"] == prev.get("segment"):
            f = {**prev["features"], **f}
        out[r["id"]] = f
        prev = {"segment": r["segment"], "features": f}
    return out


def full_profiles(upto: int, start: int = 1):
    from . import profile as P

    P.EXTRA_READERS.clear()
    prof, _ = learn(upto, start)  # first pass, to know who has a second wajh
    P.EXTRA_READERS.update(P.khulf_convention(prof, upto, start))
    prof, gaps = learn(upto, start)
    rows = rows_in(upto, start)
    feats = row_features(rows)
    tables = madd_tables()
    full: dict[str, dict[str, dict]] = {}
    conflicts = []
    for r in RUWAT:
        p: dict[str, dict] = {}
        for c in TEXT_CATS:
            if c in prof.get(r, {}):
                ws = {w: sorted({s.rstrip("?") for s in src}) for w, src in prof[r][c].items()}
                p[c] = {"wujuh": ws, "source": "rows"}
        # madd lengths from the book's tables
        for cat in ("munfasil", "muttasil"):
            if r in tables.get(cat, {}):
                book = tables[cat][r]
                seen = set(p.get(cat, {}).get("wujuh", {}))
                # the text shows qasr vs not-qasr only; a conflict is a wajh the rows show that
                # the table doesn't allow
                if ("qasr" in seen and "qasr" not in book) or (seen - {"qasr"} and not book - {"qasr"}):
                    conflicts.append((r, cat, "table " + "/".join(sorted(book)), "rows " + "/".join(sorted(seen))))
                p[cat] = {"wujuh": {w: ["al-Futuh v1 pp. 52-53"] for w in sorted(book)}, "source": "book table"}
        # features from labels
        for row in rows:
            if r in (row["ruwat"] or row["ruwat_min"] or []):
                for cat, wj in feats[row["id"]].items():
                    if cat in ("munfasil", "muttasil"):
                        if not set(wj) <= set(p.get(cat, {}).get("wujuh", {})):
                            conflicts.append((r, cat, "label says " + "/".join(wj), row["id"]))
                        continue
                    q = p.setdefault(cat, {"wujuh": {}, "source": "labels"})
                    for w in wj:
                        q["wujuh"].setdefault(w, []).append(row["id"])
        full[r] = p
    return full, gaps, conflicts, feats


PLACE_WUJUH = yaml.safe_load((Path(__file__).parent / "data" / "place_wujuh.yaml").read_text()) or []


def generate(rawi: str, span: list[str], full: dict, confirmed: set) -> list[tuple[dict, dict]]:
    """Every (choice, text) a rawi's profile gives for a span: farsh first, then the uṣūl rules,
    over each way the span can be read (stop or not at a pause sign). Only reviewed occurrences;
    silah before a hamza tied to silah elsewhere unless the profile separates them."""
    from .profile import contexts, farsh_texts

    hafs = load_hafs()

    def wujuh(c):
        w = full[rawi].get(c, {}).get("wujuh")
        if not w and c == "silah_mim_hamza":  # one category in the books; learned apart
            w = full[rawi].get("silah_mim", {}).get("wujuh")
        # nothing known for this rawi here: leave the word as it is (the category's first wajh,
        # which is the Hafs text)
        return list(w or [WUJUH[c][0]])

    places = [e for e in PLACE_WUJUH if e["rawi"] == rawi]
    out = []
    for words, stop in contexts(span, hafs, farsh_texts()[rawi]):
        occs = [o for o in detect(words, stop=stop) if reviewed(o.cat, o.word, o.nxt)]
        cats = sorted({o.cat for o in occs if o.cat in TEXT_CATS})
        if "silah_mim_hamza" in cats and "munfasil" not in cats:
            cats = sorted(cats + ["munfasil"])
        # place-tied wujuh: at the place the entry's wujuh, elsewhere its `elsewhere`
        here = {e["category"]: e for e in places if any(o.cat == e["category"] and o.word == e["word"] for o in occs)}
        elsewhere = {e["category"]: e for e in places if e["category"] not in here}

        def wujuh(c, _w=wujuh):  # noqa: E731
            if c in here:
                return list(here[c]["wujuh"])
            if c in elsewhere:
                return list(elsewhere[c]["elsewhere"])
            return _w(c)

        tie = "silah_mim" in cats and "silah_mim_hamza" in cats and set(wujuh("silah_mim")) == set(wujuh("silah_mim_hamza"))
        free = [c for c in cats if not (tie and c == "silah_mim_hamza")]
        for combo in itertools.product(*[wujuh(c) for c in free]):
            ch = dict(zip(free, combo))
            if tie:
                ch["silah_mim_hamza"] = ch["silah_mim"]
            out.append((ch, apply(words, occs, ch)))
    return out


@lru_cache(maxsize=1)
def confirmed_occurrences() -> frozenset[tuple[str, str]]:
    """(category, word) pairs some row of the passage reads with a non-default wajh: a stand-in
    for the reviewed occurrence tables of the real model (detector candidates the book never
    reads differently, like imala on عَلَىٰ, are dropped)."""
    hafs = load_hafs()
    out = set()
    for r in rows_in(20):
        ok, cats, occs, _ = match_row(r, hafs)
        for o in occs:
            seen = {ch.get(o.cat) for ch in ok} - {None}
            if seen and WUJUH.get(o.cat, [None])[0] not in seen:  # every match reads it differently
                out.add((o.cat, o.word))
    return frozenset(out)


def compare(upto: int, full: dict, feats: dict, start: int = 1):
    """For each row and each rawi it names: is the row's text one the rawi's profile generates
    (farsh from the farsh entries, then the uṣūl rules), and are its label features within the
    profile? A miss records, for the closest generated reading, each word that still differs
    and how (`spike.diff`). Also counts readings the profile generates for a span that no row
    gives that rawi (over-generation: constraints needed)."""
    from .diff import describe
    from .farsh import load_places, resolve_farsh

    hafs = load_hafs()
    places, _ = load_places()
    farsh_text = {r: resolve_farsh(r, places, hafs)[0] for r in RUWAT}
    rows = rows_in(upto, start)
    feats = {**feats, **row_features(rows)}
    confirmed = confirmed_occurrences()
    misses, over = [], defaultdict(int)
    gen_cache: dict[tuple, list[dict]] = {}
    book_texts: dict[tuple, set] = defaultdict(set)
    claimed_span: dict[tuple, tuple] = {}
    choice_cache: dict[tuple, list] = {}
    for r in rows:
        span = tuple(w["id"] for w in r["words"] if w["id"] in hafs)
        book = {w["id"]: (w.get("alts") or [w["t"]]) for w in r["words"]}
        for rawi in (r["ruwat"] or r["ruwat_min"] or []):
            key = (rawi, span)
            if key not in gen_cache:
                gen_cache[key] = generate(rawi, list(span), full, confirmed)
                choice_cache[key] = gen_cache[key]
                gen_cache[key] = [g for _, g in gen_cache[key]]
            gens = gen_cache[key]

            seen_words = claimed(r["segment"])
            starts = quote_starts(r)

            def bad(g):
                return [i for i in span if i in seen_words and not any(same(g[i], t, i == span[-1], i in starts) for t in book[i])]

            scored = sorted(gens, key=lambda g: len(bad(g)))
            if not scored or bad(scored[0]):
                g = scored[0] if scored else {i: hafs[i] for i in span}
                diffs = [(i, g[i], book[i][0], describe(g[i], book[i][0])) for i in bad(g)]
                misses.append((r["id"], rawi, "text", diffs))
            for cat, wj in feats[r["id"]].items():
                if not set(wj) <= set(full[rawi].get(cat, {}).get("wujuh", {})):
                    misses.append((r["id"], rawi, f"feature {cat}={'/'.join(wj)}", []))
            book_texts[key].add(tuple(w["t"] for w in r["words"] if w["id"] in seen_words))
            claimed_span[key] = tuple(i for i in span if i in seen_words)
    # extra readings: distinct texts (on the words the box speaks about, a pausal final vowel not
    # counting as a difference) beyond the number of readings the book gives that rawi for the span
    from .text import clusters

    def unpaused(w: str) -> str:
        cl = clusters(w)
        if cl:
            cl[-1] = cl[-1][0] + "".join(m for m in cl[-1][1:] if m not in "\u064e\u064f\u0650\u064b\u064c\u064d")
        return "".join(cl)

    for (rawi, span), gens in gen_cache.items():
        words = claimed_span[(rawi, span)]
        distinct = {tuple(unpaused(g[i]) if i == span[-1] else g[i] for i in words) for g in gens}
        if len(distinct) > len(book_texts[(rawi, span)]):
            over[rawi] += len(distinct) - len(book_texts[(rawi, span)])
    return misses, over


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--upto", type=int, default=5)
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--test", default=None, help="predict al-Baqarah A-B with profiles learned up to --upto, e.g. 6-20")
    a = ap.parse_args()
    full, gaps, conflicts, feats = full_profiles(a.upto)
    if a.test:
        lo, hi = map(int, a.test.split("-"))
        misses, over = compare(hi, full, feats, start=lo)
        rows = rows_in(hi, lo)
        n_pairs = sum(len(r["ruwat"] or r["ruwat_min"] or []) for r in rows)
        bad_pairs = {(m[0], m[1]) for m in misses}
        print(f"learned on 2:1-{a.upto}; predicting 2:{lo}-{hi}: {len(rows)} rows, {n_pairs} row/rawi pairs, "
              f"{n_pairs - len(bad_pairs)} reproduced, {len(bad_pairs)} not")
        kinds = defaultdict(int)
        for m in misses:
            if m[2] == "text":
                for d in m[3]:
                    kinds[d[3]] += 1
            else:
                kinds[m[2].split("=")[0]] += 1
        print("  what differs (word-level, all misses):")
        for k, v in sorted(kinds.items(), key=lambda kv: -kv[1]):
            print(f"    {v:4}  {k}")
        if a.show:
            for m in misses:
                print("   ", m[0], m[1], m[2], " | ".join(f"{d[0]} {d[1]}→{d[2]} [{d[3]}]" for d in m[3]))
        print(f"  extra readings: {sum(over.values())} {dict(over)}")
        return
    (BUILD / "profile_full.json").write_text(json.dumps(full, ensure_ascii=False, indent=1))
    misses, over = compare(a.upto, full, feats)
    if a.show:
        for r in RUWAT:
            parts = [f"{c}=" + "/".join(v["wujuh"]) for c, v in full[r].items()]
            print(f"{r:17} " + "  ".join(parts))
    n_pairs = sum(len(r["ruwat"] or r["ruwat_min"] or []) for r in rows_in(a.upto))
    print(f"rows: {len(rows_in(a.upto))}, row/rawi pairs: {n_pairs}")
    print(f"  not reproduced by the rawi's profile: {len(misses)}")
    for m in misses[:20]:
        print("    ", *m)
    print(f"  book table vs rows/labels conflicts: {len(conflicts)}")
    for c in conflicts[:10]:
        print("    ", *c)
    print(f"  extra readings the profiles allow but no row shows (need constraints): {sum(over.values())} {dict(over)}")


if __name__ == "__main__":
    main()
