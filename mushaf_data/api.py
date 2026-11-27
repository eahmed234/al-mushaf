"""Retrieval over data/: the first cut of milestone 8 (resolve / enumerate / explain), to see whether
the way the data is stored serves the questions an app asks.

    m = Mushaf(edition="sughra", options=(), farsh="books")
    m.read("warsh", "2:1-5")          # one reading: per word its text, the choices behind it, cites
    m.choices("warsh", "2:1-20")      # the span's choices, one per category (the khulf convention)
    m.count("warsh", "2:1-20")        # how many readings those choices make (taḥrīr applied)
    m.explain("2:9:6")                # everything stored about one word, for every rāwī
    m.who("2:9:6")                    # the twenty grouped by reading at that word

    python3 -m mushaf_data.api warsh 2:1-5 [--explain 2:9:6] [--json]

A reading takes one wajh per category for the whole span (data/profiles.yaml's convention); `choice`
picks them, otherwise each category's first wajh (the book's preferred one) is taken. Farsh comes
from data/farsh_books (al-Wāfī and al-Īḍāḥ) or data/farsh (al-Budūr). A farsh option is stored as the
book's words for the reading, not as text: where a rāwī's option isn't the muṣḥaf's own (`base`),
the word's text is unknown (`text: None`) and the uṣūl rules aren't applied to it.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import re
from dataclasses import asdict, dataclass, field
from functools import lru_cache

import yaml

from . import usul_tables
from .constraints import allowed, load as load_constraints
from .generate import CHOICE_FEATURES, TEXT_CATS, WAQF_HAMZ_CATS, WAQF_RAWI, book_gate
from .paths import DATA
from .profiles import place_wujuh
from .ruwat import RUWAT
from .spine import projection, slot_data, wid, words
from .usul import FEATURE_ONLY, WUJUH, apply, detect
from .waqf import forms as waqf_forms

FARSH_SOURCES = {"books": "farsh_books", "budur": "farsh"}
AYAH_END = re.compile("[۝]")


# --- references ---------------------------------------------------------------------------------

def parse_ref(ref: str) -> tuple[tuple[int, int], tuple[int, int | None]]:
    """"2" | "2:255" | "2:1-20" | "1:1-2:20" → ((sūrah, āyah), (sūrah, āyah or None for the end))."""
    a, _, b = ref.partition("-")
    s1, _, a1 = a.partition(":")
    start = (int(s1), int(a1) if a1 else 1)
    if not b:
        return start, (int(s1), int(a1) if a1 else None)
    if ":" in b:
        s2, a2 = b.split(":")
        return start, (int(s2), int(a2))
    return start, (int(s1), int(b))


def span(rawi: str, ref: str) -> list[str]:
    """The rāwī's slots in the reference, in order (his spine projection: added and empty slots)."""
    (s1, a1), (s2, a2) = parse_ref(ref)
    out = []
    for s in projection(rawi):
        sa = s.rstrip("abcdefgh")
        su, ay, _ = wid(sa)
        if (su, ay) < (s1, a1) or su > s2 or (su == s2 and a2 is not None and ay > a2):
            continue
        out.append(s)
    return out


@lru_cache(maxsize=1)
def _added_text() -> dict[str, str]:
    return {a["id"]: a.get("text", {}).get("value", "") if isinstance(a.get("text"), dict) else a.get("text", "")
            for a in slot_data().get("added") or []}


def hafs_text(slot: str) -> str:
    return words().get(slot) or _added_text().get(slot, "")


# --- stored data, indexed by slot ---------------------------------------------------------------

@lru_cache(maxsize=2)
def farsh_index(source: str = "books") -> dict[str, list[dict]]:
    """slot → farsh entries at it (their `place` and `also`). al-Budūr's `recurs` (forms the books
    give "حيث وقع") are not expanded: the table stores forms, not slots (see the report)."""
    out: dict[str, list[dict]] = {}
    for f in sorted((DATA / FARSH_SOURCES[source]).glob("*.yaml")):
        for e in yaml.safe_load(f.read_text(encoding="utf-8")) or []:
            e = {**e, "file": f.name}
            for w in dict.fromkeys(e["place"] + e.get("also", [])):
                out.setdefault(w, []).append(e)
    return out


