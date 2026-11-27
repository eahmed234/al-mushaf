# The spike extended: the sources used up, then an API over data/

2026-11-27. Two questions: (1) have the source books been used fully for the spike's scope
(al-Fātiḥah, al-Baqarah, Āl ʿImrān)? (2) does the way `data/` is stored serve retrieval? A first
API (`mushaf_data/api.py`, milestone 8's resolve / enumerate / explain) was built to find out.

## 1. The books, for sūrahs 1-3

| Book | What it gives | State |
| --- | --- | --- |
| al-Wāfī | uṣūl (all twenty, with al-Īḍāḥ), farsh of the seven | read: uṣūl chapters; farsh pp. 50-52, 199-242 |
| al-Īḍāḥ | uṣūl and farsh of the Durrah three | read: uṣūl chapters; farsh pp. 52-55, 187-230 |
| al-Budūr | every place, all ten; per-rubʿ imālah and idghām lists | pp. 15-75 extracted (farsh, uṣūl, taḥrīr, waqf rows); imālah lists used; **uṣūl rows now checked through Āl ʿImrān** |
| al-Ḍabbāʿ | taḥrīr of the Shāṭibiyyah | **read this session**: pp. 153-296, 225 statements → `data/tahrir/dabba.yaml` |
| Ghayth al-Nafʿ | farsh of the seven, āyah counts | not read (Eisa: al-Ḍabbāʿ only, for now); used by hand in review |
| al-Buḥūr | al-Budūr's verse evidence | nothing new to extract; cited by hand |
| al-Futūḥ | boxes per place | a check, never a source |

Read but not used yet: al-Budūr's "المدغم" lists (idghām kabīr occurrences, milestone 5) and its
178 waqf-on-hamz rows (against `waqf.py`, milestone 5); its 69 taḥrīr statements now sit in
`data/tahrir/budur.yaml` by place.

What this found in the tables (fixed from the page, `pipeline/unify_gaps.py`):
- Hishām, the second hamzah maḍmūmah: idkhāl with a khulf, and at Ṣād and al-Qamar tas-hīl too
  (wafi 90-91). The table had Ḥafṣ's taḥqīq for him, uncited.
- imālah: "النهار" listed as no-imālah stood for every النهار; wafi 152 means ويولج النهار (the rāʾ
  maftūḥah). Now the phrase.
- `naql_word` (naql across words, عَذَابٌ أَلِيمٌ) had no link to the naql table, so the engine read
  it as Ḥafṣ for everyone. Linked (`usul_tables.ENGINE_ONLY`): al-Futūḥ from the books alone
  661 → 664 of 666 pairs.
- al-Ḍabbāʿ's 99 restrictions against the uṣūl tables: 6 flagged, none a table error (each is
  about one case of a table, the check compares the whole table).

## 2. The API

```python
from mushaf_data.api import Mushaf
m = Mushaf(edition="sughra", options=(), farsh="books")   # or farsh="budur"
m.read("warsh", "2:1-5")       # per word: text, farsh options, rules (table, case, wujūh+cites, chosen), stop, waqf form
m.choices("warsh", "2:1-20")   # category → wujūh with cites: the reading's free choices
m.count("warsh", "2:1-20")     # 72 combinations, 18 after taḥrīr
m.who("1:4:1")                 # the twenty grouped by reading, with cites
m.explain("1:4:1")             # both farsh tables, rules per rāwī, taḥrīr at the word
```

`python3 -m mushaf_data.api warsh 2:1-5`; `python3 -m checks.api` (against KFGQPC).

| Measure | Result |
| --- | --- |
| KFGQPC's eight riwāyāt, sūrahs 1-3, every word | **75,653 / 76,375 agree (99.1%)**, 0 unaligned, 625 with no text (farsh) |
| the same with al-Budūr's farsh tables | 98.8% before the naql fix, same as the books' |
| speed | load 1.7 s; a whole sūrah 0.6 s warm (2.3 s cold); choices and count 0.2 s |

What's left of the 0.9%: engine detectors, not data. The vocative يَٰٓأَيُّهَا as munfaṣil (Qālūn,
Ibn Kathīr, al-Sūsī: ~63 each), Warsh's imālah marks in KFGQPC's writing (146), idghām inside a
word (al-Sūsī خَلَقكُّمۡ), أَلَا with KFGQPC's sign.

## 3. Does the storage serve retrieval?

**Works as stored**
- The spine's projection per rāwī (added and empty slots) makes a passage's word list one call.
- The uṣūl tables reach every word with their page cites, editions and options included; a reading
  is the span's choices (one wajh per category: the khulf convention), so a whole sūrah's
  readings are a short list of choices, not millions of texts.
- Taḥrīr as allowed tuples filters cleanly; candidate statements hang off places and categories.

**Doesn't, in order of cost**
1. **Farsh options are the book's words, not text.** "بالألف" can't be rendered: 625 words in three
   sūrahs for KFGQPC's eight have no text, more for the others (Ibn ʿĀmir, the Kūfīs, the Durrah
   have no KFGQPC text at all). The uṣūl can't run on those words either. It is also why the two
   farsh tables can't be compared for the Durrah readers: Yaʿqūb's "بالألف" at مالك is Ḥafṣ's own,
   but nothing says so. **Needed: each option's text per slot** (`text: {slot: …}`), written from the
   book's words and checked against KFGQPC wherever one of its readers has a file.
2. **One table case per engine category.** The tables have finer cases (hamzatayn: maftūḥah,
   maksūrah, maḍmūmah…) but the engine reads one (`usul_tables.where`), so Hishām's fix above
   doesn't reach a reading yet. The case-from-the-word logic exists, but in a check
   (`pipeline/crosscheck_budur.case_for`). **Needed: the engine picks the case per word.**
3. **Listed words are bare words, matched at run time.** One bare word in a list (النهار) changed
   every occurrence. `pipeline/anchor.py` ties three tables' lists to slots; **all listed entries
   should store their slots**.
4. **al-Budūr's `recurs` stores word forms**, expanded by searching the Qurʾān when a check runs;
   the books' tables store slots. Store slots.
5. **Taḥrīr candidates use ids the engine doesn't have** (madd degrees, specific places' features:
   `alan_alif1`, `farsh_haantum`). They're served as statements; enforcing them needs the
   categories, then Eisa's review.

## 4. Next

In order of what unblocks most: (1) option text for the farsh of 1-3 (a model writes it from the
book's words; KFGQPC checks the eight; Eisa reviews the rest); (2) per-word case selection in the
engine; (3) anchor every listed entry; then milestone 4 continues (al-Nisāʾ on) with the text in
the extraction from the start.
