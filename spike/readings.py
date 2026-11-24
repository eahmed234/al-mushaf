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
import json
import re
from collections import defaultdict

import yaml

from .profile import TEXT_CATS, claimed, context, learn, match_row, rows_in, same
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


def row_features(rows: list[dict]) -> dict[str, dict[str, list[str]]]:
    """row id -> features, with كالسابق inheriting from the row above in the segment."""
    hafs = load_hafs()
    out, prev = {}, {}
    for r in rows:
        span = [w["id"] for w in r["words"] if w["id"] in hafs]
        cats = {o.cat for o in detect([(i, hafs[i]) for i in span])}
        madd_cat = "munfasil" if cats & {"munfasil", "silah_mim_hamza"} else ("muttasil" if "muttasil" in cats else None)
        f = label_features(r["label"], madd_cat)
        imala_cats = sorted(c for c in cats if c.startswith("imala_"))
        if len(imala_cats) == 1:
            for phrase, wj in (("التقليل", "taqlil"), ("تقليل", "taqlil"), ("الإمالة", "imala"), ("إمالة", "imala"),
                               ("الفتح", "fath"), ("وفتح", "fath")):
                if phrase in r["label"]:
                    f[imala_cats[0]] = [wj]
                    break
        if "كالسابق" in r["label"] and r["segment"] == prev.get("segment"):
            f = {**prev["features"], **f}
        out[r["id"]] = f
        prev = {"segment": r["segment"], "features": f}
    return out


def full_profiles(upto: int, start: int = 1):
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


def confirmed_occurrences() -> set[tuple[str, str]]:
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
    return out


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
    for r in rows:
        span = tuple(w["id"] for w in r["words"] if w["id"] in hafs)
        book = {w["id"]: (w.get("alts") or [w["t"]]) for w in r["words"]}
        for rawi in (r["ruwat"] or r["ruwat_min"] or []):
            key = (rawi, span)
            if key not in gen_cache:
                ft = {i: t.split(" / ")[0] for i, t in farsh_text[rawi].items()}
                words, stop = context(list(span), hafs, ft)
                occs = detect(words, stop=stop)
                cats = sorted({o.cat for o in occs if o.cat in TEXT_CATS})
                if "silah_mim_hamza" in cats and "munfasil" not in cats:
                    cats = sorted(cats + ["munfasil"])
                def wujuh(c):
                    w = full[rawi].get(c, {}).get("wujuh")
                    if not w and c == "silah_mim_hamza":  # one category in the books; learned apart
                        w = full[rawi].get("silah_mim", {}).get("wujuh")
                    return list(w or {"?": 0})

                # reviewed occurrences only: a candidate no row anywhere reads differently is dropped
                occs = [o for o in occs if o.cat not in TEXT_CATS or (o.cat, o.word) in confirmed or o.cat == "munfasil"]
                cats = sorted({o.cat for o in occs if o.cat in TEXT_CATS} | ({"munfasil"} if "silah_mim_hamza" in cats else set()))
                # tied choices: silah before a hamza is the same choice as silah elsewhere, unless the
                # rawi's profile says otherwise (Warsh)
                tie = "silah_mim" in cats and "silah_mim_hamza" in cats and set(wujuh("silah_mim")) == set(wujuh("silah_mim_hamza"))
                free = [c for c in cats if not (tie and c == "silah_mim_hamza")]
                gens = []
                for combo in itertools.product(*[wujuh(c) for c in free]):
                    ch = dict(zip(free, combo))
                    if tie:
                        ch["silah_mim_hamza"] = ch["silah_mim"]
                    gens.append(apply(words, occs, ch))
                gen_cache[key] = gens
            gens = gen_cache[key]

            seen_words = claimed(r["segment"])

            def bad(g):
                return [i for i in span if i in seen_words and not any(same(g[i], t, i == span[-1], i == span[0]) for t in book[i])]

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
    for (rawi, span), gens in gen_cache.items():
        distinct = {tuple(g[i] for i in claimed_span[(rawi, span)]) for g in gens}
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
