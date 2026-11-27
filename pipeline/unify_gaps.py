"""Apply the gap re-read of 2026-11-26 to the unified drafts (pipeline/unified/*.yaml).

    python3 -m pipeline.unify_gaps        edits the drafts in place, then records each finding in
                                          pipeline/open_sort.yaml `resolved`; run unify_merge after

Each gap (pipeline/open_sort.yaml `gaps`) was re-read from its page by a Sonnet reader
(pipeline/work/gaps/<id>.json: pages, quote, finding, change); the changes below were checked
against the pages before applying. Every edit names its page. Safe to run twice.
"""
from __future__ import annotations

import json

import yaml

from mushaf_data.paths import ROOT
from mushaf_data.ruwat import RUWAT

DIR = ROOT / "pipeline/unified"
WORK = ROOT / "pipeline/work/gaps"
SORT = ROOT / "pipeline/open_sort.yaml"
SHATIBI = RUWAT[:14]
# gaps whose re-read leaves a choice for Eisa: the question to ask
QUESTIONS = {
    "idgham_kabir#2": "تأمنا (wafi 294): every reader has either ikhfāʾ of the first nūn's vowel (ikhtilās) or idghām with "
                      "ishmām, and the book calls ishmām the more famous. Should ishmām be the default and ikhtilās the "
                      "option? (Yaʿqūb and Khalaf al-ʿĀshir follow their aṣl here, idah 66.)",
    "silah_ha#2": "يؤده، نوله، نصله، نؤته for Ibn Jammāz: idah 71-72 give Abū Jaʿfar's two ruwāt sukūn, then give Ibn "
                  "Jammāz ishbāʿ (وامدد جد), without saying whether it replaces the sukūn. Ishbāʿ only, or both?",
}
# questions a re-read settled: (question id, finding)
SETTLED = {
    "sakt_al#0": ("sakt_al#1", "wafi 106: Khallād has no sakt on the first route and sakt on ال and شيء on the second, "
                               "so the reviewed table's two wujūh [sakt, none] are right in both words."),
}


def load(c):
    return yaml.safe_load((DIR / f"{c}.yaml").read_text(encoding="utf-8"))


def save(c, t):
    (DIR / f"{c}.yaml").write_text(yaml.safe_dump(t, allow_unicode=True, sort_keys=False, width=140), encoding="utf-8")


def listed(t, pred):
    hits = [x for x in t.get("listed") or [] if pred(x)]
    assert hits, "listed entry not found"
    return hits


def vocab(t, wid, ar, en):
    if wid not in {w["id"] for w in t["wujuh"]}:
        t["wujuh"].append({"id": wid, "ar": ar, "en": en})


def cite(x, *pages):
    x["cite"] = list(dict.fromkeys(list(x.get("cite") or []) + list(pages)))


