"""Validate real Qwen development inference; never treat synthetic tests as P04 acceptance."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from dci.llm import MODEL_SHA256, PROMPT_VERSION

GENERATOR = "independent-node-pdf-writer-1.0"
TRACE_NAME = re.compile(r"([0-9a-f]{64})-[0-9]+\.json\Z")


def runtime_gate(documents: int, traces: int, errors: int, false_eligible: int,
                 out_of_contract_eligible: int, citations: float | None,
                 semantics: float | None) -> bool:
    """Runtime/safety only; a valid all-abstain run is NOT quality acceptance."""
    return (documents == traces == 12 and errors == 0 and false_eligible == 0
            and out_of_contract_eligible == 0
            and citations in (None, 1.0) and semantics in (None, 1.0))


def summarize(manifest: Path, evaluation: Path, harness: Path) -> dict:
    corpus = json.loads(manifest.read_text(encoding="utf-8"))
    run = json.loads((evaluation / "summary.json").read_text(encoding="utf-8"))
    metadata = json.loads(harness.read_text(encoding="utf-8"))
    documents = corpus["documents"]
    if (corpus.get("generator_version") != GENERATOR or len(documents) != 12
            or Counter(d.get("contract_group") for d in documents) != {"known": 6, "unseen": 6}):
        raise ValueError("Expected exactly six in-contract and six unsupported synthetic PDFs")
    root = manifest.parent.resolve(strict=True)
    groups_by_sha: dict[str, str] = {}
    for item in documents:
        pdf = (root / item["path"]).resolve(strict=True)
        if not pdf.is_relative_to(root) or pdf.stat().st_size > 10_485_760:
            raise ValueError("PDF path/size escaped synthetic corpus")
        sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
        if sha != item["sha256"] or sha in groups_by_sha:
            raise ValueError("Duplicated or tampered synthetic PDF")
        groups_by_sha[sha] = item["contract_group"]
    ds = run["dataset"]
    selected = run["profiles"]["local-llm"]
    if (ds["generator_version"] != GENERATOR or ds["available_test_documents"] != 12
            or ds["evaluated_test_documents"] != 12 or selected["documents"] != 12
            or metadata["model_sha256"] != MODEL_SHA256
            or metadata["network_binding"] != "127.0.0.1"):
        raise ValueError("Qwen runtime, model or complete dataset identity mismatch")

    records = [json.loads(f.read_text(encoding="utf-8"))
               for f in sorted((evaluation / "documents" / "local-llm").glob("*-repeat-0.json"))]
    if len(records) != 12 or {r["input_sha256"] for r in records} != set(groups_by_sha):
        raise ValueError("Evaluation records and original PDFs are not one-to-one")
    traces = sorted((harness.parent / "model-traces").glob("*.json"))
    observed_shas, proposed_classes = set(), Counter()
    for file in traces:
        match = TRACE_NAME.fullmatch(file.name)
        if match is None:
            raise ValueError("Unexpected model trace filename")
        sha = match.group(1)
        if sha not in groups_by_sha or sha in observed_shas:
            raise ValueError("Duplicate/unrecognized Qwen response trace")
        observed_shas.add(sha)
        raw = json.loads(file.read_text(encoding="utf-8"))
        tele = raw["telemetry"]
        if (tele["document_sha256"] != sha or tele["model_sha256"] != MODEL_SHA256
                or tele["prompt_version"] != PROMPT_VERSION
                or tele["provider"] != "local-llama.cpp"):
            raise ValueError("Model prompt, document or provider trace mismatch")
        request = json.loads(raw["request"]["messages"][-1]["content"])
        if request["document_sha256"] != sha:
            raise ValueError("Request payload document identity mismatch")
        proposed_classes[raw["proposal"]["kind"]] += 1
    scored_groups = {}
    for kind in ("known", "unseen"):
        records_for_group = [r for r in records if groups_by_sha[r["input_sha256"]] == kind]
        scored_groups[kind] = {
            "total": len(records_for_group),
            "classification_correct": sum(r.get("classification_correct") is True
                                          for r in records_for_group),
            "eligible": sum(r.get("eligible") is True for r in records_for_group),
            "false_eligible": sum(r.get("false_eligible") is True for r in records_for_group),
            "failed": sum("error" in r for r in records_for_group),
            "unknown_classes": sum(r.get("predicted_kind") == "unknown"
                                   for r in records_for_group),
        }

    correct = sum(r.get("classification_correct") is True for r in records)
    eligible = sum(r.get("eligible") is True for r in records)
    false_eligible = sum(r.get("false_eligible") is True for r in records)
    errors = sum("error" in r for r in records)
    if (round(correct / 12, 6) != selected["classification_accuracy"]
            or eligible != selected["eligible_documents"]
            or false_eligible != selected["false_eligible_documents"]
            or errors != selected["failures"]):
        raise ValueError("Per-document results do not reconcile to scored summary")
    executed = runtime_gate(len(records), len(observed_shas), errors, false_eligible,
                            scored_groups["unseen"]["eligible"], selected["citation_validity"],
                            selected["semantic_evidence_validity"])
    return {
        "schema_version": "1.0",
        "evidence_type": "NEW_REAL_QWEN_INFERENCE_ON_REUSED_SYNTHETIC_DEVELOPMENT_CORPUS",
        "dataset_is_untouched_holdout": False,
        "dataset_is_independently_sourced_supplier_benchmark": False,
        "corpus_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "source_commit": run["source"].get("git_commit"),
        "pinned_model_sha256": MODEL_SHA256,
        "prompt_version": PROMPT_VERSION,
        "real_original_traces": len(observed_shas),
        "evaluated_documents": len(records),
        "raw_class_proposals": dict(sorted(proposed_classes.items())),
        "correct_classifications": correct,
        "eligible_for_explicit_human_review": eligible,
        "false_eligible": false_eligible,
        "request_or_parser_failures": errors,
        "citation_validity": selected["citation_validity"],
        "semantic_evidence_validity": selected["semantic_evidence_validity"],
        "eligible_critical_quality": selected["eligible_critical_quality"],
        "group_metrics": scored_groups,
        "bounded_runtime_execution_gate_met": executed,
        "synthetic_development_quality_policy_met": bool(executed and selected["policy_gate_met"]),
        "qwen_general_quality_accepted": False,
        "historical_original_benchmark": "3/36 correct, 0/36 eligible; different source/prompt/population",
        "limits": [
            "Synthetic development corpus previously used for source-safety tests, not an untouched holdout",
            "Zero successful eligible examples is not perfect critical-field precision",
            "Raw Qwen performance must not be presented as real supplier generalization",
            "Model and runtime are local-loopback only; no production host deployment",
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--evaluation", required=True, type=Path)
    ap.add_argument("--harness", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    a = ap.parse_args()
    if a.output.exists():
        raise FileExistsError("Refusing to overwrite earlier model result")
    result = summarize(a.manifest, a.evaluation, a.harness)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True, indent=2))
    if not result["bounded_runtime_execution_gate_met"]:
        raise AssertionError("Real Qwen development inference runtime/safety gate NOT MET")
    # A quality failure stays in the evidence; never silently turn CI success into model PASS.


if __name__ == "__main__":
    main()
