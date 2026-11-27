# Extracting taḥrīr (al-Ḍabbāʿ, Sharḥ Itḥāf al-Bariyyah)

You read one page of **Mukhtaṣar Bulūgh al-Umniyyah**, al-Ḍabbāʿ's commentary on al-Ḥusaynī's
*Itḥāf al-Bariyyah bi-Taḥrīrāt al-Shāṭibiyyah*: the taḥrīr of the seven qurrāʾ (14 ruwāt) by the
Shāṭibiyyah's ṭarīq. Write down every statement that **limits which wujūh may be read together, or
which wujūh the ṭarīq allows**. The text is OCR; read through it, never correct a quote. Use only the
page; add nothing you know about the qirāʾāt.

## Input

`## PAGE` (statements start here) and `## NEXT PAGE BEGINS` (only to finish a statement that runs
on; don't extract statements that start there). The vocabulary file (`VOCAB.md`) lists the
categories and their wujūh ids.

## Output

`{"book": "dabba", "page": 201, "rows": [...]}` to the file you're told (`"rows": []` if the page has
none). One row per statement:

| field | what |
| --- | --- |
| `kind` | `combination`: wujūh of two or more categories (or two places) that go together or don't ("إذا اجتمع… فعلى القصر…"); `restriction`: one category, which of its wujūh the ṭarīq allows for a rāwī, or allows only at some words ("ليس من طريق الشاطبية", "والمقروء به… فقط", "يؤخذ له بـ… فقط"); `place`: the wujūh of one word or place, when the page gives them as a set ("فيها ثلاثة أوجه") |
| `readers` | ruwāt ids the statement is about |
| `cats` | category ids from VOCAB.md, in the order the tuples give them. A feature VOCAB doesn't have: a short new snake_case id, and list it in `new_ids` |
| `allowed` | the tuples the book allows, each a list with one wajh id per `cats` entry, e.g. `[["qasr","tawassut"],["tul","tul"]]`. For a `restriction`, one-element tuples: `[["izhar"]]` |
| `forbidden` | tuples the book rules out, if it says so instead (`"ممتنع"`, `"لا يجوز"`, `"فلا يأتي"`); else `[]` |
| `words` | the words the statement is about or gives as its example, as the book writes them (`["شيئا", "الآخرة"]`); `[]` if none |
| `sura`, `ayah` | when the statement is about one place and the page says where (`"في يس"`, `[البقرة: ٢٠]`): the sūrah number, and the āyah number if given; else `null` |
| `condition` | `"wasl"`, `"waqf"`, `"start"` (ibtidāʾ), `"junction"` (between two sūrahs), or `null` |
| `source` | `"commentary"` (al-Ḍabbāʿ), `"verse"` (only when the prose doesn't restate it), `"footnote"` (the editor's notes); for a footnote, also `"via"`: whose view it reports ("المتولي", "الخليجي") |
| `new_ids` | wajh or category ids you made up for this row (`[]` if none) |
| `note` | one plain English sentence of what the statement says |
| `quote` | the words of the page that state it, copied exactly, at most 300 characters, found once on the page |

## Rules

- **Taḥrīr only.** Not rows: what a rāwī reads where nothing is limited (that is the uṣūl tables'
  job), biographies, sources, grammar, the reason for a wajh (توجيه), the verse explained word by word.
- A statement that lists wujūh **for each choice of another** ("فعلى قصر البدل… وعلى توسطه…") is one
  `combination` row: put every allowed tuple in `allowed`.
- "**ستة أوجه**", "**ثلاثة أوجه**": count your tuples; they must match the number the book gives.
- A wajh the commentary says is "not read" or "not from the ṭarīq" for this ṭarīq but read by the
  Nashr / Ṭayyibah: a `restriction` with the Shāṭibiyyah's wujūh in `allowed`; say the other in `note`.
- Two ruwāt with the same ruling: one row naming both.
- **الباقون / غيره** is the rest of the 14.
- Reader names: نافع = qalun/warsh, ابن كثير / المكي = bazzi/qunbul, أبو عمرو / البصري = duri_abuamr/susi,
  ابن عامر / الشامي = hisham/ibn_dhakwan, عاصم = shuba/hafs, حمزة = khalaf_an_hamzah/khallad,
  الكسائي / علي = abul_harith/duri_kisai, الأزرق = warsh (his ṭarīq), قالون = qalun, ورش = warsh,
  البزي = bazzi, قنبل = qunbul, الدوري = duri_abuamr (or duri_kisai if the page says الكسائي),
  السوسي = susi, هشام = hisham, ابن ذكوان = ibn_dhakwan, شعبة / أبو بكر = shuba, حفص = hafs,
  خلف = khalaf_an_hamzah, خلاد = khallad, أبو الحارث = abul_harith.
- Footnotes that only give a source, a biography or a variant spelling of a quoted book are not rows.

## Check before you write

Every rāwī id is one of the 14; every tuple has as many ids as `cats`; every id is in VOCAB.md or in
`new_ids`; the number of tuples matches any number the book states; every quote is copied, not
retyped.
