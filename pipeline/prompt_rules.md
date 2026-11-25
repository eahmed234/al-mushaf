# Extracting the rules of an uṣūl chapter (al-Wāfī, al-Īḍāḥ)

You read one page of an uṣūl chapter: **al-Wāfī fī Sharḥ al-Shāṭibiyyah** (the seven qurrāʾ, 14
ruwāt) or **al-Īḍāḥ li-Matn al-Durrah** (Abū Jaʿfar, Yaʿqūb, Khalaf al-ʿĀshir: 6 ruwāt). Write down
every **rule** the page states: who reads what, and where it applies. The text is OCR; read
through it, never correct a quote. Use only the page; add nothing you know.

## Input

`## PAGE` (statements start here) and `## NEXT PAGE BEGINS` (only to finish a statement).

## Output

`{"book": "wafi", "page": 51, "rows": [...]}` to the file you're told. One row per clause that gives
readers a reading:

| field | what |
| --- | --- |
| `category` | an id from the table below, or `"new:<short_snake_id>"` for a rule no category covers (e.g. `new:mim_before_sakin`) |
| `wajh` | the wajh id from that category's list, or `null` (new categories, or none fits) |
| `readers` | ruwāt ids the clause gives the reading to (tables below) |
| `khulf` | those of them for whom it is one of two or more wujūh ("بخلف عنه", "بالوجهين", "وجهان") |
| `reading` | the book's words for the reading, short |
| `applies` | the book's words for where it applies (the condition: "إذا وقعت قبل متحرك", "بعد ياء ساكنة"), short; `""` if it names words only |
| `words` | the Qurʾānic words the book names as **covered** (as the page writes them, without vowels you add); `[]` if none |
| `except` | words the book names as **excluded** from the rule; `[]` if none |
| `scope` | `"all"`: everywhere the condition holds; `"listed"`: only the words named; `"place"`: one place (say which in `words`) |
| `condition` | `"wasl"`, `"waqf"` or `null` (both / not said) |
| `quote` | the words of the page that state it, copied exactly, at most 250 characters, found once on the page |

Rules:

- **"الباقون" / "غيرهم"** means the rest *of the book's readers*: in al-Wāfī the 14 ruwāt of the seven;
  in al-Īḍāḥ the 6 of the three. Never the twenty.
- A reader's name means both his ruwāt. In **al-Wāfī** "خلف" is Ḥamzah's rāwī (khalaf_an_hamzah):
  Khalaf al-ʿĀshir isn't in the Shāṭibiyyah. In **al-Īḍāḥ** "خلف" is Khalaf al-ʿĀshir (ishaq, idris),
  and "إسحاق" / "إدريس" his ruwāt. Codes in the verse (رموز) are explained in the prose; read the prose.
- al-Īḍāḥ often says a reader "follows his aṣl" (يوافق أصله، كأصله) or differs from it (خالف أصله): write
  the reading it states; if it gives none beyond "his aṣl", use `reading: "كأصله"`, `wajh: null`.
- **Use an existing category whenever the rule is that category**: the ṣilah of hāʾ al-kināyah is
  `silah_ha` (its listed exceptions too, with `scope: "listed"`), the ṣilah of mīm al-jamʿ is
  `silah_mim` / `silah_mim_hamza`. A rule about named words inside a bāb takes the bāb's category
  with `scope: "listed"`. Use `new:` only for a rule no category is about; before naming one, reuse a
  `new:` name you already used if it's the same rule (one name per rule, across both books).
- One wajh per row: two wujūh for the same readers are two rows, each with them in `khulf`.
- Not rows: definitions, grammar, justifications (حجة، توجيه), the poem's wording explained, history.

## Reader names

Qurrāʾ: نافع = qalun/warsh, ابن كثير = bazzi/qunbul, المكي = bazzi/qunbul, أبو عمرو = duri_abuamr/susi, البصري = duri_abuamr/susi, ابن عامر = hisham/ibn_dhakwan, الشامي = hisham/ibn_dhakwan, عاصم = shuba/hafs, حمزة = khalaf_an_hamzah/khallad, الكسائي = abul_harith/duri_kisai, علي = abul_harith/duri_kisai, أبو جعفر = ibn_wardan/ibn_jammaz, يعقوب = ruways/rawh.

Ruwāt: قالون = qalun, ورش = warsh, البزي = bazzi, قنبل = qunbul, الدوري عن أبي عمرو = duri_abuamr, دوري أبي عمرو = duri_abuamr, دوري البصري = duri_abuamr, السوسي = susi, هشام = hisham, ابن ذكوان = ibn_dhakwan, شعبة = shuba, أبو بكر = shuba, حفص = hafs, خلف عن حمزة = khalaf_an_hamzah, خلاد = khallad, أبو الحارث = abul_harith, الدوري عن الكسائي = duri_kisai, دوري الكسائي = duri_kisai, دوري علي = duri_kisai, الدوري = duri_abuamr, ابن وردان = ibn_wardan, ابن جماز = ibn_jammaz, رويس = ruways, روح = rawh, إسحاق = ishaq, إدريس = idris.

