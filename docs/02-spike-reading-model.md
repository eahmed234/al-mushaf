# Spike: can a reading be data?

Draft, 2026-11-24. Timebox: **5 working days**. Throwaway code; the data format and the list of
hard cases are what we keep.

## The question

Can farsh, uṣūl, wujūh and taḥrīr be written as plain data so that a small resolver turns
*(rāwī, choices, stopping points)* into exactly one valid reading, for all 20 ruwāt, and refuses
any combination the books do not allow?

Sub-questions the spike must answer, each with a yes/no and evidence:

| # | Question |
| --- | --- |
| Q1 | Does the format express every wajh al-Futūḥ lists for the passage, for every rāwī? |
| Q2 | When two facts touch the same word (e.g. ibdāl and madd on يؤمنون), do they compose without special cases? |
| Q3 | Can taḥrīr be expressed as constraints (allowed combinations) rather than code? Both kinds: riwāyah-wide (badal × dhawāt al-yāʾ) and local (a few neighbouring words)? |
| Q4 | How do waqf-dependent readings (Ḥamzah on hamz, rawm/ishmām, Hishām) fit: is the stop part of the input? |
| Q5 | What does "one reading" contain? Visible text alone can't distinguish tawassuṭ from ishbāʿ, so the output needs text **plus** pronunciation features. What exactly? |

If Q1–Q3 are yes, we build on the format. If any is no, we have found the flaw in a week instead
of a month.

## The passage: al-Fātiḥah and al-Baqarah 1–20

Chosen because the inputs already exist and it is dense with khilāf:

- **al-Futūḥ already extracted:** 202 table rows anchored in this range (`../mushaf/out/vol1.jsonl`,
  pdf pp. 47–63); 187 with readers fully resolved to the 20 ruwāt, 13 bounded, 2 contextual.
- **Colour classes present** (counted from those rows): farsh 95, ṣilat mīm al-jamʿ 66, waqf 28,
  madd al-badal / līn 21, ibdāl 14, idghām / taghlīẓ 12, tarqīq al-rāʾ 12, imālah / taqlīl 8,
  ṣilat hāʾ al-kināyah 3.
- **Hard cases visible in the rows themselves** (labels quoted from al-Futūḥ via the extraction):
  - 2:3, `v1-p051-r8`: ṣilah for Qālūn with Ibn Kathīr; Warsh *بالإبدال وتغليظ اللام*; al-Sūsī
    with tarqīq; Abū Jaʿfar with ṣilah.
  - 2:4, `v1-p052-r3`: qaṣr / tawassuṭ / ishbāʿ groups for the munfaṣil; Idrīs *بالسكت على «أل»*;
    Ḥamzah *بالإشباع والسكت على «أل»* with Khallād *بالتحقيق*; Warsh *والنقل مع ثلاثة البدل*.
  - p. 47: the istiʿādhah / basmalah wujūh (cutting and joining), which are wujūh of the
    recitation rather than of any word.
- **KFGQPC check data:** mushaflab's M0.6 already classified all 290 Warsh–Ḥafṣ differences in this
  range (`../mushaflab/docs/review/m0/warsh-residuals.md`). The same can be done for the other 7.
- Durrah ruwāt (Abū Jaʿfar, Yaʿqūb, Khalaf al-ʿĀshir) appear in the rows, so all 20 are exercised.

Any statement above about *what a rāwī reads* is a pointer to a row, not a fact we assert. The
spike reads the rows; nobody types readings.

### State of the al-Futūḥ extraction in this range

From `../mushaf/out/vol1.jsonl`, 2026-11-24:

- 1,307 Qurʾānic words: 1,104 match Ḥafṣ, 111 match a KFGQPC riwāyah, **69 `unattested`**
  (a reading of the 12, or an extraction error) and **23 `unaligned`**.
- **97 of the 202 rows are elided** ("…"), with only the changed tail quoted. They have not
  been rebuilt into full readings yet.
- The labels are prose (*بالإشباع والإبدال، والنقل مع ثلاثة البدل*), not structured tags.
- The `mushaf` folder is **not under git**.

### Day 0 result (2026-11-24)

`../mushaf` is in git, with the PDFs and fonts pinned by hash in `SOURCES.md`. I (Claude)
checked all 92 flagged words against crops of the print. These verdicts are a vision model's,
not a person's.

