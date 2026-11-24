"""Read the local books (books/<slug>.txt) by page, or search them.

TXT pages are split on PAGE_SEPARATOR lines; page n here is page n of the PDF and of Aljam3.
Search ignores Arabic diacritics and tatweel, and treats أ إ آ ٱ as ا and ى as ي.

    python3 tools/book.py SLUG PAGE [PAGE2]       print pages
    python3 tools/book.py SLUG -s PATTERN [-C N]  pages and lines matching a regex
    python3 tools/book.py SLUG --pdf PAGE OUT.png render a PDF page (needs pymupdf)
"""
import argparse
import functools
import pathlib
import re
import sys

BOOKS = pathlib.Path(__file__).resolve().parent.parent / "books"
_MARKS = re.compile("[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_ALIF = str.maketrans("أإآٱى", "ااااي")


def fold(s):
    return _MARKS.sub("", s).translate(_ALIF)


@functools.lru_cache(maxsize=None)
def pages(slug):
    text = (BOOKS / f"{slug}.txt").read_text(encoding="utf-8")
    return [""] + re.split(r"\n?^PAGE_SEPARATOR$\n?", text, flags=re.M)


def page(slug, n):
    return pages(slug)[n]


def search(slug, pattern, context=0):
    rx = re.compile(fold(pattern))
    for n, p in enumerate(pages(slug)):
        lines = p.splitlines()
        for i, line in enumerate(lines):
            if rx.search(fold(line)):
                yield n, i, lines[max(0, i - context): i + context + 1]


def render(slug, n, out, zoom=2.0):
    import pymupdf
    doc = pymupdf.open(BOOKS / f"{slug}.pdf")
    doc[n - 1].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).save(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("pages", nargs="*", type=int)
    ap.add_argument("-s", "--search")
    ap.add_argument("-C", type=int, default=0)
    ap.add_argument("--pdf", nargs=2, metavar=("PAGE", "OUT"))
    a = ap.parse_args()
    if a.pdf:
        render(a.slug, int(a.pdf[0]), a.pdf[1])
    elif a.search:
        for n, i, ctx in search(a.slug, a.search, a.C):
            print(f"p{n}:{i}: " + " ⏎ ".join(ctx))
    else:
        lo, hi = a.pages[0], a.pages[-1]
        for n in range(lo, hi + 1):
            print(f"===== {a.slug} p. {n}")
            print(page(a.slug, n))


if __name__ == "__main__":
    sys.exit(main())
