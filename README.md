# al-Mushaf

A muṣḥaf for the twenty riwāyāt of the ten qurrāʾ (al-Shāṭibiyyah and al-Durrah): pick a rāwī and
the uṣūl and taḥrīr options you want, and get one valid reading of any passage, rendered in any
font and in 13- or 15-line layouts. Built by Eisa and Yusuf (who decide jointly), with Claude.

This README is for catching up: what exists, what was decided and why, where the code is, and
what comes next. The detailed running state is [`STATUS.md`](STATUS.md); the spike's findings are
[`spike/REPORT.md`](spike/REPORT.md).

## Where things stand (2026-11-24)

The project is past its first milestone: a **data-model spike** that tested whether one format
(farsh places, uṣūl profiles and occurrences, taḥrīr constraints) can produce every valid reading
of a passage for any rāwī, checked against books. The passage was al-Fātiḥah and al-Baqarah
1–20, for all twenty ruwāt. The answer was yes:

| Check | Result |
| --- | --- |
| al-Futūḥ al-Bāhira's rows of 1:1–2:20 reproduced | **674 / 676** row/rāwī pairs (the two left are one farsh entry) |
| Same, from the book profiles alone, no rows seen | **661 / 666** (99%) |
| Unseen ayahs (learn 2:1–5, predict 2:6–20) | **513 / 518** (99%), against 83% with profiles learned from rows |
| KFGQPC's eight published riwāyāt, word by word | **2,047 / 2,056** words (99.6%) |
| Ḥamzah's and Hishām's waqf forms, al-Futūḥ vols 1–6 | every printed form generated in **806 / 871** rows (93%) |
| Uṣūl profile table reviewed by Eisa | **160 / 160** rows right |

The spike is **closed**. The next phase is the real data layer, built from the books, with the
spike's checks as its tests. See "What comes next".

## How it fits together

This repo stands alone: everything it needs comes from public sources it fetches itself (Setup,
below). One sibling repository is an optional dependency, used only by the checks:

| Repo | What it is | Role here |
| --- | --- | --- |
| **`al-mushaf`** (this one) | docs, the reading-model spike, the book tools | the project |
| `../mushaf` | extractor for *al-Futūḥ al-Bāhira* (6 vols): glyph-level text, colours, rows, reader lists | the main jamʿ source, used as a **check** |

The reading model, as the spike left it:

```
words         the Ḥafṣ spine (surah:ayah:word → text); to become riwāyah-neutral (docs/04)
farsh         per place: the options and who reads each              (checks/futuh/farsh.py, from al-Futūḥ for now)
profiles      rāwī × uṣūl category → wujūh, each row citing a page  (data/profiles.yaml)
occurrences   where a category applies: a detector + the books' lists (mushaf_data/usul.py, mushaf_data/occurrences.py)
constraints   taḥrīr as allowed tuples over categories and features  (data/constraints.yaml)
place wujūh   wujūh tied to one place (Ruways at 2:20)               (data/place_wujuh.yaml)
waqf          Ḥamzah's and Hishām's stop on hamz, by rule            (mushaf_data/waqf.py)
reading       per word: text + the choices that made it (madd lengths, sakt, imālah…)
```

Inputs to a reading: the rāwī, the passage, the options (wujūh), and where the reader stops.

## The sources

