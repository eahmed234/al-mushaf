"""Class each farsh place as true farsh or covered by an uṣūl rule (Eisa 2026-11-25: aṣl vs farsh
comes from al-Wāfī / al-Īḍāḥ, not from al-Budūr, which states a rule once).

    python3 -m pipeline.farsh_class 002 [--write]

The evidence per place:
  rule    an uṣūl table (data/usul) gives the place's readings: RULES, checked by hand, each
          case looked up in its table
  farsh   otherwise, the surah's farsh chapter of al-Wāfī or al-Īḍāḥ has the word (pages cited)
  unclear neither
`rule_words()` (listed words and case examples) shows which tables mention a word, as a lead for
RULES. With --write, each place in data/farsh/SSS.yaml gets `class: {kind, farsh, rule, note}`.
"""
from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from functools import lru_cache

import yaml

from mushaf_data.occurrences import skel as skel_of, skels, tokens
from mushaf_data.paths import DATA
from mushaf_data.spine import words
from tools import book

# the surah's farsh chapter in each book (PDF pages)
CHAPTERS = {"001": {"wafi": range(50, 53), "idah": range(52, 56)},  # سورة أم القرآن
            "002": {"wafi": range(199, 232), "idah": range(187, 223)},
            "003": {"wafi": range(231, 243), "idah": range(223, 231)}}
# Places whose readings an uṣūl table gives (checked by hand, 2026-11-26): place → [(table, case
# prefix)]. al-Budūr states these at the place; the books' uṣūl chapters hold the rule.
YA = "Eisa (category review 2026-11-26): the yāʾāt could be farsh; the tables list them word by word"
RULES = {"001": {"1:7:4": [("ha_mim_jam", "hāʾ after a sākin yāʾ")]},  # the books state the rule in this chapter
         "002": {
    "2:6:5": [("ha_mim_jam", "hāʾ after a sākin yāʾ")], "2:38:14": [("ha_mim_jam", "hāʾ after a sākin yāʾ")],
    "2:79:5": [("ha_mim_jam", "hāʾ after a sākin yāʾ")],
    "2:61:38": [("ha_mim_jam", "hāʾ before the plural mīm before a sākin, after a sākin yāʾ"),
                ("ha_mim_jam", "mīm after a hāʾ")],
    "2:29:13": [("waqf_rasm", "نون هنّ")], "2:68:7": [("waqf_rasm", "هو، هي")], "2:91:16": [("waqf_rasm", "هو، هي")],
    "2:91:22": [("waqf_rasm", "ما istifhāmiyyah")],
    "2:218:12": [("waqf_rasm", "hāʾ al-taʾnīth written with a tāʾ")],
    "2:265:6": [("waqf_rasm", "hāʾ al-taʾnīth written with a tāʾ")],
    "2:150:15": [("hamz_mufrad", "hamzah after a lām-alif")],
    **{p: [("ya_idafa", None)] for p in ("2:30:24", "2:124:18", "2:125:18", "2:152:1", "2:186:15", "2:249:19")},
    **{p: [("ya_zaida", None)] for p in ("2:40:13", "2:152:6", "2:186:9", "2:197:27")},
}}
# farsh, with the rule for one part (the stop on يؤت with its yāʾ is waqf_rasm)
PART = {"002": {"2:269:6": [("waqf_rasm", "the yāʾ dropped from the rasm before a sākin")]}}
NOTES = {"002": {**{p: YA for p in ("2:30:24", "2:124:18", "2:125:18", "2:152:1", "2:186:15", "2:249:19",
                                    "2:40:13", "2:152:6", "2:186:9", "2:197:27")},
                 "2:142:20": "first treated at al-Fātiḥah (الصراط)"}}
# the chapter pages, checked by hand, where the token match misses the book's spelling or catches
# the commentary's prose; they replace the matched pages
PAGES = {"001": {"1:4:1": ["wafi 50", "idah 52", "idah 53"], "1:6:2": ["wafi 50", "wafi 51", "idah 53", "idah 54"],
                 "1:7:1": ["wafi 50", "wafi 51", "idah 53", "idah 54"]},
         "002": {"2:34:3": ["idah 188", "idah 193"], "2:61:52": ["wafi 204"], "2:177:18": ["wafi 204"],
                 "2:81:7": ["wafi 205"], "2:98:8": ["wafi 207"], "2:143:44": ["wafi 212"], "2:233:55": ["wafi 220"],
                 "2:259:53": ["wafi 223"], "2:282:66": ["wafi 229", "idah 220"],
                 "2:142:20": ["wafi 50", "wafi 51"],  # الصراط: al-Fātiḥah's farsh
                 **{p: ["wafi 201"] for p in ("2:29:16", "2:112:6", "2:137:17", "2:282:48")},  # وها هو
                 "2:91:24": ["wafi 204"], "2:273:12": ["wafi 227", "wafi 228", "idah 219"], "2:280:4": ["idah 208"],
                 "2:214:18": ["wafi 218", "idah 215"], "2:258:21": ["wafi 222"]}}
