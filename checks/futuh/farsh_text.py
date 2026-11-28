"""The written farsh text (pipeline.farsh_text) against al-Futūḥ's rows: an independent check for all
twenty, and the only one for the twelve ruwāt KFGQPC has no text for.

    python3 -m checks.futuh.farsh_text [--surah 1 2 3] [--show N] [--rawi ID]

al-Futūḥ is not by al-Qāḍī, so it can catch what al-Budūr and al-Wāfī / al-Īḍāḥ agreeing can't: an
error in the books themselves, or one the extraction made twice. For each farsh word with written
text and each rāwī, the forms al-Futūḥ prints for him there (every row that names him and quotes the
word) are compared with his written text(s), after folding what mushaf_data.diff explains as uṣūl
(the written text is the farsh only; al-Futūḥ prints it with his uṣūl applied):

  agree         every written text is printed, and nothing else is
  differ        al-Futūḥ prints him at the word, never with his text
  extra         his text is printed, and also a farsh form we don't have (a khulf missed?)
  khulf_unseen  a khulf: one text printed, the other not (al-Futūḥ's boxes aren't exhaustive)
  agree_inferred   no row surely names him, but every row that may name him prints his text
  differ_inferred  no row surely names him, and no row that may name him prints his text
  no_row        no row names him and quotes the word, or the rows that may name him split
  no_text       the writer left his group's text empty

The inferred kinds come from al-Futūḥ's jamʿ labels ("قالون واندرج من اندرج: بالتوسط", "أصحاب التوسط"),
which don't name everyone they cover: the extractor gives each such row who surely reads it
(ruwat_min) and who may (ruwat_max). Every rāwī reads some row of the box, so when all the rows that
may name him print the same farsh form, that is his form even if his row isn't known. Not where a
row whose names the extractor couldn't all read also quotes the word: that row may be his, so the
pair stays no_row. (At 2:184 "قالون واندرج أبو عمر وأبو جعفر" misspells Abū ʿAmr; the extractor stops
at the unknown word and calls the row Qālūn's alone, which left Abū ʿAmr out of every candidate row.)
"""
from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict

from mushaf_data.ruwat import RUWAT
from mushaf_data.spine import words

from ..farsh import differs, prep

# KFGQPC publishes these eight; al-Futūḥ is the only independent check for the other twelve
KFGQPC = {"hafs", "shuba", "qalun", "warsh", "bazzi", "qunbul", "duri_abuamr", "susi"}
TWELVE = [r for r in RUWAT if r not in KFGQPC]
KINDS = ("agree", "differ", "extra", "khulf_unseen", "agree_inferred", "differ_inferred", "no_row", "no_text")


def _unread():
    """A test for rows whose label head (before ":") has words ../mushaf's reader lexicon can't read: names the
    extractor dropped. Without ":" the unread words are the description, which is normal."""
    import sys
    from .rows import MUSHAF
    if str(MUSHAF) not in sys.path:
        sys.path.insert(0, str(MUSHAF))
    from futuh.readers import Lexicon, head_of, parse_head
    lex = Lexicon()
    return lambda label: ":" in label and bool(parse_head(lex, head_of(label))["unparsed"])


def printed(surah: int) -> tuple[dict, dict]:
    """Two maps from (slot, rāwī). The first: {(form, last)}, every form al-Futūḥ surely gives him at the word
    (elided rows rebuilt); `last` when it is the row's last quoted word (where the row may stop, so its last
    vowel isn't compared). The second: {row id: {(form, last)}} for the rows that only may name him, left out
    where a row that may hold anyone quotes the word."""
    from .rows import load_rows, rebuild

    out = defaultdict(set)
    maybe = defaultdict(lambda: defaultdict(set))
    blind = set()  # words quoted by a row that may hold anyone: resolved to nobody, or with names unread
    unread = _unread()
    rows = load_rows(lambda s, a: s == surah)
    rebuild(rows, words())  # a "…" row repeats the row above and changes only what it quotes
    for r in rows:
        # "الجميع عدا من سيأتي": everyone no other row of the box names (ruwat_max); otherwise only
        # the ruwāt the label surely names
        readers = r.ruwat or (r.ruwat_max if r.label.startswith("الجميع") else r.ruwat_min)
        q = [w for w in (r.full or r.quoted) if w.id]
        anyone = not (r.ruwat or r.ruwat_min or r.ruwat_max) or unread(r.label)
        for i, w in enumerate(q):
            for t in w.alts or [w.t]:
                for x in readers:
                    out[(w.id, x)].add((t, i == len(q) - 1))
                if anyone:
                    blind.add(w.id)
                elif not r.ruwat and not r.label.startswith("الجميع"):
                    for x in set(r.ruwat_max) - set(r.ruwat_min):
                        maybe[(w.id, x)][r.id].add((t, i == len(q) - 1))
    return out, {k: v for k, v in maybe.items() if k[0] not in blind}


