"""The farsh table: every place covers the twenty, and it agrees with KFGQPC where KFGQPC can
show it. Numbers are al-Baqarah's at milestone 2; a drop is a regression."""
import copy
import unittest
from unittest import mock

import yaml

from mushaf_data.paths import DATA
from mushaf_data.ruwat import RUWAT
from pipeline.farsh import coverage

from . import needs


class Coverage(unittest.TestCase):
    def opts(self):
        return [{"readers": ["bazzi", "qunbul"], "khulf": [], "reading": "a"},
                {"readers": [r for r in RUWAT if r not in ("bazzi", "qunbul")], "khulf": [], "reading": "b"}]

    def test_full(self):
        self.assertEqual(coverage(self.opts()), {"missing": [], "twice": []})

    def test_khulf_gets_the_other_option(self):
        o = self.opts()
        o[0]["readers"].append("qalun"); o[0]["khulf"] = ["qalun"]
        o[1]["readers"].remove("qalun")
        self.assertEqual(coverage(o), {"missing": [], "twice": []})
        self.assertEqual(o[1]["implied"], ["qalun"])

    def test_planted_rawi_in_two_options(self):
        o = self.opts()
        o[0]["readers"].append("warsh")
        self.assertEqual(coverage(o)["twice"], ["warsh"])

    def test_planted_rawi_missing_with_hafs_named(self):
        o = self.opts()
        o[1]["readers"].remove("warsh")
        self.assertEqual(coverage(o)["missing"], ["warsh"])


@needs.sources
class AgainstKFGQPC(unittest.TestCase):
    def test_al_baqarah(self):
        """Every disagreement read: none left unexplained (checks.farsh.KNOWN), 2026-11-27."""
        from checks import farsh
        r = farsh.check(2)
        self.assertGreaterEqual(len(r["both"]), 418)
        self.assertEqual((r["kfgqpc_only"], r["table_only"]), ([], []))

    def test_al_fatiha(self):
        from checks import farsh
        r = farsh.check(1)
        self.assertEqual((len(r["both"]), r["kfgqpc_only"], r["table_only"]), (8, [], []))

    def test_recurring_farsh_reaches_later_places(self):
        """وهو at 2:85:19 is covered by the entry at 2:29:16 (wafi 201: وها هو بعد الواو والفا ولامها)."""
        from checks import farsh
        self.assertIn("qalun", farsh.table(2).get("2:85:19", set()))

    def test_planted_new_disagreement_is_unexplained(self):
        from checks import farsh
        real = farsh.table

        def plus_one(surah):
            t = real(surah)
            t["2:2:1"] = t.get("2:2:1", set()) | {"warsh"}  # ذَٰلِكَ: no farsh
            return t
        with mock.patch.object(farsh, "table", plus_one):
            r = farsh.check(2, 5)
        self.assertIn(("2:2:1", "warsh"), r["table_only"])

    def test_planted_missing_entry_is_caught(self):
        from checks import farsh
        real = farsh.table

        def without_yukadhdhibun(surah):
            t = real(surah)
            t.pop("2:10:12", None)  # يكذبون: the Kūfiyyūn's reading
            return t
        base = len(farsh.check(2, 25)["both"])
        with mock.patch.object(farsh, "table", without_yukadhdhibun):
            r = farsh.check(2, 25)
        self.assertLess(len(r["both"]), base)


