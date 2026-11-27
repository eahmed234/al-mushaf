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
import re
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
    elif not any(_key(t) == _key(str(r["word"])) or _key(t).endswith(_key(str(r["word"]))) or t == str(r["word"])
                 for t in str(r["words"]).split()):
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
    """A skeleton without the hamzah (ءَاتَيۡتُكُم and آتيتكم)."""
    from mushaf_data.occurrences import skel
    return skel(w).replace("ء", "")


@lru_cache(maxsize=None)
def _sura_words(sura: int) -> list[tuple[str, str]]:
    from mushaf_data.spine import words
    return [(w, _key(t)) for w, t in words().items() if int(w.split(":")[0]) == sura]


SUFFIX = "(?:ك|كم|هم|ه|ها|ني|نا|هما|كما|كن|هن|ن)"


def _sim(a: str, b: str) -> float:
    """How close a book word's key is to a Ḥafṣ word's: 1 when equal but for prefixes (و ف ب ك ل,
    the article) and a pronoun suffix on either side (بيوت / بُيُوتِكُمۡ، هو / وَهُوَ), else the
    letters' ratio."""
    import difflib
    import re
    pre = "^(?:[وفبكل]{0,2}ل?)"
    if a == b:
        return 1.0
    short, long_ = sorted((a, b), key=len)
    if len(short) >= 3 and re.fullmatch(pre + re.escape(short) + SUFFIX + "?", long_):
        return 1.0
    if len(short) == 2 and re.fullmatch("[وفل]" + re.escape(short), long_):  # هو / وَهُوَ، لَهُوَ only
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
    target = next((i for i, t in enumerate(toks) if t == wk or t.endswith(wk) or _sim(wk, t) == 1.0), None) if wk else None
    best, out = (0.0, 0.0), []
    for i in range(len(ws) - n + 1):
        sims = [_sim(t, ws[i + j][1]) for j, t in enumerate(toks)]
        if target is not None:  # the word itself first, its neighbours only to choose among equals
            j = target
            others = [x for k, x in enumerate(sims) if k != j]
            score = (sims[j], sum(others) / len(others) if others else 1.0)
        else:
            j = min(range(n), key=lambda x: sims[x]) if min(sims) < 1 else max(range(n), key=lambda x: len(toks[x]))
            score = (sum(sims) / n, 0.0)
        if score > best:
            best, out = score, [ws[i + j][0]]
        elif score == best:
            out.append(ws[i + j][0])
    if target is not None:
        floor = 1.0 if r.get("where") in ("all", "listed") else 0.86 if n == 1 else 0.8  # many places: the word itself; one word alone: مِن is not متنا
        return out if best[0] >= floor and (n == 1 or best[1] >= 0.4) else []
    return out if best[0] >= (0.86 if n == 1 else 0.7) else []


def _sura_words_text(w: str) -> str:
    from mushaf_data.spine import words
    return words()[w]


COMMON = {"الباقون", "الباقين", "الوصل", "الوقف", "القرآن", "الكلمة", "الحرف", "الموضع", "الموضعين", "الحالين"}


def topics(reading: str) -> set[str]:
    """What a reading is about: its words with the article (بكسر السين → السين; بالتاء على الخطاب →
    التاء، الخطاب), less the common ones."""
    toks = {re.sub("^[وب]?", "", t) for t in re.findall(r"\S+", reading)}
    return {t for t in toks if t.startswith("ال") and t not in COMMON}


def before_ok(reading: str, nxt: str) -> bool:
    """A reading the book ties to the next word's hamzah (أنا: "قبل همزة قطع مضمومة أو مفتوحة" /
    "مكسورة", wafi 222) holds only where the next word starts with that hamzah."""
    if not re.search("قبل همز", reading):
        return True
    first = nxt[:2]
    if "مكسورة" in reading:
        return first.startswith("\u0625") or first == "\u0621\u0650"
    if re.search("مضمومة|مفتوحة", reading):
        return first[:1] in "\u0623\u0621\u0622" and not first.startswith("\u0625")
    return first[:1] in "\u0623\u0625\u0621\u0622"


PREFIXES = {"الواو": "\u0648", "الفاء": "\u0641", "اللام": "\u0644", "الباء": "\u0628"}


def prefix_ok(reading: str, hafs: str) -> bool:
    """A reading the book ties to a prefix (هو، هي: "إذا قرنت بالواو أو الفاء أو اللام", wafi 201) holds
    only on words that start with one of the named letters."""
    if not re.search("قرن|اقترن|اتصل|سبق", reading):
        return True
    named = [c for name, c in PREFIXES.items() if name in reading]
    return not named or hafs[:1] in named


def all_pages(slug: str) -> list[int]:
    return sorted(int(f.stem[1:]) for f in (OUT / slug).glob("p*.json"))


