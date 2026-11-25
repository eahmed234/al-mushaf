"""Build the Ḥafṣ word spine from KFGQPC's official text (sources/, see tools/sources.tsv).

Writes sources/spine/hafs.jsonl: one item per word, ayah end and rubʿ sign (۞), in Qurʾān order,
ids surah:ayah:word (a ۞ is surah:ayah:0). Same item shape as the spine the spike was built on
(id, kind, clusters[].cps), so nothing else changes.

    python3 tools/build_spine.py [--check OTHER_SPINE.jsonl]
"""
import argparse
import json
import pathlib
import unicodedata
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "sources/kfgqpc/official/UthmanicHafs_v2-0.zip"
OUT = ROOT / "sources/spine/hafs.jsonl"
HIZB = "۞"


def clusters(word: str) -> list[str]:
    out: list[str] = []
    for c in word:
        if unicodedata.category(c) == "Mn" and out:
            out[-1] += c
        else:
            out.append(c)
    return out


def cps(cl: str) -> str:
    return " ".join(f"U+{ord(c):04X}" for c in cl)


def build() -> list[dict]:
    z = zipfile.ZipFile(SRC)
    name = next(n for n in z.namelist() if n.endswith("hafsData_v2-0.json"))
    items = []
    for a in json.loads(z.read(name)):
        s, ay = int(a["sura_no"]), int(a["aya_no"])
        # words are separated by spaces, and by a no-break space after a ۞ and before the ayah
        # number (2:286 has a plain space there): the number is always the last token
        toks = [t for t in a["aya_text"].replace("\xa0", " ").split(" ") if t]
        number = toks.pop()
        n = 0
        for tok in toks:
            if tok == HIZB:
                items.append({"id": f"{s}:{ay}:0", "kind": "hizb",
                              "clusters": [{"id": f"{s}:{ay}:0:1", "kind": "sign", "cps": cps(HIZB)}]})
                continue
            n += 1
            items.append({"id": f"{s}:{ay}:{n}", "kind": "word",
                          "clusters": [{"id": f"{s}:{ay}:{n}:{k}", "cps": cps(c)} for k, c in enumerate(clusters(tok), 1)]})
        items.append({"id": f"{s}:{ay}:end", "kind": "ayah_end", "clusters": [{"cps": cps(number)}]})
    return items


def text_of(it: dict) -> str:
    return "".join(chr(int(c[2:], 16)) for cl in it["clusters"] for c in cl["cps"].split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", default=None, help="another spine to compare word by word")
    a = ap.parse_args()
    items = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items), encoding="utf-8")
    kinds = {}
    for i in items:
        kinds[i["kind"]] = kinds.get(i["kind"], 0) + 1
    print(f"{OUT}: {kinds}")
    if a.check:
        other = {}
        for line in open(a.check, encoding="utf-8"):
            it = json.loads(line)
            if it["kind"] in ("word", "hizb"):
                other[it["id"]] = text_of(it)
        mine = {i["id"]: text_of(i) for i in items if i["kind"] in ("word", "hizb")}
        diff = [k for k in mine if other.get(k) != mine[k]]
        missing = [k for k in other if k not in mine]
        print(f"compared with {a.check}: {len(mine) - len(diff)}/{len(mine)} items identical, "
              f"{len(diff)} differ, {len(missing)} only there")
        for k in (diff + missing)[:10]:
            print("  ", k, repr(mine.get(k)), repr(other.get(k)))


if __name__ == "__main__":
    main()
