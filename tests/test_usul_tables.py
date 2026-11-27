"""data/usul/: one table per category for all twenty, holding the same rules as the reviewed
profile table the engine reads."""
import copy
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


class Editions(unittest.TestCase):
    """Options (ahl al-adāʾ views, off by default) and the kubrā (other ṭuruq), Eisa 2026-11-26."""

    def test_sughra_leaves_out_the_kubra(self):
        self.assertEqual(set(usul_tables.profiles()["idris"]["sakt_al"]["wujuh"]), {"none"})
        k = usul_tables.profiles("kubra")["idris"]
        self.assertEqual(set(k["sakt_al"]["wujuh"]), {"none", "sakt"})
        self.assertEqual(set(k["sakt_mafsul"]["wujuh"]), {"none", "sakt"})

    def test_every_extra_is_offered_or_in_the_kubra(self):
        ex = usul_tables.extras()
        self.assertTrue(any(e["kind"] == "options" for e in ex.values()))
        on = usul_tables.active("sughra", [k for k, e in ex.items() if e["kind"] == "options"])
        self.assertTrue(all(e["kind"] == "options" for e in on))
        self.assertEqual({e["kind"] for e in usul_tables.active("kubra")}, {"kubra"})

    def test_planted_unknown_option_is_refused(self):
        with self.assertRaises(ValueError):
            usul_tables.active("sughra", ["badal:no_such_view"])
        with self.assertRaises(ValueError):  # a kubrā entry can't be switched on as an option
            usul_tables.active("sughra", ["sakt_al:idris_sakt"])
        with self.assertRaises(ValueError):
            usul_tables.active("sughrah")

    def test_planted_extra_outside_the_engine_vocabulary_is_caught(self):
        t = copy.deepcopy(usul_tables.tables())
        t["sakt_al"]["kubra"][0]["adds"] = {"category": "sakt_al", "wujuh": ["ishba"]}
        usul_tables.extras.cache_clear()
        try:
            with mock.patch.object(usul_tables, "tables", lambda: t), self.assertRaises(ValueError):
                usul_tables.extras()
        finally:
            usul_tables.extras.cache_clear()
