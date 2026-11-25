# Extraction pilot: al-Budūr pp. 16–25

2026-11-25. Milestone 1 of docs/05: which model reads book pages into rows well enough, at what
cost, with the review sheet for Eisa to approve.

## Set-up

- **Pages**: al-Budūr al-Zāhirah pp. 16–25, the first rubʿ (1:7–2:25), packed with the Ḥafṣ words
  of the quarter (`pipeline.pack`). p. 15 is the worked example in the instructions, not scored.
- **Gold set**: read by Claude (Opus) from the pages, checked by the validator, stored as offsets
  (`pipeline/gold/budur/`); **reviewed by Eisa on 2026-11-25** (v3: 196 rows, 519 rāwī-units).
- **Runs**: one Claude Code subagent per model, the same instructions (`prompt.md`), all ten pages,
  then the validator once to fix rejected quotes.
- **Score** (`pipeline.score`): per rāwī at a place: category (or kind), khulf, and which reading
  (an overlapping quote or the same reader group). Rows about words outside the passage are
  counted apart.

## Results

| Run | Instructions | Rows | Rejected | Recall | Precision | Ignoring category | Tokens | Time |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Haiku 5.5 | v1 | 143 | 0 | 87.2% | 79.6% | 96.5% | ~210k | 7.4 min |
| Sonnet 5.5 | v1 | 166 | 2 | 94.8% | 93.4% | 99.4% | ~131k | 4.7 min |
| Sonnet 5.5 | v2 | 191 | 0 | **96.9%** | **95.8%** | 99.0% | ~135k | 4.4 min |

v1 → v2: the conventions the first round showed were open (general rules aren't rows; a waqf
wajh that is another rule takes that rule's category; rawm/sukūn combinations are wujūh, not
taḥrīr; "جميع القراء" is ittifāq; quotes unique on the page), applied to the gold set as well.

## What's left between Sonnet v2 and the gold set

- **Model errors (about 6 units)**: ṣilah before a hamzah at عليهم ءأنذرتهم labelled silah_mim
  instead of silah_mim_hamza (5); Khallād's taḥqīq at أنذرتهم أم left out (1).
- **Judgement calls (about 9 units)**: Hishām's "لا شيء فيه" at بناء (final or middle hamzah);
  whether a reference ("ما في السفهاء من الأوجه") takes the category it points to; Khallād's
  "التحقيق بلا سكت" at a stop; Ḥamzah's five wujūh at السفهاء as uṣūl or taḥrīr.
- **Rows the gold leaves out (32 units)**: words outside the passage (شيء in other cases, the
  example عليكم أنفسكم), and the munfaṣil × muttaṣil combinations on pp. 18–19. These are faithful
  to the page; whether they belong in the data is Eisa's call (the madd combinations are taḥrīr).

## Findings

- **Haiku is out**: lower on every measure and more tokens (it made 29 tool calls to Sonnet's 9).
- **Sonnet is right on who reads what 99% of the time**; nearly all disagreement is category and
  convention. Clear instructions moved it more than a bigger model would have to.
- **The 98% bar can't be judged against an unreviewed gold**: the gold set is one reading, and
  about half of the gap is in calls the gold made, not the model. Eisa's review of the 59 rows
  where they differ settles both.
- **Cost**: about 13k tokens a page, the instructions included. At that rate al-Budūr's ~330
  remaining pages are ~4.5M tokens and the ~1,400 pages docs/05 lists ~18M, on the plan's limits.
  Larger chunks per subagent should lower it (the instructions are read once a chunk).
- **The planted errors and the first round found real bugs**: a quote found twice on a page was
  silently tied to the first place (now rejected); scoring whole rows punished splitting a
  statement (now per rāwī); scoring per rāwī alone couldn't tell which reading (now by quote or
  reader group).

## To review

