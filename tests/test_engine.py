"""The engine alone (book profiles, the book's imālah rule, constraints), no al-Futūḥ."""
import unittest

from mushaf_data import constraints
from mushaf_data.generate import generate
from mushaf_data.profiles import load
from mushaf_data.spine import passage

from . import needs


@needs.sources
class Taḥrīr(unittest.TestCase):
    """al-Budūr pp. 21-22: Warsh at 2:8, stopping at its end, has six wujūh of badal × madd ʿāriḍ."""

    def wujuh(self, cons=None):
        span = [w for w in passage() if w.startswith("2:8:")]
        gens = generate("warsh", span, load(), constraints=cons)
        return {(c.get("badal"), c.get("madd_arid")) for c, _ in gens if c["_stop"] == span[-1]}

    def test_warsh_2_8_six_wujuh(self):
        self.assertEqual(self.wujuh(), {("qasr", "qasr"), ("qasr", "tawassut"), ("qasr", "ishba"),
                                        ("tawassut", "tawassut"), ("tawassut", "ishba"), ("tul", "ishba")})

    def test_planted_missing_constraint_is_caught(self):
        cons = [c for c in constraints.CONSTRAINTS if c.get("id") != "warsh_badal_arid"]
        self.assertGreater(len(self.wujuh(cons)), 6)

    def test_every_reading_keeps_the_constraints(self):
        span = [w for w in passage() if w.startswith("2:8:")]
        for rawi in ("warsh", "khallad", "hisham", "hafs"):
            for ch, _ in generate(rawi, span, load()):
                self.assertTrue(constraints.allowed(rawi, ch), (rawi, ch))
