"""Day 3: full profiles (text wujūh from the rows, features from the labels and the book's madd
tables) and generated readings, compared with every row of the passage part.

    python3 -m checks.readings [--upto AYAH] [--show]

A Reading here is the text of a span plus a set of features (madd lengths, sakt, tarqiq ...):
what the text alone can't show (Q5).

Sources:
- text wujūh: learned from the rows (`checks.futuh.learn`), each with its row ids;
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

from .learn import TEXT_CATS, claimed, context, learn, match_row, quote_starts, reviewed, rows_in, same
from .rows import BUILD, MUSHAF, RUWAT, load_hafs
from mushaf_data import generate as G
from mushaf_data.constraints import CONSTRAINTS, allowed  # noqa: F401 (used by checks)
from mushaf_data.generate import CHOICE_FEATURES, WAQF_HAMZ_CATS, WAQF_RAWI  # noqa: F401
from mushaf_data.profiles import place_wujuh
from mushaf_data.ruwat import QARI
from mushaf_data.usul import WUJUH, apply, detect

READERS_YAML = MUSHAF / "futuh/readers.yaml"

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
        body = re.sub(r"\s+", " ", r["label"])
        present = [c for c in ("sakt_al", "sakt_mafsul") if c in cats]
        if re.search(r"(ترك|عدم) السكت", body):
            for c in present:
                f[c] = ["none"]
        elif re.search(r"(?<!ترك )(?<!عدم )السكت(?! وقف)(?! بين)(?! على الحروف)(?! على الأحرف)", body) and "على المفصول" not in body \
                and "«أل»" not in body:
            for c in present:
                f.setdefault(c, ["sakt"])
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


def full_profiles(upto: int, start: int = 1, book: bool = False):
    """Profiles per rāwī. Learned from al-Futūḥ's rows (2:start-upto), the book's madd tables and
    the row labels; with `book`, the uṣūl books' table (data/profiles.yaml) replaces every
    category it covers, and the rows only fill categories the books table doesn't have yet."""
    from . import learn as P

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
                table = tables[cat][r]
                seen = set(p.get(cat, {}).get("wujuh", {}))
                # the text shows qasr vs not-qasr only; a conflict is a wajh the rows show that
                # the table doesn't allow
                if ("qasr" in seen and "qasr" not in table) or (seen - {"qasr"} and not table - {"qasr"}):
                    conflicts.append((r, cat, "table " + "/".join(sorted(table)), "rows " + "/".join(sorted(seen))))
                p[cat] = {"wujuh": {w: ["al-Futuh v1 pp. 52-53"] for w in sorted(table)}, "source": "book table"}
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
    if book:
        from mushaf_data.profiles import load
        for r, cats in load().items():
            full[r].update(cats)
        # a place entry's wujūh are the rāwī's too (label features are checked against the profile;
        # generation still uses the place entry itself)
        for e in place_wujuh():
            q = full[e["rawi"]].setdefault(e["category"], {"wujuh": {}, "source": "place"})
            for w in list(e["wujuh"]) + list(e.get("elsewhere", [])):
                q["wujuh"].setdefault(w, ["data/place_wujuh.yaml"])
    return full, gaps, conflicts, feats


PLACE_WUJUH = place_wujuh()


def sakt_print(word: str) -> str:
    """How al-Futūḥ prints a word with sakt on al-: the hamzah after ٱلۡ with its fatḥah and no
    maddah (ٱلۡأٓخِرِ → ٱلۡأَخِرِ). A print convention (Eisa 2026-11-24), applied only when comparing."""
    return re.sub("(\u0671\u0644\u06e1)\u0623\u0653", "\\1\u0623\u064e", word)


