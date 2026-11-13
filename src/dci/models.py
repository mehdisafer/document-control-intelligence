"""Versioned boundary types shared by parsers, extractors, rules and the API.

Offsets are Unicode code-point offsets into canonical page text; end is exclusive.
Boxes use PDF points, top-left origin, independent of the source raster DPI.
Money and quantities cross boundaries as decimal strings, never binary floats.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Word(StrictModel):
    text: str
    start: int
    end: int
    bbox: tuple[float, float, float, float]
    confidence: float | None = None


class Page(StrictModel):
    number: int = Field(ge=1)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    text: str
    words: list[Word] = Field(default_factory=list)
    method: Literal["native", "ocr"]


class ParsedDocument(StrictModel):
    schema_version: str = "1.0"
    sha256: str
    pages: list[Page]
    parser_version: str
    timings: dict[str, float] = Field(default_factory=dict)


class Evidence(StrictModel):
    page: int = Field(ge=1)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: str
    bbox: tuple[float, float, float, float] | None = None


class ExtractedField(StrictModel):
    raw: str | None = None
    normalized: str | None = None
    origin: Literal["extracted", "human"] = "extracted"
    status: Literal["supported", "abstained", "corrected"] = "abstained"
    evidence: list[Evidence] = Field(default_factory=list)
    transformations: list[str] = Field(default_factory=list)
    reason: str | None = None


class LineItem(StrictModel):
    fields: dict[str, ExtractedField]


DocumentKind = Literal["purchase_order", "delivery_note", "invoice", "unknown"]


class Extraction(StrictModel):
    schema_version: str = "1.0"
    contract_version: str = "purchasing-1.0"
    document_sha256: str
    kind: DocumentKind
    classification_confidence: float = Field(ge=0, le=1)
    profile: str
    model_version: str
    fields: dict[str, ExtractedField]
    line_items: list[LineItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    timings: dict[str, float] = Field(default_factory=dict)


class Finding(StrictModel):
    code: str
    severity: Literal["info", "warning", "error"]
    message: str
    field: str | None = None
    document_id: str | None = None


class CheckResult(StrictModel):
    rule_version: str = "purchasing-rules-1.0"
    decision: Literal["eligible", "review", "rejected"]
    findings: list[Finding]
    calculated: dict[str, str] = Field(default_factory=dict)


class Reconciliation(StrictModel):
    rule_version: str = "three-way-1.0"
    status: Literal["matched", "partial", "missing", "contradictory", "review"]
    findings: list[Finding]
    totals: dict[str, str] = Field(default_factory=dict)