@needs.books
class AslOrFarsh(unittest.TestCase):
    """Each place of al-Baqarah classed as an uṣūl rule (data/usul) or true farsh (the farsh
    chapters of al-Wāfī pp. 199-231 / al-Īḍāḥ pp. 187-222), 2026-11-27."""

    def test_every_place_is_classed(self):
        places = yaml.safe_load((DATA / "farsh" / "002.yaml").read_text(encoding="utf-8"))
        kinds = [e["class"]["kind"] for e in places]
        self.assertEqual((kinds.count("rule"), kinds.count("farsh"), kinds.count("unclear")), (21, 129, 0))
        for e in places:
            c = e["class"]
            self.assertTrue(c.get("rule") if c["kind"] == "rule" else c.get("farsh"), e["place"])

    def test_no_place_left_flagged(self):
        """أمانيهم (one reading in two clauses) and جدال (wafi 218, idah 214) settled 2026-11-27."""
        for s in ("001", "002"):
            flagged = [e["place"] for e in yaml.safe_load((DATA / "farsh" / f"{s}.yaml").read_text(encoding="utf-8"))
                       if "review" in e]
            self.assertEqual(flagged, [], s)

    def test_planted_merge_keeps_khulf_apart(self):
        from pipeline.farsh import merge
        o = [{"readers": ["qalun"], "khulf": ["qalun"], "reading": "a", "cite": "x"},
             {"readers": ["qalun"], "khulf": ["qalun"], "reading": "b", "cite": "x"}]
        self.assertEqual(len(merge(o)), 2)  # Qālūn's two wujūh are not one reading

    def test_the_file_matches_the_classifier(self):
        from pipeline.farsh_class import classify
        for s in ("001", "002"):
            for e in yaml.safe_load((DATA / "farsh" / f"{s}.yaml").read_text(encoding="utf-8")):
                self.assertEqual(e["class"], classify(e, s), e["place"])

    def test_fatiha(self):
        """al-Budūr p. 15: مالك, and الصراط / صراط as two places (Khallād's ishmām is in the first)."""
        f = {tuple(e["place"]): e for e in yaml.safe_load((DATA / "farsh" / "001.yaml").read_text(encoding="utf-8"))}
        self.assertEqual(set(f), {("1:4:1",), ("1:6:2",), ("1:7:1",), ("1:7:4", "1:7:7")})
        self.assertTrue(all("review" not in e for e in f.values()))
        who = lambda p, reading: next(o["readers"] for o in f[p]["options"] if reading in o["reading"])  # noqa: E731
        self.assertIn("khallad", who(("1:6:2",), "مثل خلف"))
        self.assertIn("khallad", who(("1:7:1",), "الخالصة"))
        self.assertEqual(f[("1:7:4", "1:7:7")]["class"]["kind"], "rule")
        # reviewed 2026-11-27: Khallād has both wujūh at 1:6 (wafi 51 n. 1), and the pure ṣād is the base
        first = f[("1:6:2",)]
        self.assertTrue(all("khallad" in o["khulf"] for o in first["options"] if "khallad" in o["readers"]))
        self.assertEqual([o["reading"] for o in first["options"] if o.get("base")], ["بالصاد الخالصة"])
        self.assertTrue(all(e["status"] == "checked" for e in f.values()))

    def test_planted_rule_pointing_at_no_case_is_refused(self):
        from pipeline import farsh_class
        rules = copy.deepcopy(farsh_class.RULES)
        rules["002"]["2:6:5"] = [("ha_mim_jam", "no such case")]
        with mock.patch.object(farsh_class, "RULES", rules), self.assertRaises(ValueError):
            farsh_class.classify({"place": ["2:6:5"]}, "002")


class CrosscheckCases(unittest.TestCase):
    """The al-Budūr crosscheck picks the table case from the word (2026-11-27)."""

    def test_cases(self):
        from pipeline.crosscheck_budur import WASL_SAKIN, case_for, key
        self.assertEqual(case_for("imala_ya", "مُوسَىٰ", 3), 9)          # fuʿlā (wafi 150)
        self.assertEqual(case_for("imala_ya", "وَٱلۡأُنثَىٰ", 3), 9)
        self.assertEqual(case_for("imala_ya", "نَصَٰرَىٰ", 3), 4)          # after a rāʾ
        self.assertEqual(case_for("imala_ya", "نَرَى", 3, "ٱللَّهَ"), WASL_SAKIN + 1)
        self.assertEqual(case_for("imala_jaa_shaa", "شَآءَ", 5, "ٱللَّهُ"), 5)  # not a final alif
        self.assertEqual(case_for("ibdal_sakin", "بِمُؤۡمِنِينَ", 0), 0)    # fāʾ
        self.assertEqual(case_for("ibdal_sakin", "ٱلذِّئۡبُ", 0), 1)       # ʿayn
        self.assertEqual(case_for("hamzatayn", "أَئِنَّكُمۡ", 0), 1)       # second maksūrah
        self.assertNotEqual(key("أَزۡكَىٰ"), key("زكى"))                   # planted collision


