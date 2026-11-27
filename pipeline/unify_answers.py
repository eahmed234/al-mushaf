"""Apply Eisa's answers to the uṣūl questions (review of 2026-11-26) to the unified drafts.

    python3 -m pipeline.unify_answers     edits pipeline/unified/*.yaml in place and writes the rulings
                                          to pipeline/open_sort.yaml `answers`; run unify_merge after

Where Eisa said "check budur", al-Budūr's place notes decided it (pages cited). Policy answers add
`options` (ahl al-adāʾ views, off by default) and `kubra` (other ṭuruq, for the kubrā version) to the
tables. Safe to run twice.
"""
from __future__ import annotations

import yaml

from mushaf_data.paths import ROOT
from mushaf_data.ruwat import RUWAT

from .unify_gaps import cite, listed, load, save, vocab

SORT = ROOT / "pipeline/open_sort.yaml"
SHATIBI = RUWAT[:14]

ANSWERS = {
    "policy:ahl_adaa": "options, off by default (Eisa)",
    "policy:footnotes": "kubrā version only (Eisa)",
    "policy:order": "the book's first-listed wajh is the default (Eisa); every table already follows it except "
                    "Warsh's two hamzahs in one word, kept tashīl first: see `order_exception`",
    "basmalah#0": "Eisa: waṣl and sakt are the two ways of dropping the basmalah (isqāṭ), beside keeping it "
                  "(ithbāt). wafi 46: the khilāf in the basmalah from Ibn ʿĀmir, Warsh and Abū ʿAmr is famous, "
                  "and sakt is preferred over waṣl (wafi 47); so they have basmalah, sakt, waṣl, as Yaʿqūb "
                  "'like Abū ʿAmr' (idah 50) and Qaṭr min Ghayth al-Nafʿ (Eisa's photo: ithbāt and isqāṭ).",
    "basmalah#2": "Eisa: the 'three wujūh' of idah 52 are the three ways of keeping the basmalah (end-basmalah-"
                  "start: join all, cut all, cut then join), not a choice of dropping it. Abū Jaʿfar: basmalah only.",
    "ha_mim_jam#3": "Eisa: عليهم، إليهم، لديهم are ḍamm in both states for Ḥamzah; the other words differ: ḍamm in "
                    "waṣl before a sākin, kasr at waqf (wafi 52). Waqf case: kasr; the three words listed with ḍamm.",
    "hamz_waqf#3": "Eisa: the three wujūh (tashīl, ibdāl yāʾ, ḥadhf) are right.",
    "hamzatayn#1": "al-Budūr (Eisa: check al-Budūr): Hishām taḥqīq with and without idkhāl (budur 134, 166, 236, "
                   "265, 269), idkhāl only in the seven places (budur 120, 121, 238, 245); in Fuṣṣilat idkhāl with "
                   "tashīl or taḥqīq, tashīl first (budur 282). The table follows.",
    "idgham_kabir#2": "Eisa: ishmām the default; Abū Jaʿfar has no option, idghām only (idah 65).",
    "istiadha#0": "Eisa: jahr the default, ikhfāʾ the option. (Eisa: the chapter marks nothing in the muṣḥaf.)",
    "istiadha#1": "Eisa: Khalaf's default is jahr at the start of al-Fātiḥah and ikhfāʾ elsewhere.",
    "madd_lazim#1": "al-Budūr: آلآن: Ibn Wardān reads like Qālūn, with naql, so ishbāʿ or qaṣr (budur 145-146); "
                    "Ibn Jammāz has no naql (idah 119), ishbāʿ. الم أحسب: Abū Jaʿfar makes sakt on the letters, "
                    "so no naql, ishbāʿ (budur 244).",
    "rawm_ishmam#0": "Eisa: yes, rawm and ishmām are options for all fourteen.",
    "sakt_mafsul#0": "Eisa: wafi 105 defines the sakt; the categories are the mafṣūl ʿāmm (this table) and the "
                     "khāṣ (ال، شيء: sakt_al). wafi 106: Khalaf sakt in the mafṣūl on the first madhhab, none on "
                     "the second, so [sakt, none]; Khallād none on both.",
    "silah_ha#2": "al-Budūr: Abū Jaʿfar (both ruwāt) sukūn in يؤده، نؤته، نوله، نصله (budur 66, 70, 85); "
                  "the Durrah's 'وامدد جد' is Ibn Jammāz's ṣilah in ويتقه (idah 72).",
    "silah_ha#6": "al-Budūr: Ruways 'بقصر الهاء أي اختلاس حركتها' in بيده (budur 51); Ibn Wardān kasr without "
                  "ṣilah in ترزقانه (budur 163): qaṣr and ikhtilās are one wajh.",
    "ya_zaida#2": "Eisa: two āyāt. Hūd 78 (ولا تخزون في ضيفي): Abū Jaʿfar keeps it in waṣl, Yaʿqūb in both; "
                  "al-Ḥijr 69 (واتقوا الله ولا تخزون): dropped in both states for all but Yaʿqūb (idah 180).",
    "ya_zaida#3": "Eisa: dropped is the default; kept in waṣl is disputed, kubrā only.",
}