# Farsh the books state for every occurrence ("حيث وقع"); al-Budūr gives it at the first place
# (checked by hand, 2026-11-27): place → the forms it covers and the page. Expanded to places by
# pipeline.anchor.find wherever the farsh is read (checks.farsh; the engine later).
RECUR = {
    "2:29:16": {"forms": ["وهو", "فهو", "لهو"], "cite": ["wafi 201"]},     # وها هو بعد الواو والفا ولامها
    "2:74:7": {"forms": ["وهي", "فهي", "لهي"], "cite": ["wafi 201"]},
    "2:67:7": {"forms": ["يأمركم", "ويأمركم", "يأمرهم", "تأمرهم", "ينصركم", "يشعركم"], "cite": ["wafi 202", "wafi 203"],
               "skip": "\u0631\u06e1"},  # a rāʾ already sākin in Ḥafṣ (إِن يَنصُرۡكُمُ, 3:160): nothing to read
    "2:168:11": {"forms": ["خطوات"], "cite": ["wafi 213"]},
    "1:7:1": {"forms": ["صراط", "الصراط", "بالصراط"], "cite": ["wafi 50", "wafi 51"]},  # Khallād's ishmām: 1:6:2 only
    "2:61:52": {"forms": ["النبيين", "النبين", "النبيون", "النبي", "نبي", "نبيا", "بالنبيين", "بالنبين", "النبوة"],
                "cite": ["wafi 204"]},
    "2:189:13": {"forms": ["البيوت", "بيوت", "بيوتكم", "بيوتهم", "بيوتنا", "بيوتهن", "بيوتكن", "بيوتا"],
                 "cite": ["wafi 218"]},  # حيث وقع وكيف نزل
    "3:66:1": {"forms": ["هأنتم"], "cite": ["wafi 235"]},  # حيث وقع في القرآن الكريم
    "2:91:24": {"forms": ["أنبياء", "الأنبياء"], "cite": ["wafi 204"]},
}
ARABIC = re.compile(r"[ء-يٰ-ۓۥۦـً-ْٓ-ٟ۟-ۭ]+")


NEAR = 120  # characters: a mention counts when a reading is stated close by (قرأ …، بالفتح …)
READING = re.compile(r"قرا|وقرا|بالفتح|بالضم|بالكسر|بالاسكان|بالتشديد|بالتخفيف|بالهمز|بالياء|بالتاء|بالنون")


@lru_cache(maxsize=None)
def chapter_tokens(surah: str) -> dict[str, set[str]]:
    """skeleton → the chapter pages where the word is mentioned next to a stated reading."""
    out: dict[str, set[str]] = defaultdict(set)
    for slug, pages in CHAPTERS[surah].items():
        for p in pages:
            text = book.fold(book.page(slug, p))
            for m in re.finditer(r"\S+", text):
                window = text[max(0, m.start() - NEAR): m.end() + NEAR]
                if READING.search(window):
                    for k in tokens(m.group()):
                        out[k].add(f"{slug} {p}")
                        out[core(k)].add(f"{slug} {p}")
                    out[short(m.group())].add(f"{slug} {p}")
    return out


GENERAL = re.compile(r"حيث (?:وقع|وقعت|اتي|جاء|نزل|ذكر|ورد)|كيف (?:وقع|اتي|جاء|نزل)|في جميع القران|في القران الكريم")
EARLIER = {"wafi": [*range(50, 53), *range(199, 420)], "idah": [*range(52, 56), *range(187, 436)]}


@lru_cache(maxsize=None)
def general_tokens(slug: str) -> dict[str, list[int]]:
    """core skeleton → pages of the book's farsh where the word is said to hold wherever it occurs
    (حيث وقع، كيف أتى …, within NEAR characters)."""
    out: dict[str, list[int]] = defaultdict(list)
    for p in EARLIER[slug]:
        try:
            text = book.fold(book.page(slug, p))
        except IndexError:
            break
        for m in re.finditer(r"\S+", text):
            if GENERAL.search(text[max(0, m.start() - NEAR): m.end() + NEAR]):
                for k in tokens(m.group()):
                    if p not in out[core(k)]:
                        out[core(k)].append(p)
    return out


