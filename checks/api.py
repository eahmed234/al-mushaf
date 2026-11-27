"""The retrieval API's readings against KFGQPC's eight riwāyāt, whole sūrahs.

    python3 -m checks.api [--surah 1 2 3] [--farsh books|budur] [--show N]

Each riwāyah's KFGQPC words are aligned with the API's reading of the sūrah (the rāwī's spine
projection; checks.spine shows they align without gaps). A word agrees when KFGQPC's form is the
API's text under some choice the rāwī has: the default reading, or one category switched to another
of his wujūh (a khulf). `unknown`: the API has no text (a farsh reading stored only as the book's
words). KFGQPC reads one wajh throughout, which the single switches cover.
"""
from __future__ import annotations

import argparse
import difflib
from collections import Counter

from mushaf_data.api import Mushaf

from .kfgqpc import FILES, key
from .kfgqpc import skel as kskel
from .spine import BASMALAH, UNNUMBERED_BASMALAH, kwords


def candidates(m: Mushaf, rawi: str, ref: str) -> dict[str, set]:
    """slot → every text the rāwī's reading gives it, default and one switch at a time."""
    base = m.read(rawi, ref, stop=False)
    out = {w.slot: ({w.text} if w.text is not None else set()) for w in base}
    for cat, ws in m.choices(rawi, ref, stop=False).items():
        for wj in list(ws)[1:]:
            try:
                alt = m.read(rawi, ref, choice={cat: wj}, stop=False)
            except ValueError:  # taḥrīr rules the single switch out
                continue
            for w in alt:
                if w.text is not None:
                    out[w.slot].add(w.text)
    return out


def check(rawi: str, surah: int, m: Mushaf) -> dict:
    ref = str(surah)
    cand = candidates(m, rawi, ref)
    slots = [s for s in cand if not (surah == 1 and rawi in UNNUMBERED_BASMALAH and s in BASMALAH)]  # their count
    kw = kwords(rawi)[surah]
    hafs = {w.slot: w.hafs for w in m.read(rawi, ref, stop=False)}
    A = [kskel(hafs[s]) for s in slots]
    B = [kskel(w) for w in kw]
    res, rows = Counter(), []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, A, B, autojunk=False).get_opcodes():
        if tag != "equal" and i2 - i1 != j2 - j1:
            res["unaligned"] += i2 - i1
            continue
        for s, k in zip(slots[i1:i2], kw[j1:j2]):
            if not cand[s]:
                res["unknown"] += 1
                continue
            if key(k) in {key(t) for t in cand[s]}:
                res["agree"] += 1
            else:
                res["differ"] += 1
                rows.append((rawi, s, hafs[s], " / ".join(sorted(cand[s])), k))
    return {**res, "rows": rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--surah", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--farsh", default="books")
    ap.add_argument("--show", type=int, default=0)
    a = ap.parse_args()
    m = Mushaf(farsh=a.farsh)
    tot = Counter()
    for s in a.surah:
        for rawi in FILES:
            r = check(rawi, s, m)
            tot.update({k: v for k, v in r.items() if k != "rows"})
            print(f"{s:3} {rawi:12} agree {r.get('agree', 0):5}  differ {r.get('differ', 0):4}  unknown {r.get('unknown', 0):3}"
                  f"  unaligned {r.get('unaligned', 0)}")
            for x in r["rows"][: a.show]:
                print("     ", *x)
    n = tot["agree"] + tot["differ"]
    print(f"total: {tot['agree']}/{n} agree ({100 * tot['agree'] / max(n, 1):.1f}%), {tot['unknown']} unknown, "
          f"{tot['unaligned']} unaligned")


if __name__ == "__main__":
    main()
