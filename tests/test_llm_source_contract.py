"""Contract tests for the new Qwen structured-candidate narrowing (no inference)."""
import unittest
from types import SimpleNamespace

from dci.extraction import Candidate, SCALAR_KEYS
from dci.llm import (
    ModelUnavailable, _allowed_field_candidates, _exact_title_signals,
    _schema, _validate_proposal,
)


def candidate(identifier, label, raw="24.00"):
    return Candidate(identifier, 1, 0, 20, label, raw, f"{label}: {raw}")


def proposal(kind="invoice", *, subtotal=None, total=None, line_rows=None):
    fields = {key: None for key in SCALAR_KEYS}
    fields["subtotal"] = subtotal
    fields["total"] = total
    return {"kind": kind, "fields": fields, "line_rows": line_rows or []}


class QwenStrictFieldContractTests(unittest.TestCase):
    def setUp(self):
        self.candidates = [
            candidate("C0", "Subtotal"), candidate("C1", "Total"),
            candidate("C2", "https://attacker.invalid/999"), candidate("C3", "Currency", "EUR"),
            candidate("C4", "Total HT"),
        ]
        self.allowed = _allowed_field_candidates(self.candidates)

    def test_only_semantically_supported_ids_enter_the_schema(self):
        schema = _schema(self.allowed, ["R0"])
        fields = schema["properties"]["fields"]["properties"]
        self.assertEqual(fields["subtotal"]["enum"], [None, "C0", "C4"])
        self.assertEqual(fields["total"]["enum"], [None, "C1"])
        self.assertEqual(fields["document_date"]["enum"], [None])
        self.assertNotIn("C2", [value for item in fields.values()
                               for value in item["enum"] if value is not None])

    def test_valid_fields_and_null_abstention_are_allowed(self):
        _validate_proposal(proposal(subtotal="C0", total="C1"), self.allowed, {"R0"})
        _validate_proposal(proposal(), self.allowed, {"R0"})

    def test_wrong_known_label_cannot_be_selected_for_other_field(self):
        with self.assertRaises(ModelUnavailable):
            _validate_proposal(proposal(subtotal="C1"), self.allowed, {"R0"})

    def test_unknown_url_label_is_never_valid(self):
        with self.assertRaises(ModelUnavailable):
            _validate_proposal(proposal(total="C2"), self.allowed, {"R0"})

    def test_duplicate_source_identifiers_are_rejected(self):
        with self.assertRaises(ModelUnavailable):
            _allowed_field_candidates([candidate("C0", "Subtotal"), candidate("C0", "Total")])

    def test_real_conflicting_known_labels_are_both_preserved(self):
        self.assertEqual(self.allowed["subtotal"], ["C0", "C4"])

    def test_duplicate_or_undocumented_rows_still_rejected(self):
        with self.assertRaises(ModelUnavailable):
            _validate_proposal(proposal(line_rows=["R0", "R0"]), self.allowed, {"R0"})
        with self.assertRaises(ModelUnavailable):
            _validate_proposal(proposal(line_rows=["R9"]), self.allowed, {"R0"})

    def test_prompt_requires_unambiguous_title_signal_for_document_class(self):
        from dci.llm import PROMPT, PROMPT_VERSION
        self.assertEqual(PROMPT_VERSION, "structured-extraction-1.4")
        self.assertIn("exact_title_signals", PROMPT)
        self.assertIn("ALL signals have the same kind", PROMPT)
        self.assertIn("A unique PURCHASE ORDER title", PROMPT)
        self.assertIn("conflicting kinds", PROMPT)
        self.assertIn("output.kind is unknown", PROMPT)

    def test_exact_title_signals_are_bounded_and_not_guessed_from_reference(self):
        doc = SimpleNamespace(pages=[
            SimpleNamespace(number=1, text="INVOICE\nPurchase order: PO-9\nOrdinary text"),
            SimpleNamespace(number=2, text="FOOTER\nBON DE LIVRAISON"),
        ])
        signals = _exact_title_signals(doc)
        self.assertEqual([x["kind"] for x in signals], ["invoice", "delivery_note"])
        self.assertEqual([x["page"] for x in signals], [1, 2])


if __name__ == "__main__":
    unittest.main()
