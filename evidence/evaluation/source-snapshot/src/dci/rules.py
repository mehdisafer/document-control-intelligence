"""Deterministic, versioned purchasing checks using decimal arithmetic.

Rules do not repair extracted amounts and do not approve documents. ``eligible``
means the deterministic checks found no blocker; explicit human acceptance is a
separate service operation. Citation *support* is verified against parsed pages by
the extraction boundary; this module additionally rejects absent provenance.

The v1 case contract is one purchase order, one or more deliveries, and one or more
invoices, in a two-decimal currency. Credit notes, allowances, freight and multiple
prices for the same SKU inside a document need a richer contract and human review.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from functools import wraps

from .models import CheckResult, ExtractedField, Extraction, Finding, Reconciliation


CONTRACT_VERSION = "purchasing-1.0"
RULE_VERSION = "purchasing-rules-1.0"
MATCH_VERSION = "three-way-1.0"
MONEY_TOLERANCE = Decimal("0.01")
QUANTITY_TOLERANCE = Decimal("0")
PRICE_TOLERANCE = Decimal("0.0001")
RATE_TOLERANCE = Decimal("0.0001")
CLASSIFICATION_THRESHOLD = 0.80
CENT = Decimal("0.01")
CURRENCIES = frozenset({"EUR", "USD", "GBP", "CHF"})
HEADER_FIELDS = frozenset({
    "document_id", "purchase_order_id", "supplier_id", "currency", "subtotal",
    "tax", "total", "document_date",
})
LINE_FIELDS = frozenset({"sku", "quantity", "unit_price", "net_amount", "tax_rate"})
BASE_REQUIRED = ("document_id", "purchase_order_id", "supplier_id", "currency")
MONEY_HEADERS = ("subtotal", "tax", "total")
MONEY_LINES = ("unit_price", "net_amount", "tax_rate")
NUMERIC = re.compile(r"-?(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,6})?\Z")
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/\-]{0,79}\Z")


def _field_value(value: ExtractedField | None) -> str | None:
    if value is None or value.status not in {"supported", "corrected"}:
        return None
    result = value.normalized
    return result if result is not None and result.strip() else None


def _decimal(value: str | None) -> Decimal | None:
    """Bound lexical complexity before Decimal; reject NaN/Inf/exponents/commas."""
    if value is None or not NUMERIC.fullmatch(value):
        return None
    try:
        number = Decimal(value)
    except InvalidOperation:
        return None
    return number if number.is_finite() else None


def _money(number: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = 40
        return number.quantize(CENT, rounding=ROUND_HALF_UP)


def _format(number: Decimal) -> str:
    return format(number, "f")


def _amount(number: Decimal) -> str:
    return format(_money(number), ".2f")


def _document_id(document: Extraction) -> str:
    return _field_value(document.fields.get("document_id")) or document.document_sha256


def _decimal_policy(function):
    """Keep financial results independent of a caller's thread-local context."""
    @wraps(function)
    def checked(*args, **kwargs):
        with localcontext() as context:
            context.prec = 64
            context.rounding = ROUND_HALF_UP
            return function(*args, **kwargs)
    return checked


