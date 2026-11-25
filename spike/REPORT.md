# Reading-model spike: report

2026-11-24. Passage: al-Fātiḥah and al-Baqarah 1–20, all twenty ruwāt of the Shāṭibiyyah and the
Durrah. The question (docs/02-spike-reading-model.md): can one data format — farsh places, uṣūl
profiles and occurrences, taḥrīr constraints — produce every valid reading of a passage for any
rāwī, checked against books rather than against another app's output?

**Answer: yes.** Q1–Q5 below, each with its evidence. The format needed no special case per
category; what it did need, and what the spike got wrong first, is in "What didn't work" and
"Before building for real".

## Numbers

| Check | Result |
| --- | --- |
| al-Futūḥ rows of 1:1–2:20 reproduced, book profiles, no training rows | **661 / 666** row/rāwī pairs (99%) |
| Predict 2:6–20 (2:13–20) after seeing 2:1–5 (2:1–12) | **513 / 518** (99%), **285 / 287** (99%) |
| All rows of 1:1–2:20, book profiles plus the rows | **674 / 676**; the two left are one farsh entry |
| Same, with profiles learned from the rows instead of the books | 429 / 518 (83%), 255 / 287 (89%) |
| Readings generated that no row of the box gives (full passage) | 3 |
| KFGQPC, eight riwāyāt, whole passage, word by word | **2,047 / 2,056** words (99.6%); Ḥafṣ and Shuʿbah 100% |
| Ḥamzah's and Hishām's waqf forms, al-Futūḥ vols 1–6 | every printed form generated in **806 / 871** rows (93%) |
| al-Budūr's per-rubʿ imālah lists tied to the spine | 171 / 175 |
| Book profile rows reviewed by Eisa | 160 / 160 right |

Commands: `spike/README.md`. Code: ~3,600 lines of Python in `spike/` (more than the "few hundred"
the plan expected; most of it is loading and checking, not the resolver).

## Q1. Does the format express every wajh al-Futūḥ lists?

Yes. Of 676 row/rāwī pairs, two are left, and they are data, not model: the farsh entry for the
ishmām of قِيلَ (2:13, Abū al-Ḥārith and al-Dūrī ʿan al-Kisāʾī) prints a form the entry doesn't
carry yet. Seven others were the print, settled by Eisa on 2026-11-24 with the page beside them:

- 2:8 ٱلۡأٓخِرِ in the sakt rows (Khallād, Idrīs, Khalaf) is printed ٱلۡأَخِرِ: al-Futūḥ's way of
  printing the sakt form. A print convention, applied when comparing (`readings.sakt_print`).