@lru_cache(maxsize=1)
def tahrir_index() -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    """(slot → al-Budūr's taḥrīr statements there, category → al-Ḍabbāʿ's rows about it)."""
    by_slot, by_cat = {}, {}
    p = DATA / "tahrir" / "budur.yaml"
    for e in (yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else None) or []:
        for w in e["place"]:
            by_slot.setdefault(w, []).append(e)
    p = DATA / "tahrir" / "dabba.yaml"
    for e in (yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else None) or []:
        for c in e["cats"]:
            by_cat.setdefault(c, []).append(e)
    return by_slot, by_cat


def options_for(entry: dict, rawi: str) -> list[dict]:
    """The rāwī's options at a farsh entry (more than one: a khulf, or one per aspect)."""
    return [o for o in entry["options"] if rawi in o["readers"]]


# --- results ------------------------------------------------------------------------------------

@dataclass
class Rule:
    cat: str            # the engine's category (usul.WUJUH)
    table: str          # data/usul table and case that give it
    case: str
    wujuh: dict         # wajh → cites, for this rāwī
    chosen: str
    text_visible: bool  # False: a feature the text can't show (madd length, sakt…)


@dataclass
class Word:
    slot: str
    hafs: str
    text: str | None                    # None: a farsh reading stored only as the book's words
    farsh: list[dict] = field(default_factory=list)   # the rāwī's options here: reading, cite, base
    rules: list[Rule] = field(default_factory=list)
    stop: bool = False
    waqf: str | None = None             # the waqf form taken (Ḥamzah's ruwāt, Hishām)
    tahrir: list[dict] = field(default_factory=list)  # al-Budūr's statements at this word