def apply() -> list[str]:
    t = load("basmalah")
    c = t["cases"][0]
    for r in ("warsh", "duri_abuamr", "susi", "hisham", "ibn_dhakwan"):
        c["ruwat"][r] = {"wujuh": ["basmala", "sakt", "wasl"], "cite": ["wafi 46", "wafi 47"]}
    c["note"] = ("basmala is keeping the basmalah (three ways: join all, cut all, cut the sūrah's end and join the "
                 "basmalah to the next; joining it to the end and stopping on it is not allowed, wafi 49); sakt and "
                 "waṣl are the two ways of dropping it (Eisa 2026-11-26)")
    t["options"] = [{"about": "al-arbaʿ al-zuhr (القيامة، المطففين، البلد، الهمزة)", "view": "ahl al-adāʾ",
                     "ruwat": ["warsh", "duri_abuamr", "susi", "hisham", "ibn_dhakwan"],
                     "reads": "basmala before them for those who make sakt elsewhere, sakt for those who make waṣl",
                     "cite": ["wafi 47"], "default": "off"}]
    save("basmalah", t)

    t = load("ha_mim_jam")
    w = next(c for c in t["cases"] if c["case"] == "hāʾ before the plural mīm, at waqf")
    for r in ("khalaf_an_hamzah", "khallad"):
        w["ruwat"][r] = {"wujuh": ["kasr_ha"], "cite": ["wafi 52"]}
    if not any(x.get("case") == w["case"] and "عليهم" in x["words"] for x in t["listed"]):
        t["listed"].append({"words": ["عليهم", "إليهم", "لديهم"], "case": w["case"],
                            "ruwat": {"khalaf_an_hamzah": ["damm_ha"], "khallad": ["damm_ha"]}, "cite": ["wafi 52"],
                            "note": "Ḥamzah's ḍamm in these three holds in waqf and waṣl"})
    m = next(c for c in t["cases"] if c["case"] == "mīm, at waqf")
    for r, s in m["ruwat"].items():  # wafi 52: all agree on sukūn of the mīm at waqf
        if s.get("via") in ("as_hafs", "asl_unstated"):
            m["ruwat"][r] = {"wujuh": ["sukun_mim"], "cite": ["wafi 52"]}
    save("ha_mim_jam", t)

    t = load("hamzatayn")
    for x in [x for x in t["listed"] if x["ruwat"] == {"hisham": ["tahqiq_idkhal"]} and len(x["words"]) > 3]:
        x["words"] = [w for w in x["words"] if w != "أتنكم لتكفرون"]
        cite(x, "budur 120", "budur 121")
    f = listed(t, lambda x: x["words"] == ["أتنكم لتكفرون فصلت"])[0]
    f["ruwat"] = {"hisham": ["tashil_idkhal", "tahqiq_idkhal"]}
    cite(f, "budur 282")
    t["order_exception"] = ("Warsh, second hamzah maftūḥah: al-Wāfī's verse names the ibdāl (Egyptians) before the "
                            "tashīl (Baghdādīs, wafi 84), but the reviewed table and al-Budūr (budur 20: 'الأول مثل "
                            "المكي والثاني إبدالها') put tashīl first; kept tashīl first until Eisa says otherwise")
    save("hamzatayn", t)

    t = load("idgham_kabir")
    vocab(t, "idgham_ishmam", "الإدغام مع الإشمام", "idghām with ishmām")
    vocab(t, "ikhtilas", "الإخفاء (الاختلاس)", "ikhfāʾ of the vowel (ikhtilās)")
    if not any("تأمنا" in x["words"] for x in t["listed"]):
        rw = {r: ["idgham_ishmam", "ikhtilas"] for r in RUWAT}
        rw.update({"ibn_wardan": ["idgham"], "ibn_jammaz": ["idgham"]})
        t["listed"].append({"words": ["تأمنا"], "case": "mithlayn inside one word", "ruwat": rw,
                            "cite": ["wafi 294", "idah 65", "idah 66"],
                            "note": "ishmām the default (the more famous, wafi 294; Eisa); Abū Jaʿfar idghām only"})
    save("idgham_kabir", t)

    t = load("istiadha")
    t["cases"][1]["ruwat"]["khalaf_an_hamzah"]["wujuh"] = ["ikhfa", "jahr"]
    t["cases"][1]["note"] = "Khalaf: jahr at the start of al-Fātiḥah (listed), ikhfāʾ elsewhere by default (wafi 44; Eisa)"
    save("istiadha", t)

    t = load("madd_lazim")
    a = listed(t, lambda x: x["words"] == ["آلآن"])[0]
    a["ruwat"].update({"ibn_wardan": ["ishba", "qasr"], "ibn_jammaz": ["ishba"]})
    cite(a, "budur 145", "budur 146", "idah 119")
    b = listed(t, lambda x: x["words"] == ["الم أحسب الناس"])[0]
    b["ruwat"].update({"ibn_wardan": ["ishba"], "ibn_jammaz": ["ishba"]})
    cite(b, "budur 244")
    save("madd_lazim", t)

    t = load("silah_ha")
    x = listed(t, lambda x: "يؤده" in x["words"])[0]
    x["ruwat"]["ibn_jammaz"] = ["sukun"]
    cite(x, "budur 66", "budur 70", "budur 85")
    save("silah_ha", t)

    t = load("ya_zaida")
    x = listed(t, lambda x: "ولا تخزون في ضيفي" in x["words"])[0]
    x["words"] = ["ولا تخزون في ضيفي"]
    x.pop("note", None)
    x["place"] = "Hūd 78"
    if not any("وَاتَّقُوا اللَّهَ وَلَا تُخْزُونِ" in y["words"] for y in t["listed"]):
        rw = {r: ["dropped"] for r in RUWAT}
        rw.update({"ruways": ["kept_both"], "rawh": ["kept_both"]})
        t["listed"].append({"words": ["وَاتَّقُوا اللَّهَ وَلَا تُخْزُونِ"], "case": x["case"], "place": "al-Ḥijr 69",
                            "ruwat": rw, "cite": ["idah 180"]})
    q = listed(t, lambda x: "التلاق" in x["words"])[0]
    q["ruwat"]["qalun"] = ["dropped"]
    q["note"] = "Qālūn: dropped (the verifiers, wafi 196); the poem's kept-in-waṣl is for the kubrā (Eisa)"
    t["kubra"] = [{"about": "التلاق، التناد", "ruwat": ["qalun"], "reads": "kept_wasl", "cite": ["wafi 196"],
                   "why": "the poem's khulf; the verifiers drop it"}]
    save("ya_zaida", t)

    # policy: ahl al-adāʾ views become options, off by default
    for c, opt in {
        "badal": {"about": "عاداً الأولى", "ruwat": ["warsh"], "reads": "qaṣr only", "cite": ["wafi 78"]},
        "hamz_waqf": {"about": "stopping by the rasm (شركاء، يبدو، تلقاء …)", "ruwat": ["khalaf_an_hamzah", "khallad"],
                      "reads": "follow the muṣḥaf's spelling: yāʾ, wāw or ḥadhf", "cite": ["wafi 118", "wafi 119", "wafi 120"]},
        "hamzatayn_kalimatayn_muttafiq": {"about": "هؤلاء إن، البغاء إن", "ruwat": ["warsh"],
                                          "reads": "the second hamzah as a yāʾ with kasrah", "cite": ["wafi 94"]},
        "imala_ha_tanith": {"about": "hāʾ al-taʾnīth after every letter but the alif", "ruwat": ["abul_harith", "duri_kisai"],
                            "reads": "imālah", "cite": ["wafi 159"]},
    }.items():
        t = load(c)
        t["options"] = [{**opt, "view": "ahl al-adāʾ", "default": "off"}]
        save(c, t)

    # policy: other ṭuruq go to the kubrā version
    t = load("muttasil")
    t["kubra"] = [{"about": "the muttaṣil", "ruwat": ["ibn_wardan", "ibn_jammaz", "ruways", "rawh"],
                   "reads": "three ḥarakāt (1½ alifs), al-Taḥbīr", "cite": ["idah 81 n. 4"]}]
    save("muttasil", t)
    for c in ("sakt_al", "sakt_mafsul"):
        t = load(c)
        for case in t["cases"]:
            assert case["ruwat"]["idris"]["wujuh"] == ["none"]
        t["kubra"] = [{"about": "sakt on a sākin that is not a madd", "ruwat": ["idris"],
                       "reads": "sakt (al-Muṭṭawwiʿī, from al-Mubhij)", "cite": ["idah 121", "idah 122", "idah 123"]}]
        save(c, t)
    return list(ANSWERS)


def record():
    s = yaml.safe_load(SORT.read_text(encoding="utf-8"))
    text = SORT.read_text(encoding="utf-8")
    if "\nanswers:" in text:
        text = text[: text.index("\n# Eisa's answers")]
    text += ("\n# Eisa's answers (review of 2026-11-26), applied by pipeline.unify_answers; `policy:<name>` answers\n"
             "# every line the policy covers.\n" + yaml.safe_dump({"answers": ANSWERS}, allow_unicode=True, sort_keys=False, width=110))
    SORT.write_text(text, encoding="utf-8")


def main():
    print("answered:", len(apply()))
    record()


if __name__ == "__main__":
    main()
