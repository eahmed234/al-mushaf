# Unifying a category across the Shāṭibiyyah and the Durrah

You get one category's rules as read from two books: **al-Wāfī** (the Shāṭibiyyah: the seven
qurrāʾ, 14 ruwāt) and **al-Īḍāḥ** (the Durrah: Abū Jaʿfar, Yaʿqūb, Khalaf al-ʿĀshir, 6 ruwāt),
one row per statement, each with its page and the page's own words (`quote`), plus the category's
**reviewed profile rows** where it already exists. Write **one table for all twenty ruwāt**, in
**one vocabulary of wujūh**: the same rule described the same way whichever book states it.

Use only what the rows and the profile rows say. Add nothing from your own knowledge of the
qirāʾāt. Where the rows don't settle something, say so in `open`, don't guess.

## Output: `pipeline/unified/<category>.yaml`

```yaml
category: silah_mim
what: one sentence, English
wujuh:                     # the vocabulary; first = Ḥafṣ's reading
  - {id: sukun, ar: إسكان الميم, en: sukūn of the mīm}
  - {id: silah, ar: صلة الميم بواو, en: ṣilah with a wāw}
cases:                     # one per condition with its own wujūh (most categories have one)
  - case: before a consonant (حرف متحرك)
    ruwat:                 # all twenty, in this order:
      qalun: {wujuh: [sukun, silah], cite: [wafi 51]}
      ...
      ibn_wardan: {wujuh: [silah], cite: [idah 57]}
      ...
listed:                    # named words read otherwise than their case says
  - words: [أنلزمكموها]     # as the book writes them
    case: before a consonant
    ruwat: {qalun: [silah]}  # only the ruwāt whose reading here differs from their case
    cite: [wafi 51]
open:                      # what the rows leave unsettled, each with its pages
  - "…"
```

The twenty, in order: qalun, warsh, bazzi, qunbul, duri_abuamr, susi, hisham, ibn_dhakwan, shuba,
hafs, khalaf_an_hamzah, khallad, abul_harith, duri_kisai, ibn_wardan, ibn_jammaz, ruways, rawh,
ishaq, idris.

## Rules

- **Keep existing wujūh ids** (`existing_wujuh_ids`) as they are; add ids only for what they lack,
  short snake_case English (`kasr_ha`, `itbaa`, `opened`, `kept_wasl`). Labels `ar` in the books'
  own terms. One id per reading, used for both books.
- **Every case lists all twenty.** The Shāṭibiyyah rows give the fourteen, the Durrah rows the six.
  "الباقون" in al-Wāfī is the rest of the fourteen; in al-Īḍāḥ the rest of the six.
- **The Durrah's "كأصله" / "يوافق أصله"**: the rāwī reads as his aṣl — Abū Jaʿfar's ruwāt as Nāfiʿ,
  Yaʿqūb's as Abū ʿAmr, Khalaf al-ʿĀshir's as Khalaf ʿan Ḥamzah (al-Īḍāḥ pp. 40–43). Give the aṣl's
  wujūh and mark it: `{wujuh: [...], cite: [idah N], via: asl}`. If the aṣl's two ruwāt differ and the
  row doesn't say which, put it in `open`.
- **A rāwī no row speaks of** for a case: `{wujuh: [], cite: []}` and a line in `open`. Never fill
  the default in silently.
- **Khulf**: a rāwī with two wujūh lists both (the book's preferred first if it says which).
- **Disagreement** between the two books, between rows, or with the reviewed profile rows: keep
  what the rows say, and write it in `open` with both pages. Don't resolve it yourself.
- `kind: per_word` categories (idghām ṣaghīr, the yāʾāt): no general cases beyond the book's own
  classes; put every word in `listed`, with the reading of each rāwī who has one stated.
- Statements about ikhtiyār, views the book rejects, or a single shaykh's choice: in `open`, not
  in the table.
