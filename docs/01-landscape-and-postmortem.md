# al-Mushaf: landscape survey and mushaflab postmortem

2026-11-24. Written for Eisa and Yusuf before starting the blank-slate rewrite.

## The goal, restated

1. **A reading API.** Given an ayah (or a page) and a configuration (riwāyah plus one choice
   per uṣūl or taḥrīr option), return exactly one valid reading. A configuration the books
   forbid should be impossible to request.
2. **A shaping front end.** Draw that reading in any font, at any line count (15, 13, …), with
   proper muṣḥaf justification.

The example PDF (Khalaf ʿan Ḥamzah, *al-Silsilah al-Furātiyyah*, 634 pages, encrypted, 138 MB)
shows what exists today: one riwāyah, one ṭarīq, one taḥrīr per file, with the other wujūh as
margin notes (e.g. *نقل مع إسكان، روم* beside ٱلۡمَرۡءِ). It is thorough, but every alternative
sits on the page at once, and nothing about it can change.

---

## Part 1: The technical landscape

The problem splits into four layers. The useful question is which layers someone has already
solved.

| Layer | State of the art | Solved? |
| --- | --- | --- |
| A. Base text, fixed per riwāyah | KFGQPC Unicode texts and fonts for 8 riwāyāt; Tanzil; Nuqayah's `quran-text` | **Yes, for 8.** Each is one frozen taḥrīr. |
| B. Qirāʾāt knowledge as data (farsh, uṣūl, wujūh, taḥrīr constraints) | Quran.com's Qirāʾāt tab, alkiraat.com, printed muṣḥafs, al-Futūḥ itself | **No.** I found nothing public that is machine-readable and models constraints. |
| C. Layout (which words go on which line) | QUL mushaf layouts (~19 approved, incl. 15-line Madani variants and IndoPak) | **Yes for Ḥafṣ.** Partly for others. |
| D. Shaping and justification | DigitalKhatt variable fonts + HarfBuzz; QCF per-page fonts | **Mostly yes** (DigitalKhatt) |

### A. Base texts