| Class | Words | Meaning for the spike |
| --- | --- | --- |
| Faithful reading (one of the 12, or a waqf form) | 49 | Usable as is |
| Istiʿādhah (not Qurʾān) | 20 | Exclude from word alignment; it is input for the istiʿādhah wujūh |
| Encoding only (U+0622; U+0670 for the alif of idkhāl) | 8 | Normalise at ingest |
| Quote-boundary forms (shaddah of idghām dropped where a quote starts) | 2 | The resolver must know a quote's first word can differ |
| **Errors** | **13** | 8 × glyph 135 (large round dot, 775 words book-wide), 2 × lām-alif-maddah ligature, 1 lost fatḥah, 1 two-word join, 1 failed anchor |

Fixes for the errors are in `../mushaf/out/review/spike-1-1_2-20/verdicts.json`. The one
decision left is which codepoint glyph 135 should get. Mapping it once fixes all 775 words.

### Day 1 result (2026-11-24)

`python3 -m spike.rows` loads the passage in under a second. It rebuilds all 202 rows
(97 of them "…" rows) as full readings in one internal encoding (`spike/text.py`), and
every row has its readers. Things the data showed that the model must handle:

- **Complete rows and "…" rows behave differently.** A row without "…" is a complete
  statement, and words it leaves out are absent: Warsh and the others who join or pause
  between the surahs have no basmalah (p. 50, rows 7–8). A "…" row repeats the row above it
  and changes only what it quotes.
- **Sub-segments.** One box can restart its numbering at 1. Fixing this upstream gave readers
  back to 1,294 rows book-wide.
- **The basmalah between surahs** is an item of its own (`B:2:1–4`), not a word of either
  surah.
