"""Option text for the farsh tables: the word as each option's readers read it.

    python3 -m pipeline.farsh_text pack 1 2 3     # pipeline/work/farsh_text/kNNN.md + keys.json
    python3 -m pipeline.farsh_text validate       # pipeline/out/farsh_text/kNNN.json
    python3 -m pipeline.farsh_text build          # data/farsh_text/SSS.yaml

A case (key) is one Ḥafṣ word with one set of options (from data/farsh_books): the 509 farsh words of
sūrahs 1-3 are 280 cases. A writer (pipeline/prompt_farsh_text.md) groups the twenty by the text
they read; build stores, per slot, the groups with the options (entry, reading, cite) they realise.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import yaml

from mushaf_data.ruwat import RUWAT
from mushaf_data.spine import words

from .farsh_books import rows as book_rows

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "pipeline" / "work" / "farsh_text"
OUT = ROOT / "pipeline" / "out" / "farsh_text"
DATA = ROOT / "data"
CHARS = None


def chars() -> set[str]:
    global CHARS
    if CHARS is None:
        CHARS = {c for w in words().values() for c in w}
    return CHARS


def _quote(o: dict, cache: dict) -> str | None:
    book, _, page = (o.get("cite") or "").partition(" ")
    if not page.isdigit():
        return None
    k = (book, int(page))
    if k not in cache:
        cache[k] = book_rows(book, [int(page)])
    hits = [r for r in cache[k] if r["reading"] == o["reading"] and set(o["readers"]) & set(r["readers"])]
    return hits[0]["quote"] if hits else None


def cases(suras) -> list[dict]:
    """[{key, slots, hafs, options: [{n, readers, khulf, reading, cite, base, quote, entry}]}]."""
    h = words()
    order = list(h)
    pos = {w: i for i, w in enumerate(order)}
    at = defaultdict(list)
    for n in suras:
        for i, e in enumerate(yaml.safe_load((DATA / "farsh_books" / f"{n:03d}.yaml").read_text(encoding="utf-8")) or []):
            for s in e["place"]:
                at[s].append((f"{n:03d}#{i}", e))
    qc: dict = {}
    by: dict[tuple, dict] = {}
    for s in sorted(at, key=lambda w: pos[w]):
        es = at[s]
        if all(o.get("base") for _, e in es for o in e["options"]):
            continue
        opts = []
        for ref, e in es:
            for o in e["options"]:
                opts.append({"readers": o["readers"], "khulf": o.get("khulf") or [], "reading": o["reading"],
                             "cite": o.get("cite"), "base": bool(o.get("base")), "entry": ref,
                             "where": e.get("where")})
        sig = (h[s], json.dumps([(o["entry"].split("#")[0], o["reading"], o["readers"], o["khulf"]) for o in opts],
                                ensure_ascii=False))
        if sig not in by:
            for k, o in enumerate(opts, 1):
                o["n"] = k
                o["quote"] = _quote(o, qc)
            by[sig] = {"slots": [], "hafs": h[s], "options": opts}
        by[sig]["slots"].append(s)
    out = []
    for k, c in enumerate(by.values(), 1):
        s = c["slots"][0]
        i = pos[s]
        c["key"] = f"k{k:03d}"
        c["context"] = " ".join(h[w] for w in order[max(0, i - 4): i]) + " [" + h[s] + "] " + \
            " ".join(h[w] for w in order[i + 1: i + 5])
        out.append(c)
    return out


def pack(suras) -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    cs = cases(suras)
    for c in cs:
        lines = [f"# case {c['key']}", "", f"slots: {', '.join(c['slots'])} ({len(c['slots'])})",
                 f"Ḥafṣ word: {c['hafs']}", f"context: {c['context']}", "", "options:"]
        for o in c["options"]:
            lines.append(f"{o['n']}. readers {o['readers']}" + (f" khulf {o['khulf']}" if o["khulf"] else "")
                         + f" | reading: {o['reading']} | {o['cite']}" + (" | BASE (the Ḥafṣ reading)" if o["base"] else "")
                         + f" | entry {o['entry']} ({o['where']})")
            if o["quote"]:
                lines.append(f"   quote: {o['quote']}")
        (WORK / f"{c['key']}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (WORK / "keys.json").write_text(json.dumps(cs, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"{len(cs)} cases, {sum(len(c['slots']) for c in cs)} slots → {WORK}")


def check(c: dict, d: dict) -> list[str]:
    errs = []
    g = d.get("groups") or []
    seen = [r for x in g for r in x.get("readers") or []]
    missing = set(RUWAT) - set(seen)
    if missing:
        errs.append(f"not covered: {sorted(missing)}")
    if set(seen) - set(RUWAT):
        errs.append(f"unknown ids: {sorted(set(seen) - set(RUWAT))}")
    twice = {r for r in seen if seen.count(r) > 1}
    for x in g:
        if not set(x.get("khulf") or []) <= set(x.get("readers") or []):
            errs.append("khulf not among readers")
        t = x.get("text")
        if x.get("base") and t != c["hafs"]:
            errs.append(f"base text {t!r} is not the Ḥafṣ word")
        if t is not None and not x.get("base") and t == c["hafs"]:
            errs.append("a non-base group has the Ḥafṣ text (mark it base, or merge it)")
        if t and set(t) - chars():
            errs.append(f"characters outside the spine's: {[hex(ord(ch)) for ch in set(t) - chars()]}")
        for n in x.get("options") or []:
            if not 1 <= n <= len(c["options"]):
                errs.append(f"option {n} doesn't exist")
    for r in twice:
        if not all(r in (x.get("khulf") or []) for x in g if r in (x.get("readers") or [])):
            errs.append(f"{r} in two groups without khulf")
    if sum(1 for x in g if x.get("base")) > 1:
        errs.append("two base groups")
    return errs


def validate() -> dict:
    cs = {c["key"]: c for c in json.loads((WORK / "keys.json").read_text(encoding="utf-8"))}
    rep = {"cases": len(cs), "done": 0, "bad": {}, "null_text": 0}
    for k, c in cs.items():
        f = OUT / f"{k}.json"
        if not f.exists():
            continue
        rep["done"] += 1
        d = json.loads(f.read_text(encoding="utf-8"))
        e = check(c, d)
        rep["null_text"] += sum(1 for x in d["groups"] if x.get("text") is None)
        if e:
            rep["bad"][k] = e
    return rep


def build() -> dict:
    """data/farsh_text/SSS.yaml: slot → groups {text, readers, khulf, base, from: [option refs], note}."""
    cs = json.loads((WORK / "keys.json").read_text(encoding="utf-8"))
    per = defaultdict(dict)
    n = 0
    for c in cs:
        f = OUT / f"{c['key']}.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        if check(c, d):
            continue
        groups = []
        for x in d["groups"]:
            gr = {"text": x.get("text"), "readers": [r for r in RUWAT if r in x["readers"]]}
            if x.get("khulf"):
                gr["khulf"] = [r for r in RUWAT if r in x["khulf"]]
            if x.get("base"):
                gr["base"] = True
            gr["from"] = [f"{c['options'][i - 1]['entry']} {c['options'][i - 1]['cite']}: {c['options'][i - 1]['reading']}"
                          for i in x.get("options") or []]
            if x.get("note"):
                gr["note"] = x["note"]
            groups.append(gr)
        for s in c["slots"]:
            per[int(s.split(":")[0])][s] = {"hafs": c["hafs"], "case": c["key"], "status": "written", "groups": groups}
            n += 1
    out = DATA / "farsh_text"
    out.mkdir(exist_ok=True)
    head = ("# Option text: each farsh word as the twenty read it, grouped by text (the farsh only; the\n"
            "# engine adds each rāwī's uṣūl). Written from data/farsh_books' options and the books' quotes\n"
            "# (pipeline/prompt_farsh_text.md), checked by pipeline.farsh_text and checks.api (KFGQPC).\n"
            "# status: written = one model writing, not reviewed. Generated by `python3 -m pipeline.farsh_text build`.\n")
    order = {w: i for i, w in enumerate(words())}
    for su, d in per.items():
        d = dict(sorted(d.items(), key=lambda kv: order[kv[0]]))
        (out / f"{su:03d}.yaml").write_text(head + yaml.safe_dump(d, allow_unicode=True, sort_keys=False, width=140),
                                           encoding="utf-8")
    return {"slots": n, "suras": sorted(per)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["pack", "validate", "build"])
    ap.add_argument("suras", nargs="*", type=int, default=[1, 2, 3])
    a = ap.parse_args()
    if a.cmd == "pack":
        pack(a.suras)
    elif a.cmd == "validate":
        r = validate()
        print(f"{r['done']}/{r['cases']} cases written, {len(r['bad'])} with problems, {r['null_text']} groups with no text")
        for k, e in r["bad"].items():
            print("  ", k, "; ".join(e))
    else:
        print(build())


if __name__ == "__main__":
    main()
