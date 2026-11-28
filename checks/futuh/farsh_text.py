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
  no_row        no row names him and quotes the word (elided rows, labels it can't resolve)
  no_text       the writer left his group's text empty
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
KINDS = ("agree", "differ", "extra", "khulf_unseen", "no_row", "no_text")


def printed(surah: int) -> dict[tuple[str, str], set[tuple[str, bool]]]:
    """(slot, rāwī) → {(form, last)}: every form al-Futūḥ gives him at the word (elided rows rebuilt); `last` when it
    is the row's last quoted word (where the row may stop, so its last vowel isn't compared)."""
    from .rows import load_rows, rebuild

    out = defaultdict(set)
    rows = load_rows(lambda s, a: s == surah)
    rebuild(rows, words())  # a "…" row repeats the row above and changes only what it quotes
    for r in rows:
        # "الجميع عدا من سيأتي": everyone no other row of the box names (ruwat_max); otherwise only
        # the ruwāt the label surely names
        readers = r.ruwat or (r.ruwat_max if r.label.startswith("الجميع") else r.ruwat_min)
        q = [w for w in (r.full or r.quoted) if w.id]
        for i, w in enumerate(q):
            for x in readers:
                for t in w.alts or [w.t]:
                    out[(w.id, x)].add((t, i == len(q) - 1))
    return out


def same(text: str, form: str, last: bool) -> bool:
    """No farsh difference between the written text and the printed form. KFGQPC's ṣād with a small
    sīn above (وَيَبۡصُۜطُ 2:245) is read with the sīn, as al-Futūḥ writes it (وَيَبۡسُطُ)."""
    text, form = (re.sub("\u0635([\u064b-\u0652]*)\u06dc", "\u0633\\1", x) for x in (text, form))
    return not differs(prep(text), prep(form), final=not last)


def judge(texts: list[str], forms: set[tuple[str, bool]]) -> str:
    if not texts:
        return "no_text"
    if not forms:
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
        pr = printed(su)
        for slot, ent in e.items():
            for rawi in RUWAT:
                texts = [g["text"] for g in ent["groups"] if rawi in g["readers"] and g.get("text")]
                if not any(rawi in g["readers"] for g in ent["groups"]):
                    continue
                forms = pr.get((slot, rawi), set())
                out.append({"slot": slot, "rawi": rawi, "kind": judge(texts, forms), "texts": texts,
                            "forms": sorted(f for f, _ in forms), "hafs": ent["hafs"]})
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
    for kind in ("differ", "extra", "khulf_unseen"):
        rows = [r for r in res if r["kind"] == kind]
        for r in rows[: a.show]:
            print(f"  {kind:12} {r['slot']:9} {r['rawi']:16} {r['hafs']}  written {' / '.join(r['texts'])}"
                  f"  printed {' / '.join(r['forms'])}")


if __name__ == "__main__":
    main()