`PYTHONPATH=.:../mushaf ../mushaf/.venv/bin/python -m pipeline.sheet pipeline/out/sonnet-v2/budur --against pipeline/gold/budur`
→ `build/extract_review.html`. Tick "differences only" for the 59 rows to judge: 45 only in the
run, 14 only in the gold set.

## Eisa's review (2026-11-25)

59 rows marked (`pipeline/reviews/budur-16-25-sonnet-v2.json`): 46 ✓, 13 ✗. Applied to the gold
set (v3) and the instructions (v3):

- **General rules and words elsewhere are rows** (✓ on Sonnet's p. 16 rows and the munfaṣil ×
  muttaṣil combinations, pp. 18–19), reversing my v2 convention.
- **References and "leaving a rule" take the rule's category**: "ما فى لفظ الآخر لخلف وخلاد" is
  the mafṣūl khāṣ (sakt_al); "تركه" at عذاب أليم the mafṣūl ʿām (sakt_mafsul).
- **The five wujūh at السفهاء are uṣūl, not taḥrīr**, and tas-hīl with madd splits by rāwī:
  tawassuṭ for Hishām, ṭūl for Ḥamzah (p. 22).
- **At a stop on fatḥ tanwīn the stop is on the alif**: شيئا has no "with sukūn" wujūh, and
  بناءً's hamzah is middle (hamz_waqf_mid), not final.
- **The sheet's labels for the waqf categories were too narrow** ("after an alif", "after a
  mutaḥarrik"); widened in the sheet and noted in data/profiles.yaml.
- **Madd lengths are three** (qaṣr 1, tawassuṭ 2, ṭūl 3 alifs; al-Shāṭibī's way, p. 18); the
  four-degree way with its fractions waits for the kubrā version (data/constraints.yaml,
  madd_degrees).

Sonnet v2 against the reviewed gold: **96.3% recall, 95.6% precision** per rāwī. What's left is
mostly the conventions above (the run predates them) and the errors Eisa marked (silah_mim at
عليهم ءأنذرتهم; Hishām's بناء as a final hamzah) plus two omissions (Khallād's taḥqīq at أنذرتهم
أم, Warsh's qaṣr at 2:8). A run on the v3 instructions measures the bar.

## Run 3: Sonnet on the v3 instructions (2026-11-25)

236 rows, 0 rejected, ~164k tokens, 7.6 min. Against the reviewed gold set: **95.4% recall, 96.7%
precision** per rāwī. By kind of row (rāwī-units found / in the gold set):

| Run | farsh | uṣūl | taḥrīr | ittifāq |
| --- | --- | --- | --- | --- |
| Haiku v1 | 100/100 | 248/314 | 2/25 | 80/80 |
| Sonnet v1 | 100/100 | 294/314 | 5/25 | 60/80 |
| Sonnet v2 | 100/100 | 295/314 | 25/25 | 80/80 |
| Sonnet v3 | 100/100 | 292/314 | 23/25 | 80/80 |

- **Farsh is right in every run**, Haiku's included (a small sample: the passage's nine farsh
  places, 100 rāwī-units).
- **Uṣūl stays near 93%**. What's missed changes from run to run (the general rows on p. 16 and
  Qālūn's munfaṣil at عليهم أنذرتهم in v3, others in v2), so it is variance, not one rule.
- **One instruction defect, found by the subagent itself**: al-Budūr's p. 11 rule (bare "خلف" is
  Khalaf al-ʿĀshir) doesn't hold inside a statement about Ḥamzah's ruwāt, where "لخلف وخلاد" is
  Khalaf ʿan Ḥamzah (the page says "لخلف وخلاد عن حمزة"). Fixed in the instructions and
  data/readers.yaml, with two smaller ones: references carry no khulf, and naql inside شيء at a stop
  is hamz_waqf_final.

## Decision for milestone 2

