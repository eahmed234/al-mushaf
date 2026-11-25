# Status and next steps

Last updated 2026-11-24 (after the books were pulled and the profile table built). Read this first in a new session, then
`docs/02-spike-reading-model.md` (the spike plan with day-by-day results) and
`docs/03-usul-sources.md` (uṣūl books).

## Where things are

Two local git repos (no remotes, nothing pushed):

- **`~/Projects/al-mushaf`** (this repo). Docs, and the reading-model spike in `spike/`
  (Python 3.12 + PyYAML; commands in `spike/README.md`).
- **`~/Projects/mushaf`**: the al-Futūḥ al-Bāhira extractor (uv). `./rebuild.sh` rebuilds all six
  volumes in about 2.5 min; outputs go to `out/vol{1..6}.jsonl` (not tracked). `docs/known-gaps.md`
  logs every fix and open gap.
- **`books/`** (gitignored): the uṣūl books as TXT + PDF, fetched by `tools/fetch_books.py` from
  `tools/books.tsv`; `books/MANIFEST.json` has URL, size, sha256. `python3 tools/book.py SLUG PAGE`
  prints a page, `-s REGEX` searches (diacritics folded), `--pdf PAGE OUT.png` renders one. TXT
  page n = PDF page n = Aljam3 page n = printed page (al-Wāfī, al-Īḍāḥ).
- `~/Projects/mushaflab` is the old project, now only a source of inputs: the Ḥafṣ spine
  (`data/spine/hafs/v1/items.jsonl`), fonts, and KFGQPC texts.

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
| `data/place_wujuh.yaml` | wujūh tied to a place, with sources (Ruways at 2:20; Ibn Dhakwān's زَادَ, farsh) |
| `data/constraints.yaml` | taḥrīr as allowed tuples, from the books (Warsh: badal × līn, badal × dhawāt al-yāʾ); `readings` filters combinations by it |
| `data/profiles.yaml`, `book_profiles.py` | **uṣūl profiles from al-Wāfī and al-Īḍāḥ** (checked against al-Budūr, Ghayth al-Nafʿ, nQuran where they disagreed): 33 categories × 20 ruwāt, each row with page; `readings --book` uses them |

Book profiles (2026-11-24), `spike/data/profiles.yaml`, 34 categories × 20 ruwāt (reviewed by Eisa):

| Test | rows-learned | book table |
| --- | --- | --- |
| learn 2:1–5, predict 2:6–20 | 429 / 518 (83%) | **506 / 518 (98%)** |
| learn 2:1–12, predict 2:13–20 | 255 / 287 (89%) | **285 / 287 (99%)** |
| no training, 2:1–20 | 442 / 666 (Ḥafṣ default) | **654 / 666 (98%)** |

(An earlier version of these numbers was wrong: a local variable in `full_profiles` shadowed the
`book` flag, so every run used the book table. Fixed; the table above is after the fix.)
`python3 -m spike.book_profiles --vs-rows` now shows one disagreement with the rows: Ruways's
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
- Glyph 135 is the tas-hīl dot; glyph 383 is lām-alif with maddah; #76923c is the imālah green.

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

## Next steps, in order

1. ~~Pull the books~~, ~~build the profile table~~, ~~read the remaining bābs~~, ~~Eisa's review~~
   (all 160 rows right, 2026-11-24; notes applied: Warsh's tarbīʿ and badal × dhawāt al-yāʾ in
   `spike/data/constraints.yaml`, dhawāt al-rāʾ split out as `imala_ya_ra`, Ibn Dhakwān's زَادَ as
   farsh). New rows since the review (`imala_ya_ra`) are candidates.
   - Idrīs's sakt is an option (ikhtilāf; default none). A kubrā version comes later.
   - **Waqf of Ḥamzah and Hishām: its own chapter, `spike/waqf.py`** (2026-11-24). Every form a
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
2. **Occurrence tables** (started 2026-11-24, imālah done). `spike/occurrences.py` reads al-Budūr's
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
5. ~~**Spike Day 5**~~ (done 2026-11-24): `spike/kfgqpc_check.py` (eight riwāyāt, 2,047 / 2,056
   words agree) and **`spike/REPORT.md`**, answering Q1–Q5 with the numbers, what didn't work,
   the format as it ended up, and what to change before building for real. The spike is closed;
   next is the data layer as its own thing (REPORT.md, "Before building for real").

Also open, lower priority: 208 numbering irregularities in the extraction (`mushaf/docs/known-gaps.md`),
the unreproduced pairs listed above, and the alkiraat.com contact message (typed in the form,
not sent).

## Working with Eisa

- For anything judged by eye, send the PDF crop beside the output (side-by-side sheets).
- Before calling something taḥrīr, an omission, or a khulf, check the data first (dropped rows,
  colour-only marks, labels against text, footnotes). Ask only what the data can't answer.
- Never write Qurʾānic text or qirāʾāt facts from memory; every fact cites a page.
