# Extracting the farsh of a sūrah (al-Wāfī, al-Īḍāḥ)

You read one page of a **farsh chapter** (فرش الحروف): **al-Wāfī fī Sharḥ al-Shāṭibiyyah** (the
seven qurrāʾ, 14 ruwāt) or **al-Īḍāḥ li-Matn al-Durrah** (Abū Jaʿfar, Yaʿqūb, Khalaf al-ʿĀshir: 6
ruwāt). Write down every statement of **who reads a word how**. The text is OCR; read through it,
never correct a quote. Use only the page; add nothing you know about the qirāʾāt.

## Input

`## PAGE` (statements start here) and `## NEXT PAGE BEGINS` (only to finish a statement that runs
on; don't extract statements that start there).

## Output

`{"book": "wafi", "page": 236, "rows": [...]}` to the file you're told. One row per clause that gives
readers a reading of a word:

| field | what |
| --- | --- |
| `sura` | the number of the sūrah the word is in: the chapter's sūrah, unless the book names another ("في الأنعام", "بيوسف") |
| `ayah` | the āyah number if the book gives it (al-Īḍāḥ writes `[٨٠]`), as a number; else `null` |
| `word` | **the one word the reading is about**, as the book writes it ("يأمركم" in "ولا يأمركم"; "قرح" in "إن يمسسكم قرح"; "قتلوا" in "لو أطاعونا ما قتلوا") |
| `words` | that word with the neighbouring words the book quotes, in order, if they help find it ("ولا يأمركم"); just the word if none; no vowels you add |
| `where` | `"here"`: this place; `"all"`: the book says wherever it occurs (حيث وقع، كيف أتى، في جميع القرآن، حيث ذكر); `"listed"`: places the book lists (put them in `sites`) |
| `sites` | for `"listed"`: the book's words for each place ("في الأنعام", "موضعي آل عمران"); else `[]` |
| `readers` | ruwāt ids the clause gives this reading to |
| `khulf` | those of them for whom it is one of two wujūh (بخلف عنه، بالوجهين، وجهان) |
| `reading` | the book's words for the reading, short ("بكسر الحاء", "بالياء على الغيب") |
| `condition` | `"wasl"`, `"waqf"` or `null` |
| `quote` | the words of the page that state it, copied exactly, at most 250 characters, found once on the page |

## Rules

- **"الباقون" / "غيرهم" / "وقرأ غيره"** is the rest *of the book's readers*: in al-Wāfī the 14 ruwāt,
  in al-Īḍāḥ the 6. Never the twenty. Write the rest out as ids.
- A qāriʾ's name is both his ruwāt; a rāwī's name only him.
- **al-Wāfī**: "خلف" is Ḥamzah's rāwī (khalaf_an_hamzah). The verse's codes (رموز) are explained in
  the prose; read the prose, not the codes.
- **al-Īḍāḥ**: "خلف" is Khalaf al-ʿĀshir (ishaq, idris). Its footnotes name the other Durrah readers:
  "وكذا خلف من الوفاق" (Khalaf reads the same as the main text says: give him that reading),
  "ويعقوب بفتح الحاء من الوفاق" (Yaʿqūb reads fatḥ: a row with that reading). Extract those too.
  A footnote quoting the Shāṭibiyyah ("قال الإمام الشاطبي : …") is not a row.
  "وكل من لم يذكر في هذه التراجم فهو موافق لأصله" is a general note, not a row.
- **Only farsh**: a reading of a particular word. Not rows: uṣūl rules the chapter recalls in passing
  (madd, imālah lists, idghām, hamz rules, waqf of Ḥamzah), grammar, meaning, justification (توجيه،
  حجة، وجه القراءة), the verse's wording explained, history.
- Two readings for the same readers (khulf) are two rows, each with them in `khulf`.
- One place per row: if the book gives one statement for two different words, write two rows with
  the same quote, each with its own `word`.
- **The yāʾāt al-iḍāfah list** at a chapter's end ("ياءات الإضافة"): not rows (they have their own
  table). The **zawāʾid** list likewise.

## Reader names

Qurrāʾ: نافع = qalun/warsh, ابن كثير = bazzi/qunbul, المكي = bazzi/qunbul, أبو عمرو = duri_abuamr/susi,
البصري = duri_abuamr/susi, ابن عامر = hisham/ibn_dhakwan, الشامي = hisham/ibn_dhakwan, عاصم = shuba/hafs,
حمزة = khalaf_an_hamzah/khallad, الكسائي = abul_harith/duri_kisai, علي = abul_harith/duri_kisai,
الكوفيون = shuba/hafs/khalaf_an_hamzah/khallad/abul_harith/duri_kisai (al-Wāfī), الأخوان = Ḥamzah and al-Kisāʾī,
أبو جعفر = ibn_wardan/ibn_jammaz, يعقوب = ruways/rawh.

Ruwāt: قالون = qalun, ورش = warsh, البزي = bazzi, قنبل = qunbul, الدوري عن أبي عمرو = duri_abuamr,
السوسي = susi, هشام = hisham, ابن ذكوان = ibn_dhakwan, شعبة / أبو بكر = shuba, حفص = hafs,
خلاد = khallad, أبو الحارث = abul_harith, الدوري عن الكسائي = duri_kisai, ابن وردان = ibn_wardan,
ابن جماز = ibn_jammaz, رويس = ruways, روح = rawh, إسحاق = ishaq, إدريس = idris.

The ids: qalun, warsh, bazzi, qunbul, duri_abuamr, susi, hisham, ibn_dhakwan, shuba, hafs,
khalaf_an_hamzah, khallad, abul_harith, duri_kisai, ibn_wardan, ibn_jammaz, ruways, rawh, ishaq, idris.

## Check before you write

Every rāwī id is one of the twenty and one of the book's readers (al-Wāfī: the first 14; al-Īḍāḥ: the
last 6); `khulf` ⊆ `readers`; every quote is copied, not retyped; for a word with "الباقون", the rows
of that word together name each of the book's readers once (twice with khulf).