def same(text: str, form: str, last: bool) -> bool:
    """No farsh difference between the written text and the printed form. KFGQPC's ṣād with a small
    sīn above (وَيَبۡصُۜطُ 2:245) is read with the sīn, as al-Futūḥ writes it (وَيَبۡسُطُ)."""
    text, form = (re.sub("\u0635([\u064b-\u0652]*)\u06dc", "\u0633\\1", x) for x in (text, form))
    return not differs(prep(text), prep(form), final=not last)


def judge(texts: list[str], forms: set[tuple[str, bool]], maybe: dict | None = None) -> str:
    """`maybe`: {row id: forms} of the rows that may name him, used only when no row surely does."""
    if not texts:
        return "no_text"
    if not forms:
        ok = [any(same(t, f, l) for t in texts for f, l in fs) for fs in (maybe or {}).values()]
        if ok and all(ok):
            return "agree_inferred"
        if ok and not any(ok):
            return "differ_inferred"
        return "no_row"
    seen = [t for t in texts if any(same(t, f, l) for f, l in forms)]
    other = [f for f, l in forms if not any(same(t, f, l) for t in texts)]
    if not seen:
        return "differ"
    if other:
        return "extra"
    return "agree" if len(seen) == len(texts) else "khulf_unseen"


def check(surahs=(1, 2, 3), entries: dict | None = None) -> list[dict]:
    """One result per (slot, rāwī) with written text: slot, rawi, kind, texts, forms."""
    if entries is None:
        from pipeline.farsh_text import entries as load
        entries = load()
    out = []
    for su in surahs:
        e = entries.get(su) or {}
        if not e:
            continue
        pr, mb = printed(su)
        for slot, ent in e.items():
            for rawi in RUWAT:
                texts = [g["text"] for g in ent["groups"] if rawi in g["readers"] and g.get("text")]
                if not any(rawi in g["readers"] for g in ent["groups"]):
                    continue
                forms = pr.get((slot, rawi), set())
                cand = mb.get((slot, rawi), {})
                shown = forms or {x for fs in cand.values() for x in fs}
                out.append({"slot": slot, "rawi": rawi, "kind": judge(texts, forms, cand), "texts": texts,
                            "forms": sorted(f for f, _ in shown), "hafs": ent["hafs"]})
    return out


def summary(res: list[dict]) -> dict[str, Counter]:
    s = {"all": Counter(), "twelve": Counter()}
    for r in res:
        s["all"][r["kind"]] += 1
        if r["rawi"] in TWELVE:
            s["twelve"][r["kind"]] += 1
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--surah", type=int, nargs="*", default=[1, 2, 3])
    ap.add_argument("--show", type=int, default=0, help="list N results of each disagreeing kind")
    ap.add_argument("--rawi", default=None)
    a = ap.parse_args()
    res = check(a.surah)
    if a.rawi:
        res = [r for r in res if r["rawi"] == a.rawi]
    s = summary(res)
    words_n = len({r["slot"] for r in res})
    print(f"farsh words with written text: {words_n}, (word, rāwī) pairs: {len(res)}")
    for k in ("all", "twelve"):
        print(f"  {k:7}", "  ".join(f"{x} {s[k][x]}" for x in KINDS))
    for kind in ("differ", "extra", "khulf_unseen", "differ_inferred"):
        rows = [r for r in res if r["kind"] == kind]
        for r in rows[: a.show]:
            print(f"  {kind:12} {r['slot']:9} {r['rawi']:16} {r['hafs']}  written {' / '.join(r['texts'])}"
                  f"  printed {' / '.join(r['forms'])}")


if __name__ == "__main__":
    main()
