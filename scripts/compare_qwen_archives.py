"""Read-only paired comparison of original Qwen synthetic-development CI ZIP archives.

No model inference, network access, supplier-general claims or replay of results.
All reported metrics are independently reconciled against the original scored
records, original PDF hashes and raw model responses before comparison.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
from zipfile import BadZipFile, ZipFile

MANIFEST = "qwen-dev-corpus/manifest.json"
SUMMARY = "qwen-dev-run/evaluation/summary.json"
HARNESS = "qwen-dev-run/harness.json"
REPORT = "qwen-dev-report.json"
CASE_ROOT = "qwen-dev-run/evaluation/documents/local-llm/"
TRACE_ROOT = "qwen-dev-run/model-traces/"
PDF_ROOT = "qwen-dev-corpus/documents/"
TRACE = re.compile(r"([a-f0-9]{64})-[0-9]+\.json\Z")
CASE = re.compile(r"[0-9]{4}-repeat-0\.json\Z")
HASH = re.compile(r"[a-f0-9]{64}\Z")
FIELD_NAMES = {"document_id", "purchase_order_id", "supplier_id", "currency",
               "document_date", "subtotal", "tax", "total"}
LINE_NAMES = {"sku", "quantity", "unit_price", "net_amount", "tax_rate"}
OTHER = {"qwen-dev-run/server.log", "qwen-dev-run/server-resource-timeline.jsonl",
         "qwen-dev-run/evaluation/policy-before-run.json"}


class EvidenceError(ValueError):
    """The archived evidence does not satisfy the paired-evaluation contract."""


def require(condition: bool, message: str):
    if not condition:
        raise EvidenceError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(z: ZipFile, name: str) -> dict:
    try:
        value = json.loads(z.read(name))
    except (KeyError, UnicodeError, ValueError, TypeError) as exc:
        raise EvidenceError("Missing or invalid original JSON: " + name) from exc
    require(isinstance(value, dict), "Original JSON must be an object: " + name)
    return value


def allowed(name: str) -> bool:
    if not name or name.startswith("/") or "\\" in name or "\x00" in name:
        return False
    if any(part in ("", ".", "..") for part in name.split("/")):
        return False
    if name in {MANIFEST, SUMMARY, HARNESS, REPORT} | OTHER:
        return True
    if name.startswith(PDF_ROOT):
        return bool(re.fullmatch(r"[a-zA-Z0-9_.-]+\.pdf", name.removeprefix(PDF_ROOT)))
    if name.startswith(CASE_ROOT):
        return bool(CASE.fullmatch(name.removeprefix(CASE_ROOT)))
    if name.startswith(TRACE_ROOT):
        return bool(TRACE.fullmatch(name.removeprefix(TRACE_ROOT)))
    return False


def inventory(z: ZipFile) -> set[str]:
    infos = z.infolist()
    names = [i.filename for i in infos]
    require(len(infos) <= 64 and len(names) == len(set(names)), "Excess or duplicate ZIP members")
    require(all(allowed(n) for n in names), "Unsafe/unexpected ZIP path")
    require(all(not i.is_dir() and i.file_size <= 2_097_152 for i in infos)
            and sum(i.file_size for i in infos) <= 8_388_608,
            "ZIP member exceeds size/type limit")
    require(z.testzip() is None, "Original ZIP CRC failed")
    return set(names)


def truth_by_hash(z: ZipFile, names: set[str], manifest: dict) -> dict:
    specs = manifest.get("documents")
    require(manifest.get("generator_version") == "independent-node-pdf-writer-1.0"
            and isinstance(specs, list) and len(specs) == 12,
            "Original synthetic corpus identity/count mismatch")
    groups = Counter()
    truths = {}
    paths = set()
    for spec in specs:
        require(isinstance(spec, dict), "Invalid document manifest entry")
        path, digest = spec.get("path"), spec.get("sha256")
        require(isinstance(path, str) and path.startswith("documents/")
                and allowed("qwen-dev-corpus/" + path)
                and isinstance(digest, str) and HASH.fullmatch(digest)
                and digest not in truths and path not in paths,
                "Invalid/duplicated original PDF identity")
        entry = "qwen-dev-corpus/" + path
        require(entry in names and sha256(z.read(entry)) == digest,
                "Original PDF missing or failed source SHA-256")
        fields, lines = spec.get("expected_fields"), spec.get("expected_lines")
        require(isinstance(fields, dict) and set(fields) == FIELD_NAMES
                and isinstance(lines, list) and len(lines) == 1
                and isinstance(lines[0], dict) and set(lines[0]) == LINE_NAMES,
                "Source truth contract changed")
        require(spec.get("contract_group") in ("known", "unseen"),
                "Unknown synthetic source group")
        groups[spec["contract_group"]] += 1
        paths.add(path)
        truths[digest] = spec
    require(groups == {"known": 6, "unseen": 6}
            and {x for x in names if x.startswith(PDF_ROOT)} ==
            {"qwen-dev-corpus/" + p for p in paths},
            "Unmatched original source PDFs")
    return truths


def score_case(row: dict, spec: dict) -> dict:
    digest = spec["sha256"]
    extraction = row.get("extraction")
    require(row.get("input_sha256") == digest and row.get("input_path") == spec["path"]
            and row.get("expected_kind") == spec["expected_kind"],
            "Scored case input/truth identity differs from source manifest")
    require(isinstance(extraction, dict) and extraction.get("document_sha256") == digest,
            "Scored extraction does not identify original PDF")
    kind = row.get("predicted_kind")
    require(isinstance(kind, str) and kind == extraction.get("kind")
            and row.get("classification_correct") is (kind == spec["expected_kind"]),
            "Case classification score conflicts with actual extracted kind")
    expected = dict(spec["expected_fields"])
    expected.update({f"lines[{i}].{k}": v for i, line in enumerate(spec["expected_lines"])
                     for k, v in line.items()})
    comparisons = row.get("comparisons")
    require(isinstance(comparisons, list) and len(comparisons) == len(expected),
            "Incomplete or extra field comparisons")
    seen = set()
    totals = Counter()
    for c in comparisons:
        require(isinstance(c, dict) and isinstance(c.get("field"), str),
                "Invalid field comparison")
        key = c["field"]
        require(key in expected and key not in seen, "Unknown/duplicate scored field")
        seen.add(key)
        actual, target = c.get("actual"), expected[key]
        if key.startswith("lines["):
            match = re.fullmatch(r"lines\[([0-9]+)\]\.([a-z_]+)", key)
            require(match is not None, "Malformed line score key")
            lines = extraction.get("line_items")
            require(isinstance(lines, list), "Missing extracted line items")
            idx = int(match.group(1))
            entry = (lines[idx].get("fields", {}).get(match.group(2)) or {}) if idx < len(lines) else {}
        else:
            entry = (extraction.get("fields") or {}).get(key) or {}
        require(isinstance(entry, dict) and actual == entry.get("normalized"),
                "Scored field actual differs from extraction")
        require(c.get("expected") == target
                and c.get("present_in_truth") is (target is not None)
                and c.get("correct") is (actual == target)
                and c.get("abstained") is (actual is None),
                "Field correctness/abstention disagrees with original truth")
        require(type(c.get("critical")) is bool, "Missing critical field flag")
        totals["fields_total"] += 1
        totals["fields_correct"] += actual == target
        totals["present_fields_total"] += target is not None
        totals["present_fields_correct"] += target is not None and actual == target
        totals["required_abstentions"] += target is None
        totals["correct_required_abstentions"] += target is None and actual is None
        totals["critical_fields_total"] += c["critical"]
        totals["critical_fields_abstained"] += c["critical"] and actual is None
    require(seen == set(expected), "Missing expected field")
    for key in ("fields_correct", "fields_total", "present_fields_total",
                "present_fields_correct", "required_abstentions", "correct_required_abstentions",
                "critical_fields_total", "critical_fields_abstained"):
        require(row.get(key) == totals[key], "Forged case counter: " + key)
    for key in ("eligible", "false_eligible"):
        require(type(row.get(key)) is bool, "Invalid/missing decision: " + key)
    require(not row["false_eligible"] or row["eligible"],
            "False eligibility cannot occur outside eligible set")
    citations, valid = row.get("citation_total"), row.get("citation_valid")
    require(type(citations) is int and type(valid) is int and 0 <= valid <= citations,
            "Invalid original citation counts")
    totals["citation_total"] = citations
    totals["citation_valid"] = valid
    totals["classification_correct"] = kind == spec["expected_kind"]
    totals["eligible"] = row["eligible"]
    totals["false_eligible"] = row["false_eligible"]
    return {"document_key": spec["document_key"], "input_sha256": digest,
            "group": spec["contract_group"], "expected_kind": spec["expected_kind"],
            "kind": kind, "totals": dict(totals)}


def original(path: Path, expected_zip_sha256: str | None = None) -> dict:
    file_digest = sha256(path.read_bytes())
    if expected_zip_sha256 is not None:
        require(HASH.fullmatch(expected_zip_sha256) is not None
                and expected_zip_sha256 == file_digest,
                "Pinned original ZIP digest mismatch")
    try:
        with ZipFile(path) as z:
            names = inventory(z)
            manifest, summary, harness, report = (read_json(z, n)
                                                  for n in (MANIFEST, SUMMARY, HARNESS, REPORT))
            truths = truth_by_hash(z, names, manifest)
            source = summary.get("source", {})
            dataset = summary.get("dataset", {})
            require(isinstance(source, dict) and isinstance(dataset, dict)
                    and dataset.get("available_test_documents") == 12
                    and dataset.get("evaluated_test_documents") == 12
                    and source.get("git_commit") == report.get("source_commit"),
                    "Scored source/denominator does not match original")
            require(harness.get("model_sha256") == report.get("pinned_model_sha256")
                    and isinstance(harness.get("model_sha256"), str)
                    and HASH.fullmatch(harness["model_sha256"]) is not None
                    and report.get("corpus_manifest_sha256") == sha256(z.read(MANIFEST)),
                    "Pinned model/corpus provenance mismatch")
            profiles = summary.get("profiles")
            require(isinstance(profiles, dict) and "local-llm" in profiles,
                    "Local original evaluation profile missing")
            aggregate = profiles["local-llm"]
            record_names = sorted(n for n in names if n.startswith(CASE_ROOT))
            require(len(record_names) == 12, "Expected 12 original scored case files")
            scored = {}
            for name in record_names:
                row = read_json(z, name)
                pdf_id = row.get("input_sha256")
                require(pdf_id in truths and pdf_id not in scored,
                        "Duplicate/unrecognized scored PDF")
                scored[pdf_id] = score_case(row, truths[pdf_id])
            require(set(scored) == set(truths), "Incomplete scored document coverage")
            trace_names = sorted(n for n in names if n.startswith(TRACE_ROOT))
            require(len(trace_names) == 12, "Missing original model traces")
            proposals = {}
            prompt_hashes = set()
            raw_classes = Counter()
            for name in trace_names:
                match = TRACE.fullmatch(name.removeprefix(TRACE_ROOT))
                require(match is not None and match.group(1) in truths
                        and match.group(1) not in proposals, "Duplicate or unrecognized raw trace")
                pdf_id = match.group(1)
                raw = read_json(z, name)
                tele, proposal, response = (raw.get(k) for k in ("telemetry", "proposal", "response"))
                require(isinstance(tele, dict) and isinstance(proposal, dict)
                        and isinstance(response, dict), "Missing model trace fields")
                require(tele.get("document_sha256") == pdf_id
                        and tele.get("model_sha256") == harness["model_sha256"]
                        and tele.get("prompt_version") == report.get("prompt_version")
                        and tele.get("provider") == "local-llama.cpp"
                        and isinstance(tele.get("prompt_sha256"), str)
                        and HASH.fullmatch(tele["prompt_sha256"]) is not None,
                        "Original model trace provenance mismatch")
                prompt_hashes.add(tele["prompt_sha256"])
                try:
                    decoded = json.loads(response["choices"][0]["message"]["content"])
                except (KeyError, IndexError, TypeError, ValueError) as exc:
                    raise EvidenceError("Unparseable original model response") from exc
                require(decoded == proposal and isinstance(proposal.get("kind"), str)
                        and isinstance(proposal.get("fields"), dict)
                        and set(proposal["fields"]) == FIELD_NAMES,
                        "Original response contradicts raw proposal/schema")
                raw_classes[proposal["kind"]] += 1
                proposals[pdf_id] = {"kind": proposal["kind"],
                                     "scalar_ids": sum(v is not None
                                                       for v in proposal["fields"].values())}
            require(len(prompt_hashes) == 1 and set(proposals) == set(truths),
                    "Original model prompt or trace coverage inconsistent")
            totals = Counter()
            for item in scored.values():
                totals.update(item["totals"])
            den = aggregate.get("denominators")
            require(isinstance(den, dict), "Original evaluation denominators missing")
            for key in ("fields_correct", "fields_total", "present_fields_correct",
                        "present_fields_total", "required_abstentions",
                        "correct_required_abstentions", "critical_fields_abstained",
                        "critical_fields_total", "citation_total", "citation_valid"):
                require(den.get(key) == totals[key], "Forged aggregate metric: " + key)
            require(aggregate.get("documents") == 12
                    and aggregate.get("eligible_documents") == totals["eligible"]
                    and aggregate.get("false_eligible_documents") == totals["false_eligible"]
                    and abs(aggregate.get("classification_accuracy", -1)
                            - totals["classification_correct"] / 12) < 1e-6,
                    "Original summary differs from scored case metrics")
            require(report.get("evaluated_documents") == 12
                    and report.get("real_original_traces") == 12
                    and report.get("correct_classifications") == totals["classification_correct"]
                    and report.get("eligible_for_explicit_human_review") == totals["eligible"]
                    and report.get("false_eligible") == totals["false_eligible"]
                    and report.get("raw_class_proposals") == dict(raw_classes)
                    and report.get("dataset_is_untouched_holdout") is False
                    and report.get("qwen_general_quality_accepted") is False
                    and report.get("synthetic_development_quality_policy_met")
                    is bool(aggregate.get("policy_gate_met")),
                    "Original development report contradicts scored case results")
            return {"zip_sha256": file_digest, "source_commit": source["git_commit"],
                    "manifest_sha256": sha256(z.read(MANIFEST)),
                    "model_sha256": harness["model_sha256"],
                    "prompt_sha256": next(iter(prompt_hashes)),
                    "prompt_version": report["prompt_version"],
                    "scored": scored, "proposals": proposals, "totals": dict(totals),
                    "runtime_gate": report.get("bounded_runtime_execution_gate_met"),
                    "quality_gate": report.get("synthetic_development_quality_policy_met")}
    except (BadZipFile, OSError, OverflowError, RuntimeError) as exc:
        raise EvidenceError("Original ZIP cannot be safely opened/verified") from exc


def compare(baseline: Path, candidate: Path, *,
            baseline_sha256: str | None = None,
            candidate_sha256: str | None = None) -> dict:
    old, new = original(baseline, baseline_sha256), original(candidate, candidate_sha256)
    require(old["manifest_sha256"] == new["manifest_sha256"]
            and set(old["scored"]) == set(new["scored"]),
            "Refusing to compare different document populations")
    require(old["model_sha256"] == new["model_sha256"],
            "Pinned model differs; cannot call this a prompt-only comparison")
    measures = {"correct_classifications": "classification_correct",
                "eligible_documents": "eligible", "fields_correct": "fields_correct",
                "critical_abstentions": "critical_fields_abstained",
                "false_eligible": "false_eligible"}
    regressions = []
    for label, key in measures.items():
        x, y = old["totals"][key], new["totals"][key]
        adverse = (y > x) if key in ("critical_fields_abstained", "false_eligible") else (y < x)
        if adverse:
            regressions.append(f"{label}: {x} -> {y}")
    cases = []
    for pdf_id in sorted(old["scored"]):
        before, after = old["scored"][pdf_id], new["scored"][pdf_id]
        require(before["expected_kind"] == after["expected_kind"]
                and before["group"] == after["group"],
                "Source truth differs despite identical original PDF bytes")
        b, a = old["proposals"][pdf_id], new["proposals"][pdf_id]
        cases.append({"pdf_sha256": pdf_id, "document_key": before["document_key"],
                      "group": before["group"], "expected_kind": before["expected_kind"],
                      "raw_kind_before": b["kind"], "raw_kind_after": a["kind"],
                      "kind_before": before["kind"], "kind_after": after["kind"],
                      "fields_correct_before": before["totals"]["fields_correct"],
                      "fields_correct_after": after["totals"]["fields_correct"],
                      "critical_abstentions_before": before["totals"]["critical_fields_abstained"],
                      "critical_abstentions_after": after["totals"]["critical_fields_abstained"],
                      "raw_scalar_ids_before": b["scalar_ids"],
                      "raw_scalar_ids_after": a["scalar_ids"]})
    public_keys = ("zip_sha256", "source_commit", "manifest_sha256", "model_sha256",
                   "prompt_sha256", "prompt_version", "totals", "runtime_gate", "quality_gate")
    return {"schema_version": "1.0",
            "scope": "reused synthetic development PDF corpus, NOT supplier acceptance",
            "model_generalization_accepted": False,
            "same_pdf_cohort": True, "same_pinned_gguf": True,
            "baseline": {k: old[k] for k in public_keys},
            "candidate": {k: new[k] for k in public_keys},
            "case_comparison": cases,
            "nonregression_passed": not regressions,
            "nonregression_failures": regressions,
            "limitations": [
                "Prior synthetic development documents are already seen, not a final holdout.",
                "Eligibility/citation outcomes are source-checked, not independently reprocessed PDFs.",
                "Same corpus/model does not prove that prompt words caused all output differences.",
                "Nonregression is a local comparison, not full P04 model-quality acceptance.",
            ]}


def write_once(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as output:
        json.dump(value, output, sort_keys=True, indent=2)
        output.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--baseline-sha256")
    parser.add_argument("--candidate-sha256")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-nonregression", action="store_true")
    args = parser.parse_args(argv)
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError("Original comparison receipt already exists")
    report = compare(args.baseline, args.candidate,
                     baseline_sha256=args.baseline_sha256,
                     candidate_sha256=args.candidate_sha256)
    write_once(args.output, report)
    print(json.dumps({"baseline": report["baseline"]["source_commit"],
                      "candidate": report["candidate"]["source_commit"],
                      "nonregression_passed": report["nonregression_passed"],
                      "failures": report["nonregression_failures"]}, sort_keys=True))
    return int(args.require_nonregression and not report["nonregression_passed"])


if __name__ == "__main__":
    raise SystemExit(main())
