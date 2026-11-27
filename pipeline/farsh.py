"""Farsh rows → the farsh table, one file per surah: data/farsh/SSS.yaml.

    python3 -m pipeline.farsh budur 16-58 [--run pipeline/out/baqarah/budur]

Rows come from the gold set where there is one (reviewed pages) and from the run elsewhere,
validated. Farsh rows are grouped into places (rows that share a word id, on the same page or
the next); each place lists its options (readers, khulf, the book's words, the page). Coverage:
the options together must name each of the twenty once; a rāwī named with khulf at a place with
two options has the other as his second wajh (the book's "والباقون" leaves him out of it), added
as `implied`. Anything else is flagged for review. Rows about a word outside the page's places
(`place: []`) are listed apart.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import yaml

from mushaf_data.paths import DATA
from mushaf_data.ruwat import RUWAT
from mushaf_data.spine import words

from .anchor import find
from .farsh_class import CHAPTERS, RECUR, classify
from .gold import GOLD
from .pack import parse_pages
from .score import rows

OUT = DATA / "farsh"


def collect(slug: str, pages: list[int], run: Path) -> list[tuple[int, dict, str]]:
    gold_pages = {int(f.stem[1:]) for f in (GOLD / slug).glob("p*.json")}
    out = []
    for p, r in rows(GOLD / slug, [p for p in pages if p in gold_pages])[0]:
        out.append((p, r, "gold"))
    for p, r in rows(run, [p for p in pages if p not in gold_pages])[0]:
        out.append((p, r, "run"))
    return out


def places(farsh: list[tuple[int, dict, str]]) -> list[list[tuple[int, dict, str]]]:
    """Connected groups: rows sharing a word id, on the same or the next page."""
    groups: list[list] = []
    for item in sorted(farsh, key=lambda x: (x[0], x[1]["span"][1])):
        p, r, _ = item
        hit = [g for g in groups if any(set(r["place"]) & set(q["place"]) and abs(p - pp) <= 1 for pp, q, _ in g)]
        if hit:
            merged = [x for g in hit for x in g] + [item]
            groups = [g for g in groups if g not in hit] + [merged]
        else:
            groups.append([item])
    return groups


def phrases(ids: list[str]) -> list[list[str]]:
    """Runs of consecutive word ids (ما هي at 2:68:7-8 is one phrase)."""
    runs: list[list[str]] = []
    for i in ids:
        s, a, w = map(int, i.split(":"))
        if runs and runs[-1][-1].split(":")[:2] == [str(s), str(a)] and int(runs[-1][-1].split(":")[2]) == w - 1:
            runs[-1].append(i)
        else:
            runs.append([i])
    return runs


# rows the extraction filed under uṣūl that the books treat as farsh (checked by hand, 2026-11-27):
# (page, first word id) → why
AS_FARSH = {(53, "2:258:21"): "أنا before a hamzat qaṭʿ: Nāfiʿ's alif in waṣl is farsh (wafi 222)"}


def merge(options: list[dict]) -> list[dict]:
    """Rows at one place naming the same ruwāt, without khulf and under the same condition, are one
    reading told in two clauses (أمانيهم, al-Budūr p. 38: "بتخفيف الياء ساكنة، ويلزمه كسر الهاء")."""
    out: list[dict] = []
    for o in options:
        prev = next((p for p in out if p["readers"] == o["readers"] and not p["khulf"] and not o["khulf"]
                     and p.get("condition") == o.get("condition")), None)
        if prev:
            prev["reading"] = f"{prev['reading']}، {o['reading']}"
            if o["cite"] != prev["cite"]:
                prev["cite"] = f"{prev['cite']}; {o['cite']}"
        else:
            out.append(o)
    return out


# A second reading (al-Wāfī / al-Īḍāḥ) where al-Budūr leaves ruwāt unstated at a place, checked by
# hand: first word id → (ruwāt, a phrase of the option they join, cites)
SECOND = {
    "2:197:13": (["bazzi", "qunbul", "duri_abuamr", "susi", "ruways", "rawh"], "بالفتح بلا تنوين",
                 ["wafi 218", "idah 214"]),  # جدال: "ولا خلاف في جدال أنه بالفتح"; Yaʿqūb idah 214 n. 1
}


# A khulf the other books give where al-Budūr names one wajh, checked by hand: first word id →
# (rāwī, a phrase of the option that is his second wajh, cites)
KHULF = {
    # Khallād at 1:6 الصراط: ishmām and the pure ṣād (wafi 51 n. 1: "فاقتصار الناظم على الإشمام لخلاد
    # فيه قصور"; dabba 162 n. 1; buhur 48), Eisa 2026-11-27
    "1:6:2": ("khallad", "بالصاد الخالصة", ["wafi 51", "dabba 162", "buhur 48"]),
}


def add_second(first: str, options: list[dict]) -> None:
    if first in SECOND:
        who, phrase, cites = SECOND[first]
        o = next(o for o in options if phrase in o["reading"])
        o["readers"] = [x for x in RUWAT if x in set(o["readers"]) | set(who)]
        o["second"] = {"readers": who, "cite": cites}
    if first in KHULF:
        rawi, phrase, cites = KHULF[first]
        for o in options:
            if rawi in o["readers"]:
                o["khulf"] = [x for x in RUWAT if x in set(o["khulf"]) | {rawi}]
        o = next(o for o in options if phrase in o["reading"] and rawi not in o["readers"])
        o["readers"] = [x for x in RUWAT if x in set(o["readers"]) | {rawi}]
        o["khulf"] = [x for x in RUWAT if x in set(o["khulf"]) | {rawi}]
        o["second"] = {"readers": [rawi], "cite": cites}


def mark_base(entry: dict) -> None:
    """The option with Ḥafṣ is the muṣḥaf text's own reading: `base`. For a word read differently
    wherever it occurs (`recurs`), only the other options are farsh (Eisa 2026-11-27: the pure ṣād
    of ṣirāṭ is the aṣl, what Qunbul, Ruways, Khalaf and Khallād read is the farsh)."""
    for o in entry["options"]:
        if "hafs" in o["readers"]:
            o["base"] = True


def split(groups: list[list]) -> list[list]:
    """A group whose rows don't all name the same words is one place per set of words sharing the
    same rows (الصراط / صراط: Khallād's ishmām is in the first only, al-Budūr p. 15). Each row then
    keeps only the words of its place."""
    out = []
    for g in groups:
        if len({tuple(r["place"]) for _, r, _ in g}) == 1:
            out.append(g)
            continue
        ids = sorted({i for _, r, _ in g for i in r["place"]})
        by: dict[tuple, list] = defaultdict(list)
        for i in ids:
            by[tuple(n for n, (_, r, _) in enumerate(g) if i in r["place"])].append(i)
        for rows_, words_ in by.items():
            out.append([(p, {**r, "place": [i for i in r["place"] if i in words_]}, src)
                        for n, (p, r, src) in enumerate(g) if n in rows_])
    return out


def coverage(options: list[dict]) -> dict:
    """Per condition (waṣl/unstated apart from waqf-only options): each of the twenty once.
    A khulf rāwī named once, at a point with two options, has the other as his second wajh. When
    no option is Ḥafṣ's and some ruwāt are left unnamed, they read as Ḥafṣ: the book leaves out
    "والباقون" (an option `as Ḥafṣ` is added, marked implied)."""
    result = {"missing": [], "twice": []}
    for cond in ("main", "waqf"):
        opts = [o for o in options if (o.get("condition") == "waqf") == (cond == "waqf")]
        if not opts:
            continue
        count = defaultdict(int)
        for o in opts:
            for x in o["readers"]:
                count[x] += 1
        khulf = {x for o in opts for x in o["khulf"]}
        if len(opts) == 2:
            for x in khulf:
                if count[x] == 1:
                    other = next(o for o in opts if x not in o["readers"])
                    other.setdefault("implied", []).append(x)
                    count[x] += 1
        missing = [x for x in RUWAT if not count[x]]
        if cond == "main" and missing and "hafs" in missing:
            options.append({"readers": missing, "khulf": [], "reading": "كحفص (الباقون، غير مذكورين)",
                            "cite": opts[0]["cite"], "from": "implied"})
            missing = []
        if cond == "main":
            result["missing"] = missing
        result["twice"] += [x for x in RUWAT if count[x] > 1 and x not in khulf]
    return result


def build(slug: str, pages: list[int], run: Path) -> tuple[dict[int, list], list, list]:
    allrows = collect(slug, pages, run)
    for p, r, _ in allrows:
        if r["place"] and (p, r["place"][0]) in AS_FARSH:
            r["kind"], r["category"] = "farsh", None
    farsh = [x for x in allrows if x[1]["kind"] == "farsh" and x[1]["place"]]
    elsewhere = [x for x in allrows if x[1]["kind"] == "farsh" and not x[1]["place"]]
    h = words()
    by_surah: dict[int, list] = defaultdict(list)
    flagged = []
    for g in split(places(farsh)):
        ids = sorted({i for _, r, _ in g for i in r["place"]}, key=lambda w: tuple(int(x) for x in w.split(":")))
        options = []
        for p, r, src in g:
            o = {"readers": [x for x in RUWAT if x in r["readers"]], "khulf": [x for x in RUWAT if x in r["khulf"]],
                 "reading": r["reading"], "cite": f"{slug} {p}", "from": src}
            if r["condition"]:
                o["condition"] = r["condition"]
            options.append(o)
        options = merge(options)
        add_second(ids[0], options)
        cov = coverage(options)
        scope = "all" if any(r["scope"] == "all" for _, r, _ in g) else "here"
        entry = {"place": ids, "words": " ".join(h[i] for i in ids), "scope": scope,
                 "status": "checked" if all(src == "gold" for _, _, src in g) else "extracted",
                 "options": options}
        if scope == "all":  # the same word (or phrase) elsewhere in the surah, written the same way
            surah = ids[0].split(":")[0]
            runs = phrases(ids)
            if all(len(r) == 1 for r in runs):
                texts = {h[i] for i in ids}
                also = [w for w, t in h.items() if t in texts and w not in ids and w.split(":")[0] == surah]
            else:
                also = sorted({w for r in runs for w in find(" ".join(h[i] for i in r))
                               if w not in ids and w.split(":")[0] == surah}, key=lambda w: tuple(map(int, w.split(":"))))
            if also:
                entry["also"] = also
        if cov["missing"] or cov["twice"]:
            entry["review"] = {k: v for k, v in cov.items() if v}
            flagged.append(entry)
        by_surah[int(ids[0].split(":")[0])].append(entry)
    return by_surah, flagged, elsewhere


HEADER = """# Farsh of surah {s}: each place's options, read from {book} ({pages}).
# Generated by `python3 -m pipeline.farsh`; edit by reviewing, not by hand.
# status: checked = pages Eisa reviewed against a second reading; extracted = one model reading,
#   to be checked against al-Futūḥ and KFGQPC (milestone 2) and reviewed where they disagree.
# scope: all = the book says it holds wherever the word occurs; `also` lists the same word, written
#   the same way, elsewhere in the surah (prefixed forms are not matched yet).
# Option text per slot (the reading written out) comes next; `reading` is the book's own words.
# base: the option that is the muṣḥaf text's own reading (Ḥafṣ's); farsh is the other options.
# recurs: the books give the farsh wherever the word occurs (forms, page).
# second: ruwāt al-Budūr leaves unstated (or a khulf it leaves out), added to an option from al-Wāfī / al-Īḍāḥ (pages).
# class: rule = an uṣūl table (data/usul) gives the place (al-Budūr restates it here); farsh = the
#   surah's farsh chapter of al-Wāfī / al-Īḍāḥ treats it (pages); pipeline/farsh_class.py.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("pages")
    ap.add_argument("--run", default="pipeline/out/baqarah/budur")
    a = ap.parse_args()
    by_surah, flagged, elsewhere = build(a.slug, parse_pages(a.pages), Path(a.run))
    OUT.mkdir(parents=True, exist_ok=True)
    for s, entries in sorted(by_surah.items()):
        entries.sort(key=lambda e: tuple(int(x) for x in e["place"][0].split(":")))
        if f"{s:03d}" in CHAPTERS:  # aṣl or farsh, from the books' farsh chapters and data/usul
            for e in entries:
                e["class"] = classify(e, f"{s:03d}")
        for e in entries:
            mark_base(e)
            if e["place"][0] in RECUR:
                e["recurs"] = RECUR[e["place"][0]]
        f = OUT / f"{s:03d}.yaml"
        f.write_text(HEADER.format(s=s, book=a.slug, pages=a.pages)
                     + yaml.safe_dump(entries, allow_unicode=True, sort_keys=False, width=200, default_flow_style=None), encoding="utf-8")
        print(f"{f}: {len(entries)} places, {sum(1 for e in entries if 'review' in e)} flagged")
    print(f"{len(elsewhere)} farsh rows about words outside their pages' places")
    for e in flagged:
        print("  flag", e["place"], e["words"], e["review"])


if __name__ == "__main__":
    main()
