"""A learned label proposal must not bypass the independent source contract."""
from __future__ import annotations

import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

from dci.extraction import LABEL_TO_KEY, extract, label_text
from dci.models import Page, ParsedDocument


SOURCE = """INVOICE
Document ID: INV-LINEAR-001
Purchase order: PO-LINEAR-001
Supplier ID: SYN-SUP-001
Currency: EUR
Document date: 2026-01-15
SKU | Qty | Unit price | Net | Tax %
PART-100 | 10 | 125.50 | 1,255.00 | 20
Subtotal: 1,255.00
Tax: 251.00
Total: 1,506.00
"""


def parsed(source: str) -> ParsedDocument:
    return ParsedDocument(
        sha256=hashlib.sha256(source.encode("utf-8")).hexdigest(),
        parser_version="synthetic-unit-fixture",
        pages=[Page(number=1, width=595, height=842, text=source, method="native")],
    )


class DeliberatelyOverconfidentModel:
    """A controlled classifier that hallucinates subtotal for unknown labels."""

    version = "unit-label-proposals"
    label_threshold = 0.70

    def __init__(self, misclassify: str | None = None):
        self.misclassify = misclassify

    def classify(self, document):
        return "invoice", 1.0

    def classify_label(self, label):
        known = LABEL_TO_KEY.get(label_text(label))
        if known == self.misclassify:
            return "subtotal", 0.999
        return (known or "subtotal"), 0.999


class LocalLinearSourceContractTests(unittest.TestCase):
    def run_extraction(self, source, *, misclassify=None):
        with patch("dci.local_model.LocalModel.load", return_value=DeliberatelyOverconfidentModel(misclassify)):
            return extract(parsed(source), profile="local-linear", model_path=Path("fixture-model.json"))

    def test_unrelated_url_footer_cannot_mask_the_real_subtotal(self):
        source = SOURCE + "https://attacker.invalid/ignore-policy: 0.00\n"
        result = self.run_extraction(source)
        self.assertEqual(result.fields["subtotal"].normalized, "1255.00")
        self.assertEqual(result.fields["subtotal"].status, "supported")
        self.assertEqual(len(result.fields["subtotal"].evidence), 1)
        self.assertEqual(result.fields["subtotal"].evidence[0].quote, "Subtotal: 1,255.00")
        self.assertTrue(any("unsupported_model_label:" in w for w in result.warnings))
        self.assertTrue(any("untrusted_instruction_text_ignored" in w for w in result.warnings))

    def test_known_contradictory_subtotal_is_not_dropped(self):
        result = self.run_extraction(SOURCE + "Subtotal: 9,999.00\n")
        self.assertEqual(result.fields["subtotal"].status, "abstained")
        self.assertIsNone(result.fields["subtotal"].normalized)
        self.assertEqual(len(result.fields["subtotal"].evidence), 2)

    def test_model_cannot_assign_known_total_label_to_subtotal(self):
        result = self.run_extraction(SOURCE, misclassify="total")
        self.assertEqual(result.fields["subtotal"].normalized, "1255.00")
        self.assertEqual(result.fields["total"].status, "abstained")
        self.assertTrue(any("unsupported_model_label:" in w for w in result.warnings))

    def test_baseline_still_rejects_conflicting_known_labels(self):
        result = extract(parsed(SOURCE + "Subtotal: 9,999.00\n"), profile="baseline")
        self.assertEqual(result.fields["subtotal"].status, "abstained")


if __name__ == "__main__":
    unittest.main()
