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
| `render.py`, `dot_sheet.py` | preview renderer (HarfBuzz + DigitalKhatt) with the standalone tas-hīl dot |
| `data/place_wujuh.yaml` | wujūh tied to a place, with sources (Ruways at 2:20) |
| `data/profiles.yaml`, `book_profiles.py` | **uṣūl profiles from al-Wāfī and al-Īḍāḥ**: 20 categories × 20 ruwāt, each row with page; `readings --book` uses them |

Book profiles (2026-11-24), `spike/data/profiles.yaml`, 33 categories × 20 ruwāt:

| Test | rows-learned | book table |
| --- | --- | --- |
| learn 2:1–5, predict 2:6–20 | 429 / 518 (83%) | **504 / 518 (97%)** |
| learn 2:1–12, predict 2:13–20 | 255 / 287 (89%) | **285 / 287 (99%)** |
| no training, 2:1–20 | 442 / 666 (Ḥafṣ default) | **651 / 666 (98%)** |

(An earlier version of these numbers was wrong: a local variable in `full_profiles` shadowed the
`book` flag, so every run used the book table. Fixed; the table above is after the fix.)
`python3 -m spike.book_profiles --vs-rows` now shows three disagreements with the rows: Ruways's
idghām at 2:20 (a place entry covers it) and Idrīs's sakt (two categories). The remaining misses
are 2:11 لَّهُمۡ (Hishām, al-Kisāʾī, Ruways), 2:13 قِيلَ (farsh), and Ḥamzah's ruwāt and Idrīs at 2:8
ٱلۡأَخِرِ (naql in waqf, not modelled). The book table generates more waqf forms than the boxes
show (Ḥamzah, Hishām at 2:13 ٱلسُّفَهَآءُۗ and 2:14 مُسۡتَهۡزِءُونَ): one row seems to stand for several
forms through its label ("خمسة القياس"), which the comparison doesn't read yet.

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

1. ~~Pull the books~~, ~~build the profile table~~, ~~read the remaining bābs~~ (done). For it:
   - **Eisa reviews it by category** (page text beside the rows). Questions for him:
     - Idrīs: al-Futūḥ's labels give him sakt (v1 p52 r7, p54 r4, p57 r2) and naql in waqf at 2:8
       ٱلۡأَخِرِ; al-Īḍāḥ pp. 117, 121–123 gives Khalaf al-ʿĀshir neither ("وحقق همز الوقف والسكت
       أهملا") and its editor records a sakt khulf for Idrīs by other ṭuruq. Which does the app follow?
     - Ḥamzah's waqf on مُسۡتَهۡزِءُونَ: al-Wāfī pp. 116, 118 gives tashīl, ibdāl yāʾ (al-Akhfash) and
       ḥadhf (rasm); the box shows two. Which two, and why?
     - Ḥamzah's waqf on ءَأَنذَرۡتَهُمۡ: is the second hamzah "made mid by a prefix" (taḥqīq allowed,
       al-Wāfī pp. 122–123), or only tashīl?
   - Still not in the table (`not_read_yet`): Ḥamzah's naql and sakt in waqf, rawm/ishmām and
     rasm-based takhfīf in detail, the rest of the rāʾāt and lāmāt exceptions.
   - Taqlīl and imālah are written the same; the rows' learned names for them are arbitrary.
   - Word-list imālah (Ḥamzah's verbs, al-Dūrī ʿan al-Kisāʾī's words) and Abū Jaʿfar's ḥadhf of a
     maḍmūmah hamzah after kasr are new detectors in `usul.py`, from al-Wāfī pp. 150–154 and
     al-Īḍāḥ pp. 109–110, 141–144.
2. **Occurrence tables**, now the main gap: the profiles are right, but the spike doesn't know
   which places a category applies to (naql places, word-specific imālah). Build them from Ghayth
   al-Nafʿ's per-place types (`books/ghayth-1.txt`) and the lists in al-Wāfī and al-Īḍāḥ, and
   compare with the detectors (which over-match, e.g. imālah on عَلَىٰ). nQuran.com's per-ayah
   pages are a spot-check source (see `docs/03-usul-sources.md`).
3. **Read al-Futūḥ's footnotes ("تفاصيل المقطع")**: per-word statements with matn verses. They're
   already extracted as `footnote` / `text` records. Parse them into place entries like
   `data/place_wujuh.yaml`.
4. **Constraints** from al-Budūr's per-place prose (e.g. p. 20: badal in ءَامَنَّا and ٱلۡأٓخِرِ must be
   equal), then checked against al-Futūḥ's boxes.
5. **Spike Day 5**: the KFGQPC check for the 8, and `spike/REPORT.md` answering Q1–Q5.

Also open, lower priority: 208 numbering irregularities in the extraction (`mushaf/docs/known-gaps.md`),
the unreproduced pairs listed above, and the alkiraat.com contact message (typed in the form,
not sent).

## Working with Eisa

- For anything judged by eye, send the PDF crop beside the output (side-by-side sheets).
- Before calling something taḥrīr, an omission, or a khulf, check the data first (dropped rows,
  colour-only marks, labels against text, footnotes). Ask only what the data can't answer.
- Never write Qurʾānic text or qirāʾāt facts from memory; every fact cites a page.
