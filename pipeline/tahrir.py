"""Taḥrīr from al-Ḍabbāʿ (Sharḥ Itḥāf al-Bariyyah): page inputs, vocabulary, validation.

    python3 -m pipeline.tahrir pack 153 296      # pipeline/work/dabba/pNNN.txt + VOCAB.md
    python3 -m pipeline.tahrir validate          # pipeline/out/tahrir/dabba/*.json
    python3 -m pipeline.tahrir build             # data/tahrir/dabba.yaml, data/tahrir/budur.yaml

Rows (pipeline/prompt_tahrir.md) are candidates for data/constraints.yaml: `combination` rows are
allowed tuples across categories, `restriction` rows say which wujūh of one category the
Shāṭibiyyah's ṭarīq reads (checked against data/usul), `place` rows the wujūh of one word.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

from mushaf_data.ruwat import SEVEN

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "pipeline" / "work" / "dabba"
OUT = ROOT / "pipeline" / "out" / "tahrir" / "dabba"
KINDS = {"combination", "restriction", "place"}
CONDITIONS = {None, "wasl", "waqf", "start", "junction"}
SOURCES = {"commentary", "verse", "footnote"}


def page_text(n: int) -> str:
    out = subprocess.run([sys.executable, str(ROOT / "tools" / "book.py"), "dabba", str(n)],
                         capture_output=True, text=True, check=True).stdout
    return out.split("\n", 1)[1] if out.startswith("=====") else out


def vocab() -> dict[str, list[str]]:
    """Category id -> its wujūh ids, from data/usul."""
    v = {}
    for f in sorted((ROOT / "data" / "usul").glob("*.yaml")):
        t = yaml.safe_load(f.read_text(encoding="utf-8"))
        v[t["category"]] = [w["id"] for w in t.get("wujuh") or []]
    return v


def write_vocab() -> Path:
    cats = yaml.safe_load((ROOT / "data" / "categories.yaml").read_text(encoding="utf-8"))
    lines = ["# Categories and wujūh ids (from data/usul)", ""]
    for c, ws in vocab().items():
        what = (cats.get(c) or {}).get("what", "")
        lines.append(f"- `{c}`: {what}  \n  wujūh: " + ", ".join(f"`{w}`" for w in ws))
    lines += ["", "Farsh places have no category here: use `farsh_<word in Latin letters>` with the "
              "readings as short ids (`ishmam`, `kasr`), and list them in `new_ids`.", ""]
    p = WORK / "VOCAB.md"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def pack(first: int, last: int) -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    for n in range(first, last + 1):
        nxt = page_text(n + 1)[:600]
        (WORK / f"p{n:03d}.txt").write_text(
            f"# dabba page {n}\n\n## PAGE\n{page_text(n)}\n\n## NEXT PAGE BEGINS (context only)\n{nxt}\n",
            encoding="utf-8")
    print(f"wrote pages {first}-{last} and {write_vocab()}")


def check_row(r: dict, page: int, v: dict[str, list[str]]) -> list[str]:
    errs = []
    if r.get("kind") not in KINDS:
        errs.append(f"kind {r.get('kind')!r}")
    bad = [x for x in r.get("readers") or [] if x not in SEVEN]
    if bad or not r.get("readers"):
        errs.append(f"readers {bad or 'empty'}")
    cats, new = r.get("cats") or [], set(r.get("new_ids") or [])
    if not cats:
        errs.append("no cats")
    for c in cats:
        if c not in v and c not in new:
            errs.append(f"cat {c!r} not in vocab or new_ids")
    for key in ("allowed", "forbidden"):
        for t in r.get(key) or []:
            if len(t) != len(cats):
                errs.append(f"{key} tuple {t} has {len(t)} ids for {len(cats)} cats")
                continue
            for c, w in zip(cats, t):
                if c in v and w not in v[c] and w not in new:
                    errs.append(f"{key} wajh {w!r} not a {c} wajh")
    if not (r.get("allowed") or r.get("forbidden")):
        errs.append("neither allowed nor forbidden")
    if r.get("condition") not in CONDITIONS:
        errs.append(f"condition {r.get('condition')!r}")
    if r.get("source") not in SOURCES:
        errs.append(f"source {r.get('source')!r}")
    q = r.get("quote") or ""
    text = page_text(page)
    if not q or q not in text:
        errs.append("quote not on the page")
    elif text.count(q) > 1:
        errs.append("quote found more than once")
    return errs


def validate(d: Path = OUT) -> dict:
    v = vocab()
    rep = {"pages": 0, "rows": 0, "rejected": []}
    for f in sorted(d.glob("p*.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        rep["pages"] += 1
        for i, r in enumerate(j.get("rows") or []):
            rep["rows"] += 1
            e = check_row(r, j["page"], v)
            if e:
                rep["rejected"].append({"page": j["page"], "row": i, "errors": e})
    return rep


def rows(d: Path = OUT) -> list[dict]:
    """Validated rows with their page."""
    v, out = vocab(), []
    for f in sorted(d.glob("p*.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        for r in j.get("rows") or []:
            if not check_row(r, j["page"], v):
                out.append({**r, "page": j["page"]})
    return out


def offset(slug: str, page: int, quote: str) -> dict:
    """A quote as a place on the page (book text is never committed)."""
    if slug == "dabba":
        text = page_text(page)
    else:
        out = subprocess.run([sys.executable, str(ROOT / "tools" / "book.py"), slug, str(page)],
                             capture_output=True, text=True, check=True).stdout
        text = out.split("\n", 1)[1] if out.startswith("=====") else out
    i = text.find(quote)
    return {"page": page, "at": i, "len": len(quote)} if i >= 0 else {"page": page, "at": None}


def against_usul(r: dict) -> list[str]:
    """A general restriction's wujūh against the uṣūl tables: wujūh a table gives the rāwī (in any
    case or listed word) that the ṭarīq, as al-Ḍabbāʿ reads it, doesn't allow."""
    if r["kind"] != "restriction" or r.get("words") or len(r["cats"]) != 1 or r["cats"][0] not in vocab():
        return []
    t = yaml.safe_load((ROOT / "data" / "usul" / f"{r['cats'][0]}.yaml").read_text(encoding="utf-8"))
    ok = {t_[0] for t_ in r.get("allowed") or []} or None
    bad = {t_[0] for t_ in r.get("forbidden") or []}
    out = []
    for x in r["readers"]:
        ws = {w for c in t["cases"] for w in (c["ruwat"].get(x) or {}).get("wujuh") or []}
        extra = (ws - ok if ok else set()) | (ws & bad)
        if ok and not ws & ok:
            continue  # the restriction is about a case this table doesn't give him (another rule's words)
        if extra:
            out.append(f"{x}: table has {sorted(extra)}")
    return out