def core(k: str) -> str:
    """A skeleton without prefix letters and the article (وبالزبر, والزبر → زبر)."""
    c = re.sub("^[وفبكل]{0,2}ل(?=...)", "", k)
    return c if len(c) >= 3 else k


def earlier_general(entry: dict, surah: str) -> list[str]:
    """Pages of an earlier sūrah's farsh where the place's word is given for every occurrence."""
    h = words()
    start = {slug: min(r) for slug, r in CHAPTERS.get(surah, {}).items()}
    out = []
    for slug in ("wafi", "idah"):
        g = general_tokens(slug)
        for i in entry["place"]:
            for k in skels(h[i]):
                for p in g.get(core(k), []):
                    if p < start.get(slug, 10 ** 6) and f"{slug} {p}" not in out:
                        out.append(f"{slug} {p}")
    return out[:4]


def short(w: str) -> str:
    """A key that keeps the alif, for words whose skeleton is too short (إن، أن: ن)."""
    return "#" + re.sub("[^\u0621-\u064a]", "", book.fold(w)).replace("\u0621", "\u0627")


@lru_cache(maxsize=1)
def rule_words() -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for f in sorted((DATA / "usul").glob("*.yaml")):
        t = yaml.safe_load(f.read_text(encoding="utf-8"))
        for x in t.get("listed") or []:
            for w in x.get("words") or []:
                for tok in ARABIC.findall(str(w)):
                    for k in skels(tok):
                        if len(k) >= 3:
                            out[k].add(f"{f.stem}: {x.get('case', '')}"[:120])
        for c in t.get("cases") or []:
            for tok in ARABIC.findall(re.sub(r"^[^(]*", "", str(c.get("case", "")))):
                for k in skels(tok):
                    if len(k) >= 3:
                        out[k].add(f"{f.stem}: {c['case']}"[:120])
    return out


def case_name(table: str, prefix: str | None) -> str:
    """The table's case (or listed entry's case) named by its start; None: the whole table (its
    listed words decide, as for the yāʾāt)."""
    t = yaml.safe_load((DATA / "usul" / f"{table}.yaml").read_text(encoding="utf-8"))
    if prefix is None:
        return table
    names = [str(c["case"]) for c in t["cases"]] + [str(x.get("case", "")) for x in t.get("listed") or []]
    hit = [n for n in names if n.startswith(prefix)]
    if not hit:
        raise ValueError(f"{table} has no case starting {prefix!r}")
    return f"{table}: {hit[0]}"


TOPIC = {"ya_idafa": "الياء|ياء|ياءه|ياءها", "ya_zaida": "الياء|ياء|ياءه",
         "idgham_saghir": "إدغام|أدغم|الإدغام|بالإدغام|إظهار|أظهر|بالإظهار"}


# how the Ḥafṣ word ends: a yāʾ al-iḍāfah, or the kasrah left where a yāʾ zāʾidah is dropped
END = {"ya_idafa": "\u064a[\u064e\u06e1\u0653\u0670]*[\u06d6-\u06dc]*$",
       "ya_zaida": "\u0650[\u06e5\u06e6]?[\u06d6-\u06dc]*$"}


@lru_cache(maxsize=1)
def anchored() -> dict[str, str]:
    """word id → "table: case" for the listed words of the anchored word chapters (pipeline.anchor)."""
    out = {}
    for t in ("ya_idafa", "ya_zaida", "idgham_saghir"):
        tab = yaml.safe_load((DATA / "usul" / f"{t}.yaml").read_text(encoding="utf-8"))
        for x in tab.get("listed") or []:
            for p in x.get("places") or []:
                out.setdefault(p, f"{t}: {x.get('case', '')}")
    return out