@_decimal_policy
def check_document(extraction: Extraction) -> CheckResult:
    """Check a single extraction without changing any supplied value.

    Missing/abstained evidence and unsupported contracts require review. Malformed
    numbers and deterministic business contradictions reject the document. All
    calculations are separately reported; they never replace the extracted values.
    """
    findings: list[Finding] = []
    calculated: dict[str, str] = {}
    document_id = _document_id(extraction)

    def add(code: str, severity: str, message: str, field: str | None = None) -> None:
        findings.append(Finding(code=code, severity=severity, message=message,
                                field=field, document_id=document_id))

    if extraction.schema_version != "1.0" or extraction.contract_version != CONTRACT_VERSION:
        add("unsupported_contract", "warning", "The schema or contract version is not supported.")
    if extraction.kind == "unknown":
        add("unknown_document_kind", "warning", "The document type has not been established.")
    if extraction.classification_confidence < CLASSIFICATION_THRESHOLD:
        add("classification_below_threshold", "warning",
            f"Classification is below the explicit {CLASSIFICATION_THRESHOLD:.2f} review threshold.")

    def provenance(key: str, value: ExtractedField) -> None:
        if value.status == "abstained":
            return
        if value.status == "corrected":
            if value.origin != "human" or not value.reason or not value.reason.strip():
                add("invalid_human_correction", "error",
                    "A correction must be explicitly human and include a justification.", key)
            return
        if value.origin != "extracted":
            add("invalid_field_origin", "error", "A supported extraction has an invalid origin.", key)
        if not value.evidence or any(
            not evidence.quote or evidence.end <= evidence.start
            or len(evidence.quote) != evidence.end - evidence.start
            for evidence in value.evidence
        ):
            add("missing_evidence", "warning", "The extracted value lacks usable source evidence.", key)

    for key, field in extraction.fields.items():
        if key not in HEADER_FIELDS:
            add("unsupported_field", "warning", "This field is outside the v1 document contract.", key)
        provenance(key, field)

    required = BASE_REQUIRED + (MONEY_HEADERS if extraction.kind in {"purchase_order", "invoice"} else ())
    for key in required:
        if _field_value(extraction.fields.get(key)) is None:
            add("missing_required_field", "warning", "A critical field is missing or abstained.", key)

    for key in ("document_id", "purchase_order_id", "supplier_id"):
        value = _field_value(extraction.fields.get(key))
        if value is not None and not IDENTIFIER.fullmatch(value):
            add("invalid_identifier", "error", "The normalized identifier is outside the allowed format.", key)
    if extraction.kind == "purchase_order":
        reference = _field_value(extraction.fields.get("purchase_order_id"))
        identity = _field_value(extraction.fields.get("document_id"))
        if reference is not None and identity is not None and reference != identity:
            add("order_self_reference_mismatch", "error",
                "The purchase order identifier does not match its own order reference.", "purchase_order_id")

    currency = _field_value(extraction.fields.get("currency"))
    if currency is not None and currency not in CURRENCIES:
        add("unsupported_currency", "warning", "The v1 policy supports EUR, USD, GBP and CHF.", "currency")
    document_date = _field_value(extraction.fields.get("document_date"))
    if document_date is not None:
        try:
            if len(document_date) != 10 or date.fromisoformat(document_date).isoformat() != document_date:
                raise ValueError("not canonical")
        except ValueError:
            add("invalid_date", "error", "The normalized date must be a real ISO YYYY-MM-DD date.", "document_date")

    def number(fields: dict[str, ExtractedField], key: str, path: str,
               *, positive: bool = False, money: bool = False) -> Decimal | None:
        text = _field_value(fields.get(key))
        if text is None:
            return None
        value = _decimal(text)
        if value is None:
            add("invalid_number", "error", "A normalized number has invalid syntax or exceeds precision limits.", path)
            return None
        if value < 0 or (positive and value == 0):
            add("invalid_sign", "error", "Quantities must be positive; prices, rates and amounts cannot be negative.", path)
            return None
        if money and value.as_tuple().exponent < -2:
            add("invalid_money_scale", "error", "Monetary totals support at most two decimal places.", path)
            return None
        if key in {"unit_price", "tax_rate"} and value.as_tuple().exponent < -4:
            add("invalid_precision", "error", "Unit prices and tax rates support at most four decimal places.", path)
            return None
        if key == "tax_rate" and value > 100:
            add("invalid_tax_rate", "error", "The tax rate must be a percentage between 0 and 100.", path)
            return None
        return value

    header_numbers = {key: number(extraction.fields, key, key, money=True) for key in MONEY_HEADERS}
    if extraction.kind == "delivery_note":
        supplied = [key for key in MONEY_HEADERS if _field_value(extraction.fields.get(key)) is not None]
        if supplied and len(supplied) != len(MONEY_HEADERS):
            add("incomplete_optional_totals", "warning",
                "Delivery-note financial totals must be supplied as a complete subtotal/tax/total set.")

    if not extraction.line_items:
        add("missing_line_items", "warning", "At least one evidenced line item is required.", "line_items")
    skus: list[str] = []
    line_nets: list[Decimal] = []
    line_taxes: list[Decimal] = []
    expected_nets: list[Decimal] = []
    expected_taxes: list[Decimal] = []
    complete_financial_lines = True
    for index, item in enumerate(extraction.line_items):
        prefix = f"line_items[{index}]."
        for key, field in item.fields.items():
            if key not in LINE_FIELDS:
                add("unsupported_line_field", "warning", "This line field is outside the v1 contract.", prefix + key)
            provenance(prefix + key, field)
        line_required = ("sku", "quantity") + (MONEY_LINES if extraction.kind in {"purchase_order", "invoice"} else ())
        for key in line_required:
            if _field_value(item.fields.get(key)) is None:
                add("missing_required_field", "warning", "A critical line field is missing or abstained.", prefix + key)
        sku = _field_value(item.fields.get("sku"))
        if sku is not None:
            if not IDENTIFIER.fullmatch(sku):
                add("invalid_sku", "error", "The normalized SKU is outside the allowed format.", prefix + "sku")
            skus.append(sku)
        quantity = number(item.fields, "quantity", prefix + "quantity", positive=True)
        price = number(item.fields, "unit_price", prefix + "unit_price")
        net = number(item.fields, "net_amount", prefix + "net_amount", money=True)
        rate = number(item.fields, "tax_rate", prefix + "tax_rate")
        if quantity is not None and price is not None:
            expected_net = _money(quantity * price)
            expected_nets.append(expected_net)
            calculated[prefix + "quantity_times_price"] = _amount(expected_net)
            if rate is not None:
                expected_taxes.append(_money(expected_net * rate / Decimal(100)))
            if net is not None and abs(net - expected_net) > MONEY_TOLERANCE:
                add("line_net_mismatch", "error",
                    f"Declared line net {net} differs from quantity × price {_amount(expected_net)} beyond 0.01.",
                    prefix + "net_amount")
        if net is not None:
            line_nets.append(net)
        if net is not None and rate is not None:
            tax = _money(net * rate / Decimal(100))
            line_taxes.append(tax)
            calculated[prefix + "tax"] = _amount(tax)
        if None in (quantity, price, net, rate):
            complete_financial_lines = False

    for sku, count in Counter(skus).items():
        if count > 1:
            add("ambiguous_repeated_sku", "warning",
                f"SKU {sku} appears more than once; the v1 contract has no line identifier to disambiguate it.", "line_items")

    subtotal, tax, total = (header_numbers[key] for key in MONEY_HEADERS)
    if all(value is not None for value in (subtotal, tax, total)):
        expected_total = _money(subtotal + tax)
        calculated["subtotal_plus_tax"] = _amount(expected_total)
        if abs(total - expected_total) > MONEY_TOLERANCE:
            add("total_mismatch", "error", "The total differs from subtotal plus tax beyond 0.01.", "total")
    if complete_financial_lines and extraction.line_items:
        expected_subtotal = sum(line_nets, Decimal(0))
        expected_tax = sum(line_taxes, Decimal(0))
        calculated["line_net_sum"] = _amount(expected_subtotal)
        calculated["line_tax_sum"] = _amount(expected_tax)
        if subtotal is not None and abs(subtotal - expected_subtotal) > MONEY_TOLERANCE:
            add("subtotal_mismatch", "error", "The subtotal differs from the sum of line nets beyond 0.01.", "subtotal")
        if tax is not None and abs(tax - expected_tax) > MONEY_TOLERANCE:
            add("tax_mismatch", "error", "The tax differs from the sum of rounded line taxes beyond 0.01.", "tax")
        # A per-line tolerance is not an allowance that may be multiplied by the
        # number of lines. Compare the aggregate with quantity × price as well.
        quantity_price_sum = sum(expected_nets, Decimal(0))
        calculated_tax_sum = sum(expected_taxes, Decimal(0))
        calculated["quantity_price_net_sum"] = _amount(quantity_price_sum)
        calculated["quantity_price_tax_sum"] = _amount(calculated_tax_sum)
        if subtotal is not None and abs(subtotal - quantity_price_sum) > MONEY_TOLERANCE:
            add("calculated_subtotal_mismatch", "error", "The subtotal exceeds the aggregate quantity × price tolerance of 0.01.", "subtotal")
        if tax is not None and abs(tax - calculated_tax_sum) > MONEY_TOLERANCE:
            add("calculated_tax_mismatch", "error", "The tax exceeds the aggregate calculated-line-tax tolerance of 0.01.", "tax")

    if any(f.severity == "error" for f in findings):
        decision = "rejected"
    elif any(f.severity == "warning" for f in findings):
        decision = "review"
    else:
        decision = "eligible"
    return CheckResult(rule_version=RULE_VERSION, decision=decision, findings=findings, calculated=calculated)


