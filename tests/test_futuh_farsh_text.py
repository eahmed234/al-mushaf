"""The written farsh text against al-Futūḥ's rows (checks.futuh.farsh_text): the independent check
for the twelve ruwāt KFGQPC has no text for. Needs ../mushaf and the written cases in
pipeline/out/farsh_text (the private al-mushaf-extractions repo)."""
import copy
import unittest

from mushaf_data.paths import ROOT

from . import needs

WRITTEN = (ROOT / "pipeline/work/farsh_text/keys.json").exists() and (ROOT / "pipeline/out/farsh_text").exists()


@needs.futuh
@unittest.skipUnless(WRITTEN, "the written farsh text (pipeline/out/farsh_text) isn't here")
class FarshText(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from checks.futuh import farsh_text
        from pipeline.farsh_text import entries
        cls.ft = farsh_text
        cls.entries = {1: entries()[1]}
        cls.res = farsh_text.check((1,), cls.entries)

    def kinds(self, res, slot):
        return {r["rawi"]: r["kind"] for r in res if r["slot"] == slot}

    def test_malik_all_twenty(self):
        """مالك / ملك (1:4:1): al-Futūḥ prints every rāwī, each with his written text."""
        k = self.kinds(self.res, "1:4:1")
        self.assertEqual(len(k), 20)
        self.assertEqual(set(k.values()), {"agree"})

    def test_planted_error_is_caught(self):
        """Isḥāq moved to the other text at 1:4:1: the check says he differs, and nobody else."""
        e = copy.deepcopy(self.entries)
        groups = e[1]["1:4:1"]["groups"]
        src = next(g for g in groups if "ishaq" in g["readers"])
        dst = next(g for g in groups if g is not src and g.get("text"))
        src["readers"].remove("ishaq")
        dst["readers"].append("ishaq")
        k = self.kinds(self.ft.check((1,), e), "1:4:1")
        self.assertEqual(k["ishaq"], "differ")
        self.assertEqual({r for r, v in k.items() if v != "agree"}, {"ishaq"})

    def test_judge(self):
        j = self.ft.judge
        self.assertEqual(j([], {("x", False)}), "no_text")
        self.assertEqual(j(["مَٰلِكِ"], set()), "no_row")
        self.assertEqual(j(["مَٰلِكِ"], {("مَٰلِكِ", False)}), "agree")
        self.assertEqual(j(["مَٰلِكِ"], {("مَلِكِ", False)}), "differ")
        self.assertEqual(j(["مَٰلِكِ"], {("مَٰلِكِ", False), ("مَلِكِ", False)}), "extra")
        self.assertEqual(j(["مَٰلِكِ", "مَلِكِ"], {("مَلِكِ", False)}), "khulf_unseen")
