# Uṣūl sources on Aljam3

2026-11-24. The spike learned uṣūl from al-Futūḥ's rows, which leaves gaps the rows can't fill:
categories a passage never shows, khulf against omission, and taḥrīr. These muʿtabar books
state the uṣūl directly, are on Aljam3 (searchable, page links), and stay within al-Shāṭibiyyah and
al-Durrah unless noted.

| Book | Aljam3 | Covers | Organised | Gives us | Text |
| --- | --- | --- | --- | --- | --- |
| al-Qāḍī, *al-Budūr al-Zāhira* | [3480](https://aljam3.com/ar/3480) (typed); 4983 and 16689 are scans | the ten, Shāṭibiyyah + Durrah | by place, surah order | per-place readings **and taḥrīr in prose** (combinations allowed, "على كل…", "المعتمد وجوب التسوية") | good; search misses some phrases |
| al-Qāḍī, *al-Wāfī fī Sharḥ al-Shāṭibiyyah* | [1037](https://aljam3.com/ar/1037) | the seven | by bāb (uṣūl chapters), then farsh | **rules with conditions and ruwāt**, e.g. imālah of an alif before a final kasrah rāʾ for Abū ʿAmr and al-Dūrī ʿan al-Kisāʾī, Warsh taqlīl in the whole bāb (p. 151) | good |
| al-Qāḍī, *al-Īḍāḥ li-Matn al-Durrah* | [16501](https://aljam3.com/ar/16501) | the three | by bāb, following the Durrah | rules and **occurrence lists**, e.g. Ruways's idghām kabīr: four places firmly, a listed set with khulf incl. 2:20 (pp. 62–64) | good |
| al-Ṣafāqusī, *Ghayth al-Nafʿ* | [1045](https://aljam3.com/ar/1045); 16733 is a 4-volume edition | the seven | by place, with each place's uṣūl type ("المدغم", "الممال"…) | **occurrence lists by category**, and notes on the rules | good |
| al-Ḍabbāʿ, *Sharḥ Itḥāf al-Bariyyah bi-Taḥrīrāt al-Shāṭibiyyah* | [16390](https://aljam3.com/ar/16390) | the seven | by bāb | taḥrīrāt of the Shāṭibiyyah | not checked yet |
| al-Qāḍī, *al-Buḥūr al-Zākhira fī Shawāhid al-Budūr* | [16670](https://aljam3.com/ar/16670) | the ten | follows al-Budūr | the matn verses behind al-Budūr | not checked yet |

Out of scope by ṭarīq: Muḥaysin's *al-Muhadhdhab* (al-Ṭayyibah), al-Nashshār's *al-Budūr*.

Also in our own data: **al-Futūḥ's footnotes ("تفاصيل المقطع")** state, word by word, who reads
what, with the matn verses (ش / د): e.g. vol. 1 p. 62 fn 1, "(لَذَهَب بِّسَمۡعِهِمۡ) قرأها السوسي، ورويس
بخلاف عنه بالإدغام الكبير". The extraction already has them as `footnote` / `text` records; the
spike doesn't read them yet.

Checked so far against the spike:
- Ruways at 2:20: al-Futūḥ's footnote and al-Īḍāḥ pp. 62–64 agree (khulf there, izhār elsewhere
  except four places). Recorded in `spike/data/place_wujuh.yaml` with both citations.
- Abū ʿAmr's imālah in أَبۡصَٰرِهِمۡ: al-Wāfī p. 151 (the rule) matches the corrected spike.

## How they would fit the model

1. **Profiles** (rāwī × category → wujūh): from the uṣūl chapters of al-Wāfī (the seven) and
   al-Īḍāḥ (the three), each row citing a page. They replace profiles learned from rows, which is
   what limits held-out prediction (82–89%).
2. **Occurrence tables** (which places a category applies to, with exceptions): from Ghayth al-Nafʿ's
   per-place types and the lists in al-Wāfī and al-Īḍāḥ, checked against the detectors.
3. **Constraints** (taḥrīr): from al-Budūr's per-place prose and al-Ḍabbāʿ; al-Futūḥ's boxes then
   test them, instead of being the only source.
4. **Checks**: al-Futūḥ (rows and footnotes) and alkiraat.com's al-Jīqarawī as independent jamʿ
   sources.

Rule 1 still holds: each fact becomes a candidate row with its page, read from the page itself (OCR
text is checked against the PDF), and reviewed. Nothing is filled in from memory.
