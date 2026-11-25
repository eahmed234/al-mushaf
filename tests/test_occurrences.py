"""al-Budūr's per-rubʿ imālah lists tied to the spine's quarters (needs books/)."""
import random
import unittest

from mushaf_data import occurrences

from . import needs


@needs.sources
@needs.books
class ImalaLists(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lists = occurrences.lists()

    def test_lists_tied(self):
        tbl, unmatched = occurrences.build(self.lists, write=False)
        self.assertEqual((len(self.lists), len(tbl)), (175, 171))

    def test_planted_shuffled_lists_are_caught(self):
        texts = [(t, b) for _, t, b in self.lists]
        random.Random(0).shuffle(texts)
        wrong = [(p, t, b) for (p, _, _), (t, b) in zip(self.lists, texts)]
        tbl, _ = occurrences.build(wrong, write=False)
        # caught, but weakly: shuffled lists still tie 131 (a tie needs only a score of 3), so
        # the count of ties is not evidence that each list is on its own rubʿ
        self.assertLess(len(tbl), 171)

    def test_zaka_excluded_only_at_al_nur_21(self):
        """al-Wāfī pp. 142-143: the word excluded at al-Nūr 21 is mumāl elsewhere."""
        h = occurrences.hafs_all()
        places = [w for w, t in h.items() if occurrences.skel(t) == "زكي"]
        here = [w for w in places if w.startswith("24:21:")]
        self.assertTrue(here and len(places) > len(here))
        for w in places:
            self.assertEqual(occurrences.imala_excluded(h[w], w), w.startswith("24:21:"), w)
