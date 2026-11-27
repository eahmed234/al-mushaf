"""The farsh from al-Wāfī and al-Īḍāḥ's farsh chapters (Eisa 2026-11-27: shorter and more targeted
than al-Budūr's per-place commentary).

    python3 -m pipeline.farsh_books validate pipeline/out/farsh/wafi     check the readers' rows
    python3 -m pipeline.farsh_books anchor wafi 231-242                  rows → places, report

Rows (pipeline/prompt_farsh.md) name a word by sūrah, āyah (al-Īḍāḥ) and the book's own words; no
word lists go to the reader. `anchor` finds the places (pipeline.anchor.find within the sūrah,
narrowed by the āyah when given).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mushaf_data.ruwat import RUWAT

from functools import lru_cache

from .pack import parse_pages
from .validate import locate

OUT = Path(__file__).with_name("out") / "farsh"
READERS = {"wafi": set(RUWAT[:14]), "idah": set(RUWAT[14:])}
FIELDS = ("sura", "ayah", "word", "words", "where", "sites", "readers", "khulf", "reading", "condition", "quote")


def check_row(r: dict, slug: str, page: int) -> list[str]:
    bad = [f"missing {k}" for k in FIELDS if k not in r]
    if bad:
        return bad
    if not isinstance(r["sura"], int) or not 1 <= r["sura"] <= 114:
        bad.append(f"sura {r['sura']!r}")
    if r["ayah"] is not None and not isinstance(r["ayah"], int):
        bad.append(f"ayah {r['ayah']!r}")
    if r["where"] not in ("here", "all", "listed"):
        bad.append(f"where {r['where']!r}")
    if not r["readers"] or not set(r["readers"]) <= READERS[slug]:
        bad.append(f"readers outside the book's: {sorted(set(r['readers']) - READERS[slug])}")
    if not set(r["khulf"]) <= set(r["readers"]):
        bad.append("khulf not among readers")
    if not str(r["words"]).strip() or not str(r["word"]).strip():
        bad.append("no word or words")
    elif _key(str(r["word"])) not in {_key(t) for t in str(r["words"]).split()}:
        bad.append("`word` must be one of `words`")
    if locate(slug, page, r["quote"]) is None:
        bad.append("quote not found once on the page (copy it exactly; make it longer if it occurs twice)")
    return bad


def validate(d: Path) -> dict[int, list]:
    slug = d.name
    out = {}
    for f in sorted(d.glob("p*.json")):
        page = int(f.stem[1:])
        rows = json.loads(f.read_text(encoding="utf-8"))["rows"]
        out[page] = [(i, b) for i, r in enumerate(rows) if (b := check_row(r, slug, page))]
    return out


ASL = {"ibn_wardan": ("qalun", "warsh"), "ibn_jammaz": ("qalun", "warsh"), "ruways": ("duri_abuamr", "susi"),
       "rawh": ("duri_abuamr", "susi"), "ishaq": ("khalaf_an_hamzah",), "idris": ("khalaf_an_hamzah",)}
AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def rows(slug: str, pages: list[int]) -> list[dict]:
    out = []
    for p in pages:
        f = OUT / slug / f"p{p:03d}.json"
        if not f.exists():
            continue
        for r in json.loads(f.read_text(encoding="utf-8"))["rows"]:
            if not check_row(r, slug, p):
                out.append({**r, "book": slug, "page": p})
    return out


def _key(w: str) -> str:
    """A skeleton without the hamzah and without prefix letters and the article (ءَاتَيۡتُكُم and
    آتيتكم; وَٱلزُّبُرِ and وبالزبر)."""
    import re

    from mushaf_data.occurrences import skel
    k = skel(w).replace("ء", "")
    c = re.sub("^[وفبكل]{0,2}ل(?=...)", "", k)
    c = re.sub("^[وفبك](?=....)", "", c)
    return c


@lru_cache(maxsize=None)
def _sura_words(sura: int) -> list[tuple[str, str]]:
    from mushaf_data.spine import words
    return [(w, _key(t)) for w, t in words().items() if int(w.split(":")[0]) == sura]


def _sim(a: str, b: str) -> float:
    """How close a book word's key is to a Ḥafṣ word's: 1 when equal or equal but for a pronoun
    suffix on the Ḥafṣ word, else the letters' ratio."""
    import difflib
    import re
    if a == b or re.fullmatch(re.escape(a) + "(?:ك|كم|هم|ه|ها|ني|نا|هما|كما|ن)", b):
        return 1.0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def anchor(r: dict, sura: int | None = None) -> list[str]:
    """The word ids of sūrah `sura` (default: the row's) a row speaks of. The book's words, in order,
    are scored against every run of as many Ḥafṣ words (keys without hamzah, prefixes or article);
    the best run wins, and in it the word least like the book's (the variant the book writes:
    ليبيننه for لَتُبَيِّنُنَّهُۥ), or the first when all match. Runs tying for best are all returned.
    Narrowed to the āyah when given."""
    sura = sura or r["sura"]
    ws = _sura_words(sura)
    if r.get("ayah") and sura == r["sura"]:
        ws = [(w, k) for w, k in ws if int(w.split(":")[1]) == r["ayah"]] or ws
    toks = [_key(t) for t in str(r["words"]).split()]
    toks = [t for t in toks if t] or []
    if not toks or max(len(t) for t in toks) < 2:
        return []
    n = len(toks)
    # the word the reading is about (`word`), its index among the book's words
    wk = _key(str(r.get("word") or ""))
    target = next((i for i, t in enumerate(toks) if t == wk), None) if wk else None
    best, out = 0.0, []
    for i in range(len(ws) - n + 1):
        sims = [_sim(t, ws[i + j][1]) for j, t in enumerate(toks)]
        score = sum(sims) / n
        j = target if target is not None else (
            min(range(n), key=lambda x: sims[x]) if min(sims) < 1 else max(range(n), key=lambda x: len(toks[x])))
        if score > best + 1e-9:
            best, out = score, [ws[i + j][0]]
        elif abs(score - best) < 1e-9:
            out.append(ws[i + j][0])
    need = 0.86 if n == 1 else 0.7  # one word: مِن is not متنا (0.8)
    return out if best >= need else []


