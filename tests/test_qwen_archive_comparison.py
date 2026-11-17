"""Standalone synthetic negative cases for original Qwen archive comparison."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import warnings
from zipfile import ZipFile, ZIP_DEFLATED

from scripts.compare_qwen_archives import (
    EvidenceError, compare, original, main, write_once,
)

MODEL_SHA = "a" * 64
FIELDS = ("document_id", "purchase_order_id", "supplier_id", "currency",
          "document_date", "subtotal", "tax", "total")
LINES = ("sku", "quantity", "unit_price", "net_amount", "tax_rate")


def encode(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def synthetic_archive_members(*, lose_field: bool = False) -> dict[str, bytes]:
    items = {}
    manifest = {"generator_version": "independent-node-pdf-writer-1.0", "documents": []}
    totals = Counter()
    raw_classes = Counter()
    for n in range(12):
        pdf = b"%PDF-1.4\n synthetic archive evidence " + str(n).encode() + b"\n%%EOF"
        pdf_sha = hashlib.sha256(pdf).hexdigest()
        doc_key, doc_path = f"doc-{n:02d}", f"documents/doc-{n:02d}.pdf"
        group, doc_kind = ("known", "invoice") if n < 6 else ("unseen", "unknown")
        truth = {"document_id": f"INV-{n}", "purchase_order_id": "PO-1",
                 "supplier_id": "SUP-1", "currency": "EUR", "document_date": "2026-11-01",
                 "subtotal": "4.00", "tax": "1.00", "total": "5.00"}
        lines = [{"sku": "SKU-1", "quantity": "1", "unit_price": "4.00",
                  "net_amount": "4.00", "tax_rate": "25"}]
        items["qwen-dev-corpus/" + doc_path] = pdf
        manifest["documents"].append({
            "path": doc_path, "sha256": pdf_sha, "contract_group": group,
            "expected_fields": truth, "expected_lines": lines,
            "expected_kind": doc_kind, "document_key": doc_key,
        })
        actual = dict(truth)
        if lose_field and n == 0:
            actual["document_id"] = None
        extraction = {
            "kind": doc_kind, "document_sha256": pdf_sha,
            "fields": {k: {"normalized": v} for k, v in actual.items()},
            "line_items": [{"fields": {k: {"normalized": v} for k, v in lines[0].items()}}],
        }
        expected = {**truth, **{f"lines[0].{k}": v for k, v in lines[0].items()}}
        comparisons = []
        for k, target in expected.items():
            value = actual[k] if k in actual else lines[0][k.split(".")[-1]]
            comparisons.append({
                "field": k, "actual": value, "expected": target,
                "present_in_truth": True, "correct": value == target,
                "critical": k != "document_date", "abstained": value is None,
            })
        correct = sum(c["correct"] for c in comparisons)
        abstentions = sum(c["critical"] and c["abstained"] for c in comparisons)
        eligible = group == "known" and correct == 13
        record = {
            "input_sha256": pdf_sha, "input_path": doc_path,
            "expected_kind": doc_kind, "predicted_kind": doc_kind,
            "classification_correct": True, "extraction": extraction,
            "comparisons": comparisons, "fields_correct": correct, "fields_total": 13,
            "present_fields_total": 13, "present_fields_correct": correct,
            "required_abstentions": 0, "correct_required_abstentions": 0,
            "critical_fields_total": 12, "critical_fields_abstained": abstentions,
            "eligible": eligible, "false_eligible": False,
            "citation_total": 0, "citation_valid": 0,
        }
        items[f"qwen-dev-run/evaluation/documents/local-llm/{n:04d}-repeat-0.json"] = encode(record)
        proposal = {
            "kind": doc_kind,
            "fields": {k: (None if lose_field and n == 0 and k == "document_id"
                          else f"candidate-{k}") for k in FIELDS},
            "line_rows": [],
        }
        trace = {
            "proposal": proposal,
            "response": {"choices": [{"message": {"content": json.dumps(proposal)}}]},
            "telemetry": {"document_sha256": pdf_sha, "model_sha256": MODEL_SHA,
                          "prompt_sha256": "c" * 64,
                          "prompt_version": "structured-extraction-1.3",
                          "provider": "local-llama.cpp"},
        }
        items[f"qwen-dev-run/model-traces/{pdf_sha}-{1000+n}.json"] = encode(trace)
        raw_classes[doc_kind] += 1
        for metric in ("fields_correct", "fields_total", "present_fields_correct",
                       "present_fields_total", "required_abstentions",
                       "correct_required_abstentions", "critical_fields_total",
                       "critical_fields_abstained", "citation_total", "citation_valid"):
            totals[metric] += record[metric]
        totals["eligible"] += eligible
        totals["classification_correct"] += 1
    items["qwen-dev-corpus/manifest.json"] = encode(manifest)
    source = "b" * 40
    summary = {
        "source": {"git_commit": source},
        "dataset": {"available_test_documents": 12, "evaluated_test_documents": 12},
        "profiles": {"local-llm": {
            "documents": 12, "classification_accuracy": 1.0,
            "eligible_documents": totals["eligible"], "false_eligible_documents": 0,
            "policy_gate_met": False, "denominators": dict(totals),
        }},
    }
    report = {
        "source_commit": source,
        "corpus_manifest_sha256": hashlib.sha256(
            items["qwen-dev-corpus/manifest.json"]).hexdigest(),
        "pinned_model_sha256": MODEL_SHA, "prompt_version": "structured-extraction-1.3",
        "real_original_traces": 12, "evaluated_documents": 12,
        "correct_classifications": 12,
        "eligible_for_explicit_human_review": totals["eligible"],
        "false_eligible": 0, "raw_class_proposals": dict(raw_classes),
        "bounded_runtime_execution_gate_met": True,
        "synthetic_development_quality_policy_met": False,
        "dataset_is_untouched_holdout": False,
        "qwen_general_quality_accepted": False,
    }
    items["qwen-dev-run/evaluation/summary.json"] = encode(summary)
    items["qwen-dev-report.json"] = encode(report)
    items["qwen-dev-run/harness.json"] = encode({"model_sha256": MODEL_SHA})
    return items


def save(path: Path, members: dict[str, bytes]) -> Path:
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as z:
        for name, payload in members.items():
            z.writestr(name, payload)
    return path


class OriginalQwenArchiveComparatorTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.baseline = save(self.root / "baseline.zip", synthetic_archive_members())

    def candidate(self, mutate=None, *, loss=False):
        members = synthetic_archive_members(lose_field=loss)
        if mutate:
            mutate(members)
        return save(self.root / "candidate.zip", members)

    def rejected(self, mutate, message):
        with self.assertRaisesRegex(EvidenceError, message):
            original(self.candidate(mutate))

    def test_complete_original_evidence_and_case_pairing(self):
        out = compare(self.baseline, self.candidate())
        self.assertTrue(out["same_pdf_cohort"])
        self.assertTrue(out["nonregression_passed"])
        self.assertEqual(len(out["case_comparison"]), 12)
        self.assertFalse(out["model_generalization_accepted"])

    def test_loss_is_not_hidden_by_identical_classification(self):
        out = compare(self.baseline, self.candidate(loss=True))
        self.assertFalse(out["nonregression_passed"])
        self.assertIn("fields_correct: 156 -> 155", out["nonregression_failures"])
        self.assertIn("critical_abstentions: 0 -> 1", out["nonregression_failures"])

    def test_pin_original_zip_digest(self):
        with self.assertRaisesRegex(EvidenceError, "Pinned original ZIP"):
            original(self.baseline, "0" * 64)

    def test_forged_pdf_bytes_rejected(self):
        def edit(members):
            members["qwen-dev-corpus/documents/doc-00.pdf"] += b"tamper"
        self.rejected(edit, "Original PDF missing or failed")

    def test_other_manifest_is_not_paired(self):
        def edit(members):
            manifest = json.loads(members["qwen-dev-corpus/manifest.json"])
            manifest["seed"] = 100
            members["qwen-dev-corpus/manifest.json"] = encode(manifest)
            report = json.loads(members["qwen-dev-report.json"])
            report["corpus_manifest_sha256"] = hashlib.sha256(
                members["qwen-dev-corpus/manifest.json"]).hexdigest()
            members["qwen-dev-report.json"] = encode(report)
        with self.assertRaisesRegex(EvidenceError, "different document populations"):
            compare(self.baseline, self.candidate(edit))

    def test_archive_path_traversal_refused(self):
        self.rejected(lambda m: m.__setitem__("../outside.txt", b"secret"),
                      "Unsafe/unexpected ZIP path")

    def test_duplicate_zip_members_refused(self):
        path = self.candidate()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with ZipFile(path, "a") as z:
                z.writestr("qwen-dev-report.json", "{}")
        with self.assertRaisesRegex(EvidenceError, "Excess or duplicate"):
            original(path)

    def test_missing_original_model_trace(self):
        def edit(m):
            m.pop(next(k for k in m if k.startswith("qwen-dev-run/model-traces/")))
        self.rejected(edit, "Missing original model traces")

    def test_missing_scored_document(self):
        def edit(m):
            m.pop(next(k for k in m if k.startswith(
                "qwen-dev-run/evaluation/documents/local-llm/")))
        self.rejected(edit, "Expected 12 original scored")

    def test_forged_model_response(self):
        def edit(m):
            k = next(k for k in m if k.startswith("qwen-dev-run/model-traces/"))
            trace = json.loads(m[k])
            trace["proposal"]["kind"] = "fake"
            m[k] = encode(trace)
        self.rejected(edit, "Original response contradicts")

    def test_forged_model_hash(self):
        def edit(m):
            m["qwen-dev-run/harness.json"] = encode({"model_sha256": "f" * 64})
        self.rejected(edit, "Pinned model/corpus")

    def test_forged_prompt_identity(self):
        def edit(m):
            k = next(k for k in m if k.startswith("qwen-dev-run/model-traces/"))
            obj = json.loads(m[k])
            obj["telemetry"]["prompt_version"] = "version-not-executed"
            m[k] = encode(obj)
        self.rejected(edit, "provenance mismatch")

    def test_scored_truth_cannot_be_replaced(self):
        def edit(m):
            k = next(k for k in m if k.startswith(
                "qwen-dev-run/evaluation/documents/local-llm/"))
            obj = json.loads(m[k])
            obj["comparisons"][0]["expected"] = "WRONG"
            m[k] = encode(obj)
        self.rejected(edit, "disagrees with original truth")

    def test_summary_count_cannot_be_inflated(self):
        def edit(m):
            d = json.loads(m["qwen-dev-run/evaluation/summary.json"])
            d["profiles"]["local-llm"]["denominators"]["fields_correct"] += 1
            m["qwen-dev-run/evaluation/summary.json"] = encode(d)
        self.rejected(edit, "Forged aggregate metric")

    def test_scored_field_must_match_extraction(self):
        def edit(m):
            k = next(k for k in m if k.startswith(
                "qwen-dev-run/evaluation/documents/local-llm/"))
            obj = json.loads(m[k])
            obj["comparisons"][0]["actual"] = "FORGED"
            m[k] = encode(obj)
        self.rejected(edit, "Scored field actual differs")

    def test_write_once_does_not_overwrite_receipt_or_symlink(self):
        report = compare(self.baseline, self.candidate())
        out = self.root / "receipt.json"
        write_once(out, report)
        with self.assertRaises(FileExistsError):
            write_once(out, report)
        link = self.root / "link.json"
        link.symlink_to(out)
        with self.assertRaises(FileExistsError):
            write_once(link, report)

    def test_cli_optional_nonregression_gate_returns_failure_with_receipt(self):
        candidate = self.candidate(loss=True)
        path = self.root / "nonregression-failure.json"
        result = main(["--baseline", str(self.baseline), "--candidate", str(candidate),
                       "--output", str(path), "--require-nonregression"])
        self.assertEqual(result, 1)
        self.assertFalse(json.loads(path.read_text())["nonregression_passed"])
        with self.assertRaises(FileExistsError):
            main(["--baseline", str(self.baseline), "--candidate", str(candidate),
                  "--output", str(path)])


if __name__ == "__main__":
    unittest.main()
