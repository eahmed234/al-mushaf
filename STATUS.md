# Status and next steps

Last updated 2026-11-24 (after the books were pulled and the profile table built). Read this first in a new session (the overview for newcomers is `README.md`), then
`docs/02-spike-reading-model.md` (the spike plan with day-by-day results) and
`docs/03-usul-sources.md` (uṣūl books).

## Where things are

Two local git repos (no remotes, nothing pushed):

- **`~/Projects/al-mushaf`** (this repo). Docs; the engine in `mushaf_data/`, checks in `checks/`,
  facts in `data/`, tests in `tests/` (Python 3.12 + PyYAML; commands in the README). The spike's
  code as reported is tagged `spike-end` (`spike/REPORT.md`).
- **`~/Projects/mushaf`**: the al-Futūḥ al-Bāhira extractor (uv). `./rebuild.sh` rebuilds all six
  volumes in about 2.5 min; outputs go to `out/vol{1..6}.jsonl` (not tracked). `docs/known-gaps.md`
  logs every fix and open gap.
- **`books/`** (gitignored): the uṣūl books as TXT + PDF, fetched by `tools/fetch_books.py` from
  `tools/books.tsv`; `books/MANIFEST.json` has URL, size, sha256. `python3 tools/book.py SLUG PAGE`
  prints a page, `-s REGEX` searches (diacritics folded), `--pdf PAGE OUT.png` renders one. TXT
  page n = PDF page n = Aljam3 page n = printed page (al-Wāfī, al-Īḍāḥ).
- **`sources/`** (gitignored): KFGQPC texts and fonts and DigitalKhatt, fetched by
  `tools/fetch_sources.py` from `tools/sources.tsv` (URL, sha256, licence); the Ḥafṣ spine is
  built from KFGQPC's official text by `tools/build_spine.py` (identical, word for word, to the
  one the spike was built on). Nothing comes from the archived `~/Projects/mushaflab`.

### The spike (passage: al-Fātiḥah + al-Baqarah 1–20)

| Module | Does |
| --- | --- |
| `rows.py` | loads al-Futūḥ rows; rebuilds "…" rows; one encoding (`text.py`); alternatives `A * B`; junction basmalah `B:2:n`; imālah dot from the green colour |
| `diff.py` | classifies a word's difference from Ḥafṣ: madd, ṣilah, imālah, idghām, hamz, sakt, final_vowel; the rest is farsh |
| `farsh.py` | 11 farsh places, 22 variants, all 220 rāwī/place pairs settled |
| `usul.py` | detectors and transforms per uṣūl category (incl. waqf categories) |
| `profile.py` | learns text wujūh per rāwī from rows; contexts (stop at ayah end, optional at pause signs); reviewed places; claims by colour; the khulf convention |
| `readings.py` | full profiles (rows + book madd tables + label features), generation, comparison, held-out test |
| `review.py`, `review_sheet.py` | extra readings and misses, as a list and as box-by-box pictures |
| `occurrences.py` | al-Budūr's per-rubʿ "الممال" lists tied to the spine; the imālah gate (al-Wāfī pp. 142–143) |
| `waqf.py`, `waqf_check.py` | Ḥamzah's and Hishām's waqf on hamz, by rule (al-Wāfī pp. 105–127); checked against al-Futūḥ vols 1–6 (93% of 871 rows) |
| `render.py`, `dot_sheet.py` | preview renderer (HarfBuzz + DigitalKhatt) with the standalone tas-hīl dot |
| `data/place_wujuh.yaml` | wujūh tied to a place, with sources (Ruways at 2:20; Ibn Dhakwān's زَادَ at 2:10) |
| `data/constraints.yaml` | taḥrīr as allowed tuples, from the books (Warsh: badal × līn, badal × dhawāt al-yāʾ); `readings` filters combinations by it |
| `data/profiles.yaml`, `book_profiles.py` | **uṣūl profiles from al-Wāfī and al-Īḍāḥ** (checked against al-Budūr, Ghayth al-Nafʿ, nQuran where they disagreed): 33 categories × 20 ruwāt, each row with page; `readings --book` uses them |

Book profiles (2026-11-24), `data/profiles.yaml`, 34 categories × 20 ruwāt (reviewed by Eisa):

| Test | rows-learned | book table |
| --- | --- | --- |
| learn 2:1–5, predict 2:6–20 | 429 / 518 (83%) | **513 / 518 (99%)** |
| learn 2:1–12, predict 2:13–20 | 255 / 287 (89%) | **285 / 287 (99%)** |
| no training, 2:1–20 | 442 / 666 (Ḥafṣ default) | **661 / 666 (99%)** |

(An earlier version of these numbers was wrong: a local variable in `full_profiles` shadowed the
`book` flag, so every run used the book table. Fixed; the table above is after the fix.)
`python3 -m checks.futuh.readings --vs-rows` now shows one disagreement with the rows: Ruways's
idghām at 2:20 (a place entry covers it). The remaining misses are 2:11 لَّهُمۡ (Hishām, al-Kisāʾī,
Ruways), 2:13 قِيلَ (farsh), and Ḥamzah's ruwāt and Idrīs at 2:8 ٱلۡأَخِرِ (naql in waqf, not
modelled). Extra readings now count a row's alternatives ("A * B * C"); what's left of them is mostly
Qālūn's ṣilah/munfaṣil combinations (constraints) and one waqf form each for Ḥamzah and Hishām at
2:13 ٱلسُّفَهَآءُۗ.

