"""The spike's checks against al-Futūḥ al-Bāhira (needs ../mushaf): its rows for 1:1-2:20 and
the waqf forms it prints in six volumes. A drop below these numbers is a regression; a rise means
something was fixed, and the number here should be raised with it."""
import unittest
from unittest import mock

from mushaf_data import profiles

from . import needs


@needs.futuh
class Rows(unittest.TestCase):
    """The sughrā leaves out Idrīs's sakt from al-Mubhij, which al-Futūḥ prints (8 rows); the kubrā
    edition has it (Eisa 2026-11-26: other ṭuruq go to the kubrā)."""
    KUBRA_ONLY = {("idris", "sakt_al=sakt"), ("idris", "sakt_mafsul=sakt")}

    @classmethod
    def setUpClass(cls):
        from checks.futuh import readings
        cls.readings = readings
        cls.all = readings.check(20, book=True)

    def test_all_rows(self):
        self.assertEqual((self.all["reproduced"], self.all["pairs"]), (666, 676))
        self.assertLessEqual(self.all["extras"], 3)
        self.assertEqual(self.all["conflicts"], [])
        kubra = {m[0] for m in self.all["misses"] if (m[1], m[2].split()[-1].split(",")[-1]) in self.KUBRA_ONLY}
        self.assertEqual(len(kubra), 8)

    def test_from_the_books_alone(self):
        r = self.readings.check(0, book=True, test=(1, 20))
        self.assertEqual((r["reproduced"], r["pairs"]), (653, 666))

    def test_unified_usul_tables_give_the_same(self):
        """data/usul/ in place of the profile table: the same rows reproduced."""
        from mushaf_data import usul_tables
        with mock.patch.object(profiles, "load", usul_tables.profiles):
            r = self.readings.check(20, book=True)
        self.assertEqual((r["reproduced"], r["pairs"]), (666, 676))

    def test_kubra_edition_has_al_futuhs_sakt(self):
        from mushaf_data import usul_tables
        with mock.patch.object(profiles, "load", lambda *a, **k: usul_tables.profiles("kubra")):
            r = self.readings.check(20, book=True)
            b = self.readings.check(0, book=True, test=(1, 20))
        self.assertEqual((r["reproduced"], r["pairs"], b["reproduced"], b["pairs"]), (674, 676, 661, 666))
        self.assertEqual(r["conflicts"], [])

    def test_planted_profile_error_is_caught(self):
        real = profiles.load

        def wrong(*a, **k):  # Qālūn without his ṣilah of mīm al-jamʿ
            p = real(*a, **k)
            p["qalun"]["silah_mim"] = {**p["qalun"]["silah_mim"], "wujuh": {"iskan": ["planted"]}}
            return p

        with mock.patch.object(profiles, "load", wrong):
            r = self.readings.check(20, book=True)
        self.assertLess(r["reproduced"], self.all["reproduced"])
        self.assertTrue(any(m[1] == "qalun" for m in r["misses"]))


@needs.futuh
class Waqf(unittest.TestCase):
    def test_printed_forms(self):
        from checks import waqf
        r = waqf.run()
        self.assertEqual((r["covered"], r["rows"]), (806, 871))

    def test_planted_rule_error_is_caught(self):
        from checks import waqf
        real = waqf.forms
        with mock.patch.object(waqf, "forms", lambda w, r: [f for f in real(w, r) if not f[0].startswith("naql")]):
            r = waqf.run()
        self.assertLess(r["covered"], 806 - 100)