- **KFGQPC** publishes Unicode text plus a matching font for Ḥafṣ, Warsh, Qālūn, Shuʿbah,
  al-Bazzī, Qunbul, al-Dūrī and al-Sūsī. Mirrors with version lists:
  [ibnhazm/KFGQPC](https://github.com/ibnhazm/KFGQPC), [nuqayah/qpc-fonts](https://github.com/nuqayah/qpc-fonts).
  Each text prints one wajh per place, and each font is tuned to its own text's codepoint
  conventions. (mushaflab learned this the hard way: G-006, G-013, G-016, G-017.)
- **JSON repackagings**: [risan/quran-json](https://github.com/risan/quran-json) (CC BY-SA, with
  `number_in_hafs` ayah mappings for Warsh, Qālūn, Dūrī, Sūsī),
  [quran-center/quran-meta](https://github.com/quran-center/quran-meta) (counting metadata for
  Ḥafṣ, Qālūn and Warsh). All of these are the KFGQPC texts again.
- **[nuqayah/quran-text](https://github.com/nuqayah/quran-text)**: a portable Unicode Ḥafṣ. Its
  README is a short, useful list of what Unicode *cannot* express in Qurʾānic orthography:
  lām–hamzah–alif in الـٔاخرة, and the dagger alif after non-joining letters, which needs a
  hair-space hack. Every one of these limits applies to us too.

**Takeaway:** text exists for 8 of the 20, and only as frozen outputs. For the parameterized
reading we want, these are test fixtures ("with Warsh set to KFGQPC's choices, we should get
this text"), not sources.

### B. Qirāʾāt knowledge as data: the real gap

- **Quran.com** ([Ayah Study Mode → Qirāʾāt tab](https://quran.com/explore/a-brief-guide-to-the-ten-readings-qiraat))
  shows the 10 qurrāʾ and 20 ruwāt per ayah, with Ḥafṣ-agreeing readings in white. It is a
  display for people. I found no public data or API behind it.
- **[alkiraat.com](https://alkiraat.com) / the "Quran Qira'at" app**: the closest thing to our
  layer B, and further along than I first thought (looked at in a browser, 2026-11-24).
  - **Six digitized wujūhāt books** as selectable "sources", in the Ottoman jamʿ tradition:
    al-Jīqarawī's *al-Taqrīb* (kubrā) and *al-ʿAsharah* (ṣughrā), and Marzaq's kubrā (Tanqīḥ,
    Nashriyyah), ṣughrā and sabʿ. Marzaq's ṣughrā shows "still in preparation".
  - **al-Jīqarawī's *al-Wujūhāt al-Qurʾāniyyah – al-ʿAsharah* is complete**: Shāṭibiyyah and
    Durrah, Istanbul method, one ṭarīq per rāwī, with "ج" for al-Azraq ʿan Warsh. The site says
    its taḥrīrāt are light and mostly agreed, taken from *Daftar Qawāʿid al-ʿAsharah*. That is
    our scope.
  - **Data model** (from its JSON): ayah → *maqṭaʿ* (a word range) → numbered *wajh* → readers
    as rumūz (e.g. `ب د ط يع`) → per word, the text and a *ḥukm* class from a taxonomy
    (`almd_walq9r_almarateb_almunfasil_Altawsu6t`, `hamzMufrad_sakin_…`,
    `almd_walq9r_bdl4`, `swrt_om_lqraan_frsh_mlk`, …).
  - **The word text is always Ḥafṣ.** For مَٰلِكِ the qaṣr group gets the same text with a farsh
    tag. It enumerates and labels wujūh; it does not produce a reading's text.
  - It also has the matns (Ṭayyibah, Shāṭibiyyah, Durrah) as linked evidence, editor and
    moderator roles, and export for users the owner grants it.
  - "All rights reserved", and no public API documentation. Using its data in bulk needs their
    permission. **Contact them**: their ḥukm taxonomy and enumerated wujūh are exactly the
    labels and taḥrīr tables we would otherwise rebuild.
- **Al-Jāmiʿ li-l-Qirāʾāt al-ʿAshr** ([Play](https://play.google.com/store/apps/details?id=com.khair.zad)):
  one separate muṣḥaf per reading, with no toggling.
- **Printed:** the Furātiyyah series (the example PDF), and Dar-us-Salam's ten-readings Tajweed
  muṣḥaf (margin notes, colour key). Both put every wujūh on the page at once.
- **Nuqayah** ([nuqayah.com](https://nuqayah.com/en/projects)): its Al-Qari app's "144 muṣḥaf
  narrations" look like audio recitations, and its muṣḥaf apps use page assets. On GitHub, its
  open work is fonts and text (`qpc-fonts`, `quran-text`, `kitab-font`), plus two experiments
  that matter to us: `ar-justify` (kashida justification) and `digitalkhatt-examples`, a Svelte
  "mushafgen" form driving DigitalKhatt's WASM and OTF engines. I saw no qirāʾāt data model.

**Takeaway:** nobody publishes an open model of farsh, uṣūl, wujūh and taḥrīr that **outputs
a reading**. alkiraat has digitized the enumeration and labelling of the wujūh (closed data,
Ḥafṣ text only). Your al-Futūḥ extraction has the variant *text* for all 20 ruwāt, but its
labels are prose. The two are complementary, and together they are a two-source check.

### C. Layout

- **[QUL](https://qul.tarteel.ai/mushaf_layouts)** (Tarteel, MIT,
  [repo](https://github.com/TarteelAI/quranic-universal-library)): mushaf layout tables
  (page → line → word range) for about 19 approved layouts, with a *qirāʾah* column, as JSON or
  SQLite. Tarteel's app bundles this word-to-line allocation and draws on a Skia canvas
  ([blog](https://tarteel.ai/blog/from-page-to-screen-rethinking-quran-rendering-for-the-digital-age/)).
- These layouts assume the text of the printing they came from. When a riwāyah adds, drops or
  lengthens words, the line breaks need a policy. mushaflab's policy: lines keep their anchor
  words, justification absorbs the width change, and overflow moves at most one word and is
  reported. That reasoning still holds.

### D. Shaping and justification

- **QCF V1/V2/V4** (KFGQPC per-page fonts, used by quran.com): one font per page, with each word
  a single glyph. They look exactly like the print but are frozen to one text, one layout and
  one page. **Useless for us**, except as visual references.
- **[DigitalKhatt](https://github.com/DigitalKhatt)** (Amine Anane, sponsored by Tarteel):
  - OpenType variable fonts under OFL-1.1: new Madina, old Madina (1995), Shāmiyah, and the
    13-line IndoPak.
  - `digitalkhatt-js` (MIT): justification in the browser on stock HarfBuzz (WASM). It sets a
    target line width, then uses regex lookups on the line's text to apply per-character
    variation-axis values (kashida stretch, wider final forms) by priority (`StretchType`: beh,
    final ascenders, kaf, second kashida, …), with spacing and x-scale as fallbacks. It ships
    React and React Native adapters.
  - A METAFONT-to-WASM engine, a HarfBuzz fork with justification extensions, and Mushaf
    "analyzers" that infer justification rules from scans.
  - Several repos were updated this month.
- mushaflab already used DigitalKhatt's Madina font and ported its justification to Rust on
  `harfrust` (D2, D3). Its measured cost was 3 to 6 ms per page cold and under 1 ms warm
  (`docs/perf.md`). **Justifying at runtime is cheap**, so precomputed pages aren't needed.

**What D does not solve:** marks that Ḥafṣ never uses. Examples are imālah and taqlīl, tas-hīl,
ishmām and the Maghribī conventions, and whatever signs the 12 riwāyāt without a KFGQPC text
need. DigitalKhatt's fonts are drawn for Ḥafṣ (and the IndoPak conventions). This gap is real,
and it can be fixed upstream in a font that is open.

### Verdict

| Piece | Build or reuse |
| --- | --- |
| Word ids, Ḥafṣ base text, ayah counting | **Reuse** (KFGQPC / QUL / Tanzil) |
| Fixed texts of the 8 KFGQPC riwāyāt | **Reuse, as tests only** |
| Farsh for all 20 ruwāt | **Build.** Your al-Futūḥ extraction is the head start. |
| Uṣūl categories, wujūh per rāwī, taḥrīr constraints | **Build.** Nobody has this as data. |
| Reading engine (config → one reading → codepoints for a font) | **Build.** It is small if the data is right. |
| Layouts | **Reuse QUL**, plus a reflow policy |
| Shaping and justification | **Reuse DigitalKhatt** (JS + HarfBuzz WASM). Contribute marks upstream. |
| Fonts for non-Ḥafṣ signs | **Extend** DigitalKhatt (OFL) or KFGQPC's riwāyah fonts |

---

## Part 2: Postmortem of mushaflab

### Timeline

| Dates | What happened |
| --- | --- |
| Oct 21–28 (8 days, 143 commits) | Plan v2, Phases 0–8: pinned sources, Ḥafṣ spine, Rust renderer on DigitalKhatt, codepoint patches for the 7 other KFGQPC riwāyāt, a rule DSL, free-edit mode with undo, display styles, highlighting, a WASM web app with canvas-in-worker, a 16 ms page budget, Playwright goldens, a Netlify deploy |
| Nov 20 | The separate `mushaf` project: glyph-level extraction of all six volumes of al-Futūḥ al-Bāhira |
| Nov 21–23 | Architecture reset (D67), plan v3, milestones M0–M6. M0 passed: formats, letter features, and a Warsh prototype covering al-Fātiḥah plus al-Baqarah 1–20 |

### Size at the reset

| Thing | Count |
| --- | --- |
| Rust | 23k lines, 16 crates |
| Python | 18.6k lines |
| Tracked YAML / JSON | 500k / 148k lines |
| `data/` on disk / `build/` | 691 MB / 324 MB (`data/patches` alone 119 MB) |
| ADRs | 70 (D1–D72) and 4 gate records, written in about 10 working days |
| Known gaps | 100 |
| `just` recipes | 42 |
| Tests | ~540 (232 Rust, 312 Python) |
| CLAUDE.md | 10 KB, 12 "non-negotiable" rules |
| Slowest loops before the fix | `data-verify` 16 min; the pre-commit gate ~1 h (cut to ~2 min on Nov 21); web bundle 81 MB |
| Patches for Warsh alone | 82,582, of which 31,906 only rewrite the sukūn codepoint and 50,676 are `unclassified` |

### What went wrong, roughly in order of cost

**1. The data recorded outputs, not the readings that produce them.**
Each riwāyah was stored as codepoint edits against Ḥafṣ, found by diffing KFGQPC files. An edit
says *what* changed, never *why*: no farsh, no uṣūl, no wajh. That one choice caused most of
what followed:
- The data could not be reviewed: 82k unexplained edits for one riwāyah.
- There was no route to the 12 riwāyāt without a published text.
- Wujūh could not be expressed, because KFGQPC prints only one.
- The fix was to reverse-engineer the uṣūl from the diffs: 508 "rules", all of them
  `hypothesis`. Those are the books' rules, recovered badly from one taḥrīr's output.

**2. How a source encodes a sign was mixed up with how it is read.**
KFGQPC Ḥafṣ writes sukūn as U+06E1; KFGQPC Warsh writes U+0652. Hamzat al-waṣl, pause signs and
madd are encoded differently from file to file. With no neutral representation of a letter in
between, every diff mixed three things: encoding, a printing's orthography, and actual reading
differences. In the M0 Warsh prototype, **61%** of the differences between Ḥafṣ and Warsh in
al-Fātiḥah plus al-Baqarah 1–20 were encoding conventions. D72 (signs vs features) is the right
fix, but it arrived after a month.

**3. Rendering was built first, to production quality.**
Rendering is the part closest to solved (DigitalKhatt exists). The novel and risky part is the
data model. Even so, Phases 3–8 built a full renderer with:
- byte-identical goldens and fixed-point arithmetic for cross-platform determinism;
- free-edit mode with a lint layer and an "edited" marker;
- display-style conversion (Ḥijāzī and Maghribī for every riwāyah);
- a WASM web app with canvas-in-worker and a perf budget;
- iOS and Android crate stubs.

All of that rested on the patch model. When the model was replaced, D67 kept the engine, and the
legacy app has to keep building under the gate until M3. So the reset carries two systems.

**4. Process stood in for a model.**
The process was designed to keep an autonomous LLM executor safe: 12 rules, gates after every
phase, an ADR for every decision, provenance and status on every row, owner-only statuses with
signed commits, citations for test expectations, edition pinning, an un-hideable edited marker.
Each piece is defensible. Rule 1 ("never write Qurʾānic text or qirāʾāt from memory") is
essential.

Together, though, they produced:
- 70 ADRs in under two weeks, many for incidental choices (screenshot blur tolerance D61, page
  budget D62, worker canvas D63);
- 100 tracked gaps;
- an hour-long gate;
- a single human bottleneck: many decisions are "Yusuf, relayed by Eisa".

Worse, the rigour verified the wrong thing. Checksums, round-trips and goldens proved that the
patches reproduced KFGQPC exactly, and that was never the goal. **A great deal of evidence was
gathered that the model was internally consistent. None of it tested whether the model could
express a wajh.**

**5. Scope grew in every direction at once.**
Free editing, undo and redo, user highlight marks, saved edits in the browser, two extra script
styles, three platforms and a test deploy were all built within 8 days. None of them was needed
to answer the one open question: can a reading be represented as parameters?

**6. Speed hid the problem.**
143 commits in 8 days felt like progress. The phase gates were checks of completion ("did T5.4
produce goldens?"), not of direction ("can this model ever do Khalaf's sakt?"). An LLM executor
will fill any structure it is given, quickly and convincingly. The plan's structure decided what
got built, and nothing in it asked the hard question early.

### What was right, and worth carrying over

| Asset | Where | Why it matters |
| --- | --- | --- |
| **al-Futūḥ extraction** | `../mushaf/futuh/` | 48,603 table rows and 345k Qurʾānic words, extracted with glyph-level proof rather than OCR. Readers are resolved to the 20 ruwāt (88% fully, 11% bounded), and colour classes mark farsh. **Probably the most valuable thing either project produced.** |
| Signs-vs-features split (D72) | `mushaflab/docs/adr/D72.md` | The right core abstraction: readings change features, a writing style turns features into codepoints for a font. |
| The layered model (D67) | `mushaflab/docs/ARCHITECTURE.md` | Words → farsh → uṣūl occurrences → riwāyah profiles with combination tables → writing style → layout. This is the right shape. |
| Rule 1 and per-row provenance | CLAUDE.md | Keep it. Make it lighter, not weaker. |
| Codepoint class table, KFGQPC encoding facts | `data/pipeline/codepoint_classes.*`, gaps G-003 to G-017 | Hard-won knowledge of source anomalies |
| Justification port and perf numbers | `mushaf-justify`, `docs/perf.md` | Proof that runtime justification is cheap |
| Combination-table examples from al-Budūr | ARCHITECTURE.md (p. 65, p. 232) | Concrete test cases for the constraint model |

### Lessons for the blank slate

1. **Prove the model before building anything else.** The first milestone should be a small
   reading engine (data in, one reading out) running across all 20 ruwāt on a short, hard
   passage, with no renderer at all. Choose a passage that exercises the hard cases: Warsh's
   badal with dhawāt al-yāʾ, Khalaf's sakt, Ḥamzah's waqf on hamz, a Durrah rāwī.
2. **One internal representation.** Decode every source into letters with features at ingest.
   Encode into codepoints only at the edge, for a specific font.
3. **Model taḥrīr as constraints.** Each uṣūl category is a variable per rāwī. Its domain is the
   wujūh the books allow, and taḥrīr gives the allowed combinations, both across the whole
   riwāyah and locally across a few words. The API takes a partial configuration, fills in
   defaults, and rejects (or lists) what is not allowed. A constraint table can be reviewed; a
   diff cannot.
4. **Reuse layers C and D.** Use QUL layouts and DigitalKhatt fonts and justification in JS. Fork
   or contribute only where a riwāyah needs a mark that doesn't exist yet.
5. **Process sized to two equal partners.** Use one short decisions log, not one ADR per
   choice, and no owner gates: either of you decides. Data changes are reviewed as diffs
   people can read. Keep the fast test loop under a minute. Defer
   byte-identical determinism, free editing, native apps and extra script styles until the
   reading API works.
6. **Keep a direction check.** Every milestone should be judged on "can the model express X
   now?", not "were the artifacts produced?".
