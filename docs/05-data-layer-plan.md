# Plan: building the data layer

2026-11-24. The spike showed the format works (`spike/REPORT.md`). This plan builds it for the
whole Qurʾān, from the books, with the spike's checks as tests. It is written to keep cost down:
code does everything mechanical, a model reads book prose only where reading is needed, and
Eisa's time goes only to what the sources disagree on.

## Principles (carried over)

- **Every row cites a page**, read from the page. The checks (al-Futūḥ, KFGQPC, nQuran,
  alkiraat) test the data; they are never its source.
- **Data, not code**: facts live in files; code only reads them, applies them and checks them.
- **ṭarīq-aware** (kubrā later): every row says where it comes from; ikhtilāf is an option.
- **Every check catches a planted error** before its result is trusted.
- **Light process**: plain files, small modules, one category at a time.

## What gets built

```
data/
  spine/          riwāyah-neutral word slots (Ḥafṣ ids + added slots, docs/04)
  farsh/          per surah: places, options (text per slot), readers, cites
  profiles.yaml   reviewed (from the spike)
  occurrences/    per category: the places a rule applies to, from the books' lists
  constraints.yaml taḥrīr tuples, cited (a folder once it grows)
  waqf/           Ḥamzah/Hishām rasm word lists (the rules are code: mushaf_data/waqf.py)
  marks/          pause signs per edition (Madinah, IndoPak, Habṭī)
  counts/         ayah ends per riwāyah's count
  corrections/    print errors in the checks' sources (Eisa-confirmed)
mushaf_data/      the engine: load, generate, explain (ported from the spike)
checks/           the engine against al-Futūḥ (../mushaf, optional) and KFGQPC; review sheets
pipeline/         extraction jobs: prompts, batch runner, validators, review sheets
tests/            the spike's checks as tests, plus a planted error for each
```

## Who does what

Three kinds of work, used in this order of preference:

| Kind | Cost | Used for |
| --- | --- | --- |
| **Scripts** | free to run | anything mechanical: anchoring words, aligning lists to the spine, detectors, comparisons with al-Futūḥ / KFGQPC, validation, building review sheets |
| **Batch model calls** | low (see Cost) | reading book prose into structured rows: farsh per place, taḥrīr statements, word lists inside chapters |
| **Eisa** | the scarce resource | only rows the sources disagree on, and rows no check can reach, with the page beside them |

### By data area

| Area | Source | Script | Model | Eisa |
| --- | --- | --- | --- | --- |
| **Spine** | Ḥafṣ spine + farsh that adds or drops a word | builds slots from the farsh | — | spot check |
| **Farsh** | al-Budūr per place (all ten); al-Wāfī / al-Īḍāḥ farsh chapters (second reading) | anchors to slots; checks readers cover all twenty once; compares the two books, al-Futūḥ's rows and KFGQPC | extracts each place's statements (who reads what, text) | disagreements only |
| **Profiles** | done (al-Wāfī, al-Īḍāḥ; reviewed) | port | — | new rows only |
| **Occurrences** | al-Budūr's per-rubʿ "الممال" (done) and "المدغم" lists; al-Wāfī's word lists | ties lists to quarters (done for imālah); detector vs list reports | word lists stated in prose inside the uṣūl chapters | the list/detector disagreements |
| **Constraints** | al-Budūr per place; al-Ḍabbāʿ by bāb | checks each tuple against al-Futūḥ's boxes | extracts taḥrīr sentences into candidate tuples | every constraint (few, high impact) |
| **Waqf** | done (al-Wāfī pp. 105–127, al-Budūr) | port; the six-volume check | — | the 7% the check flags, by sample |
| **Marks, counts** | KFGQPC files (counts for 8); other editions TBD | import | — | which editions |

## The extraction pipeline

One request per book page (or per place for al-Budūr, which is ordered by place). Each request:

1. **A frozen prefix**, identical in every request so it caches: the instructions, the output
   schema, a reader-name table (every way the books name the twenty, mapped to ids, e.g.
   "الأخوان", "المدنيان", "سما"), and three worked examples from pages Eisa has already reviewed.
2. **The variable part**: the page text, and the Ḥafṣ words of the ayahs the page covers (so the
   model quotes slot ids, not free text).
3. **Structured output** (a JSON schema): rows of {place (slot ids), reading (text), readers,
   khulf, conditions, quote from the page, page}. The quote must be a substring of the page; a
   script rejects any row whose quote isn't there.

Then, all by script:

- **Validate**: readers resolve to ids, every place's readers cover the twenty exactly once (or
  the row says which they don't), slot ids exist, quotes are on the page.
- **Agree**: compare al-Budūr's rows with al-Wāfī / al-Īḍāḥ's for the same place, then with
  al-Futūḥ's rows and KFGQPC's eight. Rows that agree become `status: agreed`; the rest go to a
  review sheet (the same page-beside-rows sheet as the profile review, marks pasted back as data).

## Cost: batch script first, subagents second

**Message Batches** through a local script (`pipeline/batch.py`): requests go in one file, results
come back within 24 hours at **half price on every token, cache reads and writes included**. The
frozen prefix is cached (best-effort inside a concurrent batch). This is the cheapest way to read
~1,500 pages and keeps this conversation's context out of it. It needs an Anthropic API key or an
`ant auth login` profile, billed to the API, separate from the Claude Code plan.

