"""Negative-path tests for the independent-renderer evaluation acceptance gate."""
from __future__ import annotations

import copy
import unittest

from scripts.qualify_independent_layouts import safety_gate

GOOD_METRICS = {
    "documents": 12,
    "failures": 0,
    "classification_accuracy": 1.0,
    "eligible_documents": 6,
    "eligible_critical_quality": 1.0,
    "false_eligible_documents": 0,
    "citation_validity": 1.0,
    "semantic_evidence_validity": 1.0,
    "policy_gate_met": True,
}
GOOD_GROUPS = {
    "known": {
        "documents": 6,
        "correct_classifications": 6,
        "eligible_documents": 6,
        "false_eligible_documents": 0,
        "inference_or_parser_failures": 0,
    },
    "unseen": {
        "documents": 6,
        "correct_classifications": 6,
        "eligible_documents": 0,
        "false_eligible_documents": 0,
        "inference_or_parser_failures": 0,
    },
}


class IndependentSafetyGateTests(unittest.TestCase):
    def setUp(self):
        self.metrics = copy.deepcopy(GOOD_METRICS)
        self.groups = copy.deepcopy(GOOD_GROUPS)

    def test_fully_qualified_reference_passes(self):
        self.assertTrue(safety_gate(self.metrics, self.groups))

    def test_all_abstain_is_a_failure_not_perfect_quality(self):
        self.metrics["eligible_documents"] = 0
        self.metrics["eligible_critical_quality"] = None
        self.groups["known"]["eligible_documents"] = 0
        self.assertFalse(safety_gate(self.metrics, self.groups))

    def test_unknown_contract_must_remain_blocked(self):
        self.groups["unseen"]["eligible_documents"] = 1
        self.assertFalse(safety_gate(self.metrics, self.groups))

    def test_false_eligibility_always_fails(self):
        self.metrics["false_eligible_documents"] = 1
        self.assertFalse(safety_gate(self.metrics, self.groups))

    def test_missing_or_invalid_citations_cannot_pass(self):
        self.metrics["citation_validity"] = None
        self.assertFalse(safety_gate(self.metrics, self.groups))
        self.metrics["citation_validity"] = 0.99
        self.assertFalse(safety_gate(self.metrics, self.groups))

    def test_incomplete_or_failed_runs_cannot_pass(self):
        self.metrics["documents"] = 11
        self.assertFalse(safety_gate(self.metrics, self.groups))
        self.metrics["documents"] = 12
        self.groups["known"]["inference_or_parser_failures"] = 1
        self.assertFalse(safety_gate(self.metrics, self.groups))

    def test_wrong_classifications_do_not_count_as_qualified(self):
        self.metrics["classification_accuracy"] = 0.92
        self.assertFalse(safety_gate(self.metrics, self.groups))


if __name__ == "__main__":
    unittest.main()

