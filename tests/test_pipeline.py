"""The extraction pipeline's checks: the validator rejects what it should, the scorer counts
what it should, and the gold set is consistent (needs books/)."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from mushaf_data.paths import DATA
from mushaf_data.ruwat import RUWAT
from pipeline import score, validate
from pipeline.gold import GOLD

from . import needs


class Readers(unittest.TestCase):
    def test_reader_table_names_real_ruwat(self):
        d = yaml.safe_load((DATA / "readers.yaml").read_text(encoding="utf-8"))
        for section in d.values():
            for name, ids in section.items():
                self.assertTrue(ids and set(ids) <= set(RUWAT), name)


@needs.books
class Validator(unittest.TestCase):
    def row(self, **k):
        r = {"place": [], "kind": "farsh", "category": None, "readers": ["shuba", "hafs"], "khulf": [],
             "reading": "x", "condition": None, "scope": "here", "quote": "قرأ الكوفيون بفتح الياء وسكون الكاف وتخفيف الذال"}
        r.update(k)
        return r

    def test_good_row(self):
        self.assertEqual(validate.check_row(self.row(), "budur", 21, set()), [])

    def test_planted_invented_quote(self):
        bad = validate.check_row(self.row(quote="قرأ الكوفيون بضم الياء"), "budur", 21, set())
        self.assertIn("quote not on the page", bad)

    def test_planted_khulf_outside_readers(self):
        self.assertIn("khulf not within readers", validate.check_row(self.row(khulf=["warsh"]), "budur", 21, set()))

    def test_planted_unknown_rawi(self):
        self.assertTrue(any(b.startswith("rāwī") for b in validate.check_row(self.row(readers=["asim"]), "budur", 21, set())))


@needs.books
class Gold(unittest.TestCase):
    PAGES = list(range(16, 26))

    def test_spans_are_on_their_pages(self):
        texts = validate.pages("budur")
        for f in sorted((GOLD / "budur").glob("p*.json")):
            for r in json.loads(f.read_text(encoding="utf-8"))["rows"]:
                pg, a, b = r["span"]
                self.assertTrue(0 <= a < b <= len(texts[pg]), (f.name, r["span"]))
                self.assertTrue(set(r["khulf"]) <= set(r["readers"]) <= set(RUWAT))

    def test_gold_scores_itself_fully(self):
        s = score.score(GOLD / "budur", self.PAGES)
        self.assertEqual((s["recall"], s["precision"]), (1.0, 1.0))

    def test_planted_wrong_readers_are_caught(self):
        with tempfile.TemporaryDirectory() as tmp:
            for f in (GOLD / "budur").glob("p*.json"):
                d = json.loads(f.read_text(encoding="utf-8"))
                if d["page"] == 21:  # يكذبون: one rāwī moved between the two groups
                    for r in d["rows"]:
                        if "2:10:12" in r["place"]:
                            r["readers"] = [x for x in r["readers"] if x != "shuba"] if "hafs" in r["readers"] else r["readers"] + ["shuba"]
                Path(tmp, f.name).write_text(json.dumps(d, ensure_ascii=False))
            s = score.score(Path(tmp), self.PAGES)
        self.assertEqual(len(s["missed"]), 1)  # Shuʿbah's unit moved from one group to the other
        self.assertLess(s["recall"], 1.0)


class FarshBooks(unittest.TestCase):
    """The farsh read from al-Wāfī / al-Īḍāḥ (pilot 2026-11-27): rows name words, anchored here."""

    @needs.sources
    def test_anchor_takes_the_word_the_reading_is_about(self):
        from pipeline.farsh_books import anchor
        row = {"sura": 3, "ayah": None, "word": "قرح", "words": "إن يمسسكم قرح", "where": "here"}
        self.assertEqual(anchor(row), ["3:140:3"])
        row = {"sura": 3, "ayah": None, "word": "يأمركم", "words": "ولا يأمركم", "where": "here"}
        self.assertEqual(anchor(row), ["3:80:2"])

    @needs.sources
    def test_planted_word_not_in_the_sura_is_not_anchored(self):
        """متنا isn't in Āl ʿImrān; مِن is not close enough to stand for it."""
        from pipeline.farsh_books import anchor
        self.assertEqual(anchor({"sura": 3, "ayah": None, "word": "متنا", "words": "متنا", "where": "here"}), [])


class FarshBooksCombine(unittest.TestCase):
    """al-Fātiḥah to Āl ʿImrān from the books (2026-11-27): general rows carry over, conditions hold."""

    @needs.sources
    def test_general_rows_keep_their_conditions(self):
        from pipeline.farsh_books import before_ok, prefix_ok
        cond = "بإسكان الهاء إذا قرنت بالواو أو الفاء أو اللام"
        self.assertTrue(prefix_ok(cond, "وَهُوَ"))
        self.assertFalse(prefix_ok(cond, "هُوَ"))            # planted: a bare هو is not covered (wafi 201)
        alif = "بإثبات ألف أنا وصلا قبل همزة قطع مضمومة أو مفتوحة"
        self.assertTrue(before_ok(alif, "أُحۡيِۦ"))
        self.assertFalse(before_ok(alif, "مَعَكُم"))         # planted: no hamzah after أنا (wafi 222)

    @needs.sources
    def test_against_kfgqpc_nothing_contradicted_in_al_imran(self):
        from checks import farsh
        try:
            farsh.FARSH = DATA / "farsh_books"
            r = farsh.check(3)
        finally:
            farsh.FARSH = DATA / "farsh"
        self.assertGreaterEqual(len(r["both"]), 230)
        self.assertEqual(r["table_only"], [])