- **Alternatives inside one row**: "A * B * C" means the same rāwī may read any of them (Ḥamzah's
  and Hishām's waqf on hamz, 2:13 and 2:14). Two of Ḥamzah's five forms of ٱلسُّفَهَآءُ are
  the same text that differs only in madd length, which is direct evidence for Q5.
- **Quote boundaries**: a quote that starts mid-ayah drops the shaddah of idghām on its first
  word (2:17, 2:19). The rebuild keeps the context's form there.
- **Risk to test on Day 5:** a "…" row inherits the *text* of the row above, which may belong
  to another qāriʾ (Ḥamzah after Warsh at 2:17). That holds only if the book always quotes every
  word where the two differ. The KFGQPC check will show whether it does.

### Day 2 result (2026-11-24)

`python3 -m spike.farsh --show` finds **11 farsh places** with 22 variants in 1:1–2:20, and gives
each rāwī's farsh-only text. **All 220 rāwī/place pairs are settled**, 14 of them by
elimination. al-Baqarah 1–5 has no farsh at all, so the check ran on the whole passage.

- **al-Futūḥ's colours can't find farsh.** Its red (#ff0000) also marks madd length (7,138 of
  21,706 red runs book-wide cover only madd marks), ṣilah, and Ḥamzah's waqf forms. The book is
  organised by place, and its red means "this differs here".
- **Farsh is found from the letters instead** (`spike/diff.py`). Rules remove the uṣūl kinds
  (madd, ṣilah, imālah, idghām, hamz, and a pausal final vowel); whatever is left is farsh.
  On this passage the residue is exactly مَلِكِ, the sīn in (ٱل)صِّرَٰطَ, عَلَيۡهُمۡ, يُخَٰدِعُونَ,
  يُكَذِّبُونَ and the ishmām of قِيلَ. This is the first evidence for Q2: the uṣūl were
  recognisable by rule.
- **Some differences are invisible in the text.** Ishmām of the ṣād in صِرَٰطَ (1:7, Khalaf's
  row) prints the same letters as pure ṣād; only the colour and the label "بالإشمام" show it.
  Readings therefore need features taken from the row labels, not only from text (Q5).
- **What "2:8:11 missing fatḥah" really was:** a pausal form. The quote stops there, and
  pausal final vowels recur (قِيل, لَذَهَب, ٱلرَّحِيم).
- **Two more reader bugs fixed upstream:** "أصحاب الصلة عدا قنبل" ignored its exception
  (6 rows book-wide).
- **Decided:** a bare "خلف" in al-Futūḥ is Khalaf ʿan Ḥamzah (Eisa). That settled the last
  24 pairs. Khalaf's ishmām of the ṣād is still missing from his farsh-only text, because
  the text doesn't show it (see above).

### Day 3 result (2026-11-24)

`python3 -m spike.readings --show` builds each rāwī's uṣūl profile and checks it against every
row of al-Baqarah 1–5. **All 139 row/rāwī pairs are reproduced**: the text by the uṣūl rules,
the features by the labels.

- **Rules** (`spike/usul.py`): detectors over the Ḥafṣ text and transforms for each text-changing
  category: munfaṣil (qaṣr drops the maddah), ṣilat al-mīm (separately before a hamza), ṣilat
  al-hāʾ, ibdāl of a sākin hamza, naql on the article (keeping the badal maddah), idghām kabīr,
  and sakt on the separate letters. Categories the text can't show are features: muttaṣil,
  badal, sakt on «أل» and on the mafṣūl, tarqīq of rāʾ, taghlīẓ of lām, ghunnah.
- **Profiles** come from three sources, each kept with the profile:
  - text wujūh are learned from the rows that reproduce them (row ids);
  - munfaṣil and muttaṣil lengths come from al-Futūḥ's own tables (vol. 1 pp. 52–53);
  - other features come from the labels, read with a small vocabulary (كالسابق inherits the
    row above's features).
- **Composition worked without special cases.** ṣilah before a hamza takes the munfaṣil's
  maddah unless it's qaṣr (عَلَيۡهِمُۥٓ), naql keeps the badal maddah (وَبِٱلَآخِرَةِ), and idghām
  kabīr changes two words.
- **Labels depend on context.** A bare "الإشباع" means the madd the row's text contains, and after
  "عدا" it is an exception.
- **The text-only comparison was too forgiving at first.** Ibdāl and the sakt sign (U+06DC) were
  being treated as style, so `diff.py` now flags a hamza on one side only, and U+06DC as sakt.
- **Over-generation: 3 readings** for Qālūn and al-Dūrī that combine munfaṣil and mīm wujūh
  in ways no row shows. Day 4 checks whether taḥrīr constraints remove exactly these.
- **Upstream fixes:** anchoring ties now move forward (251 rows re-anchored, e.g. Āl ʿImrān's
  الٓمٓ was taken as 2:1); "أبا جعفر" is recognised.

Caveat: the text wujūh were learned from these same rows, so for them this checks that the
rules compose, not that they generalise. Day 4 tests that: learn from 2:1–5, predict 2:6–20.

### Day 4 result (2026-11-24)

| Check | Result |
| --- | --- |
| Learn on 2:1–20, reproduce every row of 2:1–20 | **627 / 651** row/rāwī pairs (96%), 0 conflicts with the book's madd tables |
| Learn on 2:1–5, predict 2:6–20 | **417 / 503** (83%) |
| Learn on 2:1–12, predict 2:13–20 | **232 / 272** (85%) |
| Readings the profiles allow that no box shows | 50, listed for review (`python3 -m spike.review`) |

On held-out ayahs, the misses are mostly categories the training ayahs never show (imālah
starts at 2:7). A profile stated in the book, like the madd tables, would close that gap. A
profile learned from a few rows can't.

What the model needed, beyond Day 3:
- **New rules:**
  - two hamzas in a word (tas-hīl, idkhāl, ibdāl);
  - idghām without ghunnah;
  - imālah before a final rāʾ, of ٱلنَّاسِ, of كَٰفِرِينَ, and of a final yāʾ;
  - naql across words (Warsh's اَلِيمُۢ, اِلَىٰ);
  - badal qaṣr where it shows (ٱلَاخِرِ).
- **Interactions:**
  - ṣilah takes its madd from the munfaṣil choice even with no munfaṣil in the span;
  - ṣilah undoes the idghām into a following mīm (قُلُوبِهِمُۥ مَرَضٞ);
  - the bare mīm before bāʾ is mīm al-jamʿ too.
- **Q4, waqf.** The stop is an input. Waqf changes hamz categories (`<cat>_waqf`,
  `hamz_waqf_final`, `hamz_waqf_mid`), and Ḥamzah's five qiyās forms of ٱلسُّفَهَآءُ come
  out as one rāwī's alternatives. In the book's convention, only a quote ending an ayah is a
  stop: a quote ending on a pause sign still shows the waṣl form (سَمۡعِهِمُۥۖ).
- **Evidence:** al-Futūḥ doesn't state every uṣūl in every box (2:15 has no ṣilah row), so a
  row is evidence only for words its box colours, in the category's own colour where it has one.
- **Choices that are one variable:** Qālūn's ṣilah before a hamza and elsewhere always go
  together.
- **Occurrences** must be reviewed: detector candidates the book never reads differently (imālah
  on عَلَىٰ, إِلَىٰ) are dropped. In the real model this is the occurrence table.
- **Reader resolution:** madd-group rows ("أصحاب التوسط") now take their readers from the book's
  tables, which adds 54 row/rāwī pairs.
- **Upstream:** the reader parser takes a row's farsh into account when learning.

**Q3, constraints.** The mechanism is simple: allowed tuples per rāwī, scoped to a place or to
the whole riwāyah. But **al-Futūḥ alone can't supply the tuples.** Its boxes aren't exhaustive:
Qālūn's munfaṣil × ṣilah combinations shown at 2:6 and at 2:12 contradict each other. Each
combination a box leaves out is either forbidden or omitted, and only a taḥrīr source can say
which. The 50 such cases are in `spike/build/review.md`. One looks like real taḥrīr: al-Dūrī
at 2:7 shows qaṣr with fatḥ and tawassuṭ with imālah of أَبۡصَٰرِهِمۡ, never crossed.

**Still unexplained (24 pairs):** imālah that is specific to a word (شَآءَ, ءَاذَانِهِم) needs
the book's occurrence lists. Ḥamzah's waqf form ٱلۡأَخِرِ, and Hishām and al-Kisāʾī's لَّهُمۡ
at 2:11, need a look at the print.

### A second source: al-Jīqarawī on alkiraat.com

alkiraat.com has al-Jīqarawī's *al-Wujūhāt al-Qurʾāniyyah – al-ʿAsharah* (Shāṭibiyyah and
Durrah, one ṭarīq per rāwī) fully digitized. It is split into maqāṭiʿ, each with numbered wujūh,
readers as rumūz, and a ḥukm class on each word. For 2:4 it gives 7 wujūh of the munfaṣil and
the hamz. It complements al-Futūḥ: structured labels, but Ḥafṣ text only. Its data is "all
rights reserved", so in the spike we **look it up by hand** for disagreements and do not bulk
download it. We ask them before any wider use.

## Rules for the spike

1. **No Qurʾānic text or qirāʾāt from memory.** Base text comes from the pinned KFGQPC Ḥafṣ
   (via mushaflab's spine). Variant text comes from al-Futūḥ rows, stored as **references**
   (`row id + word index`), resolved when the spike runs. Every fact carries a `source`.
   Anything unsourced is `hypothesis` and can't be used as a passing test.
2. **No rendering, fonts, layout, database, UI or performance work.** Output is Unicode text in a
   terminal plus a features list.
3. **One internal encoding.** Normalize sources at ingest (reuse mushaflab's
   `codepoint_classes.tsv` and the M0.6 convention classes). Never diff raw codepoints across
   sources.
4. Python + `uv`, plain YAML/TSV files, no framework. It reads `../mushaf/out/vol1.jsonl` and
   mushaflab's pinned KFGQPC texts in place; nothing from the books is copied into this repo.

## Draft data model

The spike's job is to break this, not to polish it.

```
words         surah:ayah:word → Ḥafṣ text           (imported, never edited)
places        a khilāf place: one or more word ids, a kind (farsh | an uṣūl category)
options       per place: the alternatives, each = an edit to letter features + pron. features
profiles      per rāwī: one variable per uṣūl category, with its domain (the wujūh) and source
constraints   allowed tuples over variables: riwāyah-wide, or scoped to a list of places
```

Sketch (placeholders; real values only from sources):

```yaml
# places/farsh.yaml
- id: farsh/1:4:1
  words: [1:4:1]
  options:
    - id: a
      text: {ref: hafs}
      ruwat: {ref: futuh/v1-p048-r2}
    - id: b
      text: {ref: futuh/v1-p048-r3, word: 0}
      ruwat: {ref: futuh/v1-p048-r3}        # resolved reader list, with khulf if any

# usul/badal.tsv  — one row per occurrence, found by a detector, then reviewed
# place_id      word     letter   source
# badal/2:4:x   2:4:x    ...      detector v0 + futuh/v1-p052-r3

# profiles/warsh.yaml
variables:
  badal:     {domain: [qasr, tawassut, tul], source: ...}
  dhawat_ya: {domain: [fath, taqlil],        source: ...}
constraints:
  - id: warsh/badal×dhawat_ya
    scope: riwayah                           # or: places: [...]
    vars: [badal, dhawat_ya]
    allowed: [...]                           # tuples from al-Budūr; mushaflab cites p. 232
    source: ...
```

Resolver, three functions:

```
resolve(passage, rawi, choices, stops) → Reading | Refusal(reason, sources)
enumerate(passage, rawi, stops)        → [Reading]        # every valid reading
explain(word_id, reading)              → [fact + source]  # why this word looks like this
```

A **Reading** is, per word: the text (in the internal encoding) and a list of pronunciation
features that the text can't show (madd length in counts, sakt, imālah degree, rawm/ishmām,
ṣilah…). Choices left unset take the profile's default, which is the first wajh al-Futūḥ lists
unless Yusuf decides otherwise.

## Tests (the oracle)

| Test | What passes |
| --- | --- |
| **al-Futūḥ coverage** | Every row in the range maps to at least one Reading for each rāwī it names. Rows the model can't express are listed, never skipped. |
| **al-Futūḥ exactness** | For each segment and rāwī, `enumerate` gives the same set of visible texts as the rows naming that rāwī (elided rows rebuilt from the previous row). Differences are classified: model gap, extraction error, or al-Futūḥ ambiguity. |
| **Refusal** | Every tuple not in a constraint's `allowed` list is refused, with the source. |
| **KFGQPC** | For the 8, with choices set to KFGQPC's wajh, the visible text equals KFGQPC after the encoding-convention table. Residuals classified as in mushaflab M0.6. |
| **Composition** | A listed set of words where two or more facts apply gives the same result in any application order. |
| **Second source** | For segments where `enumerate` and al-Futūḥ disagree, or where al-Futūḥ's readers are only bounded, compare with al-Jīqarawī's wujūh for that maqṭaʿ (by hand) and record the result. |

## Plan

| Day | Work | Done when |
| --- | --- | --- |
| 0 | Put `../mushaf` under git as it stands. Review the 92 `unattested` / `unaligned` words in range against the page images (the review sheets exist). | Every word in range is either verified or listed as an extraction error |
| 1 | Loader for the Ḥafṣ words and al-Futūḥ rows in range; rebuild elided rows; normalize encoding | Every row prints as full text with its 20-rāwī list |
| 2 | Farsh places and options from the rows; resolver for farsh only | Farsh-only readings of 2:1–5 for all 20 |
| 3 | Uṣūl: categories that occur (ṣilat al-mīm, munfaṣil, badal, ibdāl, sakt, naql, imālah, rāʾ/lām), profiles, detectors | 2:1–5 complete for all 20 |
| 4 | Constraints and waqf; extend to the whole passage | Coverage and refusal tests run on 1:1–2:20 |
| 5 | KFGQPC check, composition test, write the report | `spike/REPORT.md` answers Q1–Q5 |

**Stop early** if by day 3 the farsh-plus-uṣūl format needs a special case per category: that is
the answer to Q2 and the report should say so.

## Deliverables

- `spike/` with the data, the resolver (a few hundred lines) and the tests.
- `spike/REPORT.md`: Q1–Q5 with evidence; every al-Futūḥ row the model couldn't express;
  the data format as it ended up; what to change before building for real.

## Open decisions

1. **Default wajh:** the first one al-Futūḥ lists, or another rule?
2. **Taḥrīr source** for combinations al-Budūr doesn't state. al-Jīqarawī (from *Daftar Qawāʿid
   al-ʿAsharah*) is now a candidate.
3. **Istiʿādhah / basmalah wujūh:** in the model now, or later?
4. **Disagreements on the 12 riwāyāt KFGQPC doesn't publish:** settled by al-Jīqarawī, by
   al-Budūr, or by asking a teacher?