Earlier numbers: **655 / 676** row/rāwī pairs of 2:1–20 reproduced; held-out **83%** (learn 2:1–5,
predict 2:6–20) and **89%** (learn 2:1–12, predict 2:13–20); 0 conflicts with the book's madd
tables; review list empty.

### Decisions (Eisa; Eisa and Yusuf decide jointly)

- The book's standalone tas-hīl dot is stored as tatweel + U+06EC. The preview draws it centred
  between its neighbours' ink, 80 font units each side, dot at 85%, and the hamza's vowel above it.
- A bare "خلف" in al-Futūḥ is Khalaf ʿan Ḥamzah.
- 2:8:11 بِمُؤۡمِنِين has no final fatḥah in the print (it is a pausal form where the quote stops).
- "الجميع عدا من سيأتي" and "الجميع عدا أصحاب X" still cover a rāwī whom another row names for
  one wajh, for his other wajh (Qālūn's iskān at 2:3, 2:18). Applied only with khulf evidence.
- Ruways: no idghām kabīr, except a khulf at the places al-Īḍāḥ lists (2:20 here).
- Where ṭuruq or commentators differ (ikhtilāf), the wajh is an app option with the book's
  preferred reading as default (first case: Idrīs's sakt). A kubrā version comes later.
- al-Futūḥ prints the sakt form of ٱلۡأٓخِرِ as ٱلۡأَخِرِ (a print convention); row 10 at 2:11 has a
  print error (a carried-over shadda), corrected in `data/corrections/futuh_print_errors.yaml`.
- Data layer (docs/05): subagents on the plan for now (no API billing); pilot bar 98%; farsh from
  al-Budūr first, al-Wāfī / al-Īḍāḥ second; this repo stands alone (no mushaflab dependency).
- Glyph 135 is the tas-hīl dot; glyph 383 is lām-alif with maddah; #76923c is the imālah green.
- Madd lengths are three: qaṣr 1, tawassuṭ 2, ṭūl 3 alifs (al-Shāṭibī's way, al-Budūr p. 18); the
  four-degree way and its fractions wait for the kubrā version (2026-11-25).
- The Shāṭibiyyah's and the Durrah's uṣūl are one set of rules (2026-11-26): `data/categories.yaml`
  (36 categories), `data/usul/` one table per category for all twenty in one vocabulary. Unstated
  reads as Ḥafṣ (a Durrah rāwī: as his aṣl). Where a fresh reading disagreed with the reviewed
  profile, the reviewed wujūh stand (al-Futūḥ and al-Budūr sided with them each time), recorded
  under `disagreements`. Idghām ṣaghīr and the yāʾāt are per word; مالك / الصراط are farsh.
- Extraction conventions from the pilot review (2026-11-25, `pipeline/PILOT.md`): general rules
  and words elsewhere are rows; references and "leaving a rule" take the rule's category (mafṣūl
  khāṣ = sakt_al, mafṣūl ʿām = sakt_mafsul); at a stop on fatḥ tanwīn the stop is on the alif.

### What the spike has shown so far (Q1–Q5)

- Q1/Q2: farsh plus rule-based uṣūl express nearly every row; the rules compose (ṣilah + munfaṣil,
  naql + badal, ṣilah undoing idghām into mīm).
- Q3: constraints are simple allowed tuples, but al-Futūḥ's boxes aren't exhaustive, so the tuples
  must come from a taḥrīr source (al-Budūr states them in prose).
- Q4: waqf is an input (stop at ayah end; optional at pause signs); waqf has its own hamz categories.
- Q5: a reading is text plus features (madd lengths, sakt, imālah against taqlīl, ishmām of the
  ṣād…), because the text can't show them.
- Profiles learned from rows don't generalise to unseen categories; profiles read from the books'
  uṣūl chapters do (98% of 2:1–20 with no training rows), and agree with every row-learned
  profile in the passage except Idrīs's sakt.

## Where we are (2026-11-26, to resume)

- **Spike** closed (`spike/REPORT.md`, tag `spike-end`). **Milestone 0** (package, tests) and
  **milestone 1** (extraction pipeline, model pilot: Sonnet 5.5 subagents, `pipeline/PILOT.md`) done.
- **Milestone 2, farsh of al-Baqarah** (in progress): al-Budūr pp. 16-58 extracted; `data/farsh/002.yaml`
  has 147 places (3 flagged). Checked against KFGQPC (`python3 -m checks.farsh --report`): 304 pairs
  agree, 72 words disagree (mostly farsh al-Budūr states once and doesn't repeat, and hamz farsh the
  differ calls uṣūl). The al-Futūḥ farsh check is too noisy until it compares full engine readings.
- **Uṣūl** (Eisa: al-Budūr is "one and done", so aṣl vs farsh comes from al-Wāfī / al-Īḍāḥ): both
  uṣūl sections read (1,187 rules), unified into **`data/usul/`**: 36 categories (`data/categories.yaml`),
  one table each for all twenty ruwāt in one vocabulary; unstated = as Ḥafṣ (Durrah: as its aṣl);
  reviewed profile wujūh kept where a fresh reading disagreed (recorded under `disagreements`).
  Through the engine: al-Futūḥ 674/676 in the kubrā edition, 666 in the sughrā (Idrīs's sakt), KFGQPC 2,047/2,056 (tests). al-Budūr's statements in
  al-Baqarah agree on 1,216/1,356 (`python3 -m pipeline.crosscheck_budur`, build/crosscheck_budur.md).
- **Uṣūl review done (2026-11-26)**: the 200 `open` lines were mostly notes; `pipeline/open_sort.yaml`
  sorted them (3 policies, 15 questions, 34 page gaps re-read and applied by `pipeline.unify_gaps`),
  and Eisa's answers are applied by `pipeline.unify_answers` (rulings in open_sort.yaml `answers`).
  data/usul now has `notes`, `options` (ahl al-adāʾ views, off), `kubra` (other ṭuruq), and no open
  questions. Regenerate: `unify_gaps`, `unify_answers`, then `unify_merge`. Sheet:
  `PYTHONPATH=.:../mushaf ../mushaf/.venv/bin/python -m pipeline.unified_sheet` → build/unified_review.html.
  Eisa may bring a backup source for Ḥamzah's waqf. Warsh's hamzatayn keeps tashīl first
  (Eisa), against al-Wāfī's verse order (`order_exception` in hamzatayn).

- **Editions and options (2026-11-26)**: `usul_tables.profiles(edition, options)`: the sughrā (default)
  leaves out the `kubra` entries, the kubrā adds them; `options` are switched on by id
  (`usul_tables.extras()` lists them). Entries with `adds` reach the engine (Idrīs's sakt); the others
  (basmalah, badal at one word, Ḥamzah's rasm waqf, the yāʾāt, three ḥarakāt) are recorded and
  reported `modelled: False` until the engine has those categories (milestone 8).

- **Aṣl or farsh in al-Baqarah (2026-11-27)**: each of the 147 places in data/farsh/002.yaml has a
  `class` (`pipeline/farsh_class.py`, run by `pipeline.farsh`): 21 `rule` (an uṣūl table gives it:
  the hāʾ of عليهم, hāʾ al-sakt, hāʾ al-taʾnīth at a stop, the yāʾāt, لئلا; each names its table
  case) and 126 `farsh` (the farsh chapters of al-Wāfī pp. 199-231 / al-Īḍāḥ pp. 187-222, with pages;
  12 pinned by hand, the rest found next to a stated reading, so evidence to read, not proof).
  The al-Budūr crosscheck now picks the table case from the word (imālah after a rāʾ, al-Wāfī
  p. 150's faʿlā words, the alif before a sākin in waṣl; the sākin hamzah's place; the second
  hamzah's vowel) and leaves out rows that point at another word: 1,271 agree, 52 differ (was
  1,227 / 129). It found two table gaps, fixed from the page (`pipeline.unify_gaps`): Warsh's
  khulf taqlīl on the faʿlā words (wafi 150), and the alif dropped before a sākin in waṣl with
  al-Sūsī's khulf on the rāʾ (wafi 155-156), a new case pair in the imālah table.

- **al-Fātiḥah's farsh and the word chapters (2026-11-27)**: data/farsh/001.yaml has مالك and الصراط /
  صراط (al-Budūr p. 15, the rows of the instructions' worked example, validated; `extracted`, not
  yet reviewed), classed farsh with wafi 50-51 / idah 52-54; عليهم is the rule. A place whose rows
  name different words is now split per word (Khallād's ishmām is in the first الصراط only): this
  also split 2:184 (فدية طعام / مسكين, no longer flagged) and 2:197 (جدال, now flagged: al-Budūr
  leaves Ibn Kathīr, Abū ʿAmr and Yaʿqūb unstated there). Against KFGQPC the farsh agrees (its
  other differences are the basmalah's numbering); against al-Futūḥ only الصراط's ishmām and
  Ruways at 1:7:1 differ, both as al-Budūr states. The yāʾāt and idghām ṣaghīr tables' listed
  words are anchored to Ḥafṣ places (`pipeline/anchor.py`, run by unify_merge): 96 of 121 entries
  fully, the rest keep their `unanchored` forms.

Next, in order:
1. The al-Baqarah farsh disagreements with KFGQPC: review sheet, second reading of the disputed
   words from al-Wāfī / al-Īḍāḥ's farsh chapters.
2. Then docs/05 milestones 3- (riwāyah-neutral spine, the rest of the farsh, occurrences, constraints).

Working notes: subagents get their own scratch folders; reviewed data stands until Eisa rules;
book text is never committed (quotes are offsets; pipeline/out and pipeline/work are gitignored).

## Next steps, in order (older list)

1. ~~Pull the books~~, ~~build the profile table~~, ~~read the remaining bābs~~, ~~Eisa's review~~
   (all 160 rows right, 2026-11-24; notes applied: Warsh's tarbīʿ and badal × dhawāt al-yāʾ in
   `data/constraints.yaml`, dhawāt al-rāʾ split out as `imala_ya_ra`, Ibn Dhakwān's زَادَ as
   uṣūl with khulf (Eisa corrected an earlier "farsh"), imālah only at 2:10). New rows since the review (`imala_ya_ra`) are candidates.
   - Idrīs's sakt is an option (ikhtilāf; default none). A kubrā version comes later.
   - **Waqf of Ḥamzah and Hishām: its own chapter, `mushaf_data/waqf.py`** (2026-11-24). Every form a
     stop allows, by the hamzah's position and seat, each rule citing al-Wāfī pp. 105–127 (and
     al-Budūr p. 34 for خَٰسِـِٔينَ): ibdāl, naql, idghām after wāw/yāʾ, tas-hīl after an alif with
     madd/qaṣr, the five qiyās forms after an alif at the end, rawm, the nine mutaḥarrik cases with
     al-Akhfash and rasm ḥadhf, hamzah made mid by a prefix or lām al-taʿrīf (taḥqīq or takhfīf),
     يَوۡمَئِذٖ, fatḥ tanwīn, Hishām's final hamzah only, naql from the next word.
     Also the rasm forms where the rasm seats the final hamzah on a wāw or yāʾ (al-Wāfī
     pp. 119–120; al-Budūr pp. 91–92 "سبعة الرسم", p. 209 "أربعة الرسم", pp. 142, 171, 218 for
     يَبۡدَؤُاْ / ٱلۡمَلَؤُاْ), hāʾ al-tanbīh as a prefix, and the 13 wujūh of هَٰٓؤُلَآءِ (al-Budūr p. 65:
     the two tas-hīls take one length). `python3 -m spike.waqf_check` tests it against every waqf
     form al-Futūḥ prints for them in all six volumes: **806 of 871 rows (93%)** have every printed
     form generated (all 12 of شُرَكَٰٓؤُاْ's "خمسة القياس وسبعة الرسمي" included); the rest are print
     quirks (split, dotless or vowel-less forms), Ḥamzah's farsh in the same word (يُؤَدِّهِۦ), and
     rows the extraction tags with the wrong ayah. Sakt-with-waqf constraints (al-Wāfī p. 106,
     al-Budūr p. 41) are recorded in `data/constraints.yaml` but not enforced: sakt is a label
     feature, not a text choice, in the spike.
   - Still not in the table (`not_read_yet`): Ḥamzah's naql and sakt in waqf, the rest of the
     rāʾāt and lāmāt exceptions.
2. **Occurrence tables** (started 2026-11-24, imālah done). `mushaf_data/occurrences.py` reads al-Budūr's
   end-of-rubʿ "الممال" lists (complete for the ten; Ghayth al-Nafʿ's lists leave out word-list
   imālah like فَزَادَهُمُ, شَآءَ, ءَاذَانِهِمۡ), ties them to quarters of the Ḥafṣ spine (۞ items) by a
   monotonic alignment on their words and the commentary before them: **171 of 175 lists tied**,
   a list covering back to its rubʿ's ۞ (juzʾ ʿAmma rubʿs span surahs), "رءوس الآي" as a class.
   Checked against the detectors over the whole Qurʾān: 1,468 detector hits on listed words; the
   ~1,000 unlisted are ~800 عَلَى / إِلَىٰ / حَتَّىٰ / لَدَى, which al-Wāfī pp. 142–143 excepts by name
   (with مَا زَكَىٰ, al-Nūr 21), and the rest list or alignment misses. So the **imālah gate is now
   the book's rule**: every detected place except those five words (`occurrences.imala_excluded`),
   replacing "some al-Futūḥ row shows it"; passage results unchanged. The lists also exposed
   detector gaps, now fixed: alif maqṣūrah without a dagger alif (عِيسَى, تُبۡلَى), tanwīn before it
   at a stop (مُّسَمّٗى), kasr tanwīn on the rāʾ (قَرَارٖ). Still to do: al-Kisāʾī's hāʾ al-taʾnīth at
   a stop (not a spike category yet; most of the listed-but-undetected words), word-specific
   imālah outside the passage (عِمۡرَٰنَ…), and the same for idghām (al-Budūr's "المدغم" lists), naql
   and the hamz categories, which still use the row gate.
3. **Read al-Futūḥ's footnotes ("تفاصيل المقطع")**: per-word statements with matn verses. They're
   already extracted as `footnote` / `text` records. Parse them into place entries like
   `data/place_wujuh.yaml`.
4. **Constraints from al-Budūr** (2026-11-24, for 1:1–2:20). al-Budūr pp. 15–26 state taḥrīr only
   for features the spike doesn't model as text: madd degrees (pp. 18–19), badal against madd
   ʿāriḍ at a stop (pp. 21–22), sakt against waqf (pp. 21, 25), and badal equality (p. 20, which
   one choice per span already gives). All are in `data/constraints.yaml`, not enforced. The
   "extra readings" the spike counted were mostly the comparison, not missing taḥrīr: a box
   reads a span one way (stop at a final pause sign or go on), and spreads one rāwī's wujūh over
   rows of different lengths. Counting per reading way and per box: **22 → 3** extras on the full
   passage (al-Dūrī at 2:19–20, Qālūn at 2:20). Book-only runs show more (Qālūn's iskān) because
   the "الجميع عدا من سيأتي" convention is computed from the rows.
   **Features as choices** (2026-11-24): sakt on al- and shayʾ, sakt on the mafṣūl, muttaṣil, līn
   before hamz, and madd ʿāriḍ at a stop (al-Budūr p. 15: three wujūh for all) are detected and
   generated as choices with the text categories. Each row's label features must now hold on a
   reading whose text is the row's (a bare "السكت" means the sakt places in the row); before, they
   only had to be in the profile. Checked: 94 madd/badal and 19 sakt label statements in 2:1–20, no
   new misses, and a corrupted label is caught. Enforced: Warsh badal × madd ʿāriḍ (exactly al-Budūr's
   six wujūh at 2:8), Warsh badal × līn, badal × dhawāt al-yāʾ, Khallād's sakt on al- × his stop
   (naql only without sakt). Not yet: Khalaf's mafṣūl sakt × a stop on a word starting with a
   hamzah (the spike doesn't stop on those with naql yet), madd degrees (wujūh are not degrees).
   Next for taḥrīr: read al-Budūr's and al-Ḍabbāʿ's taḥrīr beyond this passage as the occurrence
   work reaches further.
5. ~~**Spike Day 5**~~ (done 2026-11-24): `checks/kfgqpc.py` (eight riwāyāt, 2,047 / 2,056
   words agree) and **`spike/REPORT.md`**, answering Q1–Q5 with the numbers, what didn't work,
   the format as it ended up, and what to change before building for real. The spike is closed;
   next is the data layer as its own thing (REPORT.md, "Before building for real").
6. **Data layer** (docs/05). ~~Milestone 0~~ (done 2026-11-24): the spike split into
   `mushaf_data/` (engine: generation takes farsh and the occurrence gate as inputs, so al-Futūḥ
   is only a check), `checks/`, `data/`, and 25 `unittest` tests with the spike's numbers, each
   with a planted error. The planted errors found: a profile row without a cite crashed the
   loader instead of being reported (fixed); **shuffled imālah lists still tie 131 of 175
   quarters**, so the tie count is weak evidence that a list sits on its own rubʿ (to tighten
   in milestone 5). The KFGQPC check still takes its profiles from the al-Futūḥ merge.
   Milestone 1 (2026-11-25): `pipeline/` built and piloted on al-Budūr pp. 16–25
   (`pipeline/PILOT.md`). Sonnet 5.5 subagents: 96.9% recall / 95.8% precision per rāwī against
   Claude's gold set (99% on who reads what); Haiku 5.5 out (87% / 80%, more tokens). ~13k tokens
   a page. Eisa reviewed the 59 rows (2026-11-25): gold set and instructions v3
   (`pipeline/PILOT.md`, "Eisa's review"); Sonnet v2 against it: 96.3% / 95.6%. Sonnet on the
   v3 instructions: 95.4% / 96.7% overall, **farsh 100% in every run**, uṣūl ~93% (variance);
   one instruction defect it found itself (bare "خلف" in a statement about Ḥamzah is Khalaf ʿan
   Ḥamzah) fixed. Decision: Sonnet for milestone 2 (farsh, al-Baqarah); uṣūl rows only check the
   reviewed profile table.
   Milestone 2 started (2026-11-25): al-Budūr pp. 26–58 extracted by three Sonnet subagents
   (1,072 rows, 0 rejected, ~630k tokens); with the reviewed gold for pp. 16–25,
   `data/farsh/002.yaml` has **147 farsh places** for al-Baqarah, 3 flagged for coverage
   (two points in one statement). Checked against KFGQPC's seven other riwāyāt
   (`checks/farsh.py`, spelling conventions folded): 304 (word, rāwī) pairs agree; 39 words where
   KFGQPC differs and the table doesn't say so (mostly a farsh the book states once and doesn't
   restate: وهو/فهو, خطوات, يأمركم; and uṣūl the differ can't fold), 33 the other way (mostly
   hamz farsh the differ calls uṣūl: هزوا، النبيين، الصابئين). Report: `python3 -m checks.farsh
   --report` → build/farsh_check_002.md. The al-Futūḥ check is too noisy over the whole surah
   until it compares with the engine's full readings (needs occurrence tables, milestone 5).

Also open, lower priority: 208 numbering irregularities in the extraction (`mushaf/docs/known-gaps.md`),
the unreproduced pairs listed above, and the alkiraat.com contact message (typed in the form,
not sent).

## Working with Eisa

- For anything judged by eye, send the PDF crop beside the output (side-by-side sheets).
- Before calling something taḥrīr, an omission, or a khulf, check the data first (dropped rows,
  colour-only marks, labels against text, footnotes). Ask only what the data can't answer.
- Never write Qurʾānic text or qirāʾāt facts from memory; every fact cites a page.
