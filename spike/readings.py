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

from .profile import TEXT_CATS, learn, rows_in, same
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
    ("إشباع البدل", "badal", ["tul"]),
    ("بتوسط الصلة", "munfasil", ["tawassut"]),
    ("السكت على «أل»", "sakt_al", ["sakt"]),
    ("السكت على المفصول", "sakt_mafsul", ["sakt"]),
    ("ترك السكت", "sakt_mafsul", ["none"]),
    ("عدم السكت", "sakt_mafsul", ["none"]),
    ("ترقيق الراء", "tarqiq_ra", ["tarqiq"]),
    ("تفخيم الراء", "tarqiq_ra", ["tafkhim"]),
    ("تغليظ اللام", "taghliz_lam", ["taghliz"]),
    ("ترقيق اللام", "taghliz_lam", ["tarqiq"]),
    ("ترك الغنة", "ghunna", ["none"]),
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
    if madd_cat and madd_cat not in out:
        rest = body.replace("قصر البدل", "").replace("توسط ومد البدل", "").replace("إشباع البدل", "")
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
        madd_cat = "munfasil" if "munfasil" in cats else ("muttasil" if "muttasil" in cats else None)
        f = label_features(r["label"], madd_cat)
        if "كالسابق" in r["label"] and r["segment"] == prev.get("segment"):
            f = {**prev["features"], **f}
        out[r["id"]] = f
        prev = {"segment": r["segment"], "features": f}
    return out


def full_profiles(upto: int):
    prof, gaps = learn(upto)
    rows = rows_in(upto)
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


def compare(upto: int, full: dict, feats: dict):
    """For each row and each rawi it names: is the row's text one the rawi's profile generates,
    and are its label features within the profile? Also count readings the profile generates
    for the span that no row gives that rawi (over-generation: constraints needed)."""
    hafs = load_hafs()
    rows = rows_in(upto)
    misses, over = [], defaultdict(int)
    gen_cache: dict[tuple, list[dict]] = {}
    book_texts: dict[tuple, set] = defaultdict(set)
    for r in rows:
        span = tuple(w["id"] for w in r["words"] if w["id"] in hafs)
        words = [(i, hafs[i]) for i in span]
        occs = detect(words)
        cats = sorted({o.cat for o in occs if o.cat in TEXT_CATS})
        book = {w["id"]: (w.get("alts") or [w["t"]]) for w in r["words"]}
        for rawi in (r["ruwat"] or r["ruwat_min"] or []):
            key = (rawi, span)
            if key not in gen_cache:
                opts = [list(full[rawi].get(c, {}).get("wujuh", {"?": 0})) for c in cats]
                gen_cache[key] = [apply(words, occs, dict(zip(cats, combo))) for combo in itertools.product(*opts)]
            hit = [g for g in gen_cache[key] if all(any(same(g[i], t, i == span[-1]) for t in book[i]) for i in span)]
            if not hit:
                misses.append((r["id"], rawi, "text"))
            for cat, wj in feats[r["id"]].items():
                if not set(wj) <= set(full[rawi].get(cat, {}).get("wujuh", {})):
                    misses.append((r["id"], rawi, f"feature {cat}={'/'.join(wj)}"))
            book_texts[key].add(tuple(r["words"][k]["t"] for k in range(len(r["words"]))))
    for (rawi, span), gens in gen_cache.items():
        distinct = {tuple(g[i] for i in span) for g in gens}
        if len(distinct) > len(book_texts[(rawi, span)]):
            over[rawi] += len(distinct) - len(book_texts[(rawi, span)])
    return misses, over


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--upto", type=int, default=5)
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    full, gaps, conflicts, feats = full_profiles(a.upto)
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