def build() -> dict:
    """data/tahrir/dabba.yaml (al-Ḍabbāʿ's rows) and data/tahrir/budur.yaml (al-Budūr's per-place
    taḥrīr statements, pp. 15-75), every row with its page and quote offset."""
    import glob
    outdir = ROOT / "data" / "tahrir"
    outdir.mkdir(exist_ok=True)
    keep = ("kind", "readers", "cats", "allowed", "forbidden", "words", "sura", "ayah", "condition",
            "source", "via", "new_ids", "note")
    dab, flagged = [], 0
    for r in rows():
        e = {k: r[k] for k in keep if r.get(k) not in (None, [], "")}
        e["cite"] = f"dabba {r['page']}"
        e["quote"] = offset("dabba", r["page"], r["quote"])
        e["status"] = "extracted"
        chk = against_usul(r)
        if chk:
            e["usul_check"] = chk
            flagged += 1
        dab.append(e)
    bud = []
    files = sorted(glob.glob(str(ROOT / "pipeline/gold/budur/p0*.json")))
    files += [f for f in sorted(glob.glob(str(ROOT / "pipeline/out/baqarah/budur/p0*.json")))
              if Path(f).name not in {Path(g).name for g in files}]
    for f in files:
        j = json.loads(Path(f).read_text(encoding="utf-8"))
        page = j.get("page") or int(Path(f).stem[1:])
        for r in j.get("rows") or []:
            if r.get("kind") != "tahrir":
                continue
            bud.append({"place": r["place"], "readers": r["readers"], "khulf": r.get("khulf") or [],
                        "reading": r["reading"], "condition": r.get("condition"), "cite": f"budur {page}",
                        "quote": ({"page": r["span"][0], "at": r["span"][1], "len": r["span"][2] - r["span"][1]}
                                  if r.get("span") else offset("budur", page, r["quote"])),
                        "status": "checked" if "/gold/" in f else "extracted"})
    head = ("# Taḥrīr statements read from {}: candidates for data/constraints.yaml, not enforced.\n"
            "# Generated by `python3 -m pipeline.tahrir build`; quotes are offsets into the book's page.\n")
    (outdir / "dabba.yaml").write_text(
        head.format("al-Ḍabbāʿ, Sharḥ Itḥāf al-Bariyyah (pp. 153-296; pipeline/prompt_tahrir.md)")
        + "# usul_check: wujūh the uṣūl table gives a rāwī that this statement's ṭarīq doesn't allow.\n"
        + yaml.safe_dump(dab, allow_unicode=True, sort_keys=False, width=140), encoding="utf-8")
    (outdir / "budur.yaml").write_text(
        head.format("al-Budūr al-Zāhirah's places, al-Fātiḥah to Āl ʿImrān (pp. 15-75)")
        + yaml.safe_dump(bud, allow_unicode=True, sort_keys=False, width=140), encoding="utf-8")
    return {"dabba": len(dab), "flagged": flagged, "budur": len(bud)}


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    p = sub.add_parser("pack")
    p.add_argument("first", type=int)
    p.add_argument("last", type=int)
    s = sub.add_parser("validate")
    s.add_argument("dir", nargs="?", default=str(OUT))
    a = ap.parse_args()
    if a.cmd == "build":
        print(build())
    elif a.cmd == "pack":
        pack(a.first, a.last)
    else:
        r = validate(Path(a.dir))
        print(f"{r['pages']} pages, {r['rows']} rows, {len(r['rejected'])} rejected")
        for x in r["rejected"]:
            print("  p", x["page"], "row", x["row"], "; ".join(x["errors"]))


if __name__ == "__main__":
    main()
