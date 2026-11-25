"""Fetch the non-book sources listed in tools/sources.tsv into sources/ (gitignored).

Each file is checked against its sha256; a mismatch stops the run. With --from DIR, a file that
already exists under DIR with the right checksum is copied instead of downloaded.

    python3 -I tools/fetch_sources.py [--from ../mushaflab/data/sources/raw]
"""
import argparse
import csv
import hashlib
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEST = ROOT / "sources"


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="src", default=None)
    a = ap.parse_args()
    bad = 0
    with open(ROOT / "tools" / "sources.tsv", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            out = DEST / row["path"]
            if out.exists() and sha(out) == row["sha256"]:
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            local = pathlib.Path(a.src) / row["path"] if a.src else None
            if local and local.exists() and sha(local) == row["sha256"]:
                shutil.copyfile(local, out)
                how = "copied"
            else:
                subprocess.run(["curl", "-sSfL", "--retry", "3", "-o", str(out), row["url"]], check=True)
                how = "downloaded"
            ok = sha(out) == row["sha256"]
            bad += not ok
            print(f"{'ok ' if ok else 'BAD'} {how:10} {row['path']}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