class Mushaf:
    def __init__(self, edition: str = "sughra", options=(), farsh: str = "books"):
        if farsh not in FARSH_SOURCES:
            raise ValueError(f"farsh source {farsh!r} is not one of {sorted(FARSH_SOURCES)}")
        self.edition, self.options, self.source = edition, tuple(options), farsh
        self.profiles = usul_tables.profiles(edition, self.options)
        self.constraints = load_constraints()
        self.places = place_wujuh()

    # -- what a rāwī reads where ----------------------------------------------------------------

    def _farsh(self, rawi: str, slot: str) -> tuple[list[dict], bool]:
        """(options, base): the rāwī's farsh options at the slot, and whether he reads the muṣḥaf's own."""
        opts = []
        for e in farsh_index(self.source).get(slot, []):
            for o in options_for(e, rawi):
                opts.append({"reading": o["reading"], "cite": o.get("cite"), "base": bool(o.get("base")),
                             "khulf": rawi in (o.get("khulf") or []), "aspect": o.get("aspect"),
                             "entry": e["file"] + ":" + " ".join(e["place"][:3])})
        return opts, (not opts or all(o["base"] for o in opts))

    def _wujuh(self, rawi: str, cat: str, slot: str) -> dict:
        for p in self.places:
            if p["rawi"] == rawi and p["category"] == cat:
                ws = p["wujuh"] if p["word"] == slot else p.get("elsewhere") or []
                return {w: [p.get("cite", "place_wujuh")] for w in ws}
        w = (self.profiles[rawi].get(cat) or {}).get("wujuh")
        if not w and cat == "silah_mim_hamza":
            w = (self.profiles[rawi].get("silah_mim") or {}).get("wujuh")
        return dict(w) if w else {WUJUH[cat][0]: ["as_hafs"]}

    def _context(self, rawi: str, ref: str, stop: bool | None):
        sl = span(rawi, ref)
        allw = list(words())
        nxt = None
        if sl:
            last = sl[-1].rstrip("abcdefgh")
            i = allw.index(last)
            nxt = allw[i + 1] if i + 1 < len(allw) else None
        # stop on the last word: asked, or by default when the span ends an āyah's end
        if stop is None:
            stop = nxt is None or wid(nxt)[1] != wid(sl[-1].rstrip("abcdefgh"))[1] if sl else False
        ws = [(s, hafs_text(s)) for s in sl] + ([] if stop or nxt is None else [(nxt, words()[nxt])])
        return sl, ws, (sl[-1] if stop and sl else None)

    def _occs(self, rawi: str, ws, stop):
        occs = [o for o in detect(ws, stop=stop) if book_gate(o.cat, o.word, o.nxt)]
        if rawi in WAQF_RAWI:
            occs = [o for o in occs if o.cat not in WAQF_HAMZ_CATS]
        return [o for o in occs if o.cat in WUJUH]

    def choices(self, rawi: str, ref: str, stop: bool | None = None) -> dict[str, dict]:
        """category → {wajh: cites} for every category the span holds (one choice each per reading)."""
        sl, ws, st = self._context(rawi, ref, stop)
        out = {}
        for o in self._occs(rawi, ws, st):
            if o.cat in TEXT_CATS or o.cat in CHOICE_FEATURES or o.cat in FEATURE_ONLY:
                if o.cat not in out:
                    out[o.cat] = self._wujuh(rawi, o.cat, o.word)
        return out

    def count(self, rawi: str, ref: str, stop: bool | None = None, limit: int = 200_000) -> dict:
        """How many readings the span's choices make: the product, and after taḥrīr when small enough
        to enumerate (`exact`)."""
        ch = self.choices(rawi, ref, stop)
        n = math.prod(len(v) for v in ch.values()) if ch else 1
        res = {"categories": len(ch), "product": n, "exact": None}
        if n <= limit:
            keys = list(ch)
            res["exact"] = sum(1 for combo in itertools.product(*[list(ch[k]) for k in keys])
                               if allowed(rawi, dict(zip(keys, combo)), self.constraints))
        return res

    def read(self, rawi: str, ref: str, choice: dict | None = None, stop: bool | None = None) -> list[Word]:
        """One reading of the span: per word its text and the facts that made it."""
        if rawi not in RUWAT:
            raise ValueError(f"unknown rāwī {rawi}")
        choice = dict(choice or {})
        sl, ws, st = self._context(rawi, ref, stop)
        occs = self._occs(rawi, ws, st)
        avail = {}
        for o in occs:
            avail.setdefault(o.cat, self._wujuh(rawi, o.cat, o.word))
        ch = {c: (choice[c] if choice.get(c) in v else next(iter(v))) for c, v in avail.items()}
        bad = [c for c in choice if c in avail and choice[c] not in avail[c]]
        if bad:
            raise ValueError(f"{rawi} has no {[(c, choice[c]) for c in bad]} here; has {[(c, list(avail[c])) for c in bad]}")
        farsh = {s: self._farsh(rawi, s) for s in sl}
        # the rules run on the Ḥafṣ text; a word read with another farsh reading keeps no rule
        live = [o for o in occs if farsh.get(o.word, ([], True))[1]]
        txt = apply(ws, live, ch)
        where = usul_tables.where()
        by_slot, _ = tahrir_index()
        out = []
        for s in sl:
            opts, base = farsh[s]
            rules = []
            for o in live:
                if o.word != s:
                    continue
                t, k = where.get(o.cat, ("", 0))
                case = usul_tables.tables()[t]["cases"][k]["case"] if t else ""
                rules.append(Rule(o.cat, t, case, avail[o.cat], ch[o.cat], o.cat not in FEATURE_ONLY))
            w = Word(s, hafs_text(s), txt.get(s) if base else None, opts, rules, stop=(s == st),
                     tahrir=by_slot.get(s, []))
            if w.stop and rawi in WAQF_RAWI and w.text:
                fs = waqf_forms(w.text, rawi)
                if fs:
                    pick = next((f for f in fs if f[0] == choice.get("waqf")), fs[0])
                    w.waqf, w.text = pick
            out.append(w)
        if not allowed(rawi, ch, self.constraints):
            raise ValueError(f"taḥrīr: {ch} is not an allowed combination for {rawi}")
        return out

    # -- one word ------------------------------------------------------------------------------

    def who(self, slot: str) -> list[dict]:
        """The twenty grouped by reading at the slot: farsh options, and the muṣḥaf's own for the rest."""
        groups: dict[tuple, dict] = {}
        for r in RUWAT:
            if slot not in projection(r):
                key = ("(not read)", None, None)
                g = groups.setdefault(key, {"reading": "the word isn't in his reading", "readers": []})
                g["readers"].append(r)
                continue
            opts, base = self._farsh(r, slot)
            for o in opts or [{"reading": "as the muṣḥaf (no farsh here)", "cite": None, "base": True, "aspect": None}]:
                key = (o["reading"], o.get("cite"), o.get("aspect"))
                g = groups.setdefault(key, {"reading": o["reading"], "cite": o.get("cite"), "base": o["base"],
                                            "aspect": o.get("aspect"), "readers": [], "khulf": []})
                g["readers"].append(r)
                if o.get("khulf"):
                    g["khulf"].append(r)
        return list(groups.values())

    def explain(self, slot: str) -> dict:
        """Everything stored about one word: the spine, both farsh tables, the uṣūl rules that
        reach it for each rāwī, and taḥrīr."""
        su, ay, _ = wid(slot.rstrip("abcdefgh"))
        ref = f"{su}:{ay}"
        res = {"slot": slot, "hafs": hafs_text(slot),
               "spine": [e for e in (slot_data().get("empty") or []) + (slot_data().get("added") or [])
                         if slot in (e.get("slot"), e.get("id"))],
               "farsh": {src: [{k: v for k, v in e.items() if k in ("place", "words", "where", "class", "options", "file")}
                               for e in farsh_index(src).get(slot, [])] for src in FARSH_SOURCES},
               "rules": {}, "tahrir": tahrir_index()[0].get(slot, [])}
        cats = set()
        for r in RUWAT:
            if slot not in projection(r):
                continue
            w = next((w for w in self.read(r, ref) if w.slot == slot), None)
            if w is None:
                continue
            for rule in w.rules:
                cats.add(rule.cat)
                res["rules"].setdefault(rule.cat, {"table": rule.table, "case": rule.case, "ruwat": {}})
                res["rules"][rule.cat]["ruwat"][r] = rule.wujuh
        res["tahrir_rules"] = {c: [{"cite": e["cite"], "note": e.get("note")} for e in tahrir_index()[1].get(c, [])]
                               for c in cats if c in tahrir_index()[1]}
        return res


