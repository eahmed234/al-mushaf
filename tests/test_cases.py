"""The engine picks the table case per word (mushaf_data.cases, 2026-11-28, docs/06 §3 item 2)."""
import copy
import unittest
from unittest import mock

from mushaf_data import cases, usul_tables
from mushaf_data.usul import detect

from .needs import sources


class CaseNames(unittest.TestCase):
    def test_numbers_name_the_tables_cases(self):
        t = usul_tables.tables()
        im = [c["case"] for c in t["imala"]["cases"]]
        self.assertTrue(im[cases.IMALA_YA_RA].startswith("imala_ya_ra:"))
        self.assertTrue(im[cases.ALIF_TANITH].startswith("imala_alif_tanith:"))
        self.assertTrue(im[cases.WASL_SAKIN].startswith("imala_wasl_sakin:"))
        self.assertTrue(im[cases.WASL_SAKIN + 1].startswith("imala_wasl_sakin_ra:"))
        hz = [c["case"] for c in t["hamzatayn"]["cases"]]
        self.assertIn("maksūrah", hz[1])
        self.assertIn("maḍmūmah", hz[2])
        ib = [c["case"] for c in t["ibdal_sakin"]["cases"]]
        self.assertEqual(["fāʾ" in ib[0], "ʿayn" in ib[1], "lām" in ib[2]], [True, True, True])
        for sub, (tab, k, _) in cases.SUBCATS.items():
            self.assertEqual(usul_tables.where()[sub], (tab, k))

    def test_the_check_and_the_engine_share_it(self):
        from pipeline import crosscheck_budur
        self.assertIs(crosscheck_budur.case_for, cases.case_for)


class FromTheWord(unittest.TestCase):
    def test_sakin_hamzah(self):
        for w, k in [("يُؤۡمِنُونَ", 0), ("وَلۡيُؤۡمِنُواْ", 0), ("سَيُؤۡتِينَا", 0), ("تَسۡتَأۡنِسُواْ", 0),
                     ("لِّلۡمُؤۡمِنِينَ", 0), ("فَأۡتِ", 0), ("ٱلۡمَأۡوَىٰ", 0),
                     ("بِئۡسَ", 1), ("بِئۡسَمَا", 1), ("ٱلذِّئۡبُ", 1), ("لُؤۡلُؤٗا", 1), ("شَأۡنٞ", 1), ("رِءۡيٗا", 1),
                     ("نَشَأۡ", 2), ("جِئۡتُمُونَا", 2), ("أَنۢبِئۡهُم", 2), ("ٱقۡرَأۡ", 2), ("تَسُؤۡهُمۡ", 2)]:
            self.assertEqual(cases.case_for("ibdal_sakin", w, -1), k, w)

    def test_planted_first_hamzah_is_not_the_sakin_one(self):
        # أَنۢبِئۡهُم: the first hamzah is moving; reading it would make the word's fāʾ the sākin one
        self.assertNotEqual(cases.case_for("ibdal_sakin", "أَنۢبِئۡهُم", -1), 0)

    def test_hamzatayn_and_imala(self):
        self.assertEqual(cases.case_for("hamzatayn", "أَؤُنَبِّئُكُم", -1), 2)
        self.assertEqual(cases.case_for("hamzatayn", "أَئِنَّكُمۡ", -1), 1)
        self.assertEqual(cases.case_for("hamzatayn", "ءَأَنذَرۡتَهُمۡ", -1), -1)  # maftūḥah: the category's own
        self.assertEqual(cases.case_for("imala_ya", "مُوسَىٰ", -1), cases.ALIF_TANITH)
        self.assertEqual(cases.case_for("imala_ya", "مُوسَى", -1, "ٱلۡكِتَٰبَ"), cases.WASL_SAKIN)

    def test_faala_written_with_an_alif(self):
        # wafi 150 lists الدنيا، العليا: an alif after the yāʾ, not ى
        for w in ("ٱلدُّنۡيَا", "ٱلدُّنۡيَآ"):
            self.assertIn("imala_alif_tanith", {o.cat for o in detect([("3:185:20", w), ("x", "إِلَّا")])}, w)
        self.assertFalse(cases.faala("أَدۡنَىٰ"))      # planted: the skeleton without its hamzah is دنيا's
        self.assertFalse(cases.faala("ٱسۡتَسۡقَىٰ"))   # a verb's letters before سقي
        self.assertFalse(cases.faala("عَلَىٰ"))        # planted: العليا's skeleton, but no alif at the end
        self.assertTrue(cases.faala("مُوسَى\u0653\u0670"))  # the spine's ىٰٓ order (2:51:3)
        from checks.kfgqpc import norm
        self.assertEqual(norm("مُوسۭيٰ").count("\u065c"), 1)     # KFGQPC's taqlīl mark for Abū ʿAmr
        self.assertEqual(norm("بِسِيمٰۭهُمۡ").count("\u065c"), 1)
        self.assertEqual(norm("عَلِيمُۢ").count("\u065c"), 0)    # (U+06E2 iqlāb untouched)

    def test_detect_moves_the_occurrence(self):
        got = {o.cat: o.base for o in detect([("3:15:2", "أَؤُنَبِّئُكُم"), ("3:15:3", "بِخَيۡرٖ")])}
        self.assertEqual(got.get("hamzatayn_madmumah"), "hamzatayn")
        self.assertNotIn("hamzatayn", got)
        got = {o.cat for o in detect([("2:53:3", "مُوسَى"), ("2:53:4", "ٱلۡكِتَٰبَ")])}
        self.assertIn("imala_wasl_sakin", got)
        got = {o.cat for o in detect([("2:53:3", "مُوسَى")], stop="2:53:3")}  # at a stop the alif is read
        self.assertIn("imala_alif_tanith", got)


