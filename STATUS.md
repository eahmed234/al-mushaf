# Status and next steps

Last updated 2026-11-24, before a context compaction. Read this first in a new session, then
`docs/02-spike-reading-model.md` (the spike plan with day-by-day results) and
`docs/03-usul-sources.md` (uṣūl books).

## Where things are

Two local git repos (no remotes, nothing pushed):

- **`~/Projects/al-mushaf`** (this repo). Docs, and the reading-model spike in `spike/`
  (Python 3.12 + PyYAML; commands in `spike/README.md`).
- **`~/Projects/mushaf`**: the al-Futūḥ al-Bāhira extractor (uv). `./rebuild.sh` rebuilds all six
  volumes in about 2.5 min; outputs go to `out/vol{1..6}.jsonl` (not tracked). `docs/known-gaps.md`
  logs every fix and open gap.
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

Current numbers: **655 / 676** row/rāwī pairs of 2:1–20 reproduced; held-out **83%** (learn 2:1–5,
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
- Profiles learned from rows don't generalise to unseen categories. They should come from the
  books' uṣūl chapters, which is the next step.

## Next steps, in order

1. **Pull the uṣūl books into a local folder** instead of querying Aljam3 each time.
   - Put them in `~/Projects/al-mushaf/books/` (gitignored: book text is not tracked) with a
     `books/MANIFEST.json` of source URL + sha256.
   - Use the typed TXT files (DOCX as fallback), from the Hugging Face datasets Aljam3 links to
     (`get_book` gives `download_urls`); keep the PDF for checking OCR.
   - Books (Aljam3 id / file id): al-Budūr 3480 / 8362 (typed; scans 4983 / 12844 and 16689);
     al-Wāfī 1037 / 2153; al-Īḍāḥ li-Matn al-Durrah 16501 / 36683; Ghayth al-Nafʿ 1045 / 2164
     (+ second file); al-Ḍabbāʿ's Sharḥ Itḥāf al-Bariyyah 16390; al-Buḥūr al-Zākhira 16670.
   - Ask Eisa before downloading (file names and sizes), per the session rules.
2. **Build the profile tables from the books.**
   - `corpus/`-style data: one row per (rāwī or qāriʾ, category, wajh), with conditions, a
     citation (book, page), and status `candidate`.
   - Sources: al-Wāfī's uṣūl chapters for the seven, al-Īḍāḥ for the three; the madd tables already
     come from al-Futūḥ vol. 1 pp. 52–53.
   - Extract from each bāb's text, never from memory. Each row is checked against its page, and
     Eisa reviews by category, with the page text beside the rows.
   - Then switch `readings.py` to use book profiles (rows stay as a check) and rerun the held-out
     test, which should improve the most.
3. **Read al-Futūḥ's footnotes ("تفاصيل المقطع")**: per-word statements with matn verses. They're
   already extracted as `footnote` / `text` records. Parse them into place entries like
   `data/place_wujuh.yaml`.
4. **Occurrence tables** from Ghayth al-Nafʿ's per-place types, compared with the detectors (which
   over-match, e.g. imālah on عَلَىٰ).
5. **Constraints** from al-Budūr's per-place prose (e.g. p. 20: badal in ءَامَنَّا and ٱلۡأٓخِرِ must be
   equal), then checked against al-Futūḥ's boxes.
6. **Spike Day 5**: the KFGQPC check for the 8, and `spike/REPORT.md` answering Q1–Q5.

Also open, lower priority: 208 numbering irregularities in the extraction (`mushaf/docs/known-gaps.md`),
21 unreproduced pairs (word-specific imālah of شَآءَ and ءَاذَانِهِم, Ḥamzah's waqf ٱلۡأَخِرِ,
Hishām and al-Kisāʾī's لَّهُمۡ at 2:11), and the alkiraat.com contact message (typed in the form,
not sent).

## Working with Eisa

- For anything judged by eye, send the PDF crop beside the output (side-by-side sheets).
- Before calling something taḥrīr, an omission, or a khulf, check the data first (dropped rows,
  colour-only marks, labels against text, footnotes). Ask only what the data can't answer.
- Never write Qurʾānic text or qirāʾāt facts from memory; every fact cites a page.
