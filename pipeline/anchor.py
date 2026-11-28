"""Anchor the listed words of every data/usul table to places of the Ḥafṣ text.

    python3 -m pipeline.anchor [--show] [--flags]

A table's `listed` entries name words, not places (al-Wāfī's "يؤده، نؤته…", al-Īḍāḥ's "النبي،
النبيين"). Matching a bare word when the engine runs reached every occurrence (النهار at wafi 152
meant ويولج النهار only), so each entry stores its slots here, once, and the engine and the checks
read the slots (docs/06 §3 item 3). Each listed word or phrase is matched to consecutive Ḥafṣ words
by skeleton (occurrences.skel; a book word may lack the Ḥafṣ word's prefix و ف ب ل ك, and a
phrase may be written with its words joined or apart: وماكنت), and data/usul gets, per entry:

  places      every word id of every match (all the words of a phrase: the entry speaks of it)
  anchor      all: every form matched somewhere; some: some forms matched; none
  unanchored  the forms nothing matched
  flag        why the places can't be told from the entry without a reading: the note names a
              condition or a count that doesn't hold, the word is a description ("ميم الجمع"), or
              a short word matches too much. A flagged entry keeps its matches as `candidates` and
              has no `places`: nothing reads it as a place until it is pinned (PINS) from the page.

Narrowing, from the entry itself:
- a sūrah in brackets after a word ("بيتي (نوح)", "أول الذبح (الصافات)") or "(قبل X)" (the next word);
- sūrahs and āyāt named in the note or `place` ("al-Tawbah", "al-Naml 27:43", "Ṣād 8 and al-Qamar 25");
- "the first …" in the note: the first match left;
- a count in the note ("both places", "the eight places of al-Naḥl"): checked, flagged if it differs.
Where the book says "wherever it occurs", or names a word with no condition, every match is kept.

Run by pipeline.unify_merge (all tables).
"""
from __future__ import annotations

import argparse
import re
import unicodedata
from collections import defaultdict
from functools import lru_cache

from mushaf_data.occurrences import skel
from mushaf_data.spine import words

YA = ("ya_idafa", "ya_zaida")
TABLES = None  # every table with a `listed` (kept for pipeline.unify_merge's import)
PREFIX = "وفبلك"
SHORT = 2           # a single word with a skeleton this short …
MANY = 40           # … matching more places than this is flagged

# notes that name a condition the matching can't see (resolved only by PINS)
CONDITION = re.compile(r"\b(?:second|third|last|only in|not in|when |with the article|without the article|"
                       r"joined|bare|in the jarr|with fāʾ|before |except|places?\b)", re.I)

