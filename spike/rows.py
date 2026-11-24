"""Day 1: load the Hafs words and al-Futuh's rows for the passage, rebuild elided rows into
full readings, and normalise the encoding.

    python3 -m spike.rows           # writes spike/build/rows.jsonl and prints a summary
    python3 -m spike.rows --show    # also prints every row as full text with its ruwat

How elided rows are rebuilt (al-Futuh's jam' convention, read from usage, not stated in the
book): a row whose quote starts with "..." repeats the row above it in the same segment and
changes only the words it quotes. So its full text is the previous row's full text with the
quoted words put in at their Hafs word positions. The first row of a segment builds on the
Hafs text of the segment. Anything that doesn't fit is flagged, never guessed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .text import drop_shadda_first, normalize

HERE = Path(__file__).resolve().parent
PROJECTS = HERE.parents[1]
SPINE = PROJECTS / "mushaflab/data/spine/hafs/v1/items.jsonl"
FUTUH = PROJECTS / "mushaf/out/vol1.jsonl"
BUILD = HERE / "build"

RUWAT = [  # the 20, in the qurra' order
    "qalun", "warsh", "bazzi", "qunbul", "duri_abuamr", "susi", "hisham", "ibn_dhakwan",
    "shuba", "hafs", "khalaf_an_hamzah", "khallad", "abul_harith", "duri_kisai",
    "ibn_wardan", "ibn_jammaz", "ruways", "rawh", "ishaq", "idris",
]


def in_passage(surah: int, ayah: int) -> bool:
    return surah == 1 or (surah == 2 and ayah <= 20)


def wid(s: str) -> tuple[int, int, int]:
    a, b, c = s.split(":")
    return int(a), int(b), int(c)


# ---------------------------------------------------------------------------------------------
# Hafs words


def load_hafs() -> dict[str, str]:
    """Word id -> normalised Hafs text, for the passage, in Qur'an order."""
    out: dict[str, str] = {}
    for line in SPINE.open():
        it = json.loads(line)
        if it["kind"] != "word":
            continue
        s, a, _ = wid(it["id"])
        if not in_passage(s, a):
            continue
        cps = " ".join(cl["cps"] for cl in it["clusters"]).split()
        out[it["id"]] = normalize("".join(chr(int(c[2:], 16)) for c in cps))
    # The basmalah before al-Baqarah: not a word of the surah, but recited at the junction.
    # Same text as 1:1; ordered between 1:7 and 2:1.
    ordered: dict[str, str] = {}
    for k, v in out.items():
        if k == "2:1:1":
            for n in range(1, 5):
                ordered[f"B:2:{n}"] = out[f"1:1:{n}"]
        ordered[k] = v
    return ordered


# ---------------------------------------------------------------------------------------------
# Rows


@dataclass
class Word:
    id: str | None  # Hafs word id, None if the book word is not anchored
    t: str  # normalised text
    raw: str  # as extracted
    src: str  # "quote" (this row prints it), "above" (inherited from the row above), "hafs"
    alts: list[str] = field(default_factory=list)  # several ways one rawi reads this word
    classes: list[str] = field(default_factory=list)  # al-Futuh colour classes on the word


@dataclass
class Row:
    id: str
    segment: str
    n: str
    label: str
    reading: str
    elided: bool
    ruwat: list[str] | None
    ruwat_min: list[str]
    ruwat_max: list[str]
    quoted: list[Word]
    full: list[Word] = field(default_factory=list)
    base: str | None = None  # id of the row it builds on, or "hafs"
    flags: list[str] = field(default_factory=list)


# al-Futuh prints the khilaf of farsh in red, but uses the same red (#ff0000) on the madd of the
# ishba' rows (2:4 بِمَآ, 2:5 أُوْلَـٰٓئِكَ): 7,138 of 21,706 red runs book-wide cover only
# madd marks. Those are classed "madd_red", not farsh.
_MADD_MARKS = set("\u0627\u0622\u0653\u0670\u0640\u0649\u0648\u064a")


def _classes(w: dict) -> list[str]:
    out = []
    for c in w.get("colors", []):
        cls = c.get("class") or "unmapped"
        if cls == "farsh" and set(w["t"][c["s"] : c["e"]]) <= _MADD_MARKS:
            cls = "madd_red"
        if cls not in out:
            out.append(cls)
    return out


SEPARATORS = {"*", "–", "-"}
_TOKEN = re.compile("[*–-]|[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]+")


