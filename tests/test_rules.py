"""Rule unit tests. Fixtures here are not parser/inference integration evidence."""

import hashlib
import unittest
from decimal import Decimal, ROUND_HALF_UP, localcontext

from dci.models import Evidence, ExtractedField, Extraction, LineItem
from dci.rules import check_document, reconcile


def field(value: str) -> ExtractedField:
    return ExtractedField(raw=value, normalized=value, status="supported", evidence=[
        Evidence(page=1, start=0, end=len(value), quote=value)
    ])


def document(kind="invoice", identity="INV-1", quantity="10", price="10.00", rate="20",
             order="PO-1", supplier="SYN-001", currency="EUR", sku="VALVE-1") -> Extraction:
    net = (Decimal(quantity) * Decimal(price)).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
    tax = (net * Decimal(rate) / 100).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
    values = {
        "document_id": identity, "purchase_order_id": order,
        "supplier_id": supplier, "currency": currency, "document_date": "2026-01-15",
    }
    line = {"sku": sku, "quantity": quantity}
    if kind != "delivery_note":
        values.update(subtotal=f"{net:.2f}", tax=f"{tax:.2f}", total=f"{net + tax:.2f}")
        line.update(unit_price=price, net_amount=f"{net:.2f}", tax_rate=rate)
    return Extraction(
        document_sha256=hashlib.sha256(f"{kind}/{identity}/{quantity}/{price}/{rate}".encode()).hexdigest(),
        kind=kind, classification_confidence=1.0, profile="rule-unit-fixture", model_version="none",
        fields={key: field(value) for key, value in values.items()},
        line_items=[LineItem(fields={key: field(value) for key, value in line.items()})],
    )


def case(ordered="10", delivered="10", invoiced="10"):
    return [document("purchase_order", "PO-1", quantity=ordered),
            document("delivery_note", "DN-1", quantity=delivered),
            document("invoice", "INV-1", quantity=invoiced)]


