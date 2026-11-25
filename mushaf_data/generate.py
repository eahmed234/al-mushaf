"""Readings: every (choice, text) a rāwī's profile gives for a span of words.

A reading is the text of each word plus the choice that made it: category → wajh for the text
categories and for the features the text can't show (madd lengths, sakt, ...), and `_stop`, the
word the span stops on (None: the reading goes on). Taḥrīr (`constraints`) removes combinations
the books don't allow.

Two inputs are still stand-ins until the data layer has them (docs/05):
- `farsh`: word id → this rāwī's text for the farsh places (from al-Futūḥ's rows in the checks);
- `gate`: whether a detected place really takes the category. The book's rule for imālah
  (`occurrences.imala_excluded`); the checks pass al-Futūḥ's row gate for the rest.
"""
from __future__ import annotations

import itertools

from .constraints import allowed
from .occurrences import imala_excluded
from .profiles import place_wujuh
from .spine import passage
from .usul import FEATURE_ONLY, WUJUH, apply, detect
from .waqf import forms as waqf_forms

TEXT_CATS = [c for c in WUJUH if c not in FEATURE_ONLY]
CHOICE_FEATURES = {"muttasil", "sakt_al", "sakt_mafsul", "lin_hamz", "madd_arid"}
WAQF_RAWI = {"khalaf_an_hamzah", "khallad", "hisham"}  # the waqf chapter (waqf.py)
WAQF_HAMZ_CATS = {"ibdal_sakin_waqf", "hamzatayn_waqf", "hamz_waqf_final", "hamz_waqf_mid", "hamz_waqf_zaid"}
PAUSE_SIGNS = set("ۖۗۘۙۚۛ")


def book_gate(cat: str, word: str, nxt: str | None = None) -> bool:
    """The books' rule where we have it: imālah everywhere the detector finds it except the five
    words al-Wāfī excepts (pp. 142-143). Other categories: every detected place."""
    if cat.startswith("imala_"):
        return not imala_excluded(passage().get(word, ""), word)
    return True


def context(span: list[str], hafs: dict[str, str], text: dict[str, str] | None = None):
    """The span's words plus the next word of the mushaf (context only), and the stop: the span's
    last word if it ends an ayah, else None (the reading goes on: ṣilah, idghām and naql look
    ahead)."""
    text = text or hafs
    words = [(i, text[i]) for i in span]
    if not span:
        return words, None
    order = list(hafs)
    k = order.index(span[-1])
    nxt = order[k + 1] if k + 1 < len(order) else None
    if nxt and nxt.split(":")[:2] == span[-1].split(":")[:2]:
        return words + [(nxt, text[nxt])], None
    return words, span[-1]


def contexts(span: list[str], hafs: dict[str, str], text: dict[str, str] | None = None):
    """Every way the span can be read: at a pause sign the reader may stop or go on."""
    words, stop = context(span, hafs, text)
    out = [(words, stop)]
    if span and stop is None and PAUSE_SIGNS & set(hafs[span[-1]]):
        out.append((words[: len(span)], span[-1]))
    return out


def generate(rawi: str, span: list[str], profiles: dict, *, farsh: dict[str, str] | None = None,
             gate=book_gate, hafs: dict[str, str] | None = None, places: list[dict] | None = None,
             constraints: list[dict] | None = None) -> list[tuple[dict, dict]]:
    """Every (choice, text) the rāwī's profile gives for a span: farsh first, then the uṣūl rules,
    over each way the span can be read (stop or not at a pause sign); Ḥamzah's ruwāt and Hishām
    take their waqf forms at a stop. `profiles` is {rāwī: {category: {"wujuh": {wajh: cites}}}}."""
    hafs = hafs if hafs is not None else passage()
    text = {**hafs, **(farsh or {})}
    places = [e for e in (place_wujuh() if places is None else places) if e["rawi"] == rawi]

    def base_wujuh(c):
        w = profiles[rawi].get(c, {}).get("wujuh")
        if not w and c == "silah_mim_hamza":  # one category in the books; detected apart
            w = profiles[rawi].get("silah_mim", {}).get("wujuh")
        # nothing known for this rāwī here: the category's first wajh (the Ḥafṣ text)
        return list(w or [WUJUH[c][0]])

    out = []
    own_waqf = rawi in WAQF_RAWI
    for words, stop in contexts(span, hafs, text):
        occs = [o for o in detect(words, stop=stop) if gate(o.cat, o.word, o.nxt)]
        if own_waqf:
            occs = [o for o in occs if o.cat not in WAQF_HAMZ_CATS]
        cats = sorted({o.cat for o in occs if o.cat in TEXT_CATS or o.cat in CHOICE_FEATURES})
        if "silah_mim_hamza" in cats and "munfasil" not in cats:
            cats = sorted(cats + ["munfasil"])  # the ṣilah's madd follows the munfaṣil
        # place-tied wujūh: at the place the entry's wujūh, elsewhere its `elsewhere`
        here = {e["category"]: e for e in places if any(o.cat == e["category"] and o.word == e["word"] for o in occs)}
        elsewhere = {e["category"]: e for e in places if e["category"] not in here}

        def wujuh(c):
            if c in here:
                return list(here[c]["wujuh"])
            if c in elsewhere:
                return list(elsewhere[c]["elsewhere"])
            return base_wujuh(c)

        tie = "silah_mim" in cats and "silah_mim_hamza" in cats and set(wujuh("silah_mim")) == set(wujuh("silah_mim_hamza"))
        free = [c for c in cats if not (tie and c == "silah_mim_hamza")]
        for combo in itertools.product(*[wujuh(c) for c in free]):
            ch = dict(zip(free, combo))
            if tie:
                ch["silah_mim_hamza"] = ch["silah_mim"]
            if not allowed(rawi, ch, constraints):
                continue
            txt = apply(words, occs, ch)
            ch = {**ch, "_stop": stop}
            if own_waqf and stop:
                al = "sakt_al" in {o.cat for o in occs if o.word == stop}
                for lab, w in waqf_forms(txt[stop], rawi):
                    c2 = {**ch, "waqf": lab}
                    if al:  # the stop on ٱلۡأَرۡضِ: naql, or the hamzah kept (with sakt or not, as in waṣl)
                        c2["waqf_al"] = "naql" if lab.startswith("naql") else ch.get("sakt_al", "none")
                    if allowed(rawi, c2, constraints):
                        out.append((c2, {**txt, stop: w}))
            else:
                out.append((ch, txt))
    return out
