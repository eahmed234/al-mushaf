"""Where things are. Everything this repo needs is inside it or fetched into it (README, Setup)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"          # the facts, reviewed and cited (committed)
SOURCES = ROOT / "sources"    # tools/fetch_sources.py, tools/build_spine.py (gitignored)
BOOKS = ROOT / "books"        # tools/fetch_books.py (gitignored)
BUILD = ROOT / "build"        # outputs of checks and sheets (gitignored)
SPINE = SOURCES / "spine/hafs.jsonl"
