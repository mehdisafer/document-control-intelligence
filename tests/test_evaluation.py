"""Metric arithmetic tests, not claims about parser/model integration."""

import unittest

from dci.evaluation import summarize, _validate_splits


class EvaluationMetricTests(unittest.TestCase):
    def test_coverage_and_quality_have_different_denominators(self):
        records = [
            {"expected_kind": "invoice", "predicted_kind": "invoice", "classification_correct": True,
             "fields_total": 10, "fields_correct": 10, "present_fields_total": 10, "present_fields_correct": 10,
             "critical_document_exact": True, "eligible": True, "eligible_and_correct": True,
             "citation_total": 10, "citation_valid": 10, "elapsed_seconds": 1.0},
            {"expected_kind": "invoice", "predicted_kind": "purchase_order", "classification_correct": False,
             "fields_total": 10, "fields_correct": 8, "present_fields_total": 10, "present_fields_correct": 8,
             "critical_document_exact": False, "eligible": True, "eligible_and_correct": False, "false_eligible": True,
             "citation_total": 10, "citation_valid": 9, "elapsed_seconds": 3.0},
            {"expected_kind": "purchase_order", "predicted_kind": "unknown", "error": {"code": "parser_failure"},
             "fields_total": 10, "present_fields_total": 10},
        ]
        summary = summarize(records)
        self.assertEqual(summary["eligible_coverage"], 0.666667)
        self.assertEqual(summary["eligible_critical_quality"], 0.5)
        self.assertEqual(summary["review_rate"], 0.333333)
        self.assertEqual(summary["false_eligible_rate_among_eligible"], 0.5)
        self.assertEqual(summary["false_eligible_rate_all_documents"], 0.333333)
        self.assertEqual(summary["normalized_present_field_accuracy"], 0.6)
        self.assertEqual(summary["citation_validity"], 0.95)
        self.assertEqual(summary["classification_macro_precision"], 0.5)
        self.assertEqual(summary["classification_macro_recall"], 0.25)
        self.assertEqual(summary["latency_seconds"]["p95_nearest_rank"], 3)
        self.assertFalse(summary["policy_gate_met"])

    def test_no_eligible_outputs_is_unknown_quality_not_perfect(self):
        summary = summarize([{"expected_kind": "invoice", "predicted_kind": "unknown"}])
        self.assertEqual(summary["eligible_coverage"], 0)
        self.assertEqual(summary["review_rate"], 1)
        self.assertIsNone(summary["eligible_critical_quality"])
        self.assertIsNone(summary["citation_validity"])
        self.assertIsNone(summary["false_eligible_rate_among_eligible"])
        self.assertFalse(summary["policy_gate_met"])

    def test_subset_cannot_satisfy_final_gate_even_with_perfect_outputs(self):
        summary = summarize([{"expected_kind": "invoice", "predicted_kind": "invoice", "eligible": True,
                              "eligible_and_correct": True, "citation_total": 1, "citation_valid": 1}], full_split=False)
        self.assertEqual(summary["eligible_critical_quality"], 1)
        self.assertFalse(summary["policy_gate_met"])

    def test_template_or_family_leakage_is_rejected(self):
        for shared in ("layout", "family_id"):
            first = {"split": "train", "layout": "layout-a", "family_id": "family-a"}
            second = {"split": "test", "layout": "layout-b", "family_id": "family-b"}
            second[shared] = first[shared]
            with self.assertRaisesRegex(ValueError, "Split leakage"):
                _validate_splits({"documents": [first, second]})


if __name__ == "__main__":
    unittest.main()