The ids: qalun, warsh, bazzi, qunbul, duri_abuamr, susi, hisham, ibn_dhakwan, shuba, hafs,
khalaf_an_hamzah, khallad, abul_harith, duri_kisai, ibn_wardan, ibn_jammaz, ruways, rawh, ishaq, idris.

## Uṣūl categories

| id | meaning | wujūh ids |
| --- | --- | --- |
| munfasil | madd munfaṣil (madd letter, hamzah in the next word) | qasr, tawassut, ishba |
| muttasil | madd muttaṣil (hamzah in the same word) | tawassut, ishba |
| badal | madd al-badal (hamzah before a madd letter) | qasr, tawassut, tul |
| lin_hamz | līn before a hamzah (شيء، سوء) | qasr, tawassut, tul |
| madd_arid | madd ʿāriḍ at a stop | qasr, tawassut, ishba |
| silah_mim | ṣilah of mīm al-jamʿ before a consonant | sukun, silah |
| silah_mim_hamza | ṣilah of mīm al-jamʿ before a hamzah | sukun, silah |
| silah_ha | ṣilah of hāʾ al-ḍamīr (فيه، منه) | none, silah |
| ibdal_sakin | ibdāl of a sākin hamzah (يؤمنون) | tahqiq, ibdal |
| naql | naql of a hamzah's vowel to a sākin before it | none, naql |
| sakt_al | sakt on the mafṣūl khāṣ: lām al-taʿrīf before a hamzah (ٱلۡأَرۡضِ), and شيء | none, sakt |
| sakt_mafsul | sakt on the mafṣūl ʿām: a sākin at a word's end before a hamzah (عذاب أليم، عليهم أنذرتهم) | none, sakt |
| idgham_kabir | idghām kabīr (al-Sūsī's and those who agree) |
| idgham_ghunna | idghām of nūn/tanwīn with or without ghunnah |
| hamzatayn | two hamzahs in one word (ءأنذرتهم) | tahqiq, tashil, tashil_idkhal, tahqiq_idkhal, ibdal |
| hamzatayn_kalimatayn_muttafiq | two hamzahs across words, same vowel | (see note) |
| hamzatayn_kalimatayn_mukhtalif | two hamzahs across words, different vowels (السفهاء ألا) | (see note) |
| imala_ra | imālah of an alif before a rāʾ with kasrah (أبصارهم، النار) | fath, taqlil, imala |
| imala_kafirin | imālah of الكافرين | fath, taqlil, imala |
| imala_nas | imālah of الناس (majrūr) | fath, imala |
| imala_ya | imālah/taqlīl of an alif from yāʾ (هدى) | fath, taqlil, imala |
| imala_ya_ra | imālah/taqlīl of ذوات الراء (alif from yāʾ after a rāʾ) | fath, taqlil, imala |
| imala_jaa_shaa | imālah of جاء، شاء | fath, imala |
| imala_zad | imālah of زاد | fath, imala |
| imala_fiil | imālah of other listed verbs | fath, imala |
| imala_duri_kisai | al-Dūrī ʿan al-Kisāʾī's own imālah words (طغيانهم، آذانهم) | fath, imala |
| sakt_huruf | sakt on the ḥurūf al-muqaṭṭaʿah (Abū Jaʿfar) | none, sakt |
| tarqiq_ra | tarqīq of rāʾ (Warsh) | tafkhim, tarqiq |
| taghliz_lam | taghlīẓ of lām (Warsh) | tarqiq, taghliz |
| hadhf_damm | dropping the hamzah of مستهزءون and the like in waṣl and waqf (Abū Jaʿfar); Ḥamzah's at a stop is hamz_waqf_mid | tahqiq, hadhf |
| ibdal_sakin_waqf | ibdāl of a sākin hamzah at a stop (Ḥamzah) | tahqiq, ibdal |
| hamzatayn_waqf | two hamzahs at a stop | tahqiq, tashil, tashil_idkhal, tahqiq_idkhal, ibdal |
| hamz_waqf_final | a final hamzah at a stop (Ḥamzah, Hishām): after an alif (السماء: ibdāl, tas-hīl with rawm) or another sākin in the same word (شيء: naql, idghām; this naql is hamz_waqf_final, not naql) | tahqiq, ibdal_madd, ibdal_qasr, tashil_rawm_madd, tashil_rawm_qasr |
| hamz_waqf_zaid | a hamzah after a prefix letter (و ف ب ل ك ها يا) at a stop. After lām al-taʿrīf, or at the start of a word after a sākin (عذاب أليم), the waqf wujūh are sakt_al / sakt_mafsul / naql | tahqiq, tashil |
| hamz_waqf_mid | a middle hamzah at a stop (Ḥamzah), after a mutaḥarrik or an alif (مستهزءون، أضاءت). A hamzah before the alif of fatḥ tanwīn (بناءً) is middle: the stop is on the alif | tahqiq, tashil, hadhf, ibdal_ya |