Every fact in the data cites a book and page. Nothing is written from memory. The books are kept
locally in `books/` (gitignored; text is not committed) and fetched with
[`tools/fetch_books.py`](tools/fetch_books.py) from the Hugging Face datasets that
[Aljam3](https://aljam3.com) links to; `books/MANIFEST.json` records each file's URL, size and
sha256. TXT page *n* = PDF page *n* = Aljam3 page *n*.

| Slug | Book | Gives |
| --- | --- | --- |
| `wafi` | al-Qāḍī, *al-Wāfī fī Sharḥ al-Shāṭibiyyah* | uṣūl of the seven (profiles, rules) |
| `idah` | al-Qāḍī, *al-Īḍāḥ li-Matn al-Durrah* | uṣūl of the three, and the Durrah's method |
| `budur` | al-Qāḍī, *al-Budūr al-Zāhirah* | per-place readings, taḥrīr in prose, per-rubʿ imālah lists |
| `ghayth-1`, `ghayth-2` | al-Ṣafāqusī, *Ghayth al-Nafʿ* | per-place notes, waqf wujūh (check) |
| `dabba` | al-Ḍabbāʿ, *Sharḥ Itḥāf al-Bariyyah* | taḥrīrāt of the Shāṭibiyyah |
| `buhur` | al-Qāḍī, *al-Buḥūr al-Zākhirah* | the matn verses behind al-Budūr |

Checks, not inputs: *al-Futūḥ al-Bāhira* (via `../mushaf`), KFGQPC's eight riwāyāt, nQuran's
al-ʿAshr al-Ṣughrā pages, alkiraat.com. See [`docs/03-usul-sources.md`](docs/03-usul-sources.md).

```bash
python3 -I tools/fetch_books.py            # download into books/ (ask before adding new books)
python3 tools/book.py wafi 74              # print a page
python3 tools/book.py budur -s 'الممال'    # search (diacritics ignored)
python3 tools/book.py wafi --pdf 74 p.png  # render the PDF page (needs pymupdf)
```

## Decisions

Decisions are Eisa's (for Eisa and Yusuf). Each is recorded where it applies.

| Decision | Where |
| --- | --- |
| The book's standalone tas-hīl dot is stored as tatweel + U+06EC; drawn centred between its neighbours' ink, vowel above | `STATUS.md`, `checks/sheets/render.py` |
| A bare "خلف" in al-Futūḥ is Khalaf ʿan Ḥamzah | `../mushaf/futuh/readers.yaml` |
| "الجميع عدا من سيأتي / عدا أصحاب X" still covers a rāwī another row names for one wajh, for his other wajh (with khulf evidence) | `checks/futuh/learn.py` (`khulf_convention`) |
| Ruways: no idghām kabīr except al-Īḍāḥ's places (khulf at 2:20) | `data/place_wujuh.yaml` |
| Ibn Dhakwān's زَادَ is uṣūl with khulf in the whole Qurʾān; imālah only at 2:10 (a place entry) | `data/profiles.yaml`, `data/place_wujuh.yaml` |
| Ikhtilāf between ṭuruq is an **option**, book's preferred wajh first (Idrīs's sakt); data stays ṭarīq-aware for a later kubrā version | `data/profiles.yaml` (`option: true`) |
| The uṣūl profile table (160 rows) is right; notes applied: tarbīʿ, dhawāt al-rāʾ split out | `data/profiles.yaml` (`review:`) |
| Ḥamzah's and Hishām's waqf is its own chapter | `mushaf_data/waqf.py` |
| al-Futūḥ prints the sakt form of ٱلۡأٓخِرِ as ٱلۡأَخِرِ (a convention); 2:11 row 10's shadda is a print error | `checks/futuh/readings.py` (`sakt_print`), `data/corrections/futuh_print_errors.yaml` |
| Finish the spike (Day 5) before building out sources | `spike/REPORT.md` |
| Waqf marks are per edition; features are marked, colour optional; the word spine becomes riwāyah-neutral | [`docs/04-scope-decisions.md`](docs/04-scope-decisions.md) |

## Setup

```bash
python3 -I tools/fetch_sources.py   # KFGQPC texts and fonts, DigitalKhatt: into sources/ (gitignored), sha256-checked
python3 tools/build_spine.py        # the Ḥafṣ word spine from KFGQPC's official text: sources/spine/hafs.jsonl
python3 -I tools/fetch_books.py     # the uṣūl books (TXT + PDF) into books/ (gitignored)
```

`tools/sources.tsv` lists each source with its URL, sha256 and licence; `fetch_sources.py
--from DIR` copies a file from a local folder instead of downloading it when the checksum
matches. The checks against al-Futūḥ need `../mushaf` (its extracted rows aren't
redistributable, so they stay there); everything else runs without it.

## The code

Plain Python 3.12 + PyYAML; tests use the standard library's `unittest`. Scripts that render or
read PDFs use the extractor's environment (`PYTHONPATH=.:../mushaf ../mushaf/.venv/bin/python`)
for pymupdf and HarfBuzz.

The spike's code was split into the engine and its checks on 2026-11-24 (milestone 0 of
docs/05); the spike as reported is tagged `spike-end`.

### `mushaf_data/`: the engine (no al-Futūḥ)

| File | Does |
| --- | --- |
| `paths.py`, `ruwat.py` | where things are; the twenty ruwāt and their qurrāʾ |
| `text.py` | one internal encoding for Qurʾānic text (`normalize`, `clusters`) |
| `spine.py` | the Ḥafṣ word spine from `sources/` (whole Qurʾān, and the spike's passage) |
| `diff.py` | classifies how a word differs from Ḥafṣ (madd, ṣilah, imālah, idghām, hamz, sakt, style; the rest is farsh) |
| `usul.py` | **detectors and transforms** per uṣūl category: where each applies, and what each wajh does to the text; `WUJUH` lists the categories |
| `profiles.py` | loads `data/profiles.yaml` (every category covers the twenty once, every row cites a page) and `data/place_wujuh.yaml` |
| `constraints.py` | taḥrīr: `allowed(rawi, choice)`, and `validate()` for `data/constraints.yaml` |
| `waqf.py` | Ḥamzah's and Hishām's waqf forms by the hamzah's position and seat, rasm forms, هَٰٓؤُلَآءِ |
| `occurrences.py` | al-Budūr's per-rubʿ imālah lists tied to the spine; the imālah gate (al-Wāfī's exceptions) |
| `generate.py` | **generation**: farsh, then uṣūl choices (text and features) under the constraints, per stop context. Farsh and the occurrence gate are inputs until the data layer has them |

