"""Compare two original Qwen development ZIPs without model inference.

Fail closed on population/provenance mismatches. The paired result is development
evidence only: never an independent supplier holdout or full P04 acceptance.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import stat
import zipfile

MAX_ENTRIES = 128
MAX_MEMBER_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024
MAX_ARCHIVE_BYTES = 40 * 1024 * 1024
CASE_RE = re.compile(r"qwen-dev-run/evaluation/documents/local-llm/(\d{4})-repeat-0\.json\Z")
TRACE_RE = re.compile(r"qwen-dev-run/model-traces/([a-f0-9]{64})-\d+\.json\Z")
MANIFEST = "qwen-dev-corpus/manifest.json"
REPORT = "qwen-dev-report.json"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_entries(archive: zipfile.ZipFile) -> set[str]:
    infos = archive.infolist()
    if not infos or len(infos) > MAX_ENTRIES:
        raise ValueError("Missing or excessive ZIP members")
    names: set[str] = set()
    total = 0
    for item in infos:
        name = item.filename
        parts = name.split("/")
        if (
            not name or name.startswith("/") or "\\" in name
            or any(p in ("", ".", "..") for p in parts)
        ):
            raise ValueError("Unsafe or non-canonical ZIP member path")
        if name in names:
            raise ValueError("Duplicate ZIP member")
        mode = item.external_attr >> 16
        if item.is_dir() or stat.S_IFMT(mode) == stat.S_IFLNK:
            raise ValueError("Directory or symlink ZIP member")
        if item.file_size > MAX_MEMBER_BYTES:
            raise ValueError("ZIP member exceeds size limit")
        total += item.file_size
        if total > MAX_TOTAL_BYTES:
            raise ValueError("ZIP total exceeds size limit")
        names.add(name)
    if archive.testzip() is not None:
        raise ValueError("Invalid ZIP member CRC")
    return names


def _json(archive: zipfile.ZipFile, names: set[str], path: str) -> dict:
    if path not in names:
        raise ValueError("Required archive record is absent: " + path)
    try:
        obj = json.loads(archive.read(path))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Malformed JSON: " + path) from exc
    if not isinstance(obj, dict):
        raise ValueError("Expected JSON object: " + path)
    return obj


def _count(row: dict, key: str) -> int:
    value = row.get(key)
    if type(value) is not int or value < 0:
        raise ValueError("Missing, invalid or negative integer: " + key)
    return value


def inspect(archive_path: Path) -> dict:
    """Re-derive original metrics from all twelve scored PDFs and raw traces."""
    if archive_path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("ZIP archive exceeds compressed size limit")
    digest = _sha(archive_path.read_bytes())
    with zipfile.ZipFile(archive_path) as archive:
        names = _safe_entries(archive)
        report = _json(archive, names, REPORT)
        raw_manifest = archive.read(MANIFEST) if MANIFEST in names else b""
        manifest = _json(archive, names, MANIFEST)
        if (
            _sha(raw_manifest) != report.get("corpus_manifest_sha256")
            or manifest.get("generator_version") != "independent-node-pdf-writer-1.0"
            or report.get("dataset_is_untouched_holdout") is not False
            or report.get("dataset_is_independently_sourced_supplier_benchmark") is not False
            or report.get("qwen_general_quality_accepted") is not False
        ):
            raise ValueError("Untrustworthy source or acceptance provenance")
        docs = manifest.get("documents")
        if not isinstance(docs, list) or len(docs) != 12:
            raise ValueError("Expected twelve manifest documents")
        blobs: dict[str, str] = {}
        truth: dict[str, str] = {}
        groups: Counter = Counter()
        for doc in docs:
            if not isinstance(doc, dict):
                raise ValueError("Invalid manifest document")
            rel = doc.get("path")
            if (
                not isinstance(rel, str) or not rel.startswith("documents/")
                or any(p in ("", ".", "..") for p in rel.split("/"))
            ):
                raise ValueError("Unsafe PDF manifest path")
            path = "qwen-dev-corpus/" + rel
            sha = doc.get("sha256")
            if path not in names or not isinstance(sha, str) or _sha(archive.read(path)) != sha:
                raise ValueError("PDF source bytes mismatch")
            if sha in blobs:
                raise ValueError("Duplicate PDF source identity")
            blobs[sha] = path
            truth[sha] = doc.get("expected_kind")
            groups[doc.get("contract_group")] += 1
        if groups != {"known": 6, "unseen": 6}:
            raise ValueError("Unexpected development group split")
        pdf_paths = {
            n for n in names
            if n.startswith("qwen-dev-corpus/documents/") and n.endswith(".pdf")
        }
        if pdf_paths != set(blobs.values()):
            raise ValueError("Extra or missing original PDF")

        paths = sorted(n for n in names if CASE_RE.fullmatch(n))
        if len(paths) != 12:
            raise ValueError("Expected 12 scored case records")
        cases: dict[str, dict] = {}
        for path in paths:
            row = _json(archive, names, path)
            sha = row.get("input_sha256")
            if sha not in blobs or sha in cases:
                raise ValueError("Unknown or duplicated scored document")
            for key in (
                "fields_correct", "fields_total", "present_fields_correct",
                "present_fields_total", "critical_fields_abstained",
                "critical_fields_total", "citation_valid", "citation_total",
            ):
                _count(row, key)
            for key in ("eligible", "classification_correct", "false_eligible"):
                if type(row.get(key)) is not bool:
                    raise ValueError("Missing boolean business result: " + key)
            if (
                row.get("expected_kind") != truth[sha]
                or row["classification_correct"] != (row.get("predicted_kind") == truth[sha])
            ):
                raise ValueError("Classification disagrees with original source truth")
            comparisons = row.get("comparisons")
            if not isinstance(comparisons, list) or len(comparisons) != row["fields_total"]:
                raise ValueError("Missing original field comparisons")
            if any(
                not isinstance(c, dict)
                or any(type(c.get(k)) is not bool for k in (
                    "correct", "critical", "abstained", "present_in_truth"
                ))
                for c in comparisons
            ):
                raise ValueError("Incomplete original field comparison")
            recalculated = {
                "fields_correct": sum(c["correct"] for c in comparisons),
                "fields_total": len(comparisons),
                "present_fields_correct": sum(
                    c["correct"] and c["present_in_truth"] for c in comparisons
                ),
                "present_fields_total": sum(c["present_in_truth"] for c in comparisons),
                "critical_fields_abstained": sum(
                    c["critical"] and c["abstained"] for c in comparisons
                ),
                "critical_fields_total": sum(c["critical"] for c in comparisons),
            }
            if any(row[key] != count for key, count in recalculated.items()):
                raise ValueError("Scored field totals disagree with original comparisons")
            if row["citation_valid"] > row["citation_total"]:
                raise ValueError("Reported valid citations exceed original citation count")
            cases[sha] = {
                key: row[key] for key in (
                    "predicted_kind", "expected_kind", "classification_correct",
                    "eligible", "false_eligible", "fields_correct", "fields_total",
                    "present_fields_correct", "present_fields_total",
                    "critical_fields_abstained", "critical_fields_total",
                    "citation_valid", "citation_total",
                )
            }
        if set(cases) != set(blobs):
            raise ValueError("Missing scored source identity")

        traces = [n for n in names if n.startswith("qwen-dev-run/model-traces/")]
        observed: set[str] = set()
        for path in traces:
            match = TRACE_RE.fullmatch(path)
            if not match or match.group(1) not in cases or match.group(1) in observed:
                raise ValueError("Invalid, absent or duplicated model trace identity")
            raw = _json(archive, names, path)
            tele, request, proposal = (
                raw.get("telemetry"), raw.get("request"), raw.get("proposal")
            )
            if not all(isinstance(x, dict) for x in (tele, request, proposal)):
                raise ValueError("Incomplete original model trace")
            if (
                tele.get("document_sha256") != match.group(1)
                or tele.get("model_sha256") != report.get("pinned_model_sha256")
                or tele.get("prompt_version") != report.get("prompt_version")
                or tele.get("provider") != "local-llama.cpp"
                or proposal.get("kind") != cases[match.group(1)]["predicted_kind"]
            ):
                raise ValueError("Model trace identity/output does not match scored source")
            try:
                payload = json.loads(request["messages"][-1]["content"])
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                raise ValueError("Missing original raw request") from exc
            if payload.get("document_sha256") != match.group(1):
                raise ValueError("Raw request source identity mismatch")
            observed.add(match.group(1))
        if len(observed) != 12 or observed != set(cases):
            raise ValueError("Twelve distinct original model responses required")

        metric_keys = (
            "fields_correct", "fields_total", "present_fields_correct",
            "present_fields_total", "critical_fields_abstained",
            "critical_fields_total", "citation_valid", "citation_total",
        )
        tallies = {key: sum(row[key] for row in cases.values()) for key in metric_keys}
        correct = sum(row["classification_correct"] for row in cases.values())
        eligible = sum(row["eligible"] for row in cases.values())
        false = sum(row["false_eligible"] for row in cases.values())
        if (
            correct != report.get("correct_classifications")
            or eligible != report.get("eligible_for_explicit_human_review")
            or false != report.get("false_eligible")
            or report.get("evaluated_documents") != 12
            or report.get("real_original_traces") != 12
            or report.get("request_or_parser_failures") != 0
        ):
            raise ValueError("Aggregated report mismatches original cases")
        summary = _json(archive, names, "qwen-dev-run/evaluation/summary.json")
        denominators = summary.get("profiles", {}).get("local-llm", {}).get(
            "denominators", {}
        )
        if any(tallies[k] != denominators.get(k) for k in tallies):
            raise ValueError("Field/citation denominators mismatch original summary")
        unsupported_eligible = sum(
            cases[doc["sha256"]]["eligible"]
            for doc in docs if doc["contract_group"] == "unseen"
        )
        independently_safe = (
            false == 0 and unsupported_eligible == 0
            and tallies["citation_valid"] == tallies["citation_total"]
        )
        return {
            "archive_sha256": digest,
            "manifest_sha256": _sha(raw_manifest),
            "source_commit": report.get("source_commit"),
            "prompt_version": report.get("prompt_version"),
            "model_sha256": report.get("pinned_model_sha256"),
            "document_sha256_by_path": {p: sha for sha, p in blobs.items()},
            "correct_classifications": correct,
            "eligible_documents": eligible,
            "false_eligible": false,
            "counters": tallies,
            "cases": cases,
            "development_quality_met": report.get(
                "synthetic_development_quality_policy_met"
            ) is True,
            "runtime_gate_met": (
                report.get("bounded_runtime_execution_gate_met") is True
                and independently_safe
            ),
            "runtime_report_contradicts_scored_source": (
                report.get("bounded_runtime_execution_gate_met") is True
                and not independently_safe
            ),
        }


def compare(baseline: Path, candidate: Path) -> dict:
    old, new = inspect(baseline), inspect(candidate)
    if not old["runtime_gate_met"]:
        raise ValueError("Baseline runtime/safety evidence is not qualified")
    if (
        old["document_sha256_by_path"] != new["document_sha256_by_path"]
        or old["manifest_sha256"] != new["manifest_sha256"]
        or old["model_sha256"] != new["model_sha256"]
        or set(old["cases"]) != set(new["cases"])
    ):
        raise ValueError("Runs are not paired: source documents/model differ")
    if (
        old["prompt_version"] == new["prompt_version"]
        and old["archive_sha256"] == new["archive_sha256"]
    ):
        raise ValueError("Comparing artifact with itself cannot qualify a candidate")
    changes: dict[str, dict] = {}
    for sha in sorted(old["cases"]):
        before, after = old["cases"][sha], new["cases"][sha]
        if (
            before["expected_kind"] != after["expected_kind"]
            or any(
                before[key] != after[key]
                for key in ("fields_total", "present_fields_total", "critical_fields_total")
            )
        ):
            raise ValueError("Case truth/denominators differ between runs")
        changes[sha] = {
            "expected_kind": before["expected_kind"],
            "classification_before": before["predicted_kind"],
            "classification_after": after["predicted_kind"],
            "field_correct_delta": after["fields_correct"] - before["fields_correct"],
            "critical_abstention_delta": (
                after["critical_fields_abstained"] - before["critical_fields_abstained"]
            ),
        }

    def metrics(result: dict) -> dict:
        c = result["counters"]
        return {
            "correct_classes": result["correct_classifications"],
            "eligible": result["eligible_documents"],
            "false_eligible": result["false_eligible"],
            "fields_correct": c["fields_correct"],
            "critical_abstained": c["critical_fields_abstained"],
            "citation_valid": c["citation_valid"],
            "citation_total": c["citation_total"],
        }

    before, after = metrics(old), metrics(new)
    regressions: list[str] = []
    for key in ("correct_classes", "eligible", "fields_correct"):
        if after[key] < before[key]:
            regressions.append(key + " decreased")
    if after["false_eligible"] > before["false_eligible"]:
        regressions.append("false eligibility increased")
    if after["critical_abstained"] > before["critical_abstained"]:
        regressions.append("critical abstention increased")
    if not new["runtime_gate_met"]:
        regressions.append("candidate runtime/safety gate failed")
    return {
        "schema_version": "1.0",
        "kind": "PAIRED_QWEN_SYNTHETIC_DEVELOPMENT_COMPARISON",
        "supplier_real_generalization": False,
        "untouched_holdout": False,
        "baseline": {
            "source_commit": old["source_commit"],
            "prompt": old["prompt_version"],
            "zip_sha256": old["archive_sha256"],
            "metrics": before,
        },
        "candidate": {
            "source_commit": new["source_commit"],
            "prompt": new["prompt_version"],
            "zip_sha256": new["archive_sha256"],
            "metrics": after,
        },
        "paired_case_count": len(changes),
        "paired_manifest_sha256": old["manifest_sha256"],
        "regressions": regressions,
        "nonregression_met": not regressions,
        "candidate_development_quality_met": new["development_quality_met"],
        "candidate_runtime_report_contradicts_source": new[
            "runtime_report_contradicts_scored_source"
        ],
        "qwen_general_quality_accepted": False,
        "cases": changes,
        "note": (
            "Source-matched observed differences; paired execution does not prove "
            "the prompt change alone caused the result."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--require-nonregression", action="store_true",
        help="Exit 3 after retaining a nonregression failure report",
    )
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Refuse to overwrite original paired comparison")
    result = compare(args.baseline, args.candidate)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        output.write(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "cases"},
                     sort_keys=True, indent=2))
    if args.require_nonregression and not result["nonregression_met"]:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