def generate(rawi: str, span: list[str], full: dict, confirmed=None) -> list[tuple[dict, dict]]:
    """The engine's readings (mushaf_data.generate) with this check's stand-ins: the rāwī's farsh
    from al-Futūḥ's rows, and the row gate for where a category applies (`learn.reviewed`)."""
    from .learn import farsh_texts, reviewed

    return G.generate(rawi, span, full, farsh=farsh_texts()[rawi], gate=reviewed, hafs=load_hafs())


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
    and how (`mushaf_data.diff`). Also counts readings the profile generates for a span that no row
    gives that rawi (over-generation: constraints needed)."""
    from mushaf_data.diff import describe
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
    box_rows: dict[tuple, list] = {}  # (rawi, segment) -> readings {word id: text} of its rows
    seg_of: dict[tuple, str] = {}
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

            sakt_row = feats[r["id"]].get("sakt_al") == ["sakt"]

            def bad(g):
                return [i for i in span if i in seen_words and not any(
                    same(g[i], t, i == span[-1], i in starts)
                    or sakt_row and same(sakt_print(g[i]), t, i == span[-1], i in starts) for t in book[i])]

            scored = sorted(gens, key=lambda g: len(bad(g)))
            if not scored or bad(scored[0]):
                g = scored[0] if scored else {i: hafs[i] for i in span}
                diffs = [(i, g[i], book[i][0], describe(g[i], book[i][0])) for i in bad(g)]
                misses.append((r["id"], rawi, "text", diffs))
            # label features: a reading whose text is the row's must also have the label's wujūh
            # (features detected in the span are choices); others: within the profile
            want = feats[r["id"]]
            text_ok = [ch for ch, g in choice_cache[key] if not bad(g)]
            for cat, wj in want.items():
                if not set(wj) <= set(full[rawi].get(cat, {}).get("wujuh", {})):
                    misses.append((r["id"], rawi, f"feature {cat}={'/'.join(wj)}", []))
            chosen = {c: wj for c, wj in want.items() if any(c in ch for ch in text_ok)}
            if text_ok and chosen and not any(all(ch.get(c) in wj for c, wj in chosen.items() if c in ch) for ch in text_ok):
                misses.append((r["id"], rawi, "features together " + ",".join(f"{c}={'/'.join(w)}" for c, w in chosen.items()), []))
            # a row with alternatives ("A * B * C") stands for each of them
            book_texts[key].update(itertools.product(*[w.get("alts") or [w["t"]] for w in r["words"] if w["id"] in seen_words]))
            claimed_span[key] = tuple(i for i in span if i in seen_words)
            # every reading of the box's rows for this rāwī, word by word (alternatives expanded)
            for combo in itertools.product(*[w.get("alts") or [w["t"]] for w in r["words"] if w["id"] in seen_words]):
                box_rows.setdefault((rawi, r["segment"]), []).append(
                    dict(zip([w["id"] for w in r["words"] if w["id"] in seen_words], combo)))
            seg_of[key] = r["segment"]
    # extra readings: distinct texts (on the words the box speaks about, a pausal final vowel not
    # counting as a difference) beyond the number of readings the book gives that rawi for the span
    from mushaf_data.text import clusters

    def unpaused(w: str) -> str:
        cl = clusters(w)
        if cl:
            cl[-1] = cl[-1][0] + "".join(m for m in cl[-1][1:] if m not in "\u064e\u064f\u0650\u064b\u064c\u064d")
        return "".join(cl)

    EXTRAS.clear()
    for (rawi, span), gens in gen_cache.items():
        words = claimed_span[(rawi, span)]
        booked = {tuple(unpaused(t) if i == span[-1] else t for i, t in zip(words, bt)) for bt in book_texts[(rawi, span)]}
        # a box reads its span one way, stopping at a final pause sign or going on (2:20:19 stops,
        # 2:7:6 goes on): count the readings of the way that gives the most of the box's rows
        by_ctx: dict = {}
        for ch, g in choice_cache[(rawi, span)]:
            tup = tuple(unpaused(g[i]) if i == span[-1] else g[i] for i in words)
            by_ctx.setdefault(ch.get("_stop"), {})[tup] = ch
        ctx = max(by_ctx, key=lambda c: (len(set(by_ctx[c]) & booked), -len(by_ctx[c])))
        distinct = by_ctx[ctx]
        # attested: some row of the same box for this rāwī reads the same on the words they share
        # (a box spreads one rāwī's wujūh over rows of different lengths: 2:16 Warsh, 2:12 Qālūn)
        others = box_rows.get((rawi, seg_of.get((rawi, span))), [])

        def attested(tup):
            g = dict(zip(words, tup))
            return tup in booked or any(
                (common := set(g) & set(o)) and all(same(g[i], o[i], i == span[-1]) for i in common) for o in others)

        unattested = [(tup, ch) for tup, ch in distinct.items() if not attested(tup)]
        n = min(len(unattested), max(0, len(distinct) - len(book_texts[(rawi, span)])))
        if n:
            over[rawi] += n
            for tup, ch in unattested:  # the readings no row gives (for review)
                EXTRAS.append((rawi, span[0], span[-1], ch))
    return misses, over


EXTRAS: list = []


def check(upto: int = 20, book: bool = True, test: tuple[int, int] | None = None) -> dict:
    """Every row/rāwī pair of al-Baqarah 1..upto (or, with `test`, of lo..hi, profiles learned on
    1..upto): is the row's reading one the rāwī's profile generates?"""
    full, gaps, conflicts, feats = full_profiles(upto, book=book)
    lo, hi = test or (1, upto)
    misses, over = compare(hi, full, feats, start=lo)
    rows = rows_in(hi, lo)
    pairs = sum(len(r["ruwat"] or r["ruwat_min"] or []) for r in rows)
    bad = {(m[0], m[1]) for m in misses}
    return {"rows": len(rows), "pairs": pairs, "reproduced": pairs - len(bad), "misses": misses,
            "extras": sum(over.values()), "over": dict(over), "conflicts": conflicts, "full": full}


def vs_rows(book, upto=20):
    """Where the rows of al-Futūḥ (2:1-upto) show a wajh the book profile doesn't allow, or the
    book allows wujūh the rows never show (expected: the passage is short)."""
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--upto", type=int, default=5)
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--test", default=None, help="predict al-Baqarah A-B with profiles learned up to --upto, e.g. 6-20")
    ap.add_argument("--book", action="store_true", help="use the uṣūl books' profiles (data/profiles.yaml)")
    ap.add_argument("--vs-rows", action="store_true", help="where the book profiles and the rows of 2:1-20 disagree")
    a = ap.parse_args()
    if a.vs_rows:
        from mushaf_data.profiles import load
        conflicts, unseen = vs_rows(load())
        print(f"{len(conflicts)} conflicts (rows show a wajh the book doesn't give):")
        for c in conflicts:
            print("  ", *c)
        print(f"{len(unseen)} book wujūh the passage's rows don't show:")
        for u in unseen:
            print("  ", *u)
        return
    full, gaps, conflicts, feats = full_profiles(a.upto, book=a.book)
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
