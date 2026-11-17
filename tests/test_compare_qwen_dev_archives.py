"""Positive/negative synthetic ZIP tests; never download or run a model."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile

from scripts.compare_qwen_dev_archives import compare, inspect


def encoded(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True) + "\n").encode("utf-8")


def make_archive(
    path: Path, *, version: str, lose_fields: bool = False,
    tamper_pdf: bool = False, missing_trace: bool = False,
    forged_aggregate: bool = False, traversal: bool = False,
    duplicate: bool = False, changed_inputs: bool = False,
    forged_field_counter: bool = False, forged_trace: bool = False,
    forged_trace_kind: bool = False, invalid_citation: bool = False,
    unsupported_eligible: bool = False,
) -> None:
    contents: dict[str, bytes] = {}
    documents: list[dict] = []
    scored: list[dict] = []
    for i in range(12):
        pdf = b"%PDF-1.4\n" + str(i).encode() + (
            b"NEW" if i == 11 and changed_inputs else b"OLD"
        )
        sha = hashlib.sha256(pdf).hexdigest()
        name = f"documents/case-{i:02d}.pdf"
        contents["qwen-dev-corpus/" + name] = (
            pdf + b"TAMPER" if tamper_pdf and i == 0 else pdf
        )
        documents.append({
            "path": name,
            "sha256": sha,
            "contract_group": "known" if i < 6 else "unseen",
            "expected_kind": "invoice",
        })
        correct = 10 - (1 if lose_fields and i == 0 else 0)
        comparisons = [
            {
                "correct": j < correct,
                "critical": j < 10,
                "abstained": bool(lose_fields and i == 0 and j == 9),
                "present_in_truth": True,
            }
            for j in range(13)
        ]
        row = {
            "input_sha256": sha,
            "expected_kind": "invoice",
            "predicted_kind": "invoice",
            "comparisons": comparisons,
            "classification_correct": True,
            "eligible": i < 6 or (unsupported_eligible and i == 6),
            "false_eligible": False,
            "fields_correct": correct + (
                1 if forged_field_counter and i == 0 else 0
            ),
            "fields_total": 13,
            "present_fields_correct": correct,
            "present_fields_total": 13,
            "critical_fields_abstained": 1 if lose_fields and i == 0 else 0,
            "critical_fields_total": 10,
            "citation_valid": 1 if invalid_citation and i == 0 else 2,
            "citation_total": 2,
        }
        contents[
            f"qwen-dev-run/evaluation/documents/local-llm/{i:04d}-repeat-0.json"
        ] = encoded(row)
        scored.append(row)
        if not (missing_trace and i == 0):
            contents[f"qwen-dev-run/model-traces/{sha}-{i}.json"] = encoded({
                "telemetry": {
                    "document_sha256": sha,
                    "model_sha256": "a" * 64,
                    "prompt_version": version,
                    "provider": (
                        "fake-provider" if forged_trace and i == 0
                        else "local-llama.cpp"
                    ),
                },
                "request": {
                    "messages": [
                        {"content": json.dumps({"document_sha256": sha})}
                    ],
                },
                "proposal": {
                    "kind": (
                        "purchase_order" if forged_trace_kind and i == 0
                        else "invoice"
                    ),
                },
            })
    manifest = encoded({
        "generator_version": "independent-node-pdf-writer-1.0",
        "documents": documents,
    })
    contents["qwen-dev-corpus/manifest.json"] = manifest
    metric_keys = (
        "fields_correct", "fields_total", "present_fields_correct",
        "present_fields_total", "critical_fields_abstained",
        "critical_fields_total", "citation_valid", "citation_total",
    )
    denom = {key: sum(row[key] for row in scored) for key in metric_keys}
    contents["qwen-dev-run/evaluation/summary.json"] = encoded({
        "profiles": {"local-llm": {"denominators": denom}},
    })
    report = {
        "corpus_manifest_sha256": hashlib.sha256(manifest).hexdigest(),
        "dataset_is_untouched_holdout": False,
        "dataset_is_independently_sourced_supplier_benchmark": False,
        "qwen_general_quality_accepted": False,
        "correct_classifications": 12 if not forged_aggregate else 11,
        "eligible_for_explicit_human_review": 7 if unsupported_eligible else 6,
        "false_eligible": 0,
        "evaluated_documents": 12,
        "real_original_traces": 12,
        "request_or_parser_failures": 0,
        "source_commit": "test-" + version,
        "prompt_version": version,
        "pinned_model_sha256": "a" * 64,
        "synthetic_development_quality_policy_met": False,
        "bounded_runtime_execution_gate_met": True,
    }
    contents["qwen-dev-report.json"] = encoded(report)
    if traversal:
        contents["../evil.txt"] = b"bad"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(contents.items()):
            archive.writestr(name, data)
        if duplicate:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                archive.writestr(
                    "qwen-dev-report.json", contents["qwen-dev-report.json"]
                )


class CompareQwenArchivesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="qwen-paired-")
        self.addCleanup(self.temp.cleanup)
        self.baseline = Path(self.temp.name) / "baseline.zip"
        self.candidate = Path(self.temp.name) / "candidate.zip"
        make_archive(self.baseline, version="structured-extraction-1.3")
        make_archive(self.candidate, version="structured-extraction-1.4")

    def test_identical_source_nonregression_does_not_claim_holdout(self):
        result = compare(self.baseline, self.candidate)
        self.assertTrue(result["nonregression_met"])
        self.assertEqual(result["paired_case_count"], 12)
        self.assertFalse(result["untouched_holdout"])
        self.assertFalse(result["supplier_real_generalization"])
        self.assertFalse(result["qwen_general_quality_accepted"])

    def test_detect_field_loss_without_classification_loss(self):
        make_archive(
            self.candidate, version="structured-extraction-1.4", lose_fields=True
        )
        result = compare(self.baseline, self.candidate)
        self.assertFalse(result["nonregression_met"])
        self.assertIn("fields_correct decreased", result["regressions"])
        self.assertIn("critical abstention increased", result["regressions"])
        self.assertEqual(result["baseline"]["metrics"]["correct_classes"], 12)
        self.assertEqual(result["candidate"]["metrics"]["correct_classes"], 12)

    def test_reject_different_pdf_population(self):
        make_archive(
            self.candidate, version="structured-extraction-1.4",
            changed_inputs=True,
        )
        with self.assertRaisesRegex(ValueError, "not paired"):
            compare(self.baseline, self.candidate)

    def test_reject_pdf_tampering(self):
        make_archive(
            self.candidate, version="structured-extraction-1.4",
            tamper_pdf=True,
        )
        with self.assertRaisesRegex(ValueError, "PDF source bytes mismatch"):
            inspect(self.candidate)

    def test_reject_missing_original_model_response(self):
        make_archive(
            self.candidate, version="structured-extraction-1.4",
            missing_trace=True,
        )
        with self.assertRaisesRegex(ValueError, "Twelve distinct original"):
            inspect(self.candidate)

    def test_reject_forged_original_trace_provider(self):
        make_archive(
            self.candidate, version="structured-extraction-1.4",
            forged_trace=True,
        )
        with self.assertRaisesRegex(ValueError, "trace identity/output"):
            inspect(self.candidate)

    def test_reject_forged_model_proposed_class(self):
        make_archive(
            self.candidate, version="structured-extraction-1.4",
            forged_trace_kind=True,
        )
        with self.assertRaisesRegex(ValueError, "trace identity/output"):
            inspect(self.candidate)

    def test_invalid_citations_cannot_report_false_green_runtime(self):
        make_archive(
            self.candidate, version="structured-extraction-1.4",
            invalid_citation=True,
        )
        result = compare(self.baseline, self.candidate)
        self.assertFalse(result["nonregression_met"])
        self.assertTrue(result["candidate_runtime_report_contradicts_source"])
        self.assertIn("candidate runtime/safety gate failed", result["regressions"])

    def test_unsupported_layout_cannot_report_false_green_runtime(self):
        make_archive(
            self.candidate, version="structured-extraction-1.4",
            unsupported_eligible=True,
        )
        result = compare(self.baseline, self.candidate)
        self.assertFalse(result["nonregression_met"])
        self.assertTrue(result["candidate_runtime_report_contradicts_source"])
        self.assertIn("candidate runtime/safety gate failed", result["regressions"])

    def test_reject_forged_report_counter(self):
        make_archive(
            self.candidate, version="structured-extraction-1.4",
            forged_aggregate=True,
        )
        with self.assertRaisesRegex(ValueError, "mismatches original"):
            inspect(self.candidate)

    def test_reject_archive_traversal(self):
        make_archive(
            self.candidate, version="structured-extraction-1.4", traversal=True
        )
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            inspect(self.candidate)

    def test_reject_duplicate_member(self):
        make_archive(
            self.candidate, version="structured-extraction-1.4", duplicate=True
        )
        with self.assertRaisesRegex(ValueError, "Duplicate ZIP member"):
            inspect(self.candidate)

    def test_reject_case_field_counter_forgery(self):
        make_archive(
            self.candidate, version="structured-extraction-1.4",
            forged_field_counter=True,
        )
        with self.assertRaisesRegex(ValueError, "field totals"):
            inspect(self.candidate)

    def test_cli_failure_preserves_original_receipt_write_once(self):
        make_archive(
            self.candidate, version="structured-extraction-1.4", lose_fields=True
        )
        output = Path(self.temp.name) / "comparison.json"
        script = (
            Path(__file__).resolve().parents[1]
            / "scripts" / "compare_qwen_dev_archives.py"
        )
        command = [
            sys.executable, str(script), "--baseline", str(self.baseline),
            "--candidate", str(self.candidate), "--output", str(output),
            "--require-nonregression",
        ]
        first = subprocess.run(
            command, capture_output=True, text=True, check=False,
        )
        self.assertEqual(first.returncode, 3, first.stderr)
        original = json.loads(output.read_text())
        self.assertFalse(original["nonregression_met"])
        second = subprocess.run(
            command, capture_output=True, text=True, check=False,
        )
        self.assertNotEqual(second.returncode, 0)
        self.assertEqual(
            json.loads(output.read_text())["regressions"],
            ["fields_correct decreased", "critical abstention increased"],
        )

    def test_reject_self_comparison(self):
        with self.assertRaisesRegex(ValueError, "itself"):
            compare(self.baseline, self.baseline)


if __name__ == "__main__":
    unittest.main()
