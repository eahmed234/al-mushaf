"""The spine across the twenty (milestone 3): Ḥafṣ is one projection, KFGQPC's eight align with
their projections without gaps."""
import unittest
from unittest import mock

from mushaf_data import spine
from mushaf_data.ruwat import RUWAT

from . import needs


@needs.sources
class Projections(unittest.TestCase):
    def test_hafs_is_his_words(self):
        self.assertEqual(spine.projection("hafs"), list(spine.words()))

    def test_the_three_places(self):
        bazzi, qalun, hafs = (set(spine.projection(r)) for r in ("bazzi", "qalun", "hafs"))
        self.assertIn("9:100:17a", bazzi)              # تجري من تحتها (budur 139)
        self.assertNotIn("9:100:17a", hafs)
        self.assertNotIn("40:26:13", qalun)            # وأن يظهر (budur 279)
        self.assertNotIn("57:24:10", qalun)            # بحذف لفظ هو (wafi 368, budur 315)
        self.assertIn("57:24:10", bazzi)

    def test_slot_data_is_sound(self):
        d = spine.slot_data()
        for e in (d.get("added") or []) + (d.get("empty") or []):
            self.assertTrue(set(e["readers"]) <= set(RUWAT), e)
            self.assertTrue(e["cite"], e)
        for a in d.get("added") or []:
            self.assertIn(a["after"], spine.words())

    def test_unknown_rawi_refused(self):
        with self.assertRaises(ValueError):
            spine.projection("hafss")


@needs.sources
class AgainstKFGQPC(unittest.TestCase):
    def test_no_gaps(self):
        from checks import spine as cs
        self.assertEqual(cs.check()["gaps"], [])

    def test_planted_missing_slot_data_is_caught(self):
        """Without the slot data the three places come back as gaps, for the ruwāt the books name."""
        from checks import spine as cs
        try:
            with mock.patch.object(spine, "slot_data", lambda: {"added": [], "empty": []}):
                spine.slots.cache_clear()
                gaps = {(g["rawi"], g["surah"]) for r in cs.FILES for s in (9, 40, 57) for g in cs.align(r, s)}
        finally:
            spine.slots.cache_clear()
        self.assertEqual(gaps, {("bazzi", 9), ("qunbul", 9), ("qalun", 57), ("warsh", 57)}
                         | {(r, 40) for r in ("qalun", "warsh", "bazzi", "qunbul", "duri_abuamr", "susi")})

    def test_a_split_token_is_not_a_gap_but_a_lost_word_is(self):
        from checks.spine import same_rasm
        self.assertTrue(same_rasm(["أَوَلَمۡ"], ["أَوَ", "لَمۡ"]))
        self.assertTrue(same_rasm(["وَأَلَّوِ"], ["وَأَن", "لَّوِ"]))
        self.assertFalse(same_rasm(["أَوۡ", "أَن"], ["وَأَن"]))