def _sura_words_text(w: str) -> str:
    from mushaf_data.spine import words
    return words()[w]


def combine(sura: int, wafi_pages: list[int], idah_pages: list[int]) -> tuple[list[dict], list[dict]]:
    """Places of the sūrah: al-Wāfī's 14 and al-Īḍāḥ's 6, each Durrah rāwī the Durrah doesn't name
    at a place reading as his aṣl (idah 226: وكل من لم يذكر في هذه التراجم فهو موافق لأصله).
    Returns (places, problems)."""
    from collections import defaultdict

    from mushaf_data.spine import words

    h = words()
    by: dict[tuple, list[dict]] = defaultdict(list)
    problems = []
    allrows = [r for r in rows("wafi", wafi_pages) + rows("idah", idah_pages) if r["sura"] == sura]
    anchors = {id(r): anchor(r, sura) for r in allrows}
    # a row whose words fit several places takes the one nearest the rows that share its quote
    # (وتحشرون with ستغلبون at 3:12; وبالكتاب with وبالزبر at 3:184)
    order = {w: i for i, w in enumerate(h)}
    for r in allrows:
        ids = anchors[id(r)]
        if r["where"] == "here" and len(ids) > 1:
            mates = [anchors[id(x)][0] for x in allrows if x is not r and x["quote"] == r["quote"]
                     and len(anchors[id(x)]) == 1]
            if mates:
                anchors[id(r)] = [min(ids, key=lambda w: min(abs(order[w] - order[m]) for m in mates))]
    for r in allrows:
        ids = anchors[id(r)]
        if not ids:
            if r["where"] == "here":
                problems.append({"unanchored": r["words"], "cite": f"{r['book']} {r['page']}"})
            continue  # a listed or general row with no place in this sūrah: its sūrah's table takes it
        if r["where"] == "here" and len(ids) > 1:
            problems.append({"ambiguous": r["words"], "places": ids[:6], "cite": f"{r['book']} {r['page']}"})
            continue  # which place it speaks of is unclear: not anchored
        key = tuple(ids)
        by[key].append(r)
    places = []
    for key, rs in sorted(by.items(), key=lambda kv: tuple(int(x) for x in kv[0][0].split(":"))):
        opts = []
        for r in rs:
            o = next((x for x in opts if x["reading"] == r["reading"] and x["cite"] == f"{r['book']} {r['page']}"), None)
            if o:
                o["readers"] = sorted(set(o["readers"]) | set(r["readers"]), key=RUWAT.index)
                continue
            opts.append({"readers": sorted(r["readers"], key=RUWAT.index), "khulf": sorted(r["khulf"], key=RUWAT.index),
                         "reading": r["reading"], "cite": f"{r['book']} {r['page']}", "book": r["book"]})
        named = {x for o in opts for x in o["readers"]}
        for d, asl in ASL.items():  # the Durrah rāwī not named here reads as his aṣl
            if d in named:
                continue
            mine = [o for o in opts if set(asl) & set(o["readers"])]
            if len({tuple(sorted(set(asl) & set(o["readers"]))) for o in mine}) > 1 and len(asl) > 1 and \
                    not any(set(asl) <= set(o["readers"]) for o in mine):
                problems.append({"asl_differs": d, "place": list(key)})
            for o in mine:
                if set(asl) & set(o["readers"]):
                    o["readers"] = sorted(set(o["readers"]) | {d}, key=RUWAT.index)
                    o.setdefault("as_asl", []).append(d)
                    break
        missing = [x for x in RUWAT if x not in {y for o in opts for y in o["readers"]}]
        if missing:  # unstated: as Ḥafṣ (Eisa 2026-11-26), with Ḥafṣ's option when he is named
            o = next((o for o in opts if "hafs" in o["readers"]), None)
            if o:
                o["readers"] = sorted(set(o["readers"]) | set(missing), key=RUWAT.index)
                o["implied"] = missing
            else:
                opts.append({"readers": missing, "khulf": [], "reading": "كحفص (غير مذكورين)", "cite": opts[0]["cite"],
                             "from": "implied", "base": True})
        for o in opts:
            if "hafs" in o["readers"]:
                o["base"] = True
        places.append({"place": list(key), "words": " ".join(h[w] for w in key[:6]),
                       "where": rs[0]["where"], "options": opts})
    return places, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["validate", "combine"])
    ap.add_argument("dir_or_sura")
    ap.add_argument("--wafi", default="")
    ap.add_argument("--idah", default="")
    a = ap.parse_args()
    if a.cmd == "validate":
        bad = validate(Path(a.dir_or_sura))
        for p, rs in bad.items():
            for i, b in rs:
                print(f"p{p} row {i}: {'; '.join(b)}")
        print(f"{sum(len(v) for v in bad.values())} rows rejected on {len(bad)} pages")
        sys.exit(0)
    import yaml

    from mushaf_data.paths import DATA
    sura = int(a.dir_or_sura)
    places, problems = combine(sura, parse_pages(a.wafi), parse_pages(a.idah))
    d = DATA / "farsh_books"
    d.mkdir(exist_ok=True)
    (d / f"{sura:03d}.yaml").write_text(
        f"# Farsh of surah {sura} from al-Wāfī ({a.wafi}) and al-Īḍāḥ ({a.idah}): pipeline/farsh_books.py\n"
        + yaml.safe_dump(places, allow_unicode=True, sort_keys=False, width=200, default_flow_style=None), encoding="utf-8")
    print(f"{len(places)} places, {len(problems)} problems")
    for p in problems:
        print("  ", p)


if __name__ == "__main__":
    main()
