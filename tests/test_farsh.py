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
    """The word-by-word chapters' listed words anchored to Ḥafṣ places (2026-11-27)."""

    def test_most_entries_anchor(self):
        n = {"all": 0, "some": 0, "none": 0}
        for c in ("ya_idafa", "ya_zaida", "idgham_saghir"):
            for x in yaml.safe_load((DATA / "usul" / f"{c}.yaml").read_text(encoding="utf-8"))["listed"]:
                n[x["anchor"]] += 1
                self.assertEqual(bool(x["places"]), x["anchor"] != "none")
        self.assertGreaterEqual(n["all"], 96)

    def test_phrases(self):
        from pipeline.anchor import find
        self.assertTrue(find("ولا تخزون في ضيفي"))            # a phrase
        self.assertTrue(find("يا عبادي لا خوف"))             # the vocative joined in Ḥafṣ
        self.assertTrue(find("فارهبون"))                      # Ḥafṣ without the zāʾidah yāʾ
        self.assertEqual(find("ولا تخزون في الأرض"), [])      # planted: no such phrase