class DocumentRulesTests(unittest.TestCase):
    def assert_code(self, result, code):
        self.assertIn(code, {finding.code for finding in result.findings})

    def test_complete_native_contract_is_eligible_without_approving(self):
        result = check_document(document())
        self.assertEqual(result.decision, "eligible")
        self.assertEqual(result.calculated["line_tax_sum"], "20.00")
        self.assertFalse(hasattr(result, "approved"))

    def test_missing_total_abstains_instead_of_calculated_repair(self):
        doc = document()
        doc.fields["total"] = ExtractedField(reason="not present")
        before = doc.model_dump()
        result = check_document(doc)
        self.assertEqual(result.decision, "review")
        self.assert_code(result, "missing_required_field")
        self.assertEqual(doc.model_dump(), before)

    def test_financial_mismatch_rejects_without_mutating_value(self):
        doc = document()
        doc.fields["total"] = field("121.00")
        result = check_document(doc)
        self.assertEqual(result.decision, "rejected")
        self.assert_code(result, "total_mismatch")
        self.assertEqual(doc.fields["total"].normalized, "121.00")
        self.assertEqual(result.calculated["subtotal_plus_tax"], "120.00")

    def test_one_cent_tolerance_is_explicit_boundary(self):
        doc = document()
        doc.fields["total"] = field("120.01")
        self.assertEqual(check_document(doc).decision, "eligible")
        doc.fields["total"] = field("120.02")
        self.assertEqual(check_document(doc).decision, "rejected")

    def test_per_line_half_up_rounding(self):
        doc = document(quantity="1", price="0.025", rate="20")
        result = check_document(doc)
        self.assertEqual(result.decision, "eligible")
        self.assertEqual(result.calculated["line_items[0].quantity_times_price"], "0.03")
        self.assertEqual(result.calculated["line_tax_sum"], "0.01")

    def test_rules_do_not_inherit_callers_decimal_precision(self):
        doc = document(quantity="999999", price="999.99")
        with localcontext() as context:
            context.prec = 6
            self.assertEqual(check_document(doc).decision, "eligible")

    def test_multiple_sku_and_mixed_rates_sum_rounded_line_taxes(self):
        doc = document(quantity="3", price="0.03", rate="20")
        second = document(quantity="1", price="0.05", rate="10", sku="VALVE-2")
        doc.line_items += second.line_items
        doc.fields.update(subtotal=field("0.14"), tax=field("0.03"), total=field("0.17"))
        result = check_document(doc)
        self.assertEqual(result.decision, "eligible")
        self.assertEqual(result.calculated["line_tax_sum"], "0.03")

    def test_line_tolerance_cannot_accumulate_into_inflated_subtotal(self):
        doc = document(quantity="1", price="100.00")
        second = document(quantity="1", price="50.00", sku="VALVE-2")
        doc.line_items += second.line_items
        doc.line_items[0].fields["net_amount"] = field("100.01")
        doc.line_items[1].fields["net_amount"] = field("50.01")
        doc.fields.update(subtotal=field("150.02"), tax=field("30.00"), total=field("180.02"))
        result = check_document(doc)
        self.assertEqual(result.decision, "rejected")
        self.assert_code(result, "calculated_subtotal_mismatch")

    def test_each_line_net_is_checked_even_when_header_balances(self):
        doc = document()
        doc.line_items[0].fields["net_amount"] = field("101.00")
        doc.fields.update(subtotal=field("101.00"), tax=field("20.20"), total=field("121.20"))
        result = check_document(doc)
        self.assertEqual(result.decision, "rejected")
        self.assert_code(result, "line_net_mismatch")

    def test_tax_is_checked_even_when_subtotal_plus_tax_balances(self):
        doc = document()
        doc.fields.update(tax=field("21.00"), total=field("121.00"))
        result = check_document(doc)
        self.assertEqual(result.decision, "rejected")
        self.assert_code(result, "tax_mismatch")

    def test_nonfinite_exponents_and_malformed_numbers_are_rejected(self):
        for bad in ["NaN", "Infinity", "-Infinity", "1e2", "1,000.00", "01.00", "1000000000000", "1.0000001", " 100"]:
            with self.subTest(bad=bad):
                doc = document()
                doc.fields["total"] = field(bad)
                result = check_document(doc)
                self.assertEqual(result.decision, "rejected")
                self.assert_code(result, "invalid_number")

    def test_negative_values_and_zero_quantities_are_rejected(self):
        for key, bad in [("quantity", "0"), ("quantity", "-1"), ("unit_price", "-1.00"), ("tax_rate", "-1")]:
            with self.subTest(key=key, bad=bad):
                doc = document()
                doc.line_items[0].fields[key] = field(bad)
                self.assertEqual(check_document(doc).decision, "rejected")

    def test_unsupported_scale_and_tax_rate_are_rejected(self):
        doc = document()
        doc.fields["total"] = field("120.000")
        self.assert_code(check_document(doc), "invalid_money_scale")
        doc = document()
        doc.line_items[0].fields["tax_rate"] = field("101")
        self.assert_code(check_document(doc), "invalid_tax_rate")

    def test_empty_lines_and_repeated_sku_require_review(self):
        doc = document()
        doc.line_items = []
        self.assertEqual(check_document(doc).decision, "review")
        self.assert_code(check_document(doc), "missing_line_items")
        doc = document("delivery_note", "DN-1")
        doc.line_items += [doc.line_items[0].model_copy(deep=True)]
        self.assertEqual(check_document(doc).decision, "review")
        self.assert_code(check_document(doc), "ambiguous_repeated_sku")

    def test_absent_or_malformed_provenance_requires_review(self):
        doc = document()
        doc.fields["total"].evidence = []
        self.assertEqual(check_document(doc).decision, "review")
        doc = document()
        doc.fields["total"].evidence[0].end += 1
        self.assertEqual(check_document(doc).decision, "review")

    def test_human_correction_is_explicit_and_justified(self):
        doc = document()
        doc.fields["total"] = ExtractedField(raw="121.00", normalized="120.00", origin="human",
                                              status="corrected", reason="Verified against signed replacement invoice.")
        self.assertEqual(check_document(doc).decision, "eligible")
        doc.fields["total"].reason = ""
        self.assert_code(check_document(doc), "invalid_human_correction")
        doc.fields["total"].reason = "claimed"
        doc.fields["total"].origin = "extracted"
        self.assertEqual(check_document(doc).decision, "rejected")

    def test_low_classification_and_unknown_type_require_review(self):
        doc = document()
        doc.classification_confidence = 0.7999
        self.assertEqual(check_document(doc).decision, "review")
        doc.classification_confidence = 0.8
        self.assertEqual(check_document(doc).decision, "eligible")
        doc.kind = "unknown"
        self.assertEqual(check_document(doc).decision, "review")

    def test_unknown_schema_fields_and_currency_require_review(self):
        for change in ["schema", "currency", "field"]:
            doc = document()
            if change == "schema":
                doc.contract_version = "purchasing-99"
            elif change == "currency":
                doc.fields["currency"] = field("JPY")
            else:
                doc.fields["discount"] = field("10.00")
            self.assertEqual(check_document(doc).decision, "review")

    def test_identifier_and_date_validation(self):
        doc = document()
        doc.fields["document_date"] = field("2026-02-30")
        self.assert_code(check_document(doc), "invalid_date")
        doc = document()
        doc.fields["supplier_id"] = field("<script>")
        self.assert_code(check_document(doc), "invalid_identifier")
        doc = document("purchase_order", "PO-2", order="PO-1")
        self.assert_code(check_document(doc), "order_self_reference_mismatch")

    def test_optional_delivery_totals_cannot_be_half_supplied(self):
        doc = document("delivery_note", "DN-1")
        self.assertEqual(check_document(doc).decision, "eligible")
        doc.fields["total"] = field("120.00")
        self.assertEqual(check_document(doc).decision, "review")


