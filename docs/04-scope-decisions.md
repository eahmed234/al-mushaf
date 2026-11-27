# Scope decisions: waqf marks, marking without colour, ḥadhf and ziyādah

2026-11-24. Three questions that came up after the spike, about what the reading model owns and
what a page shows. Proposed by Claude, agreed by Eisa (Eisa and Yusuf decide jointly); each says
what it changes in the build.

## 1. Waqf marks are a property of the edition, not of the reading

The pause signs differ between editions: the Madinah / KFGQPC set, the IndoPak set (the Waterval
edition has more wuqūf than KFGQPC's), and the Maghribi Habṭī set in Warsh and Qālūn maṣāḥif.
Separately, each riwāyah's mushaf numbers ayahs by its own count (Madanī, Makkī, Baṣrī, Kūfī…),
which moves the ayah-end stops.

**Decision.** Two layers, kept apart:

- **The engine can stop on any word.** The stop is already an input to generation (the spike's
  Q4), and the waqf chapter (`spike/waqf.py`) gives the forms for whatever word is stopped on. It
  doesn't know which edition marked the place.
- **Mark sets are data**, one file per edition: word boundary → sign type, with its source. The
  app shows the set the user picks and offers its places as stops. **Ayah counts** are a separate
  data file per riwāyah.

**Open:** a digitised IndoPak text with its marks under a usable licence (QUL has IndoPak scripts
to check). The Habṭī set for the Maghribi riwāyāt needs a source too.

## 2. Features are marked, colour is optional

A reading is text plus features (the spike's Q5): madd lengths (muttaṣil, munfaṣil, badal, līn,
ʿāriḍ), sakt, imālah against taqlīl, ishmām, rawm, tarqīq and taghlīẓ, ghunnah. The text can't
show them; al-Futūḥ shows many only by colour.

**Decision.** Each feature has a display policy the user chooses: **hidden**, **a mark**, or
**a colour**. Rules for the marks:

- **Every feature has a mark that survives greyscale print and colour-blindness.** Colour may
  repeat a mark, never replace it.
- **Choices are toggles**: badal, munfaṣil, and the rest are user options (the engine already
  generates them as choices); the mark shows which wajh is being read.
- **Qaṣr, tawassuṭ and ṭūl get distinct marks.** Unicode has one maddah, so the distinctions are
  glyph variants in the font, chosen by OpenType features. DigitalKhatt (open source, already our
  preview font) is where they go; no new codepoints.
- **Use the books' conventions where they exist**, invent only where none does, and document each:
  al-Futūḥ marks the ishmām of قِيلَ with a dot on the qāf (ق۬ـِيل); KFGQPC writes Qunbul's sīn as a
  ṣād with a small sīn (صۜ); the tas-hīl dot is already settled (STATUS.md, Decisions).

**Next:** a mock-up sheet, rendered with DigitalKhatt, with a few candidate marks per feature,
for Eisa and Yusuf to judge by eye (the same side-by-side habit as the dot work).

## 3. Ḥadhf and ziyādah: the word spine belongs to no single riwāyah

Some farsh follows the rasm of the different ʿUthmānī maṣāḥif (Shāmī, Madanī, Makkī):

- **A letter added or dropped inside a word**: وَسَارِعُوٓاْ / سَارِعُوٓاْ (Āl ʿImrān 133); Ibn ʿĀmir's
  وَبِٱلزُّبُرِ وَبِٱلۡكِتَٰبِ ٱلۡمُنِيرِ (Āl ʿImrān 184). Ordinary farsh: the word keeps its place and the
  option's text has a letter more or fewer. The model handles this today.
- **A whole word added or dropped**: تَجۡرِي مِن تَحۡتِهَا / تَجۡرِي تَحۡتَهَا (al-Tawbah 100, Ibn
  Kathīr). This breaks one assumption: word ids come from Ḥafṣ, so a word Ḥafṣ lacks has no id.

**Decision.** The word spine becomes **riwāyah-neutral**: the union of word slots across all
twenty, with stable ids; an added word gets its own slot (e.g. `9:100:17a`, after تَجۡرِي) that some riwāyāt
leave empty. Ḥafṣ is one projection of the spine, not its definition. Layout reflows per riwāyah
(the 13- and 15-line layouts need that anyway).

**Scope:** only the **qirāʾah-driven** rasm differences now, the ones the farsh chapters note.
Each tradition's spelling conventions that don't change the reading (Warsh maṣāḥif following Abū
Dāwūd in many words, for example) are a later display layer, sourced from al-Muqniʿ and Mukhtaṣar
al-Tabyīn.

## What changes in the build

| Area | Change |
| --- | --- |
| Data | `marks/<edition>.yaml` (pause signs), `counts/<riwayah>.yaml` (ayah ends), a riwāyah-neutral word spine with slot ids |
| Engine | stops accepted on any word; empty slots per riwāyah |
| Font | DigitalKhatt glyph variants for madd lengths, ishmām and other feature marks, selected by OpenType features |
| App | per-feature display policy (hidden / mark / colour); mark set chooser; feature toggles |
