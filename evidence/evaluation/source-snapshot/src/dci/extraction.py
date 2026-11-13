"""Source-bound extraction and independent, deterministic evidence validation.

Models propose assignments. This module owns normalization and proof checking;
neither a model's confidence nor a string appearing elsewhere is sufficient.
"""

from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .models import Evidence, ExtractedField, Extraction, LineItem, Page, ParsedDocument

SCALAR_KEYS = (
    "document_id", "purchase_order_id", "supplier_id", "currency", "subtotal",
    "tax", "total", "document_date",
)
LINE_KEYS = ("sku", "quantity", "unit_price", "net_amount", "tax_rate")
MIN_CRITICAL_OCR_CONFIDENCE = 0.70
MONEY_KEYS = {"subtotal", "tax", "total", "net_amount"}
LABELS = {
    "document_id": ("Document ID", "Document number", "Reference document", "Référence document", "Document reference"),
    "purchase_order_id": ("Purchase order", "Purchase order ID", "Order reference", "Commande", "Référence commande"),
    "supplier_id": ("Supplier ID", "Supplier reference", "Fournisseur", "Code fournisseur"),
    "currency": ("Currency", "Devise"),
    "subtotal": ("Subtotal", "Net total", "Total HT", "Sous-total"),
    "tax": ("Tax", "Tax amount", "TVA", "Montant TVA"),
    "total": ("Total", "Grand total", "Amount due", "Total TTC", "Total à payer"),
    "document_date": ("Document date", "Date document", "Date du document", "Issue date"),
}
TABLE_LABELS = {
    "sku": ("SKU", "Article", "Item code"),
    "quantity": ("Qty", "Quantity", "Quantite", "Quantité"),
    "unit_price": ("Unit price", "Prix unitaire"),
    "net_amount": ("Net", "Net amount", "Montant HT"),
    "tax_rate": ("Tax %", "TVA %", "Tax rate"),
}
TITLES = {
    "purchase_order": ("PURCHASE ORDER", "BON DE COMMANDE"),
    "delivery_note": ("DELIVERY NOTE", "BON DE LIVRAISON"),
    "invoice": ("INVOICE", "FACTURE"),
}
_INSTRUCTION = re.compile(
    r"ignore\s+(?:all\s+)?(?:previous|prior|system)|system\s*(?:prompt|instruction)|"
    r"send\s+(?:all\s+)?(?:documents|secrets|data)|https?://|"
    r"ignorer?\s+(?:les\s+)?instructions|override\s+(?:policy|rules)", re.I,
)


