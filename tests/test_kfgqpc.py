"""KFGQPC's eight riwāyāt, word by word, for 1:1-2:20. (The profiles still come from the
al-Futūḥ check's merge, so this needs ../mushaf too.)"""
import unittest
from unittest import mock

from . import needs


@needs.sources
@needs.futuh
class KFGQPC(unittest.TestCase):
    def test_eight_riwayat(self):
        from checks import kfgqpc
        r = kfgqpc.run(out=lambda *a: None)
        self.assertEqual(r["all"], (2047, 2056))
        self.assertEqual(r["hafs"][0], r["hafs"][1])
        self.assertEqual(r["shuba"][0], r["shuba"][1])

    def test_planted_text_error_is_caught(self):
        from checks import kfgqpc
        real = kfgqpc.kwords

        def wrong(rawi):  # one maddah lost in Warsh's text
            ws = real(rawi)
            k = next(i for i, w in enumerate(ws) if "ٓ" in w)
            return ws[:k] + [ws[k].replace("ٓ", "", 1)] + ws[k + 1:]

        only_warsh = {"warsh": kfgqpc.FILES["warsh"]}
        with mock.patch.object(kfgqpc, "FILES", only_warsh):
            base = kfgqpc.run(out=lambda *a: None)["warsh"]
            with mock.patch.object(kfgqpc, "kwords", wrong):
                r = kfgqpc.run(out=lambda *a: None)["warsh"]
        self.assertEqual(r[0], base[0] - 1)
