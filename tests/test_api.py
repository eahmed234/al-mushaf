"""The retrieval API (mushaf_data/api.py): readings, choices, explain, who; against KFGQPC."""
import unittest

from mushaf_data import api
from mushaf_data.spine import words

from .needs import sources


class Reading(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = api.Mushaf()

    def test_hafs_reads_his_own_text(self):
        ws = self.m.read("hafs", "1")
        self.assertEqual([w.text for w in ws], [words()[w.slot] for w in ws])
        self.assertTrue(ws[-1].stop)

    def test_refs(self):
        self.assertEqual(api.parse_ref("1:1-2:20"), ((1, 1), (2, 20)))
        self.assertEqual(len(api.span("hafs", "2:1-5")), 36)
        self.assertEqual(len(api.span("hafs", "1")), 29)

    def test_spine_projection(self):
        """Ibn Kathīr reads the added من at 9:100 (budur 139); Ḥafṣ doesn't."""
        self.assertIn("9:100:17a", api.span("bazzi", "9:100"))
        self.assertNotIn("9:100:17a", api.span("hafs", "9:100"))

    def test_naql_across_words_reaches_warsh(self):
        w = next(w for w in self.m.read("warsh", "2:10") if w.slot == "2:10:9")
        self.assertEqual([r.chosen for r in w.rules if r.cat == "naql_word"], ["naql"])
        self.assertNotIn("أ", w.text)

    def test_choices_and_count(self):
        ch = self.m.choices("warsh", "2:1-20")
        self.assertEqual(list(ch["badal"]), ["qasr", "tawassut", "tul"])
        c = self.m.count("warsh", "2:1-20")
        self.assertLess(c["exact"], c["product"])  # taḥrīr removes combinations

    def test_a_choice_he_doesnt_have_is_refused(self):
        with self.assertRaises(ValueError):
            self.m.read("hafs", "2:1-5", choice={"ibdal_sakin": "ibdal"})

    def test_farsh_word_takes_its_written_text(self):
        """data/farsh_text: Qālūn's مالك is the written ملك, and the uṣūl run on it."""
        w = next(w for w in self.m.read("qalun", "1:4") if w.slot == "1:4:1")
        self.assertEqual((w.text, w.source), ("مَلِكِ", "farsh_text"))
        self.assertTrue(any(not o["base"] for o in w.farsh))

    def test_farsh_word_without_text_is_unknown(self):
        """Khalaf's ishmām of the ṣād at 1:7:1 has no written form (text null): no text, no rules."""
        w = next(w for w in self.m.read("khalaf_an_hamzah", "1:7") if w.slot == "1:7:1")
        self.assertIsNone(w.text)
        self.assertEqual(w.source, "none")

    def test_who_and_explain(self):
        groups = self.m.who("1:4:1")
        self.assertEqual(sum(len(g["readers"]) for g in groups), 20)
        base = [g for g in groups if g.get("base")]
        self.assertTrue(any("hafs" in g["readers"] for g in base))
        e = self.m.explain("1:4:1")
        self.assertTrue(e["farsh"]["books"] and e["farsh"]["budur"])


@sources
class AgainstKFGQPC(unittest.TestCase):
    def test_al_fatihah_and_al_baqarah(self):
        from checks.api import check
        m = api.Mushaf()
        ag = n = 0
        for rawi in ("warsh", "qalun", "susi"):
            for s in (1, 2):
                r = check(rawi, s, m)
                ag += r.get("agree", 0)
                n += r.get("agree", 0) + r.get("differ", 0)
                self.assertEqual(r.get("unaligned", 0), 0)
        self.assertGreater(ag / n, 0.98)
        self.planted(ag)

    def planted(self, real: int):
        """Warsh without his ibdāl of the sākin hamzah: fewer words agree."""
        from checks.api import check
        m = api.Mushaf()
        m.profiles["warsh"]["ibdal_sakin"] = {"wujuh": {"tahqiq": ["planted"]}}
        self.assertLess(check("warsh", 2, m)["agree"], check("warsh", 2, api.Mushaf())["agree"])


if __name__ == "__main__":
    unittest.main()
