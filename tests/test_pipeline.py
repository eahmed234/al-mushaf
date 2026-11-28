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

    @needs.sources
    def test_anchor_the_variant_word_and_its_limits(self):
        """A row writes the reading it describes (تعملون for يَعۡمَلُونَ, idah 200); a row "wherever it
        occurs" names its first place only; the skeleton's lost hamzah and article don't widen it."""
        from pipeline.farsh_books import anchor
        row = {"sura": 2, "ayah": 144, "word": "تَعْمَلُونَ", "words": "تَعْمَلُونَ", "where": "here"}
        self.assertEqual(anchor(row), ["2:144:34"])
        row = {"sura": 2, "ayah": 96, "word": "يَعْمَلُونَ", "words": "بِمَا يَعْمَلُونَ قُلْ", "where": "here"}
        self.assertEqual(anchor(row), ["2:96:25"])          # the run goes on into 2:97
        row = {"sura": 2, "ayah": 168, "word": "خطوات", "words": "خطوات", "where": "all"}
        self.assertEqual(anchor(row), ["2:168:11", "2:208:10"])
        row = {"sura": 2, "ayah": None, "word": "الأكل", "words": "الأكل", "where": "all"}
        self.assertNotIn("2:20:23", anchor(row))             # planted: كُلِّ is not الأُكُل
        row = {"sura": 3, "ayah": None, "word": "بيوت", "words": "البيوت", "where": "all"}
        self.assertEqual(anchor(row), ["3:49:37", "3:154:55"])
        row = {"sura": 3, "ayah": None, "word": "الميت", "words": "الميت", "where": "all"}
        self.assertNotIn("2:258:23", anchor(row, 2))         # planted: وَأُمِيتُ has a hamzah


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
        idah = "إسكان الهاء بعد الواو والفاء واللام"
        self.assertTrue(prefix_ok(idah, "فَهُوَ"))
        self.assertFalse(prefix_ok(idah, "هُوَ"))            # planted: Abū Jaʿfar's bare هو (idah 192)

    def test_usul_words_and_cover(self):
        from pipeline.farsh_books import usul_covers, usul_row
        row = {"book": "wafi", "page": 51, "words": "عليهم", "reading": "بضم الهاء وقفا ووصلا"}
        self.assertTrue(usul_row(row).startswith("ha_mim_jam"))
        self.assertIsNone(usul_row({**row, "page": 200}))   # planted: a page the table doesn't cite
        self.assertTrue(usul_covers("2:61:52", "ٱلنَّبِيِّـۧنَ", "ibn_wardan", "بالهمز").startswith("hamz_mufrad"))
        self.assertIsNone(usul_covers("2:61:52", "ٱلنَّبِيِّـۧنَ", "qalun", "بالهمز"))  # planted: not in the table
        self.assertIsNone(usul_covers("2:10:12", "يَكۡذِبُونَ", "ruways", "بضم الياء"))  # planted: al-Qaṣaṣ's yāʾ

    def test_durrah_fill_where_al_idah_speaks(self):
        """The aṣl fill (idah 226) yields where al-Īḍāḥ names the rāwī elsewhere at the word."""
        import yaml

        def at(slot):
            f = DATA / "farsh_books" / f"{int(slot.split(':')[0]):03d}.yaml"
            return [o for e in yaml.safe_load(f.read_text(encoding="utf-8")) if slot in e["place"] for o in e["options"]]
        self.assertEqual(at("1:7:4"), [])                   # hāʾ al-jamʿ: uṣūl (ha_mim_jam, idah 54-55)
        tarja = [o["cite"] for o in at("3:109:10") if "ruways" in o["readers"] and not o.get("base")]
        self.assertEqual(tarja, ["idah 191"])               # not Abū ʿAmr's (wafi 219)
        wahuwa = [o["reading"] for o in at("2:85:19") if "ruways" in o["readers"]]
        self.assertFalse(any("بإسكان" in r for r in wahuwa))  # idah 192: ḍamm, not wafi 201's iskān
        nabi = [o for o in at("2:61:52") if "ibn_wardan" in o["readers"]]
        self.assertTrue(nabi and all(o.get("base") for o in nabi))  # as Ḥafṣ; hamz_mufrad (idah 115)
        # each thing the entries speak of gets its aṣl option (ونكفر 2:271: the nūn, then the jazm)
        nukaffir = sorted(o["reading"] for o in at("2:271:13") if "ibn_wardan" in o["readers"])
        self.assertEqual(nukaffir, ["بالنون", "بجزم الراء"])
        # al-Īḍāḥ's own rows reach their words (2:144 idah 200; 2:229 idah 215), not the aṣl fill
        self.assertEqual([o["cite"] for o in at("2:144:34") if "rawh" in o["readers"]], ["idah 200"])
        self.assertEqual([o["cite"] for o in at("2:229:18") if "ishaq" in o["readers"]], ["idah 215"])
        # pinned by the quote, and Abū Jaʿfar's وكأين from the uṣūl chapter (idah 112)
        self.assertTrue(any(o["cite"] == "wafi 211" and "hafs" in o["readers"] for o in at("2:140:2")))
        self.assertEqual([o["cite"] for o in at("3:146:1") if "ibn_wardan" in o["readers"]], ["idah 112"])
        self.assertEqual(at("2:24:2"), [])                  # the sakt row of الم is uṣūl, not لَّمۡ's farsh
        basat = [o for o in at("2:245:14") if "khallad" in o["readers"]]
        self.assertTrue(len(basat) == 2 and all("khallad" in o["khulf"] for o in basat))  # wafi 220

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
