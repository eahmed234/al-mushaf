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
        from checks import farsh
        r = farsh.check(2)
        self.assertGreaterEqual(len(r["both"]), 304)
        self.assertLessEqual(len(r["kfgqpc_only"]), 86)

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