@_decimal_policy
def reconcile(documents: list[Extraction]) -> Reconciliation:
    """Reconcile a case's latest active document versions.

    The caller selects active versions transactionally. This function still rejects
    duplicate document identities and hashes so a bad selection cannot double-count
    quantities. Missing evidence is never treated as a zero quantity.
    """
    findings: list[Finding] = []
    totals: dict[str, str] = {}

    def add(code: str, severity: str, message: str, document: Extraction | None = None,
            field: str | None = None) -> None:
        findings.append(Finding(code=code, severity=severity, message=message,
                                document_id=_document_id(document) if document else None, field=field))

    by_kind: dict[str, list[Extraction]] = defaultdict(list)
    requires_review = False
    for document in documents:
        by_kind[document.kind].append(document)
        result = check_document(document)
        if result.decision != "eligible":
            findings.extend(result.findings)
            requires_review = requires_review or result.decision == "review"

    missing = [kind for kind in ("purchase_order", "delivery_note", "invoice") if not by_kind[kind]]
    for kind in missing:
        add("missing_document", "warning", f"The case has no active {kind.replace('_', ' ')}.")
    if len(by_kind["purchase_order"]) > 1:
        add("multiple_purchase_orders", "error", "A v1 control case must contain exactly one active purchase order.")

    identities: set[tuple[str, str, str]] = set()
    hashes: set[str] = set()
    for document in documents:
        supplier = _field_value(document.fields.get("supplier_id"))
        identity = _field_value(document.fields.get("document_id"))
        if supplier and identity:
            key = (document.kind, supplier, identity)
            if key in identities:
                add("duplicate_document_identity", "error", "The same document identity appears more than once.", document)
            identities.add(key)
        if document.document_sha256 in hashes:
            add("duplicate_document_content", "error", "Identical document content appears more than once.", document)
        hashes.add(document.document_sha256)

    # Compare explicit values even when a piece is absent; do not compare absent
    # quantities to zero, which would confuse missing evidence with contradiction.
    for field in ("purchase_order_id", "supplier_id", "currency"):
        observed = {_field_value(doc.fields.get(field)) for doc in documents}
        observed.discard(None)
        if len(observed) > 1:
            add(f"{field}_mismatch", "error", f"The documents do not agree on {field.replace('_', ' ')}.", field=field)

    if any(f.severity == "error" for f in findings):
        return Reconciliation(rule_version=MATCH_VERSION, status="contradictory", findings=findings, totals=totals)
    if requires_review or by_kind["unknown"]:
        return Reconciliation(rule_version=MATCH_VERSION, status="review", findings=findings, totals=totals)
    if missing:
        return Reconciliation(rule_version=MATCH_VERSION, status="missing", findings=findings, totals=totals)

    order = by_kind["purchase_order"][0]
    order_lines = {
        _field_value(item.fields["sku"]): item for item in order.line_items
    }
    ordered: dict[str, Decimal] = {
        sku: _decimal(_field_value(item.fields["quantity"])) for sku, item in order_lines.items()
    }
    delivered: dict[str, Decimal] = defaultdict(Decimal)
    invoiced: dict[str, Decimal] = defaultdict(Decimal)
    expected_invoice_net = Decimal(0)
    expected_invoice_tax = Decimal(0)
    for kind, accumulator in (("delivery_note", delivered), ("invoice", invoiced)):
        for document in by_kind[kind]:
            for index, item in enumerate(document.line_items):
                sku = _field_value(item.fields["sku"])
                quantity = _decimal(_field_value(item.fields["quantity"]))
                if sku not in order_lines:
                    add("unexpected_sku", "error", f"SKU {sku} is absent from the purchase order.",
                        document, f"line_items[{index}].sku")
                    continue
                accumulator[sku] += quantity
                if kind == "invoice":
                    reference_price = _decimal(_field_value(order_lines[sku].fields["unit_price"]))
                    reference_rate = _decimal(_field_value(order_lines[sku].fields["tax_rate"]))
                    expected_net = _money(quantity * reference_price)
                    expected_invoice_net += expected_net
                    expected_invoice_tax += _money(expected_net * reference_rate / Decimal(100))
                for field, tolerance in (("unit_price", PRICE_TOLERANCE), ("tax_rate", RATE_TOLERANCE)):
                    actual = _decimal(_field_value(item.fields.get(field)))
                    expected = _decimal(_field_value(order_lines[sku].fields.get(field)))
                    if actual is not None and expected is not None and abs(actual - expected) > tolerance:
                        add(f"{field}_mismatch", "error",
                            f"SKU {sku} has {field.replace('_', ' ')} {actual}; the purchase order specifies {expected}.",
                            document, f"line_items[{index}].{field}")

    is_partial = False
    for sku, expected in ordered.items():
        shipped = delivered[sku]
        billed = invoiced[sku]
        totals[f"{sku}.ordered"] = _format(expected)
        totals[f"{sku}.delivered"] = _format(shipped)
        totals[f"{sku}.invoiced"] = _format(billed)
        totals[f"{sku}.remaining_delivery"] = _format(expected - shipped)
        totals[f"{sku}.remaining_invoice"] = _format(shipped - billed)
        if shipped - expected > QUANTITY_TOLERANCE:
            add("overdelivery", "error", f"SKU {sku}: delivered {shipped} exceeds ordered {expected}.", field="quantity")
        if billed - expected > QUANTITY_TOLERANCE:
            add("overbilling_order", "error", f"SKU {sku}: invoiced {billed} exceeds ordered {expected}.", field="quantity")
        if billed - shipped > QUANTITY_TOLERANCE:
            add("overbilling_delivery", "error", f"SKU {sku}: invoiced {billed} exceeds delivered {shipped}.", field="quantity")
        if shipped < expected or billed < shipped:
            is_partial = True
    for kind in ("purchase_order", "invoice"):
        totals[f"{kind}.total"] = _amount(sum(
            (_decimal(_field_value(doc.fields["total"])) for doc in by_kind[kind]), Decimal(0)
        ))
    declared_invoice_net = sum((_decimal(_field_value(doc.fields["subtotal"])) for doc in by_kind["invoice"]), Decimal(0))
    declared_invoice_tax = sum((_decimal(_field_value(doc.fields["tax"])) for doc in by_kind["invoice"]), Decimal(0))
    declared_invoice_total = Decimal(totals["invoice.total"])
    totals["invoice.subtotal"] = _amount(declared_invoice_net)
    totals["invoice.tax"] = _amount(declared_invoice_tax)
    totals["invoice.calculated_subtotal"] = _amount(expected_invoice_net)
    totals["invoice.calculated_tax"] = _amount(expected_invoice_tax)
    for field, actual, expected in (
        ("subtotal", declared_invoice_net, expected_invoice_net),
        ("tax", declared_invoice_tax, expected_invoice_tax),
        ("total", declared_invoice_total, expected_invoice_net + expected_invoice_tax),
    ):
        if abs(actual - expected) > MONEY_TOLERANCE:
            add("aggregate_invoice_amount_mismatch", "error",
                f"Cumulative invoice {field} {actual} differs from the order-price calculation {expected} beyond the case tolerance of 0.01.",
                field=field)
    # Tax rounded on each partial invoice can differ from one rounded PO line.
    # A material difference is an explicit review case, never a silent correction.
    if all(invoiced[sku] == quantity for sku, quantity in ordered.items()):
        order_tax = _decimal(_field_value(order.fields["tax"]))
        if abs(declared_invoice_tax - order_tax) > MONEY_TOLERANCE:
            add("partitioned_tax_rounding_review", "warning",
                "All quantities are invoiced, but partial-invoice tax rounding differs from the purchase order beyond 0.01; review the tax basis.", field="tax")
    if any(f.severity == "error" for f in findings):
        status = "contradictory"
    elif any(f.severity == "warning" for f in findings):
        status = "review"
    elif is_partial:
        status = "partial"
        add("legitimate_partial", "info", "Invoiced quantities do not exceed delivered quantities; the order remains partially fulfilled or billed.")
    else:
        status = "matched"
    return Reconciliation(rule_version=MATCH_VERSION, status=status, findings=findings, totals=totals)
