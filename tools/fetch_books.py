"""Download the uṣūl books listed in tools/books.tsv into books/ (gitignored).

Sources are the Hugging Face datasets that Aljam3 links to (ieasybooks-org). Each book gets
books/<slug>.txt and books/<slug>.pdf; books/MANIFEST.json records URL, size and sha256.
Book text is never committed.

    python3 -I tools/fetch_books.py [slug ...]
"""
import csv
import hashlib
import json
import pathlib
import subprocess
import sys
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
BOOKS = ROOT / "books"
HF = "https://huggingface.co/datasets/ieasybooks-org/{ds}/resolve/main/{ext}/{path}.{ext}"


def main(only):
    BOOKS.mkdir(exist_ok=True)
    manifest_path = BOOKS / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    with open(ROOT / "tools" / "books.tsv", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            slug = row["slug"]
            if only and slug not in only:
                continue
            entry = {"aljam3": f"https://aljam3.com/ar/{row['aljam3_book']}/{row['aljam3_file']}",
                     "files": {}}
            for ext in ("txt", "pdf"):
                url = HF.format(ds=row["dataset"], ext=ext, path=urllib.parse.quote(row["path"]))
                out = BOOKS / f"{slug}.{ext}"
                subprocess.run(["curl", "-sSfL", "--retry", "3", "-o", str(out), url], check=True)
                data = out.read_bytes()
                entry["files"][ext] = {"url": url, "bytes": len(data),
                                       "sha256": hashlib.sha256(data).hexdigest()}
                print(f"{slug}.{ext}: {len(data) / 1e6:.1f} MB")
            manifest[slug] = entry
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main(set(sys.argv[1:]))
