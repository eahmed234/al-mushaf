# Reading-model spike

Plan: `../docs/02-spike-reading-model.md`. Plain Python 3.12 with PyYAML (to read the book tables in ../mushaf/futuh/readers.yaml).

Inputs (set up with `tools/fetch_sources.py` and `tools/build_spine.py`, see the top README):

| Input | Path | Pinned |
| --- | --- | --- |
| Ḥafṣ words (KFGQPC v2.0 spine) | `../sources/spine/hafs.jsonl` | built by `tools/build_spine.py` from the sha256-pinned KFGQPC zip (`tools/sources.tsv`) |
| al-Futūḥ rows, vol. 1 | `../mushaf/out/vol1.jsonl` | rebuilt by `../mushaf/rebuild.sh` at the commit in `../mushaf` |

```bash
python3 -m spike.rows          # Day 1: load, rebuild elided rows, normalise; writes spike/build/rows.jsonl
python3 -m spike.rows --show   # print every row as full text with its ruwāt
python3 -m spike.farsh --show  # Day 2: farsh places, variants, readers; farsh-only text per rāwī
python3 -m spike.readings --show  # Day 3: uṣūl profiles per rāwī, checked against every row of 2:1–5
python3 -m spike.readings --upto 20               # Day 4: learn on 2:1–20, check every row
python3 -m spike.readings --upto 5 --test 6-20    # Day 4: learn on 2:1–5, predict 2:6–20
python3 -m spike.book_profiles                   # uṣūl profiles from al-Wāfī / al-Īḍāḥ (data/profiles.yaml)
python3 -m spike.book_profiles --vs-rows         # compare them with the profiles learned from rows
PYTHONPATH=../mushaf ../mushaf/.venv/bin/python -m spike.review_profiles   # review sheet: rows beside the cited pages (build/profile_review.html)
python3 -m spike.readings --upto 0 --test 1-20 --book   # predict 2:1–20 from the book profiles alone
python3 -m spike.kfgqpc_check [--show N]            # Day 5: the eight KFGQPC riwāyāt, word by word
python3 -m spike.occurrences [--show N]             # al-Budūr's imālah lists vs the detectors, whole Qurʾān
python3 -m spike.waqf_check [--show N]              # Ḥamzah/Hishām waqf rules against al-Futūḥ, vols 1-6
python3 -m spike.review                           # Day 4: extra readings and misses, for review
PYTHONPATH=../mushaf ../mushaf/.venv/bin/python -m spike.review_sheet   # the review as box-by-box pictures
# side-by-side of printed rows and rebuilt text (needs the extractor's env for pymupdf):
PYTHONPATH=../mushaf ../mushaf/.venv/bin/python -m spike.sheet v1-p052-r11 v1-p059-r12
```

Preview rendering (`spike/render.py`): HarfBuzz shaping with DigitalKhatt Madina, outlines drawn
as SVG. The book's standalone tas-hīl dot is stored as tatweel + U+06EC (its own letter); the
renderer spaces it like a kerned glyph (a set gap from its neighbours' ink at the dot's height)
and puts the hamza's vowel above it. `python -m spike.dot_sheet` compares it with the print (same env as `spike.sheet`).