def label_text(text: str) -> str:
    """Canonicalize labels only; source quotations are never rewritten."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9%]+", " ", text.lower()).split())


LABEL_TO_KEY = {label_text(label): key for key, labels in LABELS.items() for label in labels}
TABLE_TO_KEY = {label_text(label): key for key, labels in TABLE_LABELS.items() for label in labels}
TITLE_TO_KIND = {label_text(label): kind for kind, labels in TITLES.items() for label in labels}


def _decimal(raw: str) -> tuple[Decimal, list[str]]:
    value = raw.strip()
    transforms = []
    if value != raw:
        transforms.append("trim_outer_whitespace")
    if not re.fullmatch(r"[+-]?[0-9][0-9., \u00a0\u202f]*", value):
        raise ValueError("Expected a finite decimal literal without currency, exponent or expression")
    sign = ""
    if value[0] in "+-":
        sign, value = value[0], value[1:]
    if any(c in value for c in " \u00a0\u202f"):
        # Spaces are accepted only as thousands grouping, never as digit repair.
        if not re.fullmatch(r"\d{1,3}(?:[ \u00a0\u202f]\d{3})+(?:[.,]\d+)?", value):
            raise ValueError("Invalid thousands grouping")
        value = re.sub(r"[ \u00a0\u202f]", "", value)
        transforms.append("remove_grouping_spaces")
    if "," in value and "." in value:
        decimal_sep = "," if value.rfind(",") > value.rfind(".") else "."
        group_sep = "." if decimal_sep == "," else ","
        integer, fraction = value.rsplit(decimal_sep, 1)
        if not re.fullmatch(r"\d{1,3}(?:" + re.escape(group_sep) + r"\d{3})+", integer) or not fraction.isdigit():
            raise ValueError("Invalid mixed decimal/grouping separators")
        value = integer.replace(group_sep, "") + "." + fraction
        transforms.append("normalize_decimal_and_grouping_separators")
    elif "," in value:
        if value.count(",") != 1:
            raise ValueError("Ambiguous comma grouping")
        integer, fraction = value.split(",")
        if len(fraction) == 3 and len(integer) <= 3 and integer != "0":
            raise ValueError("Ambiguous comma: decimal or thousands separator")
        value = integer + "." + fraction
        transforms.append("decimal_comma_to_dot")
    elif value.count(".") > 1:
        raise ValueError("Ambiguous dot grouping")
    try:
        number = Decimal(sign + value)
    except InvalidOperation as exc:
        raise ValueError("Invalid decimal") from exc
    if not number.is_finite() or abs(number) > Decimal("1000000000000"):
        raise ValueError("Decimal outside supported finite range")
    if len(number.as_tuple().digits) > 20:
        raise ValueError("Decimal precision exceeds contract")
    return number, transforms


def normalize_value(field_name: str, raw: str) -> tuple[str, list[str]]:
    """Normalize a field without guessing or repairing its business value.

    Raises ValueError on unsupported/ambiguous input. Human corrections must call
    the same function and separately retain author, reason and prior revision.
    """
    if not isinstance(raw, str) or len(raw) > 256 or not raw.strip():
        raise ValueError("A bounded nonempty source value is required")
    if field_name in MONEY_KEYS or field_name in {"quantity", "tax_rate", "unit_price"}:
        value = raw
        transforms = []
        if field_name == "tax_rate" and value.strip().endswith("%"):
            value = value.strip()[:-1].strip()
            transforms.append("remove_percent_sign")
        decimal, operations = _decimal(value)
        transforms.extend(operations)
        if field_name in MONEY_KEYS:
            if decimal != decimal.quantize(Decimal("0.01")):
                raise ValueError("Money has unsupported sub-cent precision; no rounding applied")
            normalized = format(decimal, ".2f")
            transforms.append("decimal_to_fixed_2")
        elif field_name == "unit_price":
            if decimal != decimal.quantize(Decimal("0.0001")):
                raise ValueError("Unit price precision exceeds four decimals; no rounding applied")
            normalized = format(decimal, ".2f") if decimal == decimal.quantize(Decimal("0.01")) else format(decimal.normalize(), "f")
            transforms.append("decimal_price_preserve_up_to_4_minimum_2")
        else:
            precision = 6 if field_name == "quantity" else 4
            if decimal != decimal.quantize(Decimal(1).scaleb(-precision)):
                raise ValueError("Quantity/rate precision exceeds contract; no rounding applied")
            normalized = format(decimal.normalize(), "f")
            transforms.append("decimal_remove_redundant_zeros")
        return normalized, transforms
    if field_name == "currency":
        value = raw.strip().upper()
        if value not in {"EUR", "USD", "GBP", "CHF"}:
            raise ValueError("Currency is outside the versioned contract")
        return value, ["trim_outer_whitespace", "uppercase_iso_currency"]
    if field_name == "document_date":
        value = raw.strip()
        try:
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                parsed = date.fromisoformat(value)
                operation = "validate_iso_date"
            elif re.fullmatch(r"\d{2}/\d{2}/\d{4}", value):
                day, month, year = map(int, value.split("/"))
                # Purchasing contract v1 declares DD/MM/YYYY, never US MM/DD.
                parsed = date(year, month, day)
                operation = "contract_dd_mm_yyyy_to_iso"
            else:
                raise ValueError("Unsupported date format")
        except ValueError as exc:
            raise ValueError("Invalid date or unsupported format") from exc
        return parsed.isoformat(), [operation]
    if field_name in {"document_id", "purchase_order_id", "supplier_id", "sku"}:
        value = raw.strip().upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9._/-]{1,63}", value):
            raise ValueError("Invalid identifier")
        return value, ["trim_outer_whitespace", "uppercase_identifier"]
    raise ValueError("Unknown contract field")


@dataclass(frozen=True)
class Candidate:
    id: str
    page: int
    start: int
    end: int
    label: str
    raw: str
    quote: str


@dataclass(frozen=True)
class TableRow:
    id: str
    page: int
    start: int
    end: int
    quote: str
    header: Candidate
    keys: tuple[str, ...]
    cells: tuple[str, ...]


def candidates(parsed: ParsedDocument) -> list[Candidate]:
    result = []
    for page in parsed.pages:
        for match in re.finditer(r"[^\n]+", page.text):
            text = match.group()
            if "|" in text or len(text) > 400:
                continue
            parts = re.match(r"^\s*([^:=]{1,70})\s*[:=]\s*(.*?)\s*$", text)
            if not parts or not parts[2]:
                continue
            result.append(Candidate(f"C{len(result)}", page.number,
                                    match.start(), match.end(), parts[1].strip(),
                                    parts[2].strip(), text))
    return result


def table_rows(parsed: ParsedDocument) -> list[TableRow]:
    rows = []
    for page in parsed.pages:
        header = None
        keys = ()
        for match in re.finditer(r"[^\n]+", page.text):
            text = match.group()
            cells = tuple(cell.strip() for cell in text.split("|"))
            if len(cells) not in {2, 5}:
                continue
            guessed = tuple(TABLE_TO_KEY.get(label_text(cell), "") for cell in cells)
            if all(guessed) and len(set(guessed)) == len(guessed):
                if set(guessed) not in ({"sku", "quantity"}, set(LINE_KEYS)):
                    continue
                header = Candidate(f"p{page.number}h{match.start()}", page.number,
                                   match.start(), match.end(), "table_header", text, text)
                keys = guessed
                continue
            if header is None or len(cells) != len(keys) or not any(re.search(r"\d", x) for x in cells):
                continue
            rows.append(TableRow(f"R{len(rows)}", page.number,
                                 match.start(), match.end(), text, header, keys, cells))
    return rows


def _box(page: Page, start: int, end: int) -> tuple[float, float, float, float] | None:
    words = [word for word in page.words if word.start < end and word.end > start]
    if not words:
        return None
    return (min(w.bbox[0] for w in words), min(w.bbox[1] for w in words),
            max(w.bbox[2] for w in words), max(w.bbox[3] for w in words))


def source_evidence(parsed: ParsedDocument, source: Candidate | TableRow) -> Evidence:
    page = next(p for p in parsed.pages if p.number == source.page)
    return Evidence(page=source.page, start=source.start, end=source.end, quote=source.quote,
                    bbox=_box(page, source.start, source.end))


def make_field(parsed: ParsedDocument, source: Candidate, key: str) -> ExtractedField:
    try:
        value, transformations = normalize_value(key, source.raw)
        return ExtractedField(raw=source.raw, normalized=value, status="supported",
                              transformations=transformations,
                              evidence=[source_evidence(parsed, source)])
    except ValueError as exc:
        return ExtractedField(raw=source.raw, evidence=[source_evidence(parsed, source)], reason=str(exc))


def make_line(parsed: ParsedDocument, row: TableRow) -> LineItem:
    fields = {}
    for key, raw in zip(row.keys, row.cells, strict=True):
        evidence = [source_evidence(parsed, row.header), source_evidence(parsed, row)]
        try:
            value, transformations = normalize_value(key, raw)
            fields[key] = ExtractedField(raw=raw, normalized=value, status="supported",
                                         transformations=transformations, evidence=evidence)
        except ValueError as exc:
            fields[key] = ExtractedField(raw=raw, evidence=evidence, reason=str(exc))
    return LineItem(fields=fields)


def _abstained(reason: str) -> ExtractedField:
    return ExtractedField(status="abstained", reason=reason)


def _baseline_kind(parsed: ParsedDocument) -> tuple[str, float]:
    kinds = {TITLE_TO_KIND[label_text(line)] for p in parsed.pages for line in p.text.splitlines()
             if label_text(line) in TITLE_TO_KIND}
    if len(kinds) == 1:
        return kinds.pop(), 1.0
    return "unknown", 0.0


def _empty(parsed: ParsedDocument, profile: str, reason: str, elapsed: float) -> Extraction:
    return Extraction(document_sha256=parsed.sha256, kind="unknown", classification_confidence=0,
                      profile=profile, model_version="unavailable",
                      fields={key: _abstained(reason) for key in SCALAR_KEYS}, warnings=[reason],
                      timings={"extraction_seconds": elapsed})


def extract(parsed: ParsedDocument, *, profile="baseline", model_path=None, llm_config=None) -> Extraction:
    started = time.monotonic()
    scalar_candidates = candidates(parsed)
    rows = table_rows(parsed)
    selected: dict[str, list[Candidate]] = {key: [] for key in SCALAR_KEYS}
    kind, confidence = _baseline_kind(parsed)
    version = "deterministic-1.0"
    warnings = []
    model_timings = {}
    if profile == "baseline":
        for candidate in scalar_candidates:
            key = LABEL_TO_KEY.get(label_text(candidate.label))
            if key:
                selected[key].append(candidate)
    elif profile == "local-linear":
        from .local_model import LocalModel, ModelError
        try:
            model = LocalModel.load(Path(model_path)) if model_path else None
            if model is None:
                raise ModelError("No local-linear model configured", code="MODEL_UNAVAILABLE")
            kind, confidence = model.classify(parsed)
            version = model.version
            for candidate in scalar_candidates:
                key, probability = model.classify_label(candidate.label)
                if key in selected and probability >= model.label_threshold:
                    selected[key].append(candidate)
                else:
                    warnings.append(f"label_abstention:{candidate.id}")
        except ModelError:
            raise
        except OSError as exc:
            raise ModelError("Local-linear artifact is unavailable", code="MODEL_UNAVAILABLE") from exc
        except ValueError as exc:
            raise ModelError("Local-linear artifact is invalid", code="MODEL_INVALID") from exc
    elif profile == "local-llm":
        from .llm import LlamaConfig, ModelUnavailable, propose
        try:
            config = llm_config if isinstance(llm_config, LlamaConfig) else LlamaConfig.model_validate(llm_config or {})
            proposal, telemetry = propose(parsed, scalar_candidates, rows, config)
            by_id = {c.id: c for c in scalar_candidates}
            for key in SCALAR_KEYS:
                cid = proposal["fields"].get(key)
                if cid and cid in by_id:
                    selected[key].append(by_id[cid])
            kind = proposal["kind"]
            # This is not LLM self-confidence. Only an unambiguous observed title
            # supporting the model's class grants deterministic support 1.0.
            observed_kind, _ = _baseline_kind(parsed)
            confidence = 1.0 if kind != "unknown" and kind == observed_kind else 0.0
            if confidence == 0:
                kind = "unknown"
                warnings.append("classification_not_supported_by_document_title")
            row_ids = set(proposal["line_rows"])
            rows = [r for r in rows if r.id in row_ids]
            version = f"{config.model_id}:{config.model_sha256[:12]}:{config.runtime_version}"
            warnings.extend(telemetry.get("warnings", []))
            model_timings["llm_request_seconds"] = telemetry["request_seconds"]
        except ModelUnavailable:
            raise
        except ValueError as exc:
            raise ModelUnavailable("Invalid local LLM configuration", code="MODEL_CONFIG") from exc
        except OSError as exc:
            raise ModelUnavailable("Local LLM artifact is unavailable", code="MODEL_UNAVAILABLE") from exc
    else:
        raise ValueError("Unsupported extraction profile; provider fallback is forbidden")
    fields = {}
    for key, values in selected.items():
        if len(values) == 1:
            fields[key] = make_field(parsed, values[0], key)
        elif values:
            try:
                identical = len({normalize_value(key, c.raw)[0] for c in values}) == 1
            except ValueError:
                identical = False
            fields[key] = make_field(parsed, values[0], key) if identical else _abstained("Conflicting or invalid repeated critical labels require review")
            fields[key].evidence = [source_evidence(parsed, c) for c in values]
            if identical:
                warnings.append(f"identical_repeated_field:{key}")
        else:
            fields[key] = _abstained("No supported source value selected")
    if any(_INSTRUCTION.search(page.text) for page in parsed.pages):
        warnings.append("untrusted_instruction_text_ignored; document content cannot call tools or change policy")
    extraction = Extraction(document_sha256=parsed.sha256, kind=kind,
                            classification_confidence=confidence, profile=profile, model_version=version,
                            fields=fields, line_items=[make_line(parsed, row) for row in rows], warnings=warnings,
                            timings={"extraction_seconds": time.monotonic() - started, **model_timings})
    return validate_evidence(parsed, extraction)


def _citation_valid(parsed: ParsedDocument, evidence: Evidence) -> bool:
    page = next((p for p in parsed.pages if p.number == evidence.page), None)
    if page is None or not 0 <= evidence.start < evidence.end <= len(page.text):
        return False
    if page.text[evidence.start:evidence.end] != evidence.quote:
        return False
    actual_box = _box(page, evidence.start, evidence.end)
    if evidence.bbox is not None:
        if actual_box is None or any(abs(a-b) > 0.1 for a, b in zip(actual_box, evidence.bbox, strict=True)):
            return False
    return True


def _ocr_supported(parsed: ParsedDocument, evidence: Evidence) -> bool:
    page = next(p for p in parsed.pages if p.number == evidence.page)
    if page.method != "ocr":
        return True
    words = [w for w in page.words if w.start < evidence.end and w.end > evidence.start
             and any(character.isalnum() for character in w.text)]
    # This is an operational rejection threshold, not a calibrated probability
    # that OCR is right. Punctuation-only separators do not prove a field value.
    return bool(words) and all(w.confidence is not None and w.confidence >= MIN_CRITICAL_OCR_CONFIDENCE for w in words)


def _invalidate(field: ExtractedField, reason: str) -> None:
    field.normalized = None
    field.status = "abstained"
    field.reason = reason


def validate_evidence(parsed: ParsedDocument, extraction: Extraction) -> Extraction:
    """Return an independently checked copy; reject invented and misassigned proof.

    Semantic support is deliberately limited to versioned purchasing labels and
    table headers. An unknown label remains a human-review case even when an LLM
    plausibly assigns it. No source text or source truth is mutated.
    """
    result = extraction.model_copy(deep=True)
    scalar_sources = candidates(parsed)
    rows = table_rows(parsed)
    indexed = {(c.page, c.start, c.end): c for c in scalar_sources}
    occurrence = {key: [c for c in scalar_sources if LABEL_TO_KEY.get(label_text(c.label)) == key]
                  for key in SCALAR_KEYS}
    all_fields = list(result.fields.values()) + [f for line in result.line_items for f in line.fields.values()]
    if result.document_sha256 != parsed.sha256:
        for field in all_fields:
            _invalidate(field, "Evidence document digest mismatch")
        result.kind = "unknown"
        result.classification_confidence = 0
        result.warnings.append("evidence_document_mismatch")
        return result
    for key, field in result.fields.items():
        if key not in SCALAR_KEYS:
            _invalidate(field, "Field is outside contract")
            continue
        if field.origin != "extracted":
            _invalidate(field, "Model output cannot claim a human correction")
            continue
        if field.status != "supported":
            field.normalized = None
            continue
        try:
            values = {normalize_value(key, c.raw)[0] for c in occurrence[key]}
        except ValueError:
            values = set()
        if len(values) != 1:
            _invalidate(field, "Missing, conflicting or invalid repeated critical label")
            continue
        if not field.evidence or not all(_citation_valid(parsed, e) for e in field.evidence):
            _invalidate(field, "Invalid citation span, quotation or coordinates")
            continue
        if not all(_ocr_supported(parsed, ev) for ev in field.evidence):
            _invalidate(field, "OCR support falls below the critical-token threshold")
            continue
        ev = field.evidence[0]
        source = indexed.get((ev.page, ev.start, ev.end))
        if source is None or LABEL_TO_KEY.get(label_text(source.label)) != key or source.raw != field.raw:
            _invalidate(field, "Citation does not support this field/value relationship")
            continue
        for extra in field.evidence[1:]:
            extra_source = indexed.get((extra.page, extra.start, extra.end))
            if extra_source is None or LABEL_TO_KEY.get(label_text(extra_source.label)) != key:
                _invalidate(field, "Repeated citation has a different semantic label")
                break
            try:
                if normalize_value(key, extra_source.raw)[0] != field.normalized:
                    raise ValueError("Conflicting repeated source value")
            except ValueError as exc:
                _invalidate(field, str(exc))
                break
        if field.status != "supported":
            continue
        try:
            normalized, transformations = normalize_value(key, field.raw)
            if normalized != field.normalized or transformations != field.transformations:
                raise ValueError("Unsupported normalization or transformation history")
        except ValueError as exc:
            _invalidate(field, str(exc))
    for line in result.line_items:
        for key, field in line.fields.items():
            if field.origin != "extracted":
                _invalidate(field, "Model output cannot claim a human correction")
                continue
            if field.status != "supported":
                field.normalized = None
                continue
            if key not in LINE_KEYS or len(field.evidence) != 2 or not all(_citation_valid(parsed, e) for e in field.evidence):
                _invalidate(field, "A valid table header and row citation are required")
                continue
            if not all(_ocr_supported(parsed, ev) for ev in field.evidence):
                _invalidate(field, "OCR support falls below the critical-token threshold")
                continue
            h, r = field.evidence
            row = next((row for row in rows if (row.page, row.start, row.end) == (r.page, r.start, r.end)
                        and (row.header.page, row.header.start, row.header.end) == (h.page, h.start, h.end)), None)
            if row is None or key not in row.keys or row.cells[row.keys.index(key)] != field.raw:
                _invalidate(field, "Table column evidence does not support the assigned field")
                continue
            try:
                normalized, transformations = normalize_value(key, field.raw)
                if normalized != field.normalized or transformations != field.transformations:
                    raise ValueError("Unsupported normalization or transformation history")
            except ValueError as exc:
                _invalidate(field, str(exc))
    if any(f.status == "abstained" and f.raw is not None for f in all_fields):
        if "one_or_more_proposals_failed_evidence_validation" not in result.warnings:
            result.warnings.append("one_or_more_proposals_failed_evidence_validation")
    return result