def show(ws: list[Word]) -> str:
    lines = []
    for w in ws:
        t = w.text if w.text is not None else "?"
        fr = "; ".join(f"{o['reading']} ({o['cite']})" + (" [khulf]" if o["khulf"] else "") for o in w.farsh if not o["base"])
        ru = ", ".join(f"{r.cat}={r.chosen}" + ("" if r.text_visible else "*") for r in w.rules)
        lines.append(f"{w.slot:10} {t:22} {('farsh: ' + fr) if fr else ''}{' | ' if fr and ru else ''}{ru}"
                     + (f" | waqf {w.waqf}" if w.waqf else "") + (" ■" if w.stop else ""))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rawi")
    ap.add_argument("ref")
    ap.add_argument("--farsh", default="books", choices=sorted(FARSH_SOURCES))
    ap.add_argument("--edition", default="sughra")
    ap.add_argument("--explain")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    m = Mushaf(edition=a.edition, farsh=a.farsh)
    if a.explain:
        print(json.dumps(m.explain(a.explain), ensure_ascii=False, indent=1, default=str))
        return
    ws = m.read(a.rawi, a.ref)
    print(json.dumps([asdict(w) for w in ws], ensure_ascii=False, indent=1) if a.json else show(ws))
    c = m.count(a.rawi, a.ref)
    print(f"\n{len(ws)} words; {c['categories']} categories; {c['product']} combinations"
          + (f", {c['exact']} after taḥrīr" if c["exact"] is not None else ""))


if __name__ == "__main__":
    main()
