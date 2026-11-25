"""The sources are the pinned ones, and the spine is what tools/build_spine.py makes from them."""
import csv
import json
import unittest

from mushaf_data import spine
from mushaf_data.paths import ROOT, SOURCES
from tools import build_spine, fetch_sources

from . import needs


@needs.sources
class Sources(unittest.TestCase):
    def rows(self):
        with open(ROOT / "tools" / "sources.tsv", encoding="utf-8") as f:
            return list(csv.DictReader(f, delimiter="\t"))

    def test_checksums(self):
        for row in self.rows():
            self.assertEqual(fetch_sources.sha(SOURCES / row["path"]), row["sha256"], row["path"])

    def test_planted_tampered_file_is_caught(self):
        row = self.rows()[0]
        data = bytearray((SOURCES / row["path"]).read_bytes())
        data[len(data) // 2] ^= 1
        tmp = ROOT / "build" / "tampered"
        tmp.parent.mkdir(exist_ok=True)
        tmp.write_bytes(data)
        try:
            self.assertNotEqual(fetch_sources.sha(tmp), row["sha256"])
        finally:
            tmp.unlink()


@needs.sources
class Spine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.built = build_spine.build()

    def differing(self, items):
        on_disk = list(spine.items())
        return [a["id"] for a, b in zip(items, on_disk) if a != b] + (["length"] if len(items) != len(on_disk) else [])

    def test_counts(self):
        kinds = {}
        for it in spine.items():
            kinds[it["kind"]] = kinds.get(it["kind"], 0) + 1
        self.assertEqual(kinds, {"word": 77430, "ayah_end": 6236, "hizb": 199})

    def test_spine_is_built_from_the_pinned_text(self):
        self.assertEqual(self.differing(self.built), [])

    def test_planted_changed_word_is_caught(self):
        items = json.loads(json.dumps(self.built))
        w = next(i for i in items if i["id"] == "2:2:1")
        w["clusters"] = w["clusters"][:-1]
        self.assertEqual(self.differing(items), ["2:2:1"])