class ReconciliationTests(unittest.TestCase):
    def codes(self, result):
        return {finding.code for finding in result.findings}

    def test_complete_case_matches(self):
        result = reconcile(case())
        self.assertEqual(result.status, "matched")
        self.assertEqual(result.totals["VALVE-1.invoiced"], "10")

    def test_partial_is_legitimate_when_billed_not_above_delivered(self):
        result = reconcile(case("10", "6", "4"))
        self.assertEqual(result.status, "partial")
        self.assertIn("legitimate_partial", self.codes(result))
        self.assertEqual(result.totals["VALVE-1.remaining_delivery"], "4")
        self.assertEqual(result.totals["VALVE-1.remaining_invoice"], "2")

    def test_cumulative_deliveries_and_invoices(self):
        docs = case("10", "4", "3")
        docs += [document("delivery_note", "DN-2", quantity="6"),
                 document("invoice", "INV-2", quantity="7")]
        self.assertEqual(reconcile(docs).status, "matched")

    def test_invoice_tolerance_cannot_multiply_when_order_is_split(self):
        docs = case("10", "10", "5")
        docs.append(document("invoice", "INV-2", quantity="5"))
        for invoice in docs[2:]:
            invoice.fields["total"] = field("60.01")
            self.assertEqual(check_document(invoice).decision, "eligible")
        result = reconcile(docs)
        self.assertEqual(result.status, "contradictory")
        self.assertIn("aggregate_invoice_amount_mismatch", self.codes(result))

    def test_small_partial_invoice_tax_rounding_difference_is_allowed(self):
        docs = [document("purchase_order", "PO-1", quantity="3", price="0.05", rate="10"),
                document("delivery_note", "DN-1", quantity="3")]
        docs += [document("invoice", f"INV-{i}", quantity="1", price="0.05", rate="10") for i in range(3)]
        self.assertEqual(reconcile(docs).status, "matched")

    def test_material_partial_invoice_tax_rounding_requires_review(self):
        docs = [document("purchase_order", "PO-1", quantity="10", price="0.05", rate="10"),
                document("delivery_note", "DN-1", quantity="10")]
        docs += [document("invoice", f"INV-{i}", quantity="1", price="0.05", rate="10") for i in range(10)]
        result = reconcile(docs)
        self.assertEqual(result.status, "review")
        self.assertIn("partitioned_tax_rounding_review", self.codes(result))

    def test_cumulative_overdelivery_and_overbilling(self):
        docs = case("10", "6", "4")
        docs.append(document("delivery_note", "DN-2", quantity="5"))
        result = reconcile(docs)
        self.assertEqual(result.status, "contradictory")
        self.assertIn("overdelivery", self.codes(result))
        docs = case("10", "10", "6")
        docs.append(document("invoice", "INV-2", quantity="5"))
        self.assertIn("overbilling_order", self.codes(reconcile(docs)))

    def test_invoice_cannot_exceed_received_even_below_order(self):
        result = reconcile(case("10", "5", "6"))
        self.assertEqual(result.status, "contradictory")
        self.assertIn("overbilling_delivery", self.codes(result))

    def test_absent_delivery_is_missing_not_zero_delivery_conflict(self):
        docs = case()
        result = reconcile([docs[0], docs[2]])
        self.assertEqual(result.status, "missing")
        self.assertNotIn("overbilling_delivery", self.codes(result))
        self.assertEqual(reconcile([]).status, "missing")

    def test_identical_content_and_identity_do_not_double_count(self):
        docs = case()
        docs.append(docs[-1].model_copy(deep=True))
        result = reconcile(docs)
        self.assertEqual(result.status, "contradictory")
        self.assertIn("duplicate_document_content", self.codes(result))
        self.assertIn("duplicate_document_identity", self.codes(result))
        docs[-1].document_sha256 = "1" * 64
        self.assertIn("duplicate_document_identity", self.codes(reconcile(docs)))

    def test_supplier_currency_order_and_price_mismatches(self):
        for key, value in [("supplier_id", "SYN-002"), ("currency", "USD"), ("purchase_order_id", "PO-2")]:
            docs = case()
            docs[-1].fields[key] = field(value)
            result = reconcile(docs)
            self.assertEqual(result.status, "contradictory")
            self.assertIn(f"{key}_mismatch", self.codes(result))
        docs = case()
        docs[-1] = document(price="11.00")
        self.assertIn("unit_price_mismatch", self.codes(reconcile(docs)))
        docs[-1] = document(rate="10")
        self.assertIn("tax_rate_mismatch", self.codes(reconcile(docs)))

    def test_unordered_sku_is_contradiction(self):
        docs = case()
        docs[-1].line_items[0].fields["sku"] = field("OTHER")
        result = reconcile(docs)
        self.assertEqual(result.status, "contradictory")
        self.assertIn("unexpected_sku", self.codes(result))

    def test_abstention_prevents_matching(self):
        docs = case()
        docs[-1].fields["total"] = ExtractedField()
        self.assertEqual(reconcile(docs).status, "review")

    def test_two_orders_violate_case_scope(self):
        docs = case()
        docs.append(document("purchase_order", "PO-2", order="PO-2"))
        result = reconcile(docs)
        self.assertEqual(result.status, "contradictory")
        self.assertIn("multiple_purchase_orders", self.codes(result))


if __name__ == "__main__":
    unittest.main()