# Hand resolutions from the page, keyed (table, the entry's first word): what the note means.
#   ok: the note explains, it doesn't restrict (all matches stand)
#   surahs / ayat: restrict to these; nth: keep the nth match; flag: a question for Eisa
#   also: more forms of the entry's word, from the page
#   prefix / not_prefix: the Ḥafṣ word starts / doesn't start with it; jarr: its last letter has a
#   kasrah; ayah_end: the āyah's last word; slots: these word ids
OK = {"ok": True}
PINS: dict[tuple[str, str], dict] = {
    # notes that explain the rule, not where it holds
    ("idgham_saghir", "وَالصَّتَفْتِ صَفًا"): OK, ("idgham_saghir", "أو يغلب فسوف"): OK,
    ("idgham_saghir", "ومن لم يتب فأولئك"): OK, ("idgham_saghir", "واصبر لحكم ربك"): OK,
    ("imala", "الأبرار"): OK,
    ("imala", "لدى الحناجر"): OK,  # wafi 142-143: the five words by name, wherever they occur
    ("hamz_waqf", "جاء"): OK,  # wafi 115: instances of the final hamzah after an alif, wherever they occur
    ("imala", "جبارين"): OK,  # جبارين 5:22, 26:130; والجار 4:36 twice: the 4 the note names
    ("imala", "الرؤيا"): OK, ("imala", "رؤياي"): OK,  # the words carry (or lack) the article themselves
    ("tarqiq_ra", "سرا"): OK, ("tarqiq_ra", "إرصادا"): OK, ("tarqiq_ra", "فراق"): OK,
    ("waqf_rasm", "فمال هؤلاء"): OK,  # the four phrases are the four places (4:78, 18:49, 25:7, 70:36)
    ("ya_idafa", "محياي"): OK,
    # conditions the word shows
    ("imala", "أحيا"): {"prefix": "و"},  # wafi 144: "when joined with wāw" (the second entry: the rest)
    ("imala", "المحراب"): {"jarr": True},  # wafi 155: al-Miḥrāb in the jarr
    ("taghliz_lam", "صلى"): {"ayah_end": True},  # wafi 172: the alif at a verse end
    ("imala", "زاد"): {"slots": ["2:10:4"]},  # wafi 151: the first place, 2:10 فَزَادَهُمُ
    # forms the page gives that the listed word doesn't spell: wafi 102 بئس "حيث جاء وكيف أتى", with
    # wāw, fāʾ, lām or fāʾ and lām (لبئس ما: Ḥafṣ writes بِئۡسَمَا joined)
    # idah 118: Ibn Wardān's naql in الآن with the istifhām (Yūnus 51, 91) and without it, "نحو" 2:71,
    # 12:51, 8:66: every ٱلۡـَٰٔنَ (the skeleton لن is too short to search)
    ("naql", "آلآن"): {"slots": ["2:71:18", "2:187:24", "4:18:14", "8:66:1", "10:51:7", "10:91:1", "12:51:20"]},
    ("ibdal_sakin", "بئر"): {"also": ["لبئس", "فلبئس", "ولبئس", "بئسما", "فبئسما", "ولبئسما", "لبئسما"]},
}
RESOLVING = {"prefix", "not_prefix", "jarr", "ayah_end", "slots", "nth", "surahs", "ayat"}
# a second entry with the same first word (أحيا: with fāʾ, thumma or bare): the pin's other side
PINS_SECOND = {("imala", "أحيا"): {"not_prefix": "و"}}


# --- sūrah names -------------------------------------------------------------------------------