@sources
class InTheReading(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from mushaf_data.api import Mushaf
        cls.m = Mushaf()

    def word(self, rawi, ref, slot, m=None):
        return next(w for w in (m or self.m).read(rawi, ref) if w.slot == slot)

    def test_hisham_madmumah(self):
        # wafi 90-91: Hishām, the second hamzah maḍmūmah, idkhāl with a khulf (not the maftūḥah's tas-hīl)
        w = self.word("hisham", "3:15", "3:15:2")
        r = next(r for r in w.rules if r.cat == "hamzatayn_madmumah")
        self.assertEqual(list(r.wujuh), ["tahqiq_idkhal", "tahqiq"])
        self.assertIn("maḍmūmah", r.case)

    def test_planted_wrong_case_reaches_the_reading(self):
        t = copy.deepcopy(usul_tables.tables())
        t["hamzatayn"]["cases"][2]["ruwat"]["hisham"]["wujuh"] = ["tashil"]
        with mock.patch.object(usul_tables, "tables", lambda: t):
            usul_tables._profiles.cache_clear()
            try:
                from mushaf_data.api import Mushaf
                w = self.word("hisham", "3:15", "3:15:2", Mushaf())
            finally:
                usul_tables._profiles.cache_clear()
        self.assertEqual([r.chosen for r in w.rules if r.cat == "hamzatayn_madmumah"], ["tashil"])

    def test_abu_amr_faala_taqlil(self):
        # wafi 150: al-Dūrī ʿan Abī ʿAmr's taqlīl on the faʿlā words (مُوسَى at a stop: the āyah's end 2:92)
        w = self.word("duri_abuamr", "2:51", "2:51:3")
        self.assertIn("imala_alif_tanith", {r.cat for r in w.rules})

    def test_a_case_tied_to_its_category(self):
        # one wajh per span: Warsh's taqlīl on ذوات الياء and on the faʿlā words is one choice
        cats = {r.cat for w in self.m.read("warsh", "2:83") for r in w.rules}
        self.assertTrue({"imala_ya", "imala_alif_tanith"} <= cats)  # ٱلۡقُرۡبَىٰ (faʿlā) and وَٱلۡيَتَٰمَىٰ
        ch = self.m.choices("warsh", "2:83")
        self.assertIn("imala_ya", ch)
        self.assertNotIn("imala_alif_tanith", ch)
        w = self.m.read("warsh", "2:83", choice={"imala_ya": "taqlil", "badal": "tul", "madd_arid": "ishba"})  # (taḥrīr)
        self.assertEqual({r.chosen for x in w for r in x.rules if r.cat in ("imala_ya", "imala_alif_tanith")}, {"taqlil"})

    def test_the_excepted_words_everywhere(self):
        # wafi 142-143: إِلَىٰ is never mumāl, outside the spike's passage too (2:54:12)
        w = self.word("warsh", "2:54", "2:54:12")
        self.assertEqual([r for r in w.rules if r.cat.startswith("imala")], [])

    def test_constraint_written_for_the_category_binds_the_case(self):
        from mushaf_data.constraints import as_base
        self.assertEqual(as_base({"imala_alif_tanith": "taqlil"})["imala_ya"], "taqlil")
        self.assertNotIn("imala_ya", as_base({"imala_wasl_sakin": "fath"}))


@sources
class ListedInTheReading(unittest.TestCase):
    """A listed entry reaches the reading through its stored slots (pipeline.anchor), as its own
    choice at that word; nothing matches a bare word when the engine runs."""

    def test_warsh_bi_sa(self):
        from mushaf_data.api import Mushaf
        # wafi 102: Warsh's ibdāl in بئس "حيث جاء وكيف أتى" (the table's ʿayn case: taḥqīq)
        w = next(w for w in Mushaf().read("warsh", "2:90") if w.slot == "2:90:1")
        r = next(r for r in w.rules if r.cat == "ibdal_sakin_ayn")
        self.assertEqual(list(r.wujuh), ["ibdal"])
        self.assertIn("wafi 102", r.wujuh["ibdal"])
        # elsewhere the case holds: وَبِئۡرٖ is listed too, but ٱلذِّئۡبُ isn't Warsh's
        w = next(w for w in Mushaf().read("warsh", "12:13") if w.slot == "12:13:10")  # ٱلذِّئۡبُ
        self.assertEqual([list(r.wujuh) for r in w.rules if r.cat.startswith("ibdal")], [["tahqiq"]])

    def test_planted_unanchored_entry_reaches_nothing(self):
        import mushaf_data.usul_tables as ut
        from mushaf_data.api import Mushaf
        t = copy.deepcopy(ut.tables())
        for x in t["ibdal_sakin"]["listed"]:
            if "بئس" in x["words"]:
                x["places"] = []  # as if flagged: the words alone must not reach the reading
        with mock.patch.object(ut, "tables", lambda: t):
            ut.listed_at.cache_clear()
            try:
                w = next(w for w in Mushaf().read("warsh", "2:90") if w.slot == "2:90:1")
            finally:
                ut.listed_at.cache_clear()
        self.assertEqual([r.chosen for r in w.rules if r.cat == "ibdal_sakin_ayn"], ["tahqiq"])

    def test_a_listed_place_is_its_own_choice(self):
        from mushaf_data.api import Mushaf
        ch = Mushaf().choices("warsh", "2:90")
        self.assertIn("ibdal_sakin_ayn@2:90:1", ch)


if __name__ == "__main__":
    unittest.main()