class Anchors(unittest.TestCase):
    """Every table's listed words anchored to Ḥafṣ places, once (pipeline.anchor; the word-by-word
    chapters 2026-11-27, every table 2026-11-28, docs/06 §3 item 3)."""

    def listed(self):
        for f in sorted((DATA / "usul").glob("*.yaml")):
            for x in yaml.safe_load(f.read_text(encoding="utf-8")).get("listed") or []:
                yield f.stem, x

    def test_every_entry_stores_slots_or_a_flag(self):
        n = {"all": 0, "some": 0, "none": 0, "flagged": 0}
        for c, x in self.listed():
            n[x["anchor"]] += 1
            self.assertIn("places", x, (c, x["words"]))
            if x.get("flag"):
                n["flagged"] += 1
                self.assertEqual(x["places"], [], (c, x["words"]))  # a flagged entry reaches no place
            else:
                self.assertEqual(bool(x["places"]), x["anchor"] != "none", (c, x["words"]))
        self.assertGreaterEqual(n["all"], 270)
        self.assertLessEqual(n["flagged"], 60)

    def test_the_word_chapters_still_anchor(self):
        n = 0
        for c, x in self.listed():
            if c in ("ya_idafa", "ya_zaida", "idgham_saghir") and x["anchor"] == "all":
                n += 1
        self.assertGreaterEqual(n, 90)

    def test_phrases(self):
        from pipeline.anchor import find
        self.assertTrue(find("ولا تخزون في ضيفي"))            # a phrase
        self.assertTrue(find("يا عبادي لا خوف"))             # the vocative joined in Ḥafṣ
        self.assertTrue(find("فارهبون"))                      # Ḥafṣ without the zāʾidah yāʾ
        from pipeline.anchor import matches
        self.assertTrue(matches("وماكنت", ya=False, joined=True))  # written joined, two Ḥafṣ words
        self.assertFalse(matches("وماكنت", ya=False))              # (find and the rest: as before)
        self.assertEqual(find("ولا تخزون في الأرض"), [])      # planted: no such phrase

    def test_short_words_match_themselves(self):
        from mushaf_data.spine import words
        from pipeline.anchor import matches
        h = words()

        def find(w, ya=False):
            return [m[0] for m in matches(w, ya, strict=True)]
        self.assertFalse([w for w in find("أنت", ya=False) if "كُنت" in h[w]])  # not كنت (prefix ك)
        self.assertFalse([w for w in find("وال", ya=False) if h[w].startswith("وَلَا")])
        self.assertFalse([w for w in find("أنى", ya=False) if "أَنِّي" in h[w]])
        self.assertLess(len(find("آلآن", ya=False)), 10)

    def test_the_books_doubled_ya(self):
        # idah 115's النبيين: Ḥafṣ writes the second yāʾ small (ٱلنَّبِيِّـۧنَ), which the skeleton drops
        x = next(x for c, x in self.listed() if c == "hamz_mufrad" and "النبيين" in x["words"])
        self.assertIn("2:61:52", x["places"])
        self.assertNotIn("unanchored", x)

    def test_a_phrase_reaches_its_own_words_only(self):
        # wafi 152: ويولج النهار, not every النهار (the bug that once changed every occurrence)
        from mushaf_data.spine import words
        h = words()
        x = next(x for c, x in self.listed() if c == "imala" and "ويولج النهار" in x["words"])
        from mushaf_data.occurrences import skel
        nahar = [p for p in x["places"] if skel(h[p]) == "لنهر"]
        self.assertTrue(nahar)
        self.assertNotIn("2:164:9", x["places"])  # ٱلنَّهَارِ in 2:164, after ٱلَّيۡلِ
        order = list(h)
        pos = {w: i for i, w in enumerate(order)}
        for p in nahar:
            self.assertEqual(skel(h[order[pos[p] - 1]]), "ويولج")

    def test_a_surah_in_brackets_narrows(self):
        from pipeline.anchor import resolve
        r = resolve("ya_idafa", {"words": ["بيتي (نوح)"]})
        self.assertTrue(r["places"])
        self.assertEqual({p.split(":")[0] for p in r["places"]}, {"71"})
        # the same word also listed bare: which one the entry means is a question (flagged)
        x = next(x for c, x in self.listed() if c == "ya_idafa" and any("(نوح)" in str(w) for w in x["words"]))
        self.assertTrue(x.get("flag"))

    def test_planted_note_with_a_condition_is_flagged(self):
        from pipeline.anchor import resolve
        r = resolve("imala", {"words": ["موسى"], "note": "only in al-Kahf when joined with wāw"})
        self.assertTrue(r.get("flag"))
        self.assertEqual(r["places"], [])
        r = resolve("imala", {"words": ["موسى"]})
        self.assertGreater(len(r["places"]), 100)