def apply() -> list[str]:
    done = []

    t = load("hamz_mufrad")  # idah 105-106: the thirteen words (four have entries of their own)
    x = listed(t, lambda x: x["words"] == ["قرئ"] or "استهزئ" in x["words"])[0]
    x["words"] = ["قرئ", "استهزئ", "ناشئة", "رئاء", "لنبوئنهم", "ليبطئن", "شانئك", "خاسئا", "ملئت"]
    cite(x, "idah 106")
    save("hamz_mufrad", t); done.append("hamz_mufrad#1")

    t = load("idgham_kabir")
    case = next(c for c in t["cases"] if c["case"].startswith("first mudgham carrying a damma or kasra"))
    if "idgham" not in case["ruwat"]["susi"]["wujuh"]:  # wafi 66: idghām maḥḍ is the first madhhab
        case["ruwat"]["susi"]["wujuh"] = ["idgham"] + case["ruwat"]["susi"]["wujuh"]
        cite(case["ruwat"]["susi"], "wafi 66")
    four = listed(t, lambda x: "نصيب برحمتنا" in x["words"])[0]
    four["ruwat"] = {"susi": ["idgham"]}
    four["why"] = "the four forms: idghām maḥḍ only, no ishmām, and no rawm on al-Shāṭibī's view (wafi 66)"
    cite(four, "wafi 66")
    old = [x for x in t["listed"] if "جَعَلَ" in x["words"] and len(x["words"]) == 3]
    if old:  # idah 63-64: three groups, Ruways idghām and iẓhār in each
        i = t["listed"].index(old[0])
        base = {"case": old[0]["case"], "ruwat": {"ruways": ["idgham", "izhar"]}, "cite": ["idah 63", "idah 64"]}
        t["listed"][i:i + 1] = [{"words": ["جَعَلَ"], **base, "note": "the eight places of al-Naḥl"},
                                {"words": ["لَا قِبَلَ لَهُم بِهَا"], **base, "note": "al-Naml 37 (printed هُم بِمَا on idah 63, بِهَا on 64)"},
                                {"words": ["وَأَنَّهُ هُوَ"], **base, "note": "the four places of al-Najm"}]
    save("idgham_kabir", t); done += ["idgham_kabir#4", "idgham_kabir#7"]

    t = load("idgham_saghir")  # wafi 130, 133
    for c in t["cases"]:
        c["case"] = (c["case"].replace("قد before the four other letters of the eight (not named in the rows)", "قد before س ج ص ش")
                     .replace("لام هل وبل before the three other letters of the eight (not named in the rows)", "لام هل وبل before ظ ز ط"))
    save("idgham_saghir", t); done.append("idgham_saghir#1")

    t = load("imala")  # wafi 153-154: من أنصارى is al-Dūrī ʿan al-Kisāʾī's exception, with imālah
    for x in t["listed"]:
        if str(x.get("case", "")).startswith("imala_ra"):
            x["words"] = [w for w in x["words"] if w != "من أنصارى"]
    y = listed(t, lambda x: x["words"] == ["أنصارى"] or x["words"] == ["من أنصارى إلى الله"])[0]
    y["words"] = ["من أنصارى إلى الله"]
    y["note"] = "Āl ʿImrān and al-Ṣaff"
    cite(y, "wafi 154")
    save("imala", t); done.append("imala#8")

    t = load("imala_ha_tanith")  # wafi 158: the tenth letter is غ
    c = t["cases"][0]
    c["case"] = c["case"].replace("ح ق ض ا ط ع ص خ ظ (the book's 'ten')", "ح ق ض ا ط ع ص خ ظ غ (the book's ten)")
    save("imala_ha_tanith", t); done.append("imala_ha_tanith#1")

    t = load("madd_arid")  # wafi 83: the three wujūh at waqf
    for slot in t["cases"][1]["ruwat"].values():
        if slot.get("via") is None:
            cite(slot, "wafi 83")
    save("madd_arid", t); done.append("madd_arid#0")

    t = load("silah_ha")  # wafi 71 (أرجئه); idah 77, 80 spell فألقه، أرجه with a hāʾ
    vocab(t, "hamz_damm_silah", "همز ساكن مع ضم الهاء وصلتها", "sākin hamzah, ḍamm of the hāʾ, ṣilah")
    vocab(t, "nohamz_kasr_silah", "ترك الهمز مع كسر الهاء وصلتها", "no hamzah, kasr of the hāʾ, ṣilah")
    x = listed(t, lambda x: "أرجئه" in x["words"])[0]
    x["ruwat"].update({r: ["hamz_damm_silah"] for r in ("bazzi", "qunbul", "hisham")})
    x["ruwat"].update({r: ["nohamz_kasr_silah"] for r in ("warsh", "abul_harith", "duri_kisai")})
    x["note"] = "the Durrah's nohamz_silah leaves the hāʾ's vowel unstated (idah 74, 78)"
    for y in t["listed"]:
        y["words"] = [w.replace("فَأَلْقِة", "فَأَلْقِهْ").replace("أَرْجِة", "أَرْجِهْ").replace("أرجة", "أرجه") for w in y["words"]]
        y["words"] = list(dict.fromkeys(y["words"]))
    if not any("hamz_silah" in (ws or []) for y in t["listed"] for ws in (y.get("ruwat") or {}).values()) and \
            not any("hamz_silah" in (s.get("wujuh") or []) for c in t["cases"] for s in c["ruwat"].values()):
        t["wujuh"] = [w for w in t["wujuh"] if w["id"] != "hamz_silah"]
    save("silah_ha", t); done += ["silah_ha#5", "silah_ha#7"]

    t = load("sakt_al")  # wafi 106: Khallād has both routes
    for c in t["cases"]:
        c["ruwat"]["khallad"] = {"wujuh": ["sakt", "none"], "cite": ["wafi 106"], "option": True}
    for x in t.get("listed") or []:
        if "khallad" in (x.get("ruwat") or {}):
            x["ruwat"]["khallad"] = ["sakt", "none"]
    save("sakt_al", t); done.append("sakt_al#1")

    t = load("ha_mim_jam")  # idah 57: all but Ruways kasr; Abū Jaʿfar and Khalaf al-ʿĀshir named
    x = listed(t, lambda x: "فتاتهم" in x["words"])[0]
    x["ruwat"].update({r: ["kasr_ha"] for r in ("ibn_wardan", "ibn_jammaz", "ishaq", "idris")})
    save("ha_mim_jam", t); done.append("ha_mim_jam#1")

    t = load("hamzatayn")  # idah 93: in al-Naml, the second hamzah as each one's aṣl, no idkhāl
    x = listed(t, lambda x: x["words"] == ["النمل"])[0]
    x["ruwat"] = {"ruways": ["istifham_istifham", "tashil"], "rawh": ["istifham_istifham", "tahqiq"]}
    x["note"] = "the second id is the second hamzah: Ruways tashīl, Rawḥ taḥqīq, no idkhāl (idah 93)"
    save("hamzatayn", t); done.append("hamzatayn#5")

    t = load("waqf_rasm")  # wafi 180: no disagreement, stopped with hāʾ
    if not any(c["case"].startswith("hāʾ al-taʾnīth written with a hāʾ") for c in t["cases"]):
        rw = {r: {"wujuh": ["ha"], "cite": ["wafi 180"]} for r in SHATIBI}
        rw.update({r: {"wujuh": ["ha"], "cite": ["idah 40-43"], "via": "asl_unstated"} for r in RUWAT[14:]})
        i = next(i for i, c in enumerate(t["cases"]) if c["case"].startswith("hāʾ al-taʾnīth written with a tāʾ"))
        t["cases"].insert(i, {"case": "hāʾ al-taʾnīth written with a hāʾ (رحمة من الله، بقية)", "ruwat": rw})
    save("waqf_rasm", t); done.append("waqf_rasm#0")

    t = load("ya_idafa")  # wafi 191-192: each place names who opens it; the rest read sukūn
    c = next(c for c in t["cases"] if c["case"].startswith("yāʾ al-iḍāfah not before a hamzah"))
    for r in SHATIBI:
        c["ruwat"][r] = {"wujuh": ["sukun"], "cite": ["wafi 191", "wafi 192"]}
    x = listed(t, lambda x: "ومالي لا أعبد" in x["words"])[0]  # wafi 192: Ḥamzah sukūn, the rest open in waṣl
    x["ruwat"] = {r: (["sukun"] if r in ("khalaf_an_hamzah", "khallad") else ["opened"]) for r in SHATIBI}
    cite(x, "wafi 192")
    save("ya_idafa", t); done.append("ya_idafa#6")

    t = load("lin_hamz")  # wafi 82: ابنى آدم، ولو آمن are naql, not this rule
    t["listed"] = [x for x in t.get("listed") or [] if not any("آدم" in w or "ولو آمن" in w for w in x["words"])]
    save("lin_hamz", t); done.append("lin_hamz#1")

    t = load("naql")  # idah 117 n. 2, 119
    cite(listed(t, lambda x: x["words"] == ["من أجل"])[0], "idah 119")
    save("naql", t); done.append("naql#0")
    return done


