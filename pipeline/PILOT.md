# Extraction pilot: al-Budūr pp. 16–25

2026-11-25. Milestone 1 of docs/05: which model reads book pages into rows well enough, at what
cost, with the review sheet for Eisa to approve.

## Set-up

- **Pages**: al-Budūr al-Zāhirah pp. 16–25, the first rubʿ (1:7–2:25), packed with the Ḥafṣ words
  of the quarter (`pipeline.pack`). p. 15 is the worked example in the instructions, not scored.
- **Gold set**: 161 rows (485 rāwī-units) read by Claude (Opus) from the pages, checked by the
  validator; stored as offsets (`pipeline/gold/budur/`). **Not yet reviewed by Eisa.**
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