class RecursSlots(unittest.TestCase):
    """al-Budūr's `recurs` (the books' "حيث وقع") stores slots, read as slots (docs/06 §3 item 4)."""

    def recurring(self):
        for f in sorted((DATA / "farsh").glob("*.yaml")):
            for e in yaml.safe_load(f.read_text(encoding="utf-8")) or []:
                if e.get("recurs"):
                    yield e

    def test_every_recurs_stores_its_slots(self):
        from pipeline.farsh_class import RECUR, recur_slots
        n = 0
        for e in self.recurring():
            n += 1
            self.assertEqual(e["recurs"]["slots"], recur_slots(RECUR[e["place"][0]]), e["place"])
            self.assertIn(e["place"][0], e["recurs"]["slots"] + e["place"])
        self.assertGreaterEqual(n, 9)  # every RECUR entry (nine, 2026-11-28)

    def test_skip_is_applied_when_stored(self):
        # wafi 202-203: يأمركم and the like, but not a rāʾ already sākin in Ḥafṣ (إِن يَنصُرۡكُمُ 3:160)
        e = next(e for e in self.recurring() if "يأمركم" in e["recurs"]["forms"])
        self.assertNotIn("3:160:2", e["recurs"]["slots"])

    def test_readers_dont_search_forms(self):
        # planted: the forms searched when a check runs would raise
        from checks import farsh as cf
        with mock.patch("pipeline.anchor.find", side_effect=AssertionError("searched a form")):
            cf.entries(3)
            cf.places(3)

    def test_the_api_reaches_a_recurring_place(self):
        from mushaf_data.api import farsh_index
        e = next(e for e in self.recurring() if "وهو" in e["recurs"]["forms"])
        far = [w for w in e["recurs"]["slots"] if w.startswith("6:")]
        self.assertTrue(far)
        self.assertTrue(any(x.get("recurs") for x in farsh_index("budur")[far[0]]))


class AlImran(unittest.TestCase):
    """Milestone 4, first batch: al-Budūr pp. 58-75 (2026-11-27)."""

    def places(self):
        return {e["place"][0]: e for e in yaml.safe_load((DATA / "farsh" / "003.yaml").read_text(encoding="utf-8"))}

    def test_no_place_flagged(self):
        self.assertEqual([p for p, e in self.places().items() if "review" in e], [])

    def test_two_aspects_of_one_word(self):
        """تحسبن 3:169: tāʾ or yāʾ, then the sīn's vowel: each rāwī once per aspect."""
        e = self.places()["3:169:2"]
        self.assertEqual({o.get("aspect", 0) for o in e["options"]}, {0, 1})

    def test_a_restatement_is_the_base(self):
        """فنادته 3:39: al-Budūr p. 64 restates Warsh reading as Ḥafṣ."""
        e = self.places()["3:39:1"]
        self.assertTrue(all(o.get("base") for o in e["options"] if o["readers"] == ["warsh"]))

    def test_anchored_words_need_their_topic(self):
        """يكذبون 2:10 is a yāʾ zāʾidah only in al-Qaṣaṣ: still farsh here; وخافون 3:175 is the yāʾ."""
        from pipeline.farsh_class import classify
        b = {e["place"][0]: e for e in yaml.safe_load((DATA / "farsh" / "002.yaml").read_text(encoding="utf-8"))}
        self.assertEqual(classify(b["2:10:12"], "002")["kind"], "farsh")
        self.assertTrue(classify(self.places()["3:175:8"], "003")["rule"][0].startswith("ya_zaida"))

    @needs.sources
    def test_against_kfgqpc(self):
        from checks import farsh
        r = farsh.check(3)
        self.assertGreaterEqual(len(r["both"]), 307)
        self.assertEqual((r["kfgqpc_only"], r["table_only"]), ([], []))