def _latin(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub("[ʿʾ’‘'`]", "", s)
    s = re.sub(r"^(?:al|an|ash|at|ad|adh|ar|as|az)[- ]", "", s).replace("-", "").replace(" ", "")
    return s.replace("aw", "au").replace("ay", "ai").replace("dhdh", "dd")


@lru_cache(maxsize=1)
def _names() -> tuple[dict[str, int], dict[str, int]]:
    """({latin key: sūrah}, {Arabic skeleton: sūrah}) from KFGQPC's Ḥafṣ file (sora_name_en/_ar)."""
    import json

    from checks.kfgqpc import FILES, MIRROR
    lat, ar = {}, {}
    for a in json.loads((MIRROR / FILES["hafs"]).read_text(encoding="utf-8")):
        s = int(a["sora"])
        lat.setdefault(_latin(a["sora_name_en"]), s)
        k = skel(a["sora_name_ar"])
        ar.setdefault(k, s)
        if k.startswith("ل") and len(k) > 3:
            ar.setdefault(k[1:], s)  # (skel keeps the article's lām: النمل → لنمل)
    lat.update({"imran": 3, "alimran": 3, "yasin": 36, "taha": 20, "tauba": 9, "isra": 17, "nisa": 4})
    return lat, ar


NAME = re.compile(r"(?:(?:al|an|ash|at|ad|adh|ar|as|az)-)?[A-ZĀĪŪḤṢḌṬẒʿʾ][\wāīūḥṣḍṭẓʿʾ’-]*(?: ʿ?[A-Z][\wāīūḥṣḍṭẓʿʾ]*)?", re.U)


def surahs_named(note: str) -> dict[int, list[int]]:
    """{sūrah: [āyāt]} named in an English note: "al-Naml 27:43", "Ṣād 8 and al-Qamar 25", "al-Isrāʾ"."""
    lat, _ = _names()
    out: dict[int, list[int]] = {}
    for m in re.finditer(r"\b(\d{1,3}):(\d{1,3})\b", note):
        out.setdefault(int(m.group(1)), []).append(int(m.group(2)))
    for m in NAME.finditer(note):
        name = m.group(0)
        if name.lower().startswith(("al-", "an-", "ash-", "at-", "ad-", "ar-", "as-", "az-")) or name[:1] in "ĀṢṬẒḤ" or \
                _latin(name) in lat:
            k = _latin(name.split(" ")[0] if not name.startswith("Āl") else name)
            s = lat.get(k)
            if s is None:
                continue
            ay = re.match(r"\s*(\d{1,3})\b(?!:)", note[m.end():])
            out.setdefault(s, [])
            if ay:
                out[s].append(int(ay.group(1)))
    return out


def surah_in_brackets(text: str) -> tuple[set[int], str | None]:
    """(sūrahs named in brackets, the next word's skeleton for "(قبل X)")."""
    _, ar = _names()
    ss, nxt = set(), None
    for b in re.findall(r"\(([^)]*)\)", text):
        b = b.strip()
        if b.startswith("قبل"):
            nxt = skel(b[3:].split()[0]) if b[3:].split() else None
            continue
        for part in re.split("[،,و ]+(?=ال)|،|,", b):
            k = skel(part.strip())
            if k in ar:
                ss.add(ar[k])
            elif k.startswith("ل") and k[1:] in ar:
                ss.add(ar[k[1:]])
    return ss, nxt


# --- matching ----------------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _index():
    h = words()
    order = list(h)
    sk = [skel(h[w]) for w in order]
    by = defaultdict(list)
    for i, k in enumerate(sk):
        by[k].append(i)
        if len(k) > 2 and k[0] in PREFIX:
            by[k[1:]].append(i)
            if len(k) > 3 and k[1] in PREFIX:
                by[k[2:]].append(i)
    by2 = defaultdict(list)  # first two letters, prefixes off: for joined/split phrases
    for i, k in enumerate(sk):
        for j in range(0, min(2, len(k) - 2) + 1):
            if j == 0 or all(c in PREFIX for c in k[:j]):
                by2[k[j:j + 2]].append((i, j))
    return order, sk, by, by2


def _same(book: str, hafs: str) -> bool:
    return book == hafs or (hafs[:1] in PREFIX and hafs[1:] == book) or (len(hafs) > 2 and all(c in PREFIX for c in hafs[:2]) and hafs[2:] == book)


def same(book: str, hafs: str, ya: bool = True) -> bool:
    """Equal skeletons, the Ḥafṣ word perhaps with a prefix; with `ya`, a final yāʾ in one and not
    the other is allowed (the Ḥafṣ text drops the yāʾāt al-zawāʾid the book writes: آتاني / ءَاتَىٰنِ)."""
    if not ya:
        return _same(book, hafs)
    return any(_same(b, f) for b in {book, book.rstrip("ي")} for f in {hafs, hafs.rstrip("ي")} if b and f)


def akey(w: str) -> str:
    """A key that keeps what a short skeleton loses: alifs (the dagger alif as one), the seat of an
    initial hamzah (إ ≠ أ), and ى ≠ ي. For words of three letters or fewer, where the skeleton alone
    matched hundreds of words (آلآن = لن, وال = ولا, أنى = أني, أنت in كنت)."""
    w = w.replace("\u0649\u0670", "\u0649").replace("\u0670", "ا").replace("ٱ", "ا").replace("آ", "ءا")
    w = re.sub("[\u064b-\u065f\u06d6-\u06ed\u0640]", "", w)
    m = re.match("([وف]?)(.*)", w)
    pre, rest = m.group(1), m.group(2)
    rest = re.sub("^[ءأ]", "أ", rest)
    rest = rest[:1] + re.sub("[أإؤئء]", "ء", rest[1:])
    return re.sub("[^\u0621-\u064a]", "", pre + rest)


def _short_same(book: str, hafs: str) -> bool:
    """Short words: the alif key equal, the Ḥafṣ word perhaps with a wāw or fāʾ (no other prefix)."""
    return book == hafs or (hafs[:1] in "وف" and hafs[1:] == book)


def _toks(phrase: str) -> list[str]:
    toks = [skel(t) for t in re.sub(r"\([^)]*\)", " ", phrase).split()]
    toks = [t for t in toks if t]
    while "ي" in toks[:-1]:  # the vocative يا is joined to its word in the Ḥafṣ text (يَٰعِبَادِ)
        i = toks.index("ي")
        toks[i: i + 2] = ["ي" + toks[i + 1]]
    return toks


def _key(w: str) -> tuple[int, ...]:
    return tuple(int(x) for x in w.split(":"))


def matches(phrase: str, ya: bool = True, strict: bool = False, joined: bool = False) -> list[list[str]]:
    """Every run of Ḥafṣ words the phrase matches, as word ids. With `strict`, a word of three
    letters or fewer must also match by its alif key (akey). With `joined`, failing a word-by-word
    match, the phrase's letters may run on over up to four Ḥafṣ words (وماكنت = وَمَا كُنتَ).
    The listed entries are anchored with both (resolve); `find` keeps neither, as before."""
    toks = _toks(phrase)
    if strict:  # the book's doubled yāʾ, Ḥafṣ's small yāʾ (النبيين / ٱلنَّبِيِّـۧنَ: skel drops U+06E7)
        toks = [t.replace("يي", "ي") if len(t) > 4 else t for t in toks]
    if not toks:
        return []
    order, sk, by, by2 = _index()
    out = []
    first = by.get(toks[0], []) + (by.get(toks[0].rstrip("ي"), []) + by.get(toks[0] + "ي", []) if ya else [])
    raw = [t for t in re.sub(r"\([^)]*\)", " ", phrase).split() if skel(t)]
    short = [strict and len(t) <= 3 and len(raw) == len(toks) for t in toks]  # (the vocative join changes the count)
    h = words()
    for i in sorted(set(first)):
        if all(i + j < len(sk) and same(t, sk[i + j], ya) for j, t in enumerate(toks)) and \
                all(not short[j] or _short_same(akey(raw[j]), akey(h[order[i + j]])) or
                    (ya and _short_same(akey(raw[j]).rstrip("يى"), akey(h[order[i + j]]).rstrip("يى")))
                    for j in range(len(toks))):
            out.append(order[i: i + len(toks)])
    if out or not joined:
        return out
    joined = "".join(toks)
    if len(joined) < 4:
        return []
    for i, j in by2.get(joined[:2], []):
        acc, n = sk[i][j:], 1
        while len(acc) < len(joined) and n < 4 and i + n < len(sk):
            acc += sk[i + n]
            n += 1
        if acc == joined or (ya and acc.rstrip("ي") == joined.rstrip("ي")):
            out.append(order[i: i + n])
    return out


def find(phrase: str, ya: bool = True) -> list[str]:
    """Word ids where the phrase starts. Brackets and the book's notes are left out. `ya=False`:
    no allowance for a final yāʾ (for words that aren't the yāʾāt)."""
    return sorted({m[0] for m in matches(phrase, ya)}, key=_key)


# --- one entry ---------------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _ayah_ends() -> set[str]:
    last = {}
    for w in words():
        last[tuple(w.split(":")[:2])] = w
    return set(last.values())


def _count(note: str) -> int | None:
    n = {"both": 2, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
    m = re.search(r"\b(both|two|three|four|five|six|seven|eight|nine|ten|\d+) places\b", note)
    return None if not m else int(m.group(1)) if m.group(1).isdigit() else n[m.group(1)]


def resolve(table: str, x: dict, second: bool = False) -> dict:
    """{places, anchor, unanchored, flag, candidates} for one listed entry."""
    ya = table in YA
    ws = [str(w) for w in x.get("words") or []]
    note = " ".join(str(x.get(k) or "") for k in ("note", "place"))
    pin = PINS.get((table, ws[0] if ws else ""), {})
    if second:
        pin = PINS_SECOND.get((table, ws[0] if ws else ""), pin)
    named = surahs_named(note) if not pin.get("ok") else {}
    if pin.get("surahs"):
        named = {s: [] for s in pin["surahs"]}
    if pin.get("ayat"):
        named = {}
        for s, a in pin["ayat"]:
            named.setdefault(s, []).append(a)
    hits: dict[str, list[list[str]]] = {}
    for w in ws + list(pin.get("also") or []):
        ms = matches(w, ya, strict=True, joined=True)
        br, nxt = surah_in_brackets(w)
        if br:
            ms = [m for m in ms if _key(m[0])[0] in br]
        if nxt:
            h, order = words(), list(words())
            pos = {k: i for i, k in enumerate(order)}
            ms = [m for m in ms if pos[m[-1]] + 1 < len(order) and same(nxt, skel(h[order[pos[m[-1]] + 1]]), False)]
        if named and not br:
            ms = [m for m in ms if _key(m[0])[0] in named and (not named[_key(m[0])[0]] or _key(m[0])[1] in named[_key(m[0])[0]])]
        h = words()
        if pin.get("prefix"):
            ms = [m for m in ms if skel(h[m[0]]).startswith(pin["prefix"])]
        if pin.get("not_prefix"):
            ms = [m for m in ms if not skel(h[m[0]]).startswith(pin["not_prefix"])]
        if pin.get("jarr"):
            ms = [m for m in ms if re.search("[\u0650\u064d][\u06d6-\u06ed]*$", h[m[-1]])]
        if pin.get("ayah_end"):
            ends = _ayah_ends()
            ms = [m for m in ms if m[-1] in ends]
        if pin.get("slots"):
            ms = [[p] for p in pin["slots"]]
        hits[w] = ms
    flags = []
    if pin.get("nth") or (re.search(r"\bthe first\b", note) and not pin.get("ok")):
        k = pin.get("nth", 1)
        for w in hits:
            hits[w] = sorted(hits[w], key=lambda m: _key(m[0]))[k - 1:k]
    also = set(pin.get("also") or [])
    found = [w for w, ms in hits.items() if ms and w not in also]
    hits_all = hits
    hits = {w: ms for w, ms in hits.items() if w not in also}
    cands = sorted({p for ms in hits_all.values() for m in ms for p in m}, key=_key)
    if pin.get("flag"):
        flags.append(pin["flag"])
    elif not pin.get("ok") and not RESOLVING & set(pin):
        if not found:
            flags.append("no Ḥafṣ words match (a description or a spelling the skeleton misses)")
        if CONDITION.search(note) and not (_count(note) and len(ws) == 1):
            flags.append(f"the note names a condition: {note.strip()[:120]}")
        n = _count(note)
        if n and len(ws) == 1 and len(hits[ws[0]]) != n:
            flags.append(f"the note counts {n} places, {len(hits[ws[0]])} match")
        bracketed = {"".join(_toks(w)) for w in ws if surah_in_brackets(w)[0]}
        both = [w for w in ws if not surah_in_brackets(w)[0] and "".join(_toks(w)) in bracketed]
        if both:
            flags.append(f"{both[0]}: listed with a sūrah in brackets and without")
        for w, ms in hits.items():
            if len(_toks(w)) == 1 and len(_toks(w)[0]) <= SHORT and len(ms) > MANY:
                flags.append(f"{w}: a short word matching {len(ms)} places")
    out = {"anchor": "all" if len(found) == len(hits) and hits else "some" if found else "none"}
    if out["anchor"] != "all":
        out["unanchored"] = [w for w, ms in hits.items() if not ms]
    if flags:
        out["flag"] = "; ".join(flags)
        out["candidates"] = cands
        out["places"] = []
    else:
        out["places"] = cands
    return out


def anchor(table: dict, name: str | None = None) -> dict:
    """Adds `places`, `anchor` (and `unanchored`, `flag`, `candidates`) to each listed entry;
    returns counts. `name`: the table's name (the yāʾāt allow a final yāʾ)."""
    name = name or table.get("category", "")
    n = defaultdict(int)
    seen = set()
    for x in table.get("listed") or []:
        for k in ("places", "anchor", "unanchored", "flag", "candidates"):
            x.pop(k, None)
        first = str((x.get("words") or [""])[0])
        x.update(resolve(name, x, second=(name, first) in seen))
        seen.add((name, first))
        n[x["anchor"]] += 1
        n["flagged"] += bool(x.get("flag"))
    return dict(n)


def main():
    import yaml

    from mushaf_data.paths import DATA
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--flags", action="store_true")
    a = ap.parse_args()
    tot = defaultdict(int)
    for f in sorted((DATA / "usul").glob("*.yaml")):
        t = yaml.safe_load(f.read_text(encoding="utf-8"))
        if not t.get("listed"):
            continue
        c = anchor(t, f.stem)
        for k, v in c.items():
            tot[k] += v
        print(f.stem, c)
        for x in t["listed"]:
            if (a.show and x["anchor"] != "all") or (a.flags and x.get("flag")):
                print("   ", x["anchor"], x.get("words"), "|", x.get("flag", ""), "|", len(x.get("candidates") or x["places"]), x.get("cite"))
    print("all:", dict(tot))


if __name__ == "__main__":
    main()