def record():
    s = yaml.safe_load(SORT.read_text(encoding="utf-8"))
    res = {}
    for k in s["gaps"]:
        d = json.loads((WORK / f"{k.replace('#', '_')}.json").read_text(encoding="utf-8"))
        r = {"pages": d["pages"], "finding": d["finding"], "becomes": "question" if k in QUESTIONS else "note"}
        if k in QUESTIONS:
            r["q"] = QUESTIONS[k]
        res[k] = r
    res["ya_idafa#6"]["finding"] += " ومالي لا أعبد: Ḥamzah sukūn, the others open in waṣl (wafi 192), now in its entry."
    for q, (via, finding) in SETTLED.items():
        res[q] = {"pages": ["wafi 106"], "finding": finding, "becomes": "note", "by": via}
        s["questions"].pop(q, None)
    s["resolved"] = res
    text = SORT.read_text(encoding="utf-8")
    head = text[: text.index("questions:")]
    body = yaml.safe_dump({k: s[k] for k in ("questions", "gaps", "noise")}, allow_unicode=True, sort_keys=False, width=110)
    pol = yaml.safe_dump({"policies": s["policies"]}, allow_unicode=True, sort_keys=False, width=110)
    tail = ("\n# Findings of the gap re-read (pipeline.unify_gaps, from pipeline/work/gaps/): each gap becomes a note,\n"
            "# or a question where the books leave a choice.\n"
            + yaml.safe_dump({"resolved": res}, allow_unicode=True, sort_keys=False, width=110))
    SORT.write_text(head[: head.index("policies:")] + pol + "\n" + body + tail, encoding="utf-8")


def main():
    print("applied:", ", ".join(apply()))
    record()
    print("recorded", SORT)


if __name__ == "__main__":
    main()