Sonnet 5.5 subagents. For farsh, the milestone's subject, the pilot is at the bar. For uṣūl, the
reviewed profile table stays the source; al-Budūr's uṣūl rows are a check against it, with the
disagreements going to Eisa, as docs/05 already plans for two-source agreement.

## Rule pilot: al-Wāfī and al-Īḍāḥ uṣūl (2026-11-25)

Eisa: al-Budūr states an aṣl once and reminds now and then, so what is aṣl and where it applies
comes from the uṣūl sections of al-Wāfī (pp. 25–198) and al-Īḍāḥ (pp. 30–186). Pilot: al-Wāfī pp.
50–53, 67–72 and al-Īḍāḥ pp. 54–60, 71–74 (mīm al-jamʿ, the hāʾ of عليهم, hāʾ al-kināyah), one
Sonnet subagent, instructions `prompt_rules.md`, check `python3 -m pipeline.rules`.

- 136 rules (al-Wāfī 100, al-Īḍāḥ 36), 0 rejected; ~138k tokens, **~6.6k a page** (no word lists).
  The whole of both sections (331 pages) at that rate: ~2.2M tokens.
- Against the profile table: 43/45 rāwī-wajh pairs agree; the two are the book's waqf statement
  ("all stop on the mīm with sukūn") set against a waṣl profile — the check now skips waqf rows.
- Most rows fell outside the 35 categories, which is the point: the hāʾ of عليهم/إليهم/لديهم, mīm
  al-jamʿ before a sākin (Abū ʿAmr's kasr, Yaʿqūb's itbāʿ), hāʾ al-kināyah's listed words (يؤده،
  نوله، يرضه، أرجئه…), the ṣād of الصراط. These are the rules al-Budūr's places looked like farsh for.
- Fixed in the instructions: the ṣilah of hāʾ al-kināyah went to a new name instead of `silah_ha`;
  new names now reused across both books. After the full run, new categories get consolidated
  into data/profiles.yaml (reviewed), each with its word list.

## The full uṣūl run (2026-11-25)

al-Wāfī pp. 25–198 and al-Īḍāḥ pp. 30–186 (331 pages), 11 Sonnet subagents: **1,187 rules**
(al-Wāfī 772, al-Īḍāḥ 415), 0 rejected, ~1.5M tokens (~4.5k a page).

- **Against the profile table** (general waṣl rules only; listed words and single places are a
  rāwī's exceptions, not his general rule): al-Wāfī 183/264 pairs agree, al-Īḍāḥ 73/81. The
  disagreements are category boundaries, not contradictions: a bāb's rule for all readers set
  against a narrower category (p. 68: everyone's ṣilah between two mutaḥarriks against Ibn
  Kathīr's `silah_ha`; pp. 165–168: rāʾ rules for all against Warsh's `tarqiq_ra`; p. 103: the
  obligatory ibdāl of آمن against `hamzatayn`). A few imālah rows (p. 141 Khalaf al-ʿĀshir, p. 153)
  to look at with the page.
- **678 rows in 136 new names**, proposed merged into 24 families (`categories_proposal.yaml`):
  istiʿādhah, basmalah, the hāʾ of عليهم, mīm al-jamʿ before a sākin, madd lāzim, idghām ṣaghīr,
  nūn sākinah, imālah of named words, al-Kisāʾī's hāʾ al-taʾnīth, stops on the rasm, rawm and
  ishmām, the two yāʾāt; listed words go into their existing category (silah_ha, hamzatayn, naql…).
- **For review**: rows where an agent assumed readers the page doesn't name (a few pp. 113–124,
  178); apparent contradictions kept as stated (al-Īḍāḥ pp. 50/52 basmalah for Abū Jaʿfar; al-Wāfī
  pp. 146/147 تراءا); Warsh's līn "qaṣr" written as tawassuṭ (p. 82, the agent's reading).
- Rows are in `pipeline/out/rules/` (gitignored: they quote the books); the merged categories go
  into data/ after review.