### `checks/`: the engine against other sources

| File | Does |
| --- | --- |
| `futuh/rows.py` | al-Futūḥ's rows for the passage (from `../mushaf`), elided rows rebuilt, print errors corrected; `build/rows.jsonl` |
| `futuh/farsh.py`, `futuh/learn.py` | the stand-ins: farsh and the occurrence gate from the rows; profiles learned from rows (the spike's first approach) |
| `futuh/readings.py` | `check()`: every row/rāwī pair reproduced? label features, extra readings |
| `futuh/review.py` | extra readings and misses, for review |
| `waqf.py` | the waqf chapter against every waqf form in al-Futūḥ vols 1–6 |
| `kfgqpc.py` | generation against KFGQPC's eight riwāyāt, word by word |
| `farsh.py` | the farsh table against KFGQPC (and al-Futūḥ's rows); `--report` lists the disagreements |
| `sheets/` | side-by-side pictures and the profile review sheet (`review_profiles.py`); the preview renderer (HarfBuzz + DigitalKhatt) and the tas-hīl dot work |

### `pipeline/`: reading the books into rows (docs/05)

| File | Does |
| --- | --- |
| `prompt.md`, `schema.json` | the frozen instructions (reader names, categories, a worked example) and the output shape |
| `pack.py` | a page's text, the start of the next, and the Ḥafṣ words it speaks about → `pipeline/work/` (gitignored) |
| `validate.py` | rejects rows whose quote isn't on the page, unknown ruwāt, bad places; quotes become offsets |
| `gold.py`, `gold/` | the gold set: reviewed rows stored as offsets into the page (no book text in the repo) |
| `score.py` | a run against the gold set: recall, precision, what was missed and what was added |
| `sheet.py` | the review sheet: each page's rows beside the page image, ✓/✗ marks back as JSON |
| `farsh.py` | farsh rows → `data/farsh/SSS.yaml`: places, options, coverage of the twenty |

Runs write to `pipeline/out/RUN/` (gitignored: they hold quotes from the book).

### `data/`: the facts

| File | Holds |
| --- | --- |
| `profiles.yaml` | 35 categories × 20 ruwāt: wujūh, page citation, conditions, place exceptions, options; reviewed (what the engine reads) |
| `categories.yaml` | the 36 categories, one per rule for all twenty (Eisa 2026-11-26), and which extraction names belong to each |
| `usul/*.yaml` | the uṣūl from al-Wāfī and al-Īḍāḥ, one table per category: every case with all twenty ruwāt in one vocabulary, listed words, cites, disagreements, open questions (`mushaf_data/usul_tables.py`) |
| `constraints.yaml` | taḥrīr tuples (tarbīʿ, badal × dhawāt al-yāʾ, badal × ʿāriḍ, Khallād's sakt × stop…), each cited, enforced or not |
| `place_wujuh.yaml` | wujūh tied to one place |
| `corrections/futuh_print_errors.yaml` | al-Futūḥ print errors Eisa confirmed, corrected on load |
| `farsh/SSS.yaml` | farsh per surah: places, options (readers, khulf, the book's words, page), status |
| `readers.yaml` | how the books name the twenty (qurrāʾ, ruwāt, al-Budūr's groups from its p. 11) |

### `tools/`

`fetch_sources.py` and `sources.tsv` (texts and fonts), `build_spine.py` (the Ḥafṣ spine),
`fetch_books.py` and `books.tsv` (the books), `book.py` (page reader and search).

### Tests and checks

```bash
python3 -m unittest                                 # everything (about a minute); skips what isn't set up
python3 -m unittest tests.test_data tests.test_engine   # the data and the engine alone (seconds)
```

Each test has a twin that plants an error (a wrong profile row, a missing constraint, a changed
word, a broken waqf rule, shuffled lists) and checks that it's caught. Tests that need
`../mushaf` or `books/` skip without them. The checks also run on their own:

```bash
python3 -m checks.futuh.readings --upto 20 --book          # every row of 1:1–2:20: 674/676
python3 -m checks.futuh.readings --upto 0 --test 1-20 --book   # from the books alone: 661/666
python3 -m checks.waqf                                     # waqf chapter vs al-Futūḥ vols 1–6: 806/871
python3 -m checks.kfgqpc                                   # vs KFGQPC's eight riwāyāt: 2,047/2,056
python3 -m mushaf_data.occurrences                         # imālah lists vs detectors: 171/175 tied
python3 -m mushaf_data.profiles                            # the profile table, expanded
PYTHONPATH=.:../mushaf ../mushaf/.venv/bin/python -m checks.sheets.review_profiles   # review sheet (HTML)
```

## How we work

- **Every fact cites a page**, read from the page. No qirāʾāt from memory, by anyone.
- **Check the data before calling something taḥrīr** (or khulf, or an omission): dropped rows,
  colour-only marks, labels against text, footnotes. Ask Eisa only what the data can't answer,
  phrased neutrally, with the page beside it.
- **Anything judged by eye goes in a side-by-side sheet**: the print beside the output.
- **Reviews come back as data**: the review sheet's ✓/✗ and notes are pasted back and applied.
- **Every check needs a broken input it catches.** Two of the spike's results were briefly wrong
  because a check passed for the wrong reason.
- **Light process**: plain files, small modules, commits that say what changed and why. The
  postmortem of the earlier attempt ([`docs/01`](docs/01-landscape-and-postmortem.md)) is the
  reason.

## What comes next

The plan is [`docs/05-data-layer-plan.md`](docs/05-data-layer-plan.md). In short, from `spike/REPORT.md` and `docs/04-scope-decisions.md`:

1. **Build the data layer apart from the spike**, sources first: farsh from al-Budūr and the farsh
   chapters (not from al-Futūḥ's rows), occurrence tables per category from the books' lists
   (al-Budūr's "المدغم" next), the profile table as it is. al-Futūḥ, KFGQPC, nQuran and alkiraat
   become tests.
2. **Every input a choice**: the stop, joining ayahs (al-Sūsī's ٱلرَّحِيمِ مَّلِكِ across 1:3–4),
   and the features, so every constraint can bind.
3. **Gaps the checks found**: two hamzahs across words (ٱلسُّفَهَآءُ أَلَآ), al-Kisāʾī's hāʾ
   al-taʾnīth at a stop, word-specific imālah beyond the passage, naql occurrences, the قِيلَ farsh
   entry.
4. **Scope decisions** (docs/04): mark sets per edition, ayah counts per riwāyah, a
   riwāyah-neutral word spine, feature marks in DigitalKhatt (a mock-up sheet first).
5. **Open decisions**: istiʿādhah and basmalah wujūh; taḥrīr sources for the Durrah; how to settle
   the twelve riwāyāt KFGQPC doesn't publish (books first, then alkiraat and nQuran, then Eisa).

Lower priority: 208 numbering irregularities in the al-Futūḥ extraction
(`../mushaf/docs/known-gaps.md`); an unsent collaboration message to alkiraat.com.

## Documents

| Doc | About |
| --- | --- |
| [`docs/01-landscape-and-postmortem.md`](docs/01-landscape-and-postmortem.md) | quran.com, Nuqayah, alkiraat and others; why mushaflab stalled |
| [`docs/02-spike-reading-model.md`](docs/02-spike-reading-model.md) | the spike's plan and its day-by-day results |
| [`docs/03-usul-sources.md`](docs/03-usul-sources.md) | the uṣūl books and the checking sources |
| [`docs/04-scope-decisions.md`](docs/04-scope-decisions.md) | waqf marks, marking without colour, ḥadhf and ziyādah |
| [`docs/05-data-layer-plan.md`](docs/05-data-layer-plan.md) | the plan for building the data layer: who does what, the batch pipeline, cost, order of work |
| [`spike/REPORT.md`](spike/REPORT.md) | the spike's answers, numbers, and what to change before building |
| [`STATUS.md`](STATUS.md) | the running state and ordered next steps |

## Glossary

| Term | Meaning here |
| --- | --- |
| rāwī / riwāyah | a transmitter of a qāriʾ's reading / that transmission; the twenty are the unit of the app |
| farsh | readings tied to particular words |
| uṣūl | rule categories that apply wherever their conditions hold (madd, imālah, hamz…) |
| wajh / wujūh | one of the allowed ways to read a place |
| khulf | a rāwī has more than one wajh |
| taḥrīr | which wujūh of different places may be read together |
| ṭarīq / ṭuruq | the chain a riwāyah comes through; the Shāṭibiyyah and Durrah fix theirs (a later kubrā version adds the Ṭayyibah's) |
| waqf / waṣl | stopping on a word / joining it to the next |
| box / row | al-Futūḥ's layout: a box per passage, a row per reading with its readers |
