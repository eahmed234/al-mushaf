"""The data files load and validate: every category covers the twenty once, every row cites a
page, every constraint names real ruwāt and wujūh."""
import tempfile
import unittest
from pathlib import Path

import yaml

from mushaf_data import constraints, profiles
from mushaf_data.ruwat import RUWAT


def _write(data) -> Path:
    f = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8")
    yaml.safe_dump(data, f, allow_unicode=True)
    f.close()
    return Path(f.name)


class Profiles(unittest.TestCase):
    def setUp(self):
        self.raw = yaml.safe_load(profiles.PATH.read_text(encoding="utf-8"))

    def test_every_category_covers_the_twenty(self):
        p = profiles.load()
        self.assertEqual(set(p), set(RUWAT))
        cats = set(self.raw["categories"])
        for r in RUWAT:
            self.assertEqual(set(p[r]), cats, r)

    def test_planted_missing_rawi_is_caught(self):
        # Idrīs dropped from a row (a Durrah rāwī: "rest7" only fills the Shāṭibiyyah's fourteen)
        cat, rows = next((c, rs) for c, rs in self.raw["categories"].items()
                         if any(isinstance(r["who"], list) and "idris" in r["who"] for r in rs))
        row = next(r for r in rows if isinstance(r["who"], list) and "idris" in r["who"])
        row["who"] = [r for r in row["who"] if r != "idris"] or ["ishaq"]
        with self.assertRaisesRegex(ValueError, f"{cat}: no row for"):
            profiles.load(_write(self.raw))

    def test_planted_missing_cite_is_caught(self):
        rows = next(iter(self.raw["categories"].values()))
        del rows[0]["cite"]
        with self.assertRaisesRegex(ValueError, "cites no page"):
            profiles.load(_write(self.raw))

    def test_place_wujuh_name_real_ruwat_and_categories(self):
        cats = set(self.raw["categories"])
        for e in profiles.place_wujuh():
            self.assertIn(e["rawi"], RUWAT)
            self.assertIn(e["category"], cats)


class Constraints(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(constraints.validate(), [])

    def test_planted_bad_wajh_is_caught(self):
        bad = [dict(c) for c in constraints.CONSTRAINTS if "cats" in c]
        bad[0] = {**bad[0], "allowed": bad[0]["allowed"] + [["no_such_wajh"] * len(bad[0]["cats"])]}
        self.assertTrue(any("no_such_wajh" in p for p in constraints.validate(bad)))

    def test_planted_unknown_rawi_is_caught(self):
        bad = [{**c, "rawi": ["nobody"]} for c in constraints.CONSTRAINTS if "cats" in c][:1]
        self.assertTrue(any("unknown rāwī" in p for p in constraints.validate(bad)))
