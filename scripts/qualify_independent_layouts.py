"""Evaluate independently generated, fictional PDFs without treating them as supplier evidence.

Only the Node PDF writer defines this corpus. The production ReportLab corpus
generator is not imported or used. Evaluate BOTH normal and intentionally
unsupported labels/geometric tables through the real isolated PDF parser,
frozen local-linear model, semantic verifier and business eligibility gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from dci.evaluation import evaluate_manifest

FROZEN_MODEL_SHA = "234c94149697cbeda761c22cae9c27aa0f57a8215422da906b32a6bc07148ff1"
EXPECTED_VERSION = "independent-node-pdf-writer-1.0"


def qualify(manifest_path: Path, output: Path, model: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    docs = manifest["documents"]
    if manifest.get("generator_version") != EXPECTED_VERSION:
        raise ValueError("Independent generator version mismatch")
    if len(docs) != 12 or len({d["sha256"] for d in docs}) != 12:
        raise ValueError("Require all twelve independently written unique PDFs")
    if sorted(d["contract_group"] for d in docs) != ["known"] * 6 + ["unseen"] * 6:
        raise ValueError("Holdout contract groups must have six cases each")
    if len({d["family_id"] for d in docs}) != 4:
        raise ValueError("Four distinct supplier-like fictional document families required")
    model_hash = hashlib.sha256(model.read_bytes()).hexdigest()
    if model_hash != FROZEN_MODEL_SHA:
        raise ValueError("Frozen statistical model digest mismatch")

    eval_dir = output / "evaluation"
    summary = evaluate_manifest(
        manifest_path, eval_dir, profiles=("baseline", "local-linear"), model_path=model
    )
    report = {
        "schema_version": "1.0",
        "purpose": "Additional independent-RENDERER synthetic PDF evidence only",
        "source": summary["source"],
        "model_sha256": model_hash,
        "manifest_sha256": summary["manifest_sha256"],
        "generator_version": EXPECTED_VERSION,
        "total_documents": len(docs),
        "groups": {"known": 6, "unseen": 6},
        "independent_supplier_generalization_accepted": False,
        "qwen_quality_accepted": False,
        "production_host_accepted": False,
        "profiles": {},
    }
    for profile in ("baseline", "local-linear"):
        result = summary["profiles"][profile]
        group_data = {}
        for group in ("known", "unseen"):
            records = []
            for index, truth in enumerate(docs):
                if truth["contract_group"] != group:
                    continue
                record_path = eval_dir / "documents" / profile / f"{index:04d}-repeat-0.json"
                record = json.loads(record_path.read_text(encoding="utf-8"))
                records.append(record)
            group_data[group] = {
                "documents": len(records),
                "correct_classifications": sum(r.get("classification_correct") is True for r in records),
                "eligible_documents": sum(r.get("eligible") is True for r in records),
                "false_eligible_documents": sum(r.get("false_eligible") is True for r in records),
                "inference_or_parser_failures": sum("error" in r for r in records),
                "unexpected_line_rows": sum(r.get("extra_lines", 0) for r in records),
            }
            if len(records) != 6:
                raise AssertionError("Group records missing; cannot silently discard failures")
        safety = (
            result["documents"] == 12
            and result["failures"] == 0
            and result["false_eligible_documents"] == 0
            and result["citation_validity"] in (None, 1.0)
            and result["semantic_evidence_validity"] in (None, 1.0)
            and group_data["unseen"]["eligible_documents"] == 0
            and group_data["unseen"]["inference_or_parser_failures"] == 0
        )
        report["profiles"][profile] = {
            "safety_gate_met": safety,
            "classification_accuracy": result["classification_accuracy"],
            "eligible_documents": result["eligible_documents"],
            "eligible_coverage": result["eligible_coverage"],
            "eligible_critical_quality": result["eligible_critical_quality"],
            "false_eligible_documents": result["false_eligible_documents"],
            "citation_validity": result["citation_validity"],
            "semantic_evidence_validity": result["semantic_evidence_validity"],
            "synthetic_policy_gate_met": result["policy_gate_met"],
            "groups": group_data,
        }
    report["limits"] = [
        "Standalone Node implementation and novel layouts, but all PDFs remain newly authored synthetic examples.",
        "Labels known to the current source contract are intentionally present in six cases.",
        "Out-of-contract layouts should remain blocked, never accepted through confident guesses.",
        "The original 36-document frozen model holdout is separate and never overwritten.",
        "No real supplier provenance, human annotations, unseen real OCR, Qwen rerun, or target-host deployment.",
    ]
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "report.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    if not all(p["safety_gate_met"] for p in report["profiles"].values()):
        raise AssertionError("Independent-renderer safety/abstention regression failed")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--model",
        type=Path,
        default=Path("evidence/evaluation/local-linear-model.json"),
    )
    args = parser.parse_args()
    qualify(args.manifest.resolve(strict=True), args.output, args.model.resolve(strict=True))