def _reading_tokens(reading: str) -> list[str]:
    """Quranic words and alternative separators of a reading, in order (no digits)."""
    toks = _TOKEN.findall(reading)
    return [t for t in toks if t in SEPARATORS or any(not ("\u0660" <= c <= "\u0669") for c in t)]


def _quoted_words(r: dict, flags: list[str]) -> list[Word]:
    """The row's own words.

    - Words the book prints in two parts (split) are joined.
    - "A * B * C" (or "A – B") gives one word position with alternatives: one rawi reading the
      word in any of these ways (e.g. Hamzah's waqf on hamz). The position takes the first
      alternative's anchor; al-Futuh's anchoring of the others is unreliable there.
    """
    words = r["words"]
    toks = _reading_tokens(r["reading"])
    arabic = [t for t in toks if t not in SEPARATORS]
    alt_next = [False] * len(words)  # word k is followed by a separator
    if len(arabic) == len(words):
        k = -1
        for t in toks:
            if t in SEPARATORS:
                if k >= 0:
                    alt_next[k] = True
            else:
                k += 1
    elif any(t in SEPARATORS for t in toks):
        flags.append("alternatives-not-parsed")
    out: list[Word] = []
    k = 0
    while k < len(words):
        w = words[k]
        if alt_next[k]:
            group = [w]
            while alt_next[k] and k + 1 < len(words):
                k += 1
                group.append(words[k])
            alts = [normalize(x["t"]) for x in group]
            first = next((x.get("spine") for x in group if x.get("spine")), None)
            cls = list(dict.fromkeys(c for x in group for c in _classes(x)))
            out.append(Word(first, alts[0], " * ".join(x["t"] for x in group), "quote", alts, cls))
            k += 1
            continue
        raw = w["t"]
        if w.get("split") and out and out[-1].id == w.get("spine") and not out[-1].alts:
            out[-1].raw += raw
            out[-1].t = normalize(out[-1].raw)
            out[-1].classes += [c for c in _classes(w) if c not in out[-1].classes]
        else:
            out.append(Word(w.get("spine"), normalize(raw), raw, "quote", classes=_classes(w)))
        k += 1
    return out


def _junction_basmalah(rows: list[dict]) -> None:
    """al-Futuh anchors the basmalah between two surahs to 1:1 (the Fatihah's own first ayah).
    In a segment that also quotes the end of one surah and the start of the next, rename those
    words to "B:<n>:<k>", the basmalah before surah n, which sits between the two surahs."""
    by_seg: dict[str, list[dict]] = {}
    for r in rows:
        by_seg.setdefault(r["group"], []).append(r)
    for seg in by_seg.values():
        ids = [w.get("spine") for r in seg for w in r["words"] if w.get("spine")]
        nxt = sorted({wid(i)[0] for i in ids if not i.startswith("1:1:") and wid(i)[1] <= 2})
        crosses = any(i.startswith("1:7:") for i in ids) or len({wid(i)[0] for i in ids}) > 1
        if not crosses or not any(i.startswith("1:1:") for i in ids):
            continue
        surah = max(wid(i)[0] for i in ids)
        for r in seg:
            for w in r["words"]:
                if (w.get("spine") or "").startswith("1:1:"):
                    w["spine"] = f"B:{surah}:{wid(w['spine'])[2]}"


def load_rows() -> list[Row]:
    rows = []
    raw = []
    for line in FUTUH.open():
        r = json.loads(line)
        if r["type"] == "row" and any(in_passage(a["surah"], a["ayah"]) for a in r.get("ayahs", [])):
            raw.append(r)
    _junction_basmalah(raw)
    for r in raw:
        flags: list[str] = []
        rows.append(Row(
            id=r["id"], segment=r["group"], n=r["n"], label=r["readers"].strip(),
            reading=r["reading"], elided=bool(r.get("elided")),
            ruwat=r.get("ruwat"), ruwat_min=r.get("ruwat_min") or [], ruwat_max=r.get("ruwat_max") or [],
            quoted=_quoted_words(r, flags), flags=flags,
        ))
    return rows


# ---------------------------------------------------------------------------------------------
# Rebuilding


