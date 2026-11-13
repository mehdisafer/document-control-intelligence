"""Held-out, source-linked evaluation using actual parsing and inference.

The policy is declared in code before running evaluation. It applies to this
synthetic benchmark, not to supplier populations. 'Eligible' means a candidate
for explicit human acceptance; the application never auto-approves a document.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import resource
import statistics
import subprocess
import sys
import time

from .extraction import LINE_KEYS, SCALAR_KEYS, extract, validate_evidence
from .models import Extraction, ParsedDocument
from .llm import ModelUnavailable
from .local_model import ModelError
from .parsing import ParseError, parse_document, runtime_version
from .rules import check_document


EVALUATION_POLICY = {
    "version": "synthetic-heldout-1.0",
    "citation_validity_min": 1.0,
    "semantic_evidence_validity_min": 1.0,
    "false_eligible_documents_max": 0,
    "eligible_critical_quality_min": 1.0,
    "eligible_coverage_min": 0.5,
    "rationale": "No incorrect critical values may be proposed as eligible; at least half of the bounded synthetic benchmark should avoid field repair. Human approval is still mandatory. These are development targets, not service certification.",
    "applies_to": "Full untouched final split; subset and incomplete runs cannot satisfy the benchmark gate.",
}
KINDS = ("purchase_order", "delivery_note", "invoice")


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _critical(kind: str) -> tuple[set[str], set[str]]:
    scalar = {"document_id", "purchase_order_id", "supplier_id", "currency"}
    lines = {"sku", "quantity"}
    if kind != "delivery_note":
        scalar |= {"subtotal", "tax", "total"}
        lines |= {"unit_price", "net_amount", "tax_rate"}
    return scalar, lines


def _citation_exists(parsed: ParsedDocument, evidence) -> bool:
    page = next((page for page in parsed.pages if page.number == evidence.page), None)
    if page is None or not 0 <= evidence.start < evidence.end <= len(page.text):
        return False
    if page.text[evidence.start:evidence.end] != evidence.quote:
        return False
    if evidence.bbox is not None:
        box = evidence.bbox
        if not all(math.isfinite(value) for value in box):
            return False
        if not (0 <= box[0] < box[2] <= page.width + 1 and 0 <= box[1] < box[3] <= page.height + 1):
            return False
        words = [word for word in page.words if word.start < evidence.end and word.end > evidence.start]
        if not words:
            return False
        actual = (min(w.bbox[0] for w in words), min(w.bbox[1] for w in words), max(w.bbox[2] for w in words), max(w.bbox[3] for w in words))
        if any(abs(left - right) > 0.1 for left, right in zip(box, actual)):
            return False
    return True


def score_document(truth: dict, parsed: ParsedDocument, extraction: Extraction) -> dict:
    """Score real outputs against truth; preserve denominators and abstentions."""
    expected = dict(truth["expected_fields"])
    for key in truth.get("ambiguous_fields", []):
        expected[key] = None
    expected_kind = truth["expected_kind"]
    critical_scalars, critical_line_keys = _critical(expected_kind)
    comparisons = []
    for key in SCALAR_KEYS:
        field = extraction.fields.get(key)
        actual = field.normalized if field and field.status == "supported" else None
        target = expected.get(key)
        comparisons.append({"field": key, "expected": target, "actual": actual,
                            "correct": actual == target, "critical": key in critical_scalars,
                            "abstained": actual is None, "present_in_truth": target is not None})
    actual_lines: dict[str, list] = {}
    for index, line in enumerate(extraction.line_items):
        sku_field = line.fields.get("sku")
        sku = sku_field.normalized if sku_field and sku_field.status == "supported" else f"__unsupported_sku_{index}"
        actual_lines.setdefault(sku, []).append(line)
    expected_skus = set()
    for line_index, line_truth in enumerate(truth["expected_lines"]):
        sku = line_truth["sku"]
        expected_skus.add(sku)
        matches = actual_lines.get(sku, [])
        line = matches[0] if len(matches) == 1 else None
        for key in LINE_KEYS:
            field = line.fields.get(key) if line else None
            actual = field.normalized if field and field.status == "supported" else None
            target = line_truth.get(key)
            comparisons.append({"field": f"lines[{line_index}].{key}", "expected": target, "actual": actual,
                                "correct": actual == target, "critical": key in critical_line_keys,
                                "abstained": actual is None, "present_in_truth": target is not None})
    extra_lines = sum(len(lines) for sku, lines in actual_lines.items() if sku not in expected_skus)
    duplicate_lines = sum(max(0, len(lines) - 1) for lines in actual_lines.values())
    all_fields = list(extraction.fields.values()) + [field for line in extraction.line_items for field in line.fields.values()]
    citations = [evidence for field in all_fields for evidence in field.evidence]
    citation_valid = sum(_citation_exists(parsed, evidence) for evidence in citations)
    checked = validate_evidence(parsed, extraction)
    verified_fields = list(checked.fields.values()) + [field for line in checked.line_items for field in line.fields.values()]
    supported = sum(field.status == "supported" for field in all_fields)
    semantic_valid = sum(original.status == "supported" and validated.status == "supported" and original.normalized == validated.normalized for original, validated in zip(all_fields, verified_fields))
    business = check_document(extraction)
    critical = [item for item in comparisons if item["critical"]]
    complete_truth = all(item["present_in_truth"] for item in critical)
    critical_exact = (extraction.kind == expected_kind and complete_truth and all(item["correct"] for item in critical)
                      and extra_lines == 0 and duplicate_lines == 0 and len(extraction.line_items) == len(truth["expected_lines"]))
    proof_complete = citation_valid == len(citations) and semantic_valid == supported
    eligible = business.decision == "eligible"
    false_eligible = eligible and (not critical_exact or not proof_complete)
    return {
        "expected_kind": expected_kind, "predicted_kind": extraction.kind,
        "classification_correct": extraction.kind == expected_kind,
        "fields_total": len(comparisons), "fields_correct": sum(item["correct"] for item in comparisons),
        "present_fields_total": sum(item["present_in_truth"] for item in comparisons),
        "present_fields_correct": sum(item["correct"] and item["present_in_truth"] for item in comparisons),
        "required_abstentions": sum(not item["present_in_truth"] for item in comparisons),
        "correct_required_abstentions": sum(item["correct"] and not item["present_in_truth"] for item in comparisons),
        "critical_fields_total": len(critical), "critical_fields_abstained": sum(item["abstained"] for item in critical),
        "critical_document_exact": critical_exact,
        "citation_total": len(citations), "citation_valid": citation_valid,
        "supported_fields_total": supported, "semantically_supported_fields": semantic_valid,
        "eligible": eligible, "false_eligible": false_eligible,
        "eligible_and_correct": eligible and critical_exact and proof_complete,
        "business_decision": business.decision,
        "extra_lines": extra_lines, "duplicate_lines": duplicate_lines,
        "comparisons": comparisons,
        "business_check": business.model_dump(mode="json"),
    }


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def _percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    return round(values[max(0, math.ceil(len(values) * quantile) - 1)], 6)


def summarize(records: list[dict], *, full_split: bool = True) -> dict:
    """Aggregate with explicit numerators; failures remain in the denominator."""
    count = len(records)
    sums = Counter()
    metrics = ("fields_total", "fields_correct", "present_fields_total", "present_fields_correct", "required_abstentions", "correct_required_abstentions", "critical_fields_total", "critical_fields_abstained", "citation_total", "citation_valid", "supported_fields_total", "semantically_supported_fields")
    for record in records:
        sums.update({key: record.get(key, 0) for key in metrics})
    confusion = {actual: {predicted: 0 for predicted in (*KINDS, "unknown")} for actual in KINDS}
    for record in records:
        confusion[record["expected_kind"]][record.get("predicted_kind", "unknown")] += 1
    classes = {}
    for kind in KINDS:
        tp = confusion[kind][kind]
        expected_count = sum(confusion[kind].values())
        predicted_count = sum(confusion[row][kind] for row in KINDS)
        classes[kind] = {"precision": _ratio(tp, predicted_count), "recall": _ratio(tp, expected_count), "support": expected_count}
    relevant = [value for value in classes.values() if value["support"] > 0]
    eligible = sum(bool(record.get("eligible")) for record in records)
    false_eligible = sum(bool(record.get("false_eligible")) for record in records)
    eligible_correct = sum(bool(record.get("eligible_and_correct")) for record in records)
    coverage = _ratio(eligible, count)
    quality = _ratio(eligible_correct, eligible)
    citation_ratio = _ratio(sums["citation_valid"], sums["citation_total"])
    semantic_ratio = _ratio(sums["semantically_supported_fields"], sums["supported_fields_total"])
    latency = [float(record["elapsed_seconds"]) for record in records if "elapsed_seconds" in record]
    stage_keys = sorted({key for record in records for key in record.get("timings", {}) if key.endswith("seconds")})
    result = {
        "documents": count, "failures": sum("error" in record for record in records), "denominators": dict(sums),
        "classification_accuracy": _ratio(sum(bool(record.get("classification_correct")) for record in records), count),
        "classification_confusion": confusion, "classification_by_class": classes,
        "classification_macro_precision": round(statistics.mean(value["precision"] or 0 for value in relevant), 6) if relevant else None,
        "classification_macro_recall": round(statistics.mean(value["recall"] or 0 for value in relevant), 6) if relevant else None,
        "normalized_field_accuracy_including_required_abstention": _ratio(sums["fields_correct"], sums["fields_total"]),
        "normalized_present_field_accuracy": _ratio(sums["present_fields_correct"], sums["present_fields_total"]),
        "required_abstention_accuracy": _ratio(sums["correct_required_abstentions"], sums["required_abstentions"]),
        "critical_document_exact_match": _ratio(sum(bool(record.get("critical_document_exact")) for record in records), count),
        "unexpected_line_rows": sum(record.get("extra_lines", 0) for record in records),
        "duplicate_line_rows": sum(record.get("duplicate_lines", 0) for record in records),
        "critical_field_abstention_rate": _ratio(sums["critical_fields_abstained"], sums["critical_fields_total"]),
        "citation_validity": citation_ratio,
        "semantic_evidence_validity": semantic_ratio,
        "eligible_documents": eligible, "eligible_coverage": coverage, "review_rate": _ratio(count - eligible, count),
        "eligible_critical_quality": quality, "false_eligible_documents": false_eligible,
        "false_eligible_rate_among_eligible": _ratio(false_eligible, eligible),
        "false_eligible_rate_all_documents": _ratio(false_eligible, count),
        "latency_seconds": {"median": round(statistics.median(latency), 6) if latency else None, "p95_nearest_rank": _percentile(latency, 0.95), "max": max(latency) if latency else None},
        "stage_latency_seconds": {key: {"mean": round(statistics.mean(float(r["timings"][key]) for r in records if key in r.get("timings", {})), 6), "p95_nearest_rank": _percentile([float(r["timings"][key]) for r in records if key in r.get("timings", {})], 0.95)} for key in stage_keys},
        "full_final_split": full_split,
        "policy": EVALUATION_POLICY,
        "policy_gate_met": bool(full_split and count and not any("error" in record for record in records)
                                and citation_ratio == 1.0 and semantic_ratio == 1.0 and false_eligible == 0
                                and quality == 1.0 and coverage is not None and coverage >= EVALUATION_POLICY["eligible_coverage_min"]),
        "eligibility_meaning": "Eligible candidates still require explicit human approval; this is not an observed automatic publication rate.",
    }
    return result


def _hardware() -> dict:
    cpu_model = platform.processor()
    memory_total_kib = None
    if Path("/proc/cpuinfo").is_file():
        cpu_model = next((line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines() if line.startswith("model name")), cpu_model)
    if Path("/proc/meminfo").is_file():
        memory_total_kib = int(Path("/proc/meminfo").read_text().splitlines()[0].split()[1])
    return {"platform": platform.platform(), "python": sys.version, "logical_cpus": os.cpu_count(), "cpu_model": cpu_model,
            "host_memory_total_kib": memory_total_kib, "gpu_used": False,
            "execution_note": "Isolated workspace execution; CPU availability may be shared with other tasks. No machine-exclusive benchmark claim.",
            "cgroup_limits": {name: Path(f"/sys/fs/cgroup/{name}").read_text().strip() for name in ("cpu.max", "memory.max") if Path(f"/sys/fs/cgroup/{name}").is_file()}}


def _source_identity() -> dict:
    root = Path(__file__).resolve().parents[2]
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = None, True
    hashes = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted((root / "src/dci").glob("*.py"))}
    return {"git_commit": commit, "working_tree_dirty": dirty, "source_sha256": hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(), "source_files": hashes}


def _validate_splits(manifest: dict) -> None:
    ownership = {"family_id": {}, "layout": {}}
    for document in manifest["documents"]:
        split = document["split"]
        if split not in {"train", "tune", "test"}:
            continue
        for key, seen in ownership.items():
            value = document[key]
            if value in seen and seen[value] != split:
                raise ValueError(f"Split leakage: {key} {value!r} occurs in more than one split")
            seen[value] = split


def _failed_score(truth: dict, error: dict) -> dict:
    """Unavailable computation earns no correct fields; it is not an abstention success."""
    scalar, line_keys = _critical(truth["expected_kind"])
    expected = dict(truth["expected_fields"])
    for field in truth.get("ambiguous_fields", []):
        expected[field] = None
    total = len(SCALAR_KEYS) + len(LINE_KEYS) * len(truth["expected_lines"])
    present = sum(expected.get(key) is not None for key in SCALAR_KEYS) + sum(line.get(key) is not None for line in truth["expected_lines"] for key in LINE_KEYS)
    critical = len(scalar) + len(line_keys) * len(truth["expected_lines"])
    return {"error": error, "predicted_kind": "unknown", "fields_total": total,
            "present_fields_total": present, "required_abstentions": total - present,
            "critical_fields_total": critical, "critical_fields_abstained": critical,
            "eligible": False, "false_eligible": False, "business_decision": "unavailable"}


def evaluate_manifest(
    manifest_path: Path,
    output_dir: Path,
    *,
    profiles: tuple[str, ...] = ("baseline", "local-linear"),
    model_path: Path | None = None,
    llm_config=None,
    max_documents: int | None = None,
    repeats: int = 1,
    parser_timeout_seconds: float = 45,
) -> dict:
    """Evaluate only the final split; repetitions measure output variability.

    A subset is clearly incomplete and cannot meet the policy gate. Parsing is
    shared once per input; profile timing includes that same measured parse cost.
    """
    if not profiles or len(set(profiles)) != len(profiles) or not set(profiles) <= {"baseline", "local-linear", "local-llm"}:
        raise ValueError("Select distinct supported evaluation profiles")
    if not 1 <= repeats <= 10 or (max_documents is not None and max_documents < 1):
        raise ValueError("Invalid evaluation budget")
    manifest_path = Path(manifest_path).resolve(strict=True)
    root = manifest_path.parent
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    _validate_splits(manifest)
    all_test = [document for document in manifest["documents"] if document["split"] == "test"]
    if not all_test:
        raise ValueError("The corpus has no final test split")
    selected = all_test[:max_documents] if max_documents is not None else all_test
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Evaluation output is not empty; preserve it and choose a new run directory")
    output.mkdir(parents=True, exist_ok=True)
    _write_json(output / "policy-before-run.json", EVALUATION_POLICY)
    _write_json(output / "manifest.json", manifest)
    source = _source_identity()
    hardware = _hardware()
    started = time.perf_counter()
    own_before = resource.getrusage(resource.RUSAGE_SELF)
    children_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    records = {profile: [] for profile in profiles}
    signatures: dict[str, dict[str, set[str]]] = {profile: {} for profile in profiles}
    for index, truth in enumerate(selected):
        input_path = (root / truth["path"]).resolve(strict=True)
        if not input_path.is_relative_to(root):
            raise ValueError("Manifest document escapes its corpus root")
        digest = hashlib.sha256(input_path.read_bytes()).hexdigest()
        if digest != truth["sha256"]:
            raise ValueError("Input PDF digest differs from the frozen manifest")
        parsed = None
        parse_error = None
        try:
            parsed = parse_document(input_path, timeout_seconds=parser_timeout_seconds, checkpoint_dir=output / "checkpoints")
            _write_json(output / "parsed" / f"{digest}.json", parsed.model_dump(mode="json"))
        except ParseError as exc:
            parse_error = {"code": exc.code, "message": str(exc)}
        for profile in profiles:
            for repeat in range(repeats):
                began = time.perf_counter()
                record = {"input_path": truth["path"], "input_sha256": digest, "family_id": truth["family_id"], "layout": truth["layout"], "scenario": truth["scenario"], "expected_kind": truth["expected_kind"], "profile": profile, "repeat": repeat}
                if parse_error:
                    # Missing output is not silently excluded from field accuracy.
                    record.update(_failed_score(truth, parse_error))
                else:
                    try:
                        extraction = extract(parsed, profile=profile, model_path=model_path, llm_config=llm_config)
                    except (ModelUnavailable, ModelError) as exc:
                        record.update(_failed_score(truth, {"code": exc.code, "message": str(exc)}))
                        record["timings"] = {**parsed.timings, "failed_inference_seconds": time.perf_counter() - began}
                        record["elapsed_seconds"] = round(parsed.timings["wall_seconds"] + time.perf_counter() - began, 6)
                        _write_json(output / "documents" / profile / f"{index:04d}-repeat-{repeat}.json", record)
                        records[profile].append(record)
                        continue
                    record.update(score_document(truth, parsed, extraction))
                    record["extraction"] = extraction.model_dump(mode="json")
                    record["timings"] = {**parsed.timings, **extraction.timings}
                    record["elapsed_seconds"] = round(parsed.timings["wall_seconds"] + time.perf_counter() - began, 6)
                    if extraction.model_version == "unavailable":
                        record["error"] = {"code": "model_unavailable", "message": ";".join(extraction.warnings)}
                    semantic_signature = {"kind": extraction.kind, "fields": {k: (f.status, f.normalized) for k, f in extraction.fields.items()}, "line_items": [{k: (f.status, f.normalized) for k, f in line.fields.items()} for line in extraction.line_items]}
                    signature = hashlib.sha256(json.dumps(semantic_signature, sort_keys=True).encode()).hexdigest()
                    signatures[profile].setdefault(digest, set()).add(signature)
                _write_json(output / "documents" / profile / f"{index:04d}-repeat-{repeat}.json", record)
                records[profile].append(record)
    elapsed = time.perf_counter() - started
    own_after = resource.getrusage(resource.RUSAGE_SELF)
    children_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    summary = {
        "schema_version": "1.0", "created_at": datetime.now(timezone.utc).isoformat(),
        "command": sys.argv, "source": source, "hardware": hardware,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "dataset": {"generator_version": manifest.get("generator_version"), "seed": manifest.get("seed"), "selected_split": "test", "available_test_documents": len(all_test), "evaluated_test_documents": len(selected), "selection": "manifest order prefix" if len(selected) < len(all_test) else "complete test split", "repeats": repeats},
        "parser_version": runtime_version(),
        "profiles": {profile: {**summarize([record for record in values if record["repeat"] == 0], full_split=len(selected) == len(all_test)),
                               "response_variability": {"repeats": repeats, "documents_with_multiple_semantic_outputs": sum(len(outputs) > 1 for outputs in signatures[profile].values()), "evaluated_documents": len(signatures[profile]), "measured": repeats > 1}} for profile, values in records.items()},
        "resources": {"wall_seconds": round(elapsed, 6), "unique_input_documents_per_second": round(len(selected) / elapsed, 6),
                      "inferences_per_second_including_shared_parse": round(len(selected) * len(profiles) * repeats / elapsed, 6),
                      "evaluator_cpu_seconds": round(own_after.ru_utime + own_after.ru_stime - own_before.ru_utime - own_before.ru_stime, 6),
                      "completed_child_cpu_seconds": round(children_after.ru_utime + children_after.ru_stime - children_before.ru_utime - children_before.ru_stime, 6),
                      "peak_evaluator_rss_kib": own_after.ru_maxrss, "peak_completed_child_rss_kib_cumulative": children_after.ru_maxrss,
                      "rss_scope": "Linux process maxima; not aggregate live memory across server and workers. A separately running LLM server is outside these evaluator maxima."},
        "cost": {"external_api_cost_usd": 0, "compute_cost_usd": None, "compute_cost_note": "CPU/RAM measured; local infrastructure and electricity were not priced or metered."},
        "limits": ["Synthetic purchasing layouts only; not a representative supplier benchmark.", "All profiles receive the same actual parsed text. OCR errors remain part of measured field quality.", "Eligibility evaluates document rules before required human approval; cross-document reconciliation is evaluated by integration/demo tests.", "Parsing is executed once per PDF and shared across profiles; comparative inference latency is separately recorded.", "No model/prompt/threshold may be tuned using these final results. A changed model requires a new untouched evaluation set."],
    }
    _write_json(output / "summary.json", summary)
    return summary