**Subagents** in a Claude Code session are the fallback if API billing isn't wanted: a cheaper
model reads a chunk of pages (say twenty) and writes the same JSON files, and the same scripts
validate them. They cost more per page (each starts cold, with the harness's own context) and use
the plan's limits, so they suit small jobs: a single chapter, a re-read of disputed pages.

Rough size (characters ÷ 2.5 as a token estimate; to be measured in the pilot):

| Source | Pages | Page text |
| --- | --- | --- |
| al-Budūr (places) | 346 | ~220k tokens |
| al-Wāfī (farsh) | 195 | ~125k |
| al-Īḍāḥ (farsh) | 214 | ~90k |
| Ghayth al-Nafʿ | 328 | ~290k |
| al-Ḍabbāʿ | 313 | ~130k |

Per request, about 1–2k tokens of page plus context, a few thousand of cached prefix, and 1–2k
of JSON out. Over ~1,400 requests that is single-digit millions of tokens in and a few million
out, so the whole extraction costs on the order of **tens of dollars on the top model at batch
prices, and a fraction of that on a smaller one**. Output (and thinking, which bills as output)
is the larger part, so effort is kept low or medium for extraction.

**Model choice is decided by a pilot, not assumed.** Run the same 30 pages, from places whose
answers we already have (2:1–20, reviewed), through Claude Haiku 5.5, Claude Sonnet 5.5 and
Claude Opus 5.5 at low effort, with the validators and agreement checks as the score. Take the
cheapest that clears the bar (e.g. ≥98% of rows agreeing with the reviewed answers, no invented
quotes). Pilot cost: well under a dollar. The pilot also measures real token counts, replacing
the estimates above.

The real budget is Eisa's review time, so the plan spends tokens to save it: two books per place,
plus the checks, means only disagreements reach him.

## Order of work

| # | Milestone | Done when |
| --- | --- | --- |
| 0 | ~~**Package skeleton**~~ (done 2026-11-24): `mushaf_data/`, `checks/`, `data/`, `tests/` from the spike | the spike's checks pass as tests, each with a planted error caught: 25 tests, same numbers |
| 1 | **Pipeline + pilot** (built 2026-11-25, `pipeline/PILOT.md`): `pipeline/` (prompt, schema, packer, validator, gold set, scorer, review sheet); the model pilot | done 2026-11-25: Sonnet 5.5 (farsh 100% in every run, uṣūl ~93%, against the gold set Eisa reviewed); ~13–16k tokens a page; sheet format used for Eisa's review |
| 2 | **Farsh, al-Baqarah** (started 2026-11-25): al-Budūr extracted (147 places), checked against KFGQPC (304 agree, 72 words disagree); second reading from al-Wāfī/al-Īḍāḥ for the disputed words only | every place of al-Baqarah has options for all twenty; disagreements reviewed |
| 3 | ~~**Spine**~~ (done 2026-11-27): riwāyah-neutral slots from the farsh that adds or drops words; `data/spine/slots.yaml`, `spine.projection`, `checks/spine.py` | Ḥafṣ is one projection; KFGQPC's eight align without gaps |
| 4 | **Farsh, the rest**, surah by surah in batches | as milestone 2, whole Qurʾān |
| 5 | **Occurrences**: "المدغم" lists, naql, the hamz categories, hāʾ al-taʾnīth; the row gate removed | each category's table checked against al-Futūḥ book-wide |
| 6 | **Constraints**: al-Budūr and al-Ḍabbāʿ, every one reviewed | constraints checked against al-Futūḥ's boxes book-wide |
| 7 | **Marks and counts**: KFGQPC counts; Madinah marks; IndoPak and Habṭī when sourced | stops offered from a chosen edition |
| 8 | **The engine's API**: resolve / enumerate / explain over `data/` | any passage, any rāwī, any options, with the facts behind each word |

Milestones 2–6 can overlap once milestone 1 is done: each is a batch job plus its review.

## Decisions (Eisa, 2026-11-24)

1. **Subagents for now**, on the Claude Code plan; no separate API billing yet. The pipeline's
   requests are written so the same prompt, schema and validators can move to Message Batches
   later without change.
2. **The pilot's bar: 98%** of rows agreeing with reviewed pages, no invented quotes.
3. **Farsh priority: al-Budūr primary**, al-Wāfī / al-Īḍāḥ the second reading.
   **Changed 2026-11-27 (Eisa):** from Āl ʿImrān on, al-Wāfī and al-Īḍāḥ's farsh chapters are
   primary (shorter and targeted: ~10-12k tokens a page against ~27k; pilot in STATUS.md); the al-Budūr
   tables of al-Fātiḥah, al-Baqarah and Āl ʿImrān stay as the cross-check.
4. **This repo stands alone**: nothing it needs may come from the archived mushaflab. Sources are
   listed with URL and sha256 (`tools/sources.tsv`), fetched into a gitignored `sources/`, and
   the Ḥafṣ spine is built here from KFGQPC's official text. `../mushaf` (the al-Futūḥ extractor,
   active) stays a separate, optional dependency used only by the checks; its outputs can't be
   copied here because the book isn't redistributable.

### What subagents change

Each subagent gets a chunk of pages (about twenty), the same frozen instructions, schema and
reader table, and writes one JSON file per page into `pipeline/out/`; the validators and review
sheets are scripts as before. The pilot compares models through the subagents' `model` setting
(Haiku, Sonnet) against the same 30 reviewed pages, and records the tokens each run used.