def auto_rule(entry: dict) -> str | None:
    """An uṣūl table gives the place without a hand entry: its words are listed in an anchored word
    chapter, or every option is a stop on hāʾ al-taʾnīth written with a tāʾ (رحمت، امرأت)."""
    said = " ".join(o["reading"] for o in entry["options"])
    for p in entry["place"]:
        t = anchored().get(p, "")
        # an anchored word matches wherever it is written, so the place's readings must speak of the
        # table's matter (يكذبون 2:10 is a yāʾ zāʾidah only in al-Qaṣaṣ)
        tab = t.split(":")[0]
        if t and re.search(TOPIC[tab], said) and re.search(END.get(tab, ""), words()[p]):
            return t
    h = words()
    opts = [o for o in entry["options"] if not o.get("base")]
    if opts and all(re.search("وقف|يقف", o["reading"]) and re.search("بالهاء|بالتاء", o["reading"]) for o in opts) \
            and all(re.search("\u062a[\u064e\u064f\u0650\u064b-\u064d]*[\u06d6-\u06dc]*$", h[p]) for p in entry["place"]):
        return case_name("waqf_rasm", "hāʾ al-taʾnīth written with a tāʾ")
    return None


def scope_all(e: dict) -> dict:
    """al-Budūr's own "حيث وقع" (scope all): the entry's words recur, cited from its pages."""
    h = words()
    return {"forms": sorted({h[p] for p in e["place"]}), "cite": sorted({o["cite"] for o in e["options"]})}


def recurs_from(entry: dict) -> tuple[str, list[str]] | None:
    """An entry elsewhere whose farsh the books give wherever the word occurs (`recurs`) covers the
    place: (its first word id, its cites)."""
    from .anchor import find

    for f in sorted((DATA / "farsh").glob("*.yaml")):
        for e in yaml.safe_load(f.read_text(encoding="utf-8")) or []:
            rec = e.get("recurs") or (scope_all(e) if e.get("scope") == "all" else None)
            if not rec or e["place"] == entry["place"]:
                continue
            hits = {w for form in rec["forms"] for w in find(form, ya=False)}
            if set(entry["place"]) & hits:
                return e["place"][0], list(rec["cite"])
    return None


def classify(entry: dict, surah: str) -> dict:
    """kind: rule (an uṣūl table gives the place, RULES), farsh (the farsh chapter treats it), or
    unclear. `farsh` lists the chapter pages the word appears on (a match can be the commentary's
    own prose: the pages are evidence to read, not proof); `rule` the table's case."""
    h = words()
    first = entry["place"][0]
    ks = {k for i in entry["place"] for k in skels(h[i]) if len(k) >= 2}
    ks |= {short(h[i]) for i in entry["place"] if len(skel_of(h[i])) < 2}
    ks |= {core(k) for k in list(ks) if not k.startswith("#")}
    pages = PAGES.get(surah, {}).get(first) or sorted({p for k in ks for p in chapter_tokens(surah).get(k, ())},
                                                      key=lambda s: (s.split()[0], int(s.split()[1])))
    rules = RULES.get(surah, {}).get(first)
    part = PART.get(surah, {}).get(first)
    auto = None if rules else auto_rule(entry)
    if auto:
        rules = [auto]
    rec = None if (rules or pages) else recurs_from(entry)
    if rec:
        pages = rec[1]
    elif not (rules or pages):
        pages = earlier_general(entry, surah)
        if pages:
            rec = ("an earlier farsh chapter, given wherever the word occurs", pages)
    out = {"kind": "rule" if rules else "farsh" if pages else "unclear"}
    if rec:
        out["recurs_from"] = rec[0]
    if pages and not rules:
        out["farsh"] = pages
    if rules or part:
        out["rule"] = [r if isinstance(r, str) else case_name(*r) for r in rules or part]
    if first in NOTES.get(surah, {}):
        out["note"] = NOTES[surah][first]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("surah")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    f = DATA / "farsh" / f"{a.surah}.yaml"
    text = f.read_text(encoding="utf-8")
    entries = yaml.safe_load(text)
    n = Counter()
    for e in entries:
        e["class"] = classify(e, a.surah)
        n[e["class"]["kind"]] += 1
        hints = sorted({r.split(":")[0] for k in {k for i in e["place"] for k in skels(words()[i])} for r in rule_words().get(k, ())})
        both = " +rule" if e["class"]["kind"] == "farsh" and "rule" in e["class"] else ""
        print(f"{e['class']['kind']:7}{both:6} {e['place'][0]:9} {e['words'][:30]:32} "
              f"{', '.join(e['class'].get('farsh', [])[:3])} | {'; '.join(e['class'].get('rule', [])[:2])[:70]} [{', '.join(hints)}]")
    print(dict(n))
    if a.write:
        head = text[: text.index("\n- place:") + 1]
        f.write_text(head + yaml.safe_dump(entries, allow_unicode=True, sort_keys=False, width=200, default_flow_style=None),
                     encoding="utf-8")


if __name__ == "__main__":
    main()
