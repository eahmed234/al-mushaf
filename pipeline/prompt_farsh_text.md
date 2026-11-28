# Writing a farsh reading's text (option text)

The farsh tables (data/farsh_books) say, in the books' words, how each rāwī reads a word ("بالألف",
"بضم الهاء", "بياء الغيب"). An app needs the word itself. For each case you get the Ḥafṣ word (as
the muṣḥaf writes it, in KFGQPC's encoding), its context, and the options with the book's quote.
Write **the word as each option's readers read it**, grouped by text, for all twenty ruwāt.

Use only the options and quotes given. Add nothing you know about the qirāʾāt: if the book's words
don't tell you the text, say so in `note` and leave that group's `text` as `null`.

## What to write

- **Start from the Ḥafṣ word and change only what the reading changes.** Keep every other letter
  and mark exactly as it is (copy the characters; don't retype them).
- **Farsh only.** Don't apply a rāwī's general rules (uṣūl): no madd lengths, imālah or taqlīl, no
  easing of hamzahs, no ṣilah, no idghām, no naql, no sakt. The engine adds those per rāwī. Only
  what the option's reading states for this word.
- **Conditions.** An option given "wherever it occurs" may carry a condition the book states (هو
  after و، ف، ل only; before a hamzah only…). If the condition doesn't hold at this word, that
  option's readers read the Ḥafṣ word here: put them in the Ḥafṣ group and say why in `note`.
- **"على أصله", "من الوفاق", "كحفص"** and the like: the reader reads as named; often that is the Ḥafṣ word.
- A rāwī no option names reads the Ḥafṣ word.
- **Khulf**: a rāwī in two options (of one entry) has two texts: put him in both groups and in each
  group's `khulf`.
- **Two entries at one word** (each about a different thing: the tāʾ, then the sīn): a rāwī's text
  applies every option he has, one from each entry.
- **Several slots** (`slots` > 1 in a case): the same word at each; one text serves them all.

## Encoding (KFGQPC's, as in the Ḥafṣ word)

sukūn U+06E1 `ۡ` (not U+0652, which marks a silent letter: كَفَرُواْ); shaddah U+0651; fatḥah
U+064E, ḍammah U+064F, kasrah U+0650; dagger alif U+0670; maddah U+0653; hamzah on the line U+0621,
on a seat U+0623 U+0625 U+0624 U+0626, alone above a tatweel U+0640+U+0654; alif waṣlah U+0671. The
tanwīn marks depend on the next word (U+064B-064D before a letter it is pronounced at; U+0657,
U+065E, U+0656 where it merges or is hidden; a small mīm U+06E2 / U+06ED for iqlāb): keep the Ḥafṣ
word's. Write letters and marks in the order: letter, shaddah, vowel (as the Ḥafṣ word does).

## Output

One JSON file per case, `{"key": "k001", "groups": [...]}`, each group:

| field | what |
| --- | --- |
| `readers` | ruwāt ids reading this text (every one of the twenty in at least one group) |
| `khulf` | those of them for whom it is one of two texts |
| `text` | the word, or `null` if the book's words don't say |
| `options` | the option numbers (from the case) this text realises; `[]` for the Ḥafṣ group if none |
| `base` | `true` for the group whose text is the Ḥafṣ word exactly |
| `note` | why, where it isn't obvious (a condition not met, "على أصله"); else `""` |

The ids: qalun, warsh, bazzi, qunbul, duri_abuamr, susi, hisham, ibn_dhakwan, shuba, hafs,
khalaf_an_hamzah, khallad, abul_harith, duri_kisai, ibn_wardan, ibn_jammaz, ruways, rawh, ishaq, idris.

## Check before you write

Twenty ruwāt covered; the `base` group's text is the Ḥafṣ word character for character; every
other text differs from it only where its option's reading says; no uṣūl applied; run
`python3 -m pipeline.farsh_text validate` and fix what it reports for your keys.