- 2:11 لَّهُمۡ in row 10 (Hishām, al-Kisāʾī; Ruways inherits it): the typesetter carried row 9's
  shadda (al-Sūsī's idghām kabīr). A print error, corrected on load (`data/print_errors.yaml`) and
  logged in `mushaf/docs/known-gaps.md`.

With no training rows, three more pairs miss: Warsh's naql across words (عَذَابٌ أَلِيمٌ, خَلَوۡاْ إِلَىٰ),
whose places still come from the row gate (the occurrence table for naql isn't built).

Earlier "misses" that turned out to be data (dropped rows, imālah marked only by colour, labels read
wrongly) are fixed in the extraction and logged in `mushaf/docs/known-gaps.md`.

## Q2. Do facts that touch the same word compose without special cases?

Yes. Each category is a detector plus a transform; a word with several gets them in turn:
ibdāl and madd on يُؤۡمِنُونَ, naql and badal on ٱلۡأٓخِرَةِ (qaṣr drops the maddah after naql), ṣilah
and munfaṣil (the ṣilah takes the munfaṣil's length), ṣilah undoing idghām into a mīm, imālah and
hamz in the same word, Ḥamzah's waqf on a word with an imālah dot. Two things looked like special
cases and weren't: they were a choice that spans more than one word (the khulf convention for
"الجميع عدا من سيأتي") and a place-tied wajh (Ruways at 2:20), both now data
(`data/place_wujuh.yaml`, Eisa's decisions).

## Q3. Can taḥrīr be data (allowed combinations) rather than code?

Yes: `data/constraints.yaml`, allowed tuples per rāwī over categories, each from a page:
Warsh's tarbīʿ (badal × līn, al-Ḍabbāʿ pp. 201–202), badal × dhawāt al-yāʾ (al-Ḍabbāʿ p. 246,
al-Budūr p. 30), badal × madd ʿāriḍ (al-Budūr pp. 21–22; at 2:8 it gives exactly al-Budūr's six
wujūh), Khallād's sakt × his stop (al-Wāfī p. 106, al-Budūr p. 25), and the two tas-hīls of
هَٰٓؤُلَآءِ (al-Budūr p. 65, inside the waqf chapter). Two findings:

- **Most taḥrīr is about features, not text** (madd lengths, ʿāriḍ, sakt). Constraints only bite
  once those features are choices in generation, as they now are.
- **al-Futūḥ's boxes aren't exhaustive**, so taḥrīr has to come from a taḥrīr source (al-Budūr,
  al-Ḍabbāʿ) and the boxes test it. The "extra readings" the spike first counted (22) were mostly
  the comparison, not missing taḥrīr: a box reads a span one way (stop at a final pause sign or go
  on) and spreads one rāwī's wujūh over rows of different lengths. Counted properly: 3.

Riwāyah-wide constraints work. Place-scoped ones haven't been needed in this passage beyond
place-tied wujūh.

## Q4. How do waqf readings fit?

The stop is an input: at an ayah end, or optionally at a pause sign, and the box shows one of the
two. Waqf has its own chapter for Ḥamzah's ruwāt and Hishām (`waqf.py`, al-Wāfī pp. 105–127 with
al-Budūr's per-place rulings), checked against every waqf form al-Futūḥ prints in six volumes
(93%). Everyone else reads waqf on hamz as waṣl (al-Wāfī p. 99); Khalaf al-ʿĀshir with taḥqīq
(al-Īḍāḥ p. 121).

The KFGQPC check adds one more input: **joining ayahs**. al-Sūsī's ٱلرَّحِيمِ مَّلِكِ (1:3–4) is an
idghām kabīr across an ayah end; the spike always stops at an ayah, so it can't produce it.
Whether to join is a choice of the same kind as the stop.

## Q5. What is one reading?

Text plus features. The text can't show: madd lengths (muttaṣil, munfaṣil, badal, līn, ʿāriḍ),
sakt (on al-, shayʾ, the mafṣūl, the ḥurūf), imālah against taqlīl (one dot for both in al-Futūḥ),
rawm and ishmām at a stop, tarqīq and taghlīẓ, ghunnah. In the spike a reading is a dict of word
id → text plus the choice that made it (category → wajh, including the features), so every word
can be explained by the facts behind it.

## The KFGQPC check

`kfgqpc_check.py` generates each ayah for the eight riwāyāt KFGQPC publishes, aligns its words
with KFGQPC's (their ayah counts and spelling conventions differ), and compares letters, maddahs,
shaddas, imālah marks and tas-hīl dots, taking for each ayah the wajh combination closest to
KFGQPC's single printed reading. 2,047 of 2,056 words agree. KFGQPC's conventions it had to
normalise: sukūn ْ, the waṣl alif اَ۬, no shadda on lām al-shamsiyyah (Warsh, Qālūn), the shadda of
idghām on the next word, ṣād with small sīn for Qunbul's sīn, imālah as U+06EA. What's left:

- ٱلسُّفَهَآءُ أَلَآ (2:13) for six ruwāt: two hamzahs across words. The profile table has the
  category (al-Wāfī pp. 91–97); the spike has no detector for it. A gap.
- الٓمٓ (2:1) for Warsh and Qālūn: how the ḥurūf are written.
- Warsh's وَبِٱلۡأٓخِرَةِ (2:4): KFGQPC prints no maddah after naql; to look at with the badal rules.
- ٱلرَّحِيمِ مَّلِكِ for al-Sūsī (above; hidden once idghām shaddas on a first letter are
  normalised).

## What didn't work

- **Profiles learned from al-Futūḥ's rows.** They can't know categories the passage hasn't shown
  (83% held out). Profiles read from the books' uṣūl chapters (al-Wāfī, al-Īḍāḥ; 35 categories × 20
  ruwāt, every row cited, reviewed by Eisa) reach 98% with no rows at all.
- **The "some row shows a change here" gate** for where a rule applies. It can't leave the
  passage. For imālah it's replaced by the book: al-Budūr's per-rubʿ lists, which show that the
  only words the detector over-matches are the five al-Wāfī excepts by name (pp. 142–143). The
  other categories still use the row gate.
- **Learning conventions from rows.** Eisa's "الجميع عدا من سيأتي" convention is computed from the
  rows; with no rows it doesn't apply. It should be a stated rule.
- **Text-only comparison.** Taqlīl and imālah are one dot; ṣilah and sakt are often only in the
  label. Checks have to compare features too (the spike now checks each row's label features on the
  reading whose text matches).
- **My own bugs that hid results** (a shadowed flag that ran every test with the book profiles; a
  comparison that counted both ways of reading a pause sign). Both found by numbers that didn't
  move when they should have. Every check needs a deliberately broken input that it catches.

## The data format as it ended up

```
books/                      the sources, local, gitignored (MANIFEST.json: URL, size, sha256)
spike/data/profiles.yaml    rāwī × category → wujūh, with cite, cond, place, option, inherited
spike/data/place_wujuh.yaml wujūh tied to a place (Ruways 2:20; Ibn Dhakwān's زَادَ at 2:10)
spike/data/constraints.yaml allowed tuples per rāwī over categories (text and features)
spike/usul.py               detectors and transforms per category (the occurrence rule)
spike/occurrences.py        al-Budūr's per-rubʿ lists tied to the spine (imālah)
spike/waqf.py               Ḥamzah's and Hishām's waqf, by rule
farsh                       still from al-Futūḥ's rows (spike/farsh.py), 11 places in the passage
```

Close to the draft model in docs/02 (words, places, options, profiles, constraints), with three
changes: occurrences are a rule plus a book list, not a hand-made table per place; waqf is its own
module; and options carry `option: true` where the ṭuruq differ (Idrīs's sakt), with the book's
preferred wajh first.

## Before building for real

1. **Build the data layer apart from the spike**, sources first: farsh from al-Budūr and the
   farsh chapters (not from al-Futūḥ's rows), occurrence tables per category from the books' lists
   (al-Budūr's "المدغم" next), profiles as they are. al-Futūḥ, nQuran, alkiraat and KFGQPC become
   checks, never inputs.
2. **Make every input a choice**: the stop, joining ayahs, and the features, so constraints can
   bind them. Defaults are the book's first wajh (open decision 1 in docs/02).
3. **Add what the checks found missing**: two hamzahs across words, al-Kisāʾī's hāʾ al-taʾnīth at a
   stop, word-specific imālah beyond the passage, rasm-based waqf beyond the listed words, idghām
   kabīr across ayahs.
4. **Keep it ṭarīq-aware** for the kubrā version: every row says which ṭarīq it is from; ikhtilāf
   is an option, not a deletion.
5. **Keep the review loop**: a sheet with the page beside each row, Eisa's marks back as data.
6. **Settle the encoding once** (tas-hīl dot, imālah dot, KFGQPC and al-Futūḥ conventions) in one
   module, with the side-by-side sheets for anything visual.

## Open decisions (docs/02), where they stand

1. Default wajh: the book's first; Idrīs's sakt shows the pattern for ikhtilāf (an option).
2. Taḥrīr source beyond al-Budūr: al-Ḍabbāʿ for the Shāṭibiyyah is now local and cited;
   al-Jīqarawī (alkiraat) as a check. Still open for the Durrah.
3. Istiʿādhah / basmalah wujūh: not modelled yet.
4. The twelve riwāyāt KFGQPC doesn't publish: the books decide (al-Wāfī, al-Īḍāḥ, al-Budūr);
   alkiraat and nQuran check; Eisa settles what they can't.
