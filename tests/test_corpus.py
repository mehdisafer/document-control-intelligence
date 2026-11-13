from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from pypdf import PdfReader

from dci.corpus import generate_corpus, generate_demo


class CorpusTests(unittest.TestCase):
    def test_deterministic_documents_and_disjoint_splits(self):
        with tempfile.TemporaryDirectory() as temp:
            first = generate_corpus(Path(temp) / "first", seed=130, per_split=2)
            second = generate_corpus(Path(temp) / "second", seed=130, per_split=2)
            self.assertEqual([item["sha256"] for item in first["documents"]], [item["sha256"] for item in second["documents"]])
            layouts = {split: {item["layout"] for item in first["documents"] if item["split"] == split} for split in ("train", "tune", "test")}
            families = {split: {item["family_id"] for item in first["documents"] if item["split"] == split} for split in ("train", "tune", "test")}
            for a, b in (("train", "tune"), ("train", "test"), ("tune", "test")):
                self.assertFalse(layouts[a] & layouts[b])
                self.assertFalse(families[a] & families[b])
            self.assertGreaterEqual(sum(item["split"] == "train" and item["expected_kind"] == "invoice" for item in first["documents"]), 12)
            multipage = next(item for item in first["documents"] if item["scenario"] == "multipage")
            self.assertEqual(len(PdfReader(Path(temp) / "first" / multipage["path"]).pages), 3)

    def test_demo_contains_required_scenarios_real_duplicates_and_versions(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = generate_demo(Path(temp), seed=42)
            self.assertTrue({"accepted", "contradictory", "abstention", "correction", "injection", "partial", "versioned", "scanned", "duplicate"}.issubset({item["scenario"] for item in manifest["documents"]}))
            duplicate = [item for item in manifest["documents"] if item["scenario"] == "duplicate" and item["expected_kind"] == "invoice"]
            self.assertEqual(len(duplicate), 2)
            self.assertEqual(duplicate[0]["sha256"], duplicate[1]["sha256"])
            versions = [item for item in manifest["documents"] if item["scenario"] == "versioned" and item["expected_kind"] == "invoice"]
            self.assertEqual(versions[0]["document_key"], versions[1]["document_key"])
            self.assertNotEqual(versions[0]["sha256"], versions[1]["sha256"])
            for item in manifest["documents"]:
                self.assertEqual(item["sha256"], hashlib.sha256((Path(temp) / item["path"]).read_bytes()).hexdigest())
                self.assertGreater(len(PdfReader(Path(temp) / item["path"]).pages), 0)


if __name__ == "__main__":
    unittest.main()
