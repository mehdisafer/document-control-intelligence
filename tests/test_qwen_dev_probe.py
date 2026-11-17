"""Negative evidence for the Qwen development runtime/quality separation."""
import unittest

from scripts.verify_qwen_dev_probe import runtime_gate, TRACE_NAME, GENERATOR
from dci.llm import MODEL_SHA256, PROMPT_VERSION


class QwenDevelopmentProbeTests(unittest.TestCase):
    def test_model_and_protocol_pinned(self):
        self.assertEqual(PROMPT_VERSION, "structured-extraction-1.4")
        self.assertEqual(MODEL_SHA256, "b0638f08417a2d3c8652760462eb5407c6e30173cf9608ad0820757a281eea0e")
        self.assertEqual(GENERATOR, "independent-node-pdf-writer-1.0")

    def test_trace_sha_format_rejects_arbitrary_paths(self):
        self.assertIsNotNone(TRACE_NAME.fullmatch("a" * 64 + "-123.json"))
        self.assertIsNone(TRACE_NAME.fullmatch("../" + "a" * 64 + "-123.json"))

    def test_successful_real_12_response_receipt(self):
        self.assertTrue(runtime_gate(12, 12, 0, 0, 0, 1.0, 1.0))

    def test_missing_response_fails(self):
        self.assertFalse(runtime_gate(12, 11, 0, 0, 0, 1.0, 1.0))

    def test_inference_error_fails(self):
        self.assertFalse(runtime_gate(12, 12, 1, 0, 0, 1.0, 1.0))

    def test_false_eligibility_fails(self):
        self.assertFalse(runtime_gate(12, 12, 0, 1, 0, 1.0, 1.0))

    def test_unsupported_layout_acceptance_fails(self):
        self.assertFalse(runtime_gate(12, 12, 0, 0, 1, 1.0, 1.0))

    def test_invalid_citation_or_semantics_fails(self):
        self.assertFalse(runtime_gate(12, 12, 0, 0, 0, 0.9, 1.0))
        self.assertFalse(runtime_gate(12, 12, 0, 0, 0, 1.0, 0.9))

    def test_no_citations_is_not_claimed_as_perfect_but_valid_runtime(self):
        self.assertTrue(runtime_gate(12, 12, 0, 0, 0, None, None))


if __name__ == "__main__":
    unittest.main()
