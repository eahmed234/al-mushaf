# Extracting a page of al-Budūr al-Zāhirah

You read one page of *al-Budūr al-Zāhirah fī al-Qirāʾāt al-ʿAshr al-Mutawātirah* (ʿAbd al-Fattāḥ
al-Qāḍī) and write down every statement it makes about **who reads what at a place** of the
Qurʾān, as JSON rows. The page text is OCR: words are sometimes split or joined, letters
confused (ى/ي, ة/ه), Qurʾānic words written without vowels. Read through that; never correct
the quote.

Use only the page. Do not add anything you know about the qirāʾāt that the page doesn't say.

## Input file

- `## PAGE`: the page's text. Statements start here.
- `## NEXT PAGE BEGINS`: the start of the next page, only so you can finish a statement that
  runs on. Don't extract statements that start there.
- `## HAFS WORDS`: the Ḥafṣ words of the passage the page is about, one per line: `id<TAB>text`
  (id is surah:ayah:word). Places are given as these ids.

## Output

One JSON object (schema: `pipeline/schema.json`):

```json
{"book": "budur", "page": 16, "rows": [ ... ]}
```

Each row is **one clause that names readers**: "قرأ X بكذا", "وقرأ Y بكذا", "والباقون بكذا",
"أبدل همزه ورش…", "ولخلف وجهان…". Fields:

| field | what |
| --- | --- |
| `place` | ids of the word(s) the statement is about (its headword, the word the reading changes). Several ids when one statement covers several words ("في الموضعين", "عليهم أنذرتهم"). `[]` if the word isn't in HAFS WORDS; then give `place_text` |
| `kind` | `farsh`: a reading of this word that isn't a general rule (other letters, vowels, a word added or dropped: مالك/ملك، يخادعون/يخدعون، يكذبون). `usul`: a rule of the rāwī applied here (madd, ṣilah, hamz, naql, sakt, idghām, imālah, tarqīq, taghlīẓ, waqf on hamz). `tahrir`: which wujūh go together ("ستة أوجه: قصر البدل وعليه…"). `ittifaq`: the book says all twenty read alike ("اتفق", "أجمعوا", "جميع القراء يمدون…", "ولا خلاف بين القراء") |
| `category` | for `usul` rows, one id from the category table below; else `null` (also `null` if none fits) |
| `readers` | the ruwāt this clause gives the reading to, as ids (tables below). A qāriʾ's name means both his ruwāt. **"الباقون" / "غيرهم"** = all twenty minus every rāwī named for another reading of the same point in the same statement. "جميع القراء" / "الأئمة العشرة" = all twenty |
| `khulf` | the readers (subset of `readers`) for whom the book says this is one of two or more wujūh: "بخلف عنه", "بخلاف عنهما", "وجهان", "الوجه الثاني لـ…". `[]` if none |
| `reading` | the book's own words for the reading, short (at most about 12 words), copied from the page |
| `condition` | `"wasl"` if the book limits it to waṣl ("وصلا"), `"waqf"` if to a stop ("عند الوقف", "وقفا"), `null` if both ("وصلا ووقفا", "في الحالين") or not said |
| `scope` | `"all"` if the book says it applies beyond this place ("وهذا مذهبه في كل…", "حيث وقع", "في جميع القرآن"), else `"here"` |
| `quote` | the words of the page that state this row (the reader names and the reading), copied **exactly**, at most 250 characters. It must be found character for character in PAGE (or NEXT PAGE BEGINS for a statement that runs on), and only once: add words until it is unique on the page. Spaces may differ |

Rules:

- When a rāwī has two or more wujūh at a place, write one row per wajh, the rāwī in `khulf` in
  each: "ولورش وجهان: الأول … والثاني …", and also when they are listed in one clause ("بالقصر
  والتوسط والإشباع"), or at a stop ("وجهان: تحقيق الهمزة وتسهيلها"، "أربعة أوجه").
- A `tahrir` statement (which wujūh of *different* rules or places go together: "ستة أوجه: قصر
  البدل وعليه في العارض ثلاثة…", "لخلف أربعة أوجه السكت وتركه وعلى كل…") is one row for the readers
  it is about, `category: null`, its places all in `place`.
- When the readers differ between the places a statement covers (one rāwī only "في الموضع
  الأول"), split the rows by place.
- Waqf statements ("ولو وقف عليه حمزة…") are `usul` rows with `condition: "waqf"`.
- A reference that gives readers the readings of another place ("فيه لحمزة وقفا ما في بناء") is a
  row with those readers, the category of the rule it points to, the reference as `reading`, and
  `khulf: []` (the wujūh are stated at the place it points to);
  split it when it points to different rules for different readers ("فيه لورش وحمزة ما في عذاب
  أليم": Warsh's naql, Ḥamzah's sakt). A reference that names no readers ("سبق", "تقدم") is not a row.
- A wajh that leaves a rule ("تركه", "عدم السكت", "التحقيق بلا سكت") takes that rule's category.
- When the same wajh has a different length for different readers ("فإن حمزة يمد بمقدار ثلاث ألفات
  وهشاما بمقدار ألفين"), split it by reader.
- Write only the wujūh the page states. Don't add combinations it doesn't list ("مع السكون"); at a
  stop on fatḥ tanwīn there is no sukūn, rawm or ishmām (the stop is on the alif).
- A statement that only says what a rāwī doesn't have ("ليس لورش فيه مد بدل") is a row: the
  reading is what he reads instead, in the book's words.
- The rubʿ's closing list "الممال" is statements too: each word in it gives rows (who has imālah,
  who taqlīl), `kind: usul`, an imālah category.
- A wajh at a stop that is another rule (naql to lām al-taʿrīf or across words, sakt) takes that
  rule's category, with `condition: "waqf"`. Naql inside the word at a final hamzah (شيء) is
  hamz_waqf_final. Rawm, ishmām and sukūn with a length at a stop are wujūh of the same rule
  (one row each), not taḥrīr.
- A rule stated in general, or about a word outside HAFS WORDS, is a row too when it names readers
  and a reading: `place: []`, and the word, the book's example or the passage in `place_text`
  ("أنبئهم بالبقرة وننبئهم بالقدر"، "نحو عليكم أنفسكم"، "من بما أنزل إليك إلى المفلحون"). The book's
  combinations of munfaṣil and muttaṣil lengths are `tahrir` rows.
- Not rows: definitions, explanations that name no readers, the bare list of madd degrees
  (مراتب), references back ("سبق", "تقدم") that don't restate readers.

## Reader names (data/readers.yaml)

Qurrāʾ (each means both ruwāt):

| name | ruwāt |
| --- | --- |
| نافع | qalun, warsh |
| ابن كثير | bazzi, qunbul |
| المكي | bazzi, qunbul |
| أبو عمرو | duri_abuamr, susi |
| البصري | duri_abuamr, susi |
| ابن عامر | hisham, ibn_dhakwan |
| الشامي | hisham, ibn_dhakwan |
| عاصم | shuba, hafs |
| حمزة | khalaf_an_hamzah, khallad |
| الكسائي | abul_harith, duri_kisai |
| علي | abul_harith, duri_kisai |
| أبو جعفر | ibn_wardan, ibn_jammaz |
| يعقوب | ruways, rawh |
| خلف | ishaq, idris |
| خلف في اختياره | ishaq, idris |
| خلف عن نفسه | ishaq, idris |
| خلف العاشر | ishaq, idris |

Ruwāt:

| name | id |
| --- | --- |
| قالون | qalun |
| ورش | warsh |
| البزي | bazzi |
| قنبل | qunbul |
| الدوري عن أبي عمرو | duri_abuamr |
| دوري أبي عمرو | duri_abuamr |
| دوري البصري | duri_abuamr |
| السوسي | susi |
| هشام | hisham |
| ابن ذكوان | ibn_dhakwan |
| شعبة | shuba |
| أبو بكر | shuba |
| حفص | hafs |
| خلف عن حمزة | khalaf_an_hamzah |
| خلاد | khallad |
| أبو الحارث | abul_harith |
| الدوري عن الكسائي | duri_kisai |
| دوري الكسائي | duri_kisai |
| دوري علي | duri_kisai |
| الدوري | duri_abuamr |
| ابن وردان | ibn_wardan |
| ابن جماز | ibn_jammaz |
| رويس | ruways |
| روح | rawh |
| إسحاق | ishaq |
| إدريس | idris |

al-Budūr's groups (p. 11):

| name | ruwāt |
| --- | --- |
| المدنيان | qalun, warsh, ibn_wardan, ibn_jammaz |
| البصريان | duri_abuamr, susi, ruways, rawh |
| الأخوان | khalaf_an_hamzah, khallad, abul_harith, duri_kisai |
| الكوفيون | shuba, hafs, khalaf_an_hamzah, khallad, abul_harith, duri_kisai, ishaq, idris |
| الأصحاب | khalaf_an_hamzah, khallad, abul_harith, duri_kisai, ishaq, idris |

Bare "خلف" (or "خلف في اختياره / عن نفسه / العاشر") is Khalaf al-ʿĀshir (al-Budūr p. 11), **except
inside a statement about Ḥamzah's ruwāt**: "لخلف وخلاد"، "لخلف وحده" after Ḥamzah or Khallād is
named, "ولخلف وجهان" in a passage about Ḥamzah's sakt or waqf — there it is Khalaf ʿan Ḥamzah
(the page says so outright at "لخلف وخلاد عن حمزة"). "الدوري" after أبي عمرو / البصري is al-Kisāʾī's (duri_kisai);
otherwise Abū ʿAmr's. "الثلاثة الأصحاب" = الأصحاب.

The twenty ids: qalun, warsh, bazzi, qunbul, duri_abuamr, susi, hisham, ibn_dhakwan, shuba, hafs, khalaf_an_hamzah, khallad, abul_harith, duri_kisai, ibn_wardan, ibn_jammaz, ruways, rawh, ishaq, idris.

## Uṣūl categories

| id | meaning |
| --- | --- |
| munfasil | madd munfaṣil (madd letter, hamzah in the next word) |
| muttasil | madd muttaṣil (hamzah in the same word) |
| badal | madd al-badal (hamzah before a madd letter) |
| lin_hamz | līn before a hamzah (شيء، سوء) |
| madd_arid | madd ʿāriḍ at a stop |
| silah_mim | ṣilah of mīm al-jamʿ before a consonant |
| silah_mim_hamza | ṣilah of mīm al-jamʿ before a hamzah |
| silah_ha | ṣilah of hāʾ al-ḍamīr (فيه، منه) |
| ibdal_sakin | ibdāl of a sākin hamzah (يؤمنون) |
| naql | naql of a hamzah's vowel to a sākin before it |
| sakt_al | sakt on the mafṣūl khāṣ: lām al-taʿrīf before a hamzah (ٱلۡأَرۡضِ), and شيء |
| sakt_mafsul | sakt on the mafṣūl ʿām: a sākin at a word's end before a hamzah (عذاب أليم، عليهم أنذرتهم) |
| idgham_kabir | idghām kabīr (al-Sūsī's and those who agree) |
| idgham_ghunna | idghām of nūn/tanwīn with or without ghunnah |
| hamzatayn | two hamzahs in one word (ءأنذرتهم) |
| hamzatayn_kalimatayn_muttafiq | two hamzahs across words, same vowel |
| hamzatayn_kalimatayn_mukhtalif | two hamzahs across words, different vowels (السفهاء ألا) |
| imala_ra | imālah of an alif before a rāʾ with kasrah (أبصارهم، النار) |
| imala_kafirin | imālah of الكافرين |
| imala_nas | imālah of الناس (majrūr) |
| imala_ya | imālah/taqlīl of an alif from yāʾ (هدى) |
| imala_ya_ra | imālah/taqlīl of ذوات الراء (alif from yāʾ after a rāʾ) |
| imala_jaa_shaa | imālah of جاء، شاء |
| imala_zad | imālah of زاد |
| imala_fiil | imālah of other listed verbs |
| imala_duri_kisai | al-Dūrī ʿan al-Kisāʾī's own imālah words (طغيانهم، آذانهم) |
| sakt_huruf | sakt on the ḥurūf al-muqaṭṭaʿah (Abū Jaʿfar) |
| tarqiq_ra | tarqīq of rāʾ (Warsh) |
| taghliz_lam | taghlīẓ of lām (Warsh) |
| hadhf_damm | dropping the hamzah of مستهزءون and the like in waṣl and waqf (Abū Jaʿfar); Ḥamzah's at a stop is hamz_waqf_mid |
| ibdal_sakin_waqf | ibdāl of a sākin hamzah at a stop (Ḥamzah) |
| hamzatayn_waqf | two hamzahs at a stop |
| hamz_waqf_final | a final hamzah at a stop (Ḥamzah, Hishām): after an alif (السماء: ibdāl, tas-hīl with rawm) or another sākin in the same word (شيء: naql, idghām; this naql is hamz_waqf_final, not naql) |
| hamz_waqf_zaid | a hamzah after a prefix letter (و ف ب ل ك ها يا) at a stop. After lām al-taʿrīf, or at the start of a word after a sākin (عذاب أليم), the waqf wujūh are sakt_al / sakt_mafsul / naql |
| hamz_waqf_mid | a middle hamzah at a stop (Ḥamzah), after a mutaḥarrik or an alif (مستهزءون، أضاءت). A hamzah before the alif of fatḥ tanwīn (بناءً) is middle: the stop is on the alif |

## Worked example (page 15, not one you will be given)

Page text:

> مالك يوم الدين » قرأ عاصم والكسائي ويعقوب وخلف في اختياره بإثبات ألف بعد الميم لفظا والباقون يحذفها .
> الصراط ، وصراط » قرأ قنبل ورويس بالسين فيهما حيث وقعا . وقرأ خلف عن حمزة بالصاد مشمة صوت الزاى حيث وقعا كذلك. وقر أخلاد مثل خلف في الموضع الأول خاصة وهو واهدنا الصراط المستقيم » فى هذه السورة . والباقون بالصاد الخالصة في جميع القرآن .

HAFS WORDS include `1:4:1 مَٰلِكِ`, `1:6:2 ٱلصِّرَٰطَ`, `1:7:1 صِرَٰطَ`. Rows:

```json
[
 {"place": ["1:4:1"], "kind": "farsh", "category": null, "readers": ["shuba", "hafs", "abul_harith", "duri_kisai", "ruways", "rawh", "ishaq", "idris"], "khulf": [], "reading": "بإثبات ألف بعد الميم لفظا", "condition": null, "scope": "here", "quote": "قرأ عاصم والكسائي ويعقوب وخلف في اختياره بإثبات ألف بعد الميم لفظا"},
 {"place": ["1:4:1"], "kind": "farsh", "category": null, "readers": ["qalun", "warsh", "bazzi", "qunbul", "duri_abuamr", "susi", "hisham", "ibn_dhakwan", "khalaf_an_hamzah", "khallad", "ibn_wardan", "ibn_jammaz"], "khulf": [], "reading": "يحذفها", "condition": null, "scope": "here", "quote": "والباقون يحذفها"},
 {"place": ["1:6:2", "1:7:1"], "kind": "farsh", "category": null, "readers": ["qunbul", "ruways"], "khulf": [], "reading": "بالسين", "condition": null, "scope": "all", "quote": "قرأ قنبل ورويس بالسين فيهما حيث وقعا"},
 {"place": ["1:6:2", "1:7:1"], "kind": "farsh", "category": null, "readers": ["khalaf_an_hamzah"], "khulf": [], "reading": "بالصاد مشمة صوت الزاى", "condition": null, "scope": "all", "quote": "وقرأ خلف عن حمزة بالصاد مشمة صوت الزاى حيث وقعا كذلك"},
 {"place": ["1:6:2"], "kind": "farsh", "category": null, "readers": ["khallad"], "khulf": [], "reading": "مثل خلف في الموضع الأول خاصة", "condition": null, "scope": "here", "quote": "وقر أخلاد مثل خلف في الموضع الأول خاصة"},
 {"place": ["1:6:2"], "kind": "farsh", "category": null, "readers": ["qalun", "warsh", "bazzi", "duri_abuamr", "susi", "hisham", "ibn_dhakwan", "shuba", "hafs", "abul_harith", "duri_kisai", "ibn_wardan", "ibn_jammaz", "rawh", "ishaq", "idris"], "khulf": [], "reading": "بالصاد الخالصة", "condition": null, "scope": "all", "quote": "والباقون بالصاد الخالصة في جميع القرآن"},
 {"place": ["1:7:1"], "kind": "farsh", "category": null, "readers": ["qalun", "warsh", "bazzi", "duri_abuamr", "susi", "hisham", "ibn_dhakwan", "shuba", "hafs", "khallad", "abul_harith", "duri_kisai", "ibn_wardan", "ibn_jammaz", "rawh", "ishaq", "idris"], "khulf": [], "reading": "بالصاد الخالصة", "condition": null, "scope": "all", "quote": "والباقون بالصاد الخالصة في جميع القرآن"}
]
```

Check before you write: every rāwī id is one of the twenty; `khulf` ⊆ `readers`; every quote is
copied, not retyped from memory; for a place with "الباقون", the rows of that point together
name each of the twenty once (twice for a rāwī with khulf).