def combine(sura: int, wafi_pages: list[int] | None = None, idah_pages: list[int] | None = None
            ) -> tuple[list[dict], list[dict]]:
    """Places of the sūrah: al-Wāfī's 14 and al-Īḍāḥ's 6, each Durrah rāwī the Durrah doesn't name
    at a place reading as his aṣl (idah 226: وكل من لم يذكر في هذه التراجم فهو موافق لأصله).
    Rows come from every extracted page (default): this sūrah's rows wherever the book gives them,
    and the rows any chapter gives "wherever it occurs" (`where: all`), at the words of this
    sūrah that no row of its own speaks of (`recurs`). Returns (places, problems)."""
    from collections import defaultdict

    from mushaf_data.spine import words

    h = words()
    by: dict[tuple, list[dict]] = defaultdict(list)
    problems = []
    every = rows("wafi", all_pages("wafi") if wafi_pages is None else wafi_pages) + \
        rows("idah", all_pages("idah") if idah_pages is None else idah_pages)
    allrows = [r for r in every if r["sura"] == sura]
    general = [r for r in every if r["where"] == "all" and r["sura"] != sura]  # its sūrah: the first the book names
    anchors = {id(r): anchor(r, sura) for r in allrows}
    order_ids = list(h)
    nxt = {w: h[order_ids[i + 1]] for i, w in enumerate(order_ids[:-1])}
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
        if r["where"] != "here":
            ids = [w for w in ids if before_ok(r["reading"], nxt.get(w, "")) and prefix_ok(r["reading"], h[w])]
            if not ids:
                continue
        key = tuple(ids)
        by[key].append(r)
    # each word's own rows: what they speak of, and for whom
    own_topics: dict[str, list[tuple[set, set]]] = defaultdict(list)
    for key, rs in by.items():
        for w in key:
            for x in rs:
                own_topics[w].append((topics(x["reading"]), set(x["readers"])))
    extra: dict[tuple, list] = defaultdict(list)
    for r in general:  # another chapter's "حيث وقع"
        if re.search("السكت|بسكت", r["reading"]):
            continue  # the sakt of the opening letters is uṣūl (sakt_huruf), not farsh
        t = topics(r["reading"])
        for w in anchor({**r, "ayah": None}, sura):
            if not (before_ok(r["reading"], nxt.get(w, "")) and prefix_ok(r["reading"], h[w])):
                continue
            # the sūrah's own rows win for the readers they name about the same thing (ينزل's
            # exceptions); others, and other aspects of the word, still take the general row
            taken = {x for tt, rd in own_topics.get(w, []) if not t or not tt or t & tt for x in rd}
            left = [x for x in r["readers"] if x not in taken]
            if left:
                extra[(id(r), tuple(left))].append(w)
    rows_by_id = {id(r): r for r in general}
    for (rid, left), ws in extra.items():
        r = rows_by_id[rid]
        by[tuple(ws)].append({**r, "readers": list(left), "khulf": [x for x in r["khulf"] if x in left], "recurs": True})
    places = []
    for key, rs in sorted(by.items(), key=lambda kv: tuple(int(x) for x in kv[0][0].split(":"))):
        opts = []
        for r in rs:
            o = next((x for x in opts if x["reading"] == r["reading"] and x["cite"] == f"{r['book']} {r['page']}"), None)
            if o:
                o["readers"] = sorted(set(o["readers"]) | set(r["readers"]), key=RUWAT.index)
                continue
            opts.append({"readers": sorted(r["readers"], key=RUWAT.index), "khulf": sorted(r["khulf"], key=RUWAT.index),
                         "reading": r["reading"], "cite": f"{r['book']} {r['page']}", "book": r["book"],
                         **({"recurs": True} if r.get("recurs") else {})})
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


def compare(sura: int) -> dict:
    """(place word, rāwī) pairs the two farsh tables say differ from Ḥafṣ: the books' (data/farsh_books)
    against al-Budūr's (data/farsh, its uṣūl places left out). Stops are left out of both."""
    import yaml
    from collections import defaultdict

    from checks.farsh import waqf_only
    from mushaf_data.paths import DATA

    def differ(path: Path, skip_rule: bool) -> set:
        out = set()
        if not path.exists():
            return out
        for e in yaml.safe_load(path.read_text(encoding="utf-8")) or []:
            if skip_rule and (e.get("class") or {}).get("kind") == "rule":
                continue
            for o in e["options"]:
                if o.get("base") or "hafs" in o["readers"] or waqf_only(o):
                    continue
                out |= {(w, r) for w in e["place"] for r in o["readers"]}
        return out

    a = differ(DATA / "farsh" / f"{sura:03d}.yaml", True)
    b = differ(DATA / "farsh_books" / f"{sura:03d}.yaml", False)
    by = defaultdict(list)
    for w, r in a - b:
        by[("budur only", w)].append(r)
    for w, r in b - a:
        by[("books only", w)].append(r)
    return {"both": len(a & b), "budur_only": len(a - b), "books_only": len(b - a), "by": dict(by)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["validate", "combine", "compare"])
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
    if a.cmd == "compare":
        from mushaf_data.spine import words
        c = compare(sura)
        print(f"surah {sura}: {c['both']} (place, rāwī) pairs in both tables, {c['budur_only']} only al-Budūr's, "
              f"{c['books_only']} only the books'")
        for (k, w), rs in sorted(c["by"].items(), key=lambda x: tuple(map(int, x[0][1].split(":")))):
            print(f"  {k:10} {w:10} {words()[w]}  {','.join(sorted(rs))}")
        return
    places, problems = combine(sura, parse_pages(a.wafi) if a.wafi else None, parse_pages(a.idah) if a.idah else None)
    a.wafi, a.idah = a.wafi or "all extracted pages", a.idah or "all extracted pages"
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
