# Reading-model spike

Plan: `../docs/02-spike-reading-model.md`. Plain Python 3.12 with PyYAML (to read the book tables in ../mushaf/futuh/readers.yaml).

Inputs, read in place and never copied here:

| Input | Path | Pinned |
| --- | --- | --- |
| Ḥafṣ words (KFGQPC v2.0 spine) | `../mushaflab/data/spine/hafs/v1/items.jsonl` | sha256 `1fe71d33…2d28a4` |
| al-Futūḥ rows, vol. 1 | `../mushaf/out/vol1.jsonl` | rebuilt by `../mushaf/rebuild.sh` at the commit in `../mushaf` |

```bash
python3 -m spike.rows          # Day 1: load, rebuild elided rows, normalise; writes spike/build/rows.jsonl
python3 -m spike.rows --show   # print every row as full text with its ruwāt
python3 -m spike.farsh --show  # Day 2: farsh places, variants, readers; farsh-only text per rāwī
python3 -m spike.readings --show  # Day 3: uṣūl profiles per rāwī, checked against every row of 2:1–5
python3 -m spike.readings --upto 20               # Day 4: learn on 2:1–20, check every row
python3 -m spike.readings --upto 5 --test 6-20    # Day 4: learn on 2:1–5, predict 2:6–20
python3 -m spike.review                           # Day 4: extra readings and misses, for review
# side-by-side of printed rows and rebuilt text (needs the extractor's env for pymupdf):
PYTHONPATH=../mushaf ../mushaf/.venv/bin/python -m spike.sheet v1-p052-r11 v1-p059-r12
```

Preview rendering (`spike/render.py`): HarfBuzz shaping with DigitalKhatt Madina, outlines drawn
as SVG. The book's standalone tas-hīl dot is stored as tatweel + U+06EC (its own letter); the
renderer spaces it like a kerned glyph (a set gap from its neighbours' ink at the dot's height)
and puts the hamza's vowel above it. `python -m spike.dot_sheet` compares it with the print (same env as `spike.sheet`).
