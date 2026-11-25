"""The spike's checks against al-Futūḥ al-Bāhira (needs ../mushaf): its rows for 1:1-2:20 and
the waqf forms it prints in six volumes. A drop below these numbers is a regression; a rise means
something was fixed, and the number here should be raised with it."""
import unittest
from unittest import mock

from mushaf_data import profiles

from . import needs


@needs.futuh
class Rows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from checks.futuh import readings
        cls.readings = readings
        cls.all = readings.check(20, book=True)

    def test_all_rows(self):
        self.assertEqual((self.all["reproduced"], self.all["pairs"]), (674, 676))
        self.assertLessEqual(self.all["extras"], 3)
        self.assertEqual(self.all["conflicts"], [])

    def test_from_the_books_alone(self):
        r = self.readings.check(0, book=True, test=(1, 20))
        self.assertEqual((r["reproduced"], r["pairs"]), (661, 666))

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
