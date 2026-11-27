"""data/usul/: one table per category for all twenty, holding the same rules as the reviewed
profile table the engine reads."""
import unittest
from unittest import mock

import yaml

from mushaf_data import usul_tables
from mushaf_data.profiles import load as reviewed
from mushaf_data.ruwat import RUWAT


def differ(rev, uni):
    out = []
    for r in RUWAT:
        for cat, e in rev[r].items():
            if cat in uni[r] and set(e["wujuh"]) != set(uni[r][cat]["wujuh"]):
                out.append((cat, r))
    return out


class Tables(unittest.TestCase):
    def test_every_case_has_the_twenty_and_a_vocabulary(self):
        for c, t in usul_tables.tables().items():
            vocab = {w["id"] for w in t.get("wujuh") or []}
            for case in t.get("cases") or []:
                self.assertEqual(set(case["ruwat"]), set(RUWAT), (c, case.get("case")))
                for r, v in case["ruwat"].items():
                    self.assertTrue(v["wujuh"], (c, case.get("case"), r))
                    self.assertTrue(set(v["wujuh"]) <= vocab, (c, case.get("case"), r, v["wujuh"]))

    def test_same_rules_as_the_reviewed_table(self):
        # the only differences allowed are the finer splits recorded as `kept: table`
        allowed = {(d["category"], d["rawi"]) for t in usul_tables.tables().values()
                   for d in t.get("disagreements") or [] if d.get("kept") == "table" and "rawi" in d}
        self.assertEqual(set(differ(reviewed(), usul_tables.profiles())) - allowed, set())

    def test_planted_changed_wajh_is_caught(self):
        uni = usul_tables.profiles()
        uni["warsh"]["badal"] = {"wujuh": {"qasr": []}}  # Warsh's three badal wujūh cut to one
        self.assertIn(("badal", "warsh"), differ(reviewed(), uni))
