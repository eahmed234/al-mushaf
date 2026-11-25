"""Skip a test when an input it needs isn't set up here (README, Setup)."""
import unittest

from mushaf_data.paths import BOOKS, SPINE, SOURCES


def _futuh() -> bool:
    from checks.futuh.rows import available
    return available()


sources = unittest.skipUnless(SPINE.exists() and (SOURCES / "kfgqpc").exists(),
                              "sources/ not set up: tools/fetch_sources.py, tools/build_spine.py")
books = unittest.skipUnless((BOOKS / "budur.txt").exists(), "books/ not set up: tools/fetch_books.py")
futuh = unittest.skipUnless(SPINE.exists() and _futuh(), "al-Futūḥ's rows need ../mushaf (optional)")