def rebuild(rows: list[Row], hafs: dict[str, str]) -> None:
    """Fill in each row's full reading.

    - A row without "..." is a complete statement: its full text is exactly what it quotes.
      Hafs words it skips inside its range are recorded as `omits:` (e.g. no basmalah between
      the surahs for those who join or pause without it).
    - A row with "..." repeats the row above it and changes the words it quotes. Quoted words
      the row above didn't have are put in at their place.
    """
    order = {i: k for k, i in enumerate(hafs)}
    by_seg: dict[str, list[Row]] = {}
    for r in rows:
        by_seg.setdefault(r.segment, []).append(r)
    for seg_rows in by_seg.values():
        if not any(w.id for r in seg_rows for w in r.quoted):  # the isti'adhah, not Qur'an
            for r in seg_rows:
                r.full = list(r.quoted)
                r.flags.append("not-quran")
            continue
        prev: Row | None = None
        for r in seg_rows:
            if any(w.id is None for w in r.quoted):
                r.flags.append("unanchored-word")
            quoted = [w for w in r.quoted if w.id in order]
            if not r.elided:
                r.full = list(quoted)
                ids = {w.id for w in quoted}
                if quoted:
                    lo, hi = order[quoted[0].id], order[quoted[-1].id]
                    skipped = [i for i in list(hafs)[lo : hi + 1] if i not in ids]
                    if skipped:
                        r.flags.append("omits:" + " ".join(skipped))
                prev = r
                continue
            if prev is None:
                r.flags.append("elided-without-row-above")
                base: dict[str, Word] = {}
            else:
                base = {w.id: Word(w.id, w.t, w.raw, "above", w.alts, w.classes) for w in prev.full if w.id in order}
                r.base = prev.id
            for k, w in enumerate(quoted):
                old = base.get(w.id)
                # A quote that starts mid-ayah drops the shadda of idgham the word gets from the
                # word before it (2:17:16, 2:19:3); keep the context's form there.
                if k == 0 and old and w.t != old.t and drop_shadda_first(old.t) == w.t:
                    r.flags.append(f"boundary:{w.id}")
                    continue
                base[w.id] = Word(w.id, w.t, w.raw, "quote", w.alts, w.classes)
            r.full = sorted(base.values(), key=lambda w: order[w.id])
            prev = r


def ruwat_text(r: Row) -> str:
    if r.ruwat:
        return ",".join(r.ruwat)
    if r.ruwat_min or r.ruwat_max:
        extra = [x for x in r.ruwat_max if x not in r.ruwat_min]
        return ",".join(r.ruwat_min) + (" | maybe " + ",".join(extra) if extra else "")
    return "?"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()
    hafs = load_hafs()
    rows = load_rows()
    rebuild(rows, hafs)
    BUILD.mkdir(exist_ok=True)
    with (BUILD / "rows.jsonl").open("w") as f:
        for r in rows:
            f.write(json.dumps({
                "id": r.id, "segment": r.segment, "n": r.n, "label": r.label, "elided": r.elided,
                "base": r.base, "ruwat": r.ruwat, "ruwat_min": r.ruwat_min, "ruwat_max": r.ruwat_max,
                "flags": r.flags, "words": [{"id": w.id, "t": w.t, "src": w.src, **({"alts": w.alts} if w.alts else {}),
                           **({"classes": w.classes} if w.classes else {})} for w in r.full],
            }, ensure_ascii=False) + "\n")
    if a.show:
        seg = None
        for r in rows:
            if r.segment != seg:
                seg = r.segment
                print(f"\n=== segment {seg}")
            mark = "…" if r.elided else " "
            print(f"{r.n:>3}{mark} [{ruwat_text(r)}]  {r.label}")
            def show(w: Word) -> str:
                t = " | ".join(w.alts) if w.alts else w.t
                t = "{" + t + "}" if w.alts else t
                return t if w.src != "quote" else f"‹{t}›"

            print("     " + " ".join(show(w) for w in r.full))
            if r.flags:
                print("     flags: " + ", ".join(r.flags))
    segs = len({r.segment for r in rows})
    flagged = {}
    for r in rows:
        for fl in r.flags:
            flagged.setdefault(fl.split(":")[0], []).append(r.id)
    unknown = [r.id for r in rows if not r.ruwat and not r.ruwat_min and not r.ruwat_max]
    print(f"\n{len(rows)} rows in {segs} segments; {sum(r.elided for r in rows)} elided rows rebuilt", file=sys.stderr)
    for k, v in sorted(flagged.items()):
        print(f"  {k}: {len(v)}  {v[:6]}{' …' if len(v) > 6 else ''}", file=sys.stderr)
    print(f"  rows with no ruwat at all: {len(unknown)} {unknown}", file=sys.stderr)


if __name__ == "__main__":
    main()
