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

from .farsh_class import CHAPTERS, classify
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
    farsh = [x for x in allrows if x[1]["kind"] == "farsh" and x[1]["place"]]
    elsewhere = [x for x in allrows if x[1]["kind"] == "farsh" and not x[1]["place"]]
    h = words()
    by_surah: dict[int, list] = defaultdict(list)
    flagged = []
    for g in places(farsh):
        ids = sorted({i for _, r, _ in g for i in r["place"]}, key=lambda w: tuple(int(x) for x in w.split(":")))
        options = []
        for p, r, src in g:
            o = {"readers": [x for x in RUWAT if x in r["readers"]], "khulf": [x for x in RUWAT if x in r["khulf"]],
                 "reading": r["reading"], "cite": f"{slug} {p}", "from": src}
            if r["condition"]:
                o["condition"] = r["condition"]
            options.append(o)
        cov = coverage(options)
        scope = "all" if any(r["scope"] == "all" for _, r, _ in g) else "here"
        entry = {"place": ids, "words": " ".join(h[i] for i in ids), "scope": scope,
                 "status": "checked" if all(src == "gold" for _, _, src in g) else "extracted",
                 "options": options}
        if scope == "all":  # the same word elsewhere in the surah, written the same way
            surah = ids[0].split(":")[0]
            texts = {h[i] for i in ids}
            also = [w for w, t in h.items() if t in texts and w not in ids and w.split(":")[0] == surah]
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
        f = OUT / f"{s:03d}.yaml"
        f.write_text(HEADER.format(s=s, book=a.slug, pages=a.pages)
                     + yaml.safe_dump(entries, allow_unicode=True, sort_keys=False, width=200, default_flow_style=None), encoding="utf-8")
        print(f"{f}: {len(entries)} places, {sum(1 for e in entries if 'review' in e)} flagged")
    print(f"{len(elsewhere)} farsh rows about words outside their pages' places")
    for e in flagged:
        print("  flag", e["place"], e["words"], e["review"])


if __name__ == "__main__":
    main()
