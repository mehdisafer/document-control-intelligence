"""Compare frozen CPU evaluation semantics and index the observed qualification."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
ORIGINAL = ROOT / "tmp/final-evaluation-all-profiles/evaluation"
CURRENT = OUT / "evaluation-regression"


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def semantic(value):
    if isinstance(value, dict):
        return {key: semantic(item) for key, item in value.items() if key not in {"timings", "elapsed_seconds"}}
    if isinstance(value, list):
        return [semantic(item) for item in value]
    return value


def records(directory, profile):
    result = {}
    paths = {}
    for path in sorted((directory / "documents" / profile).glob("*.json")):
        value = read(path)
        key = (value["input_sha256"], value["repeat"])
        assert key not in result
        result[key], paths[key] = value, path
    return result, paths


def main():
    comparison = {"created_at": datetime.now(timezone.utc).isoformat(),
                  "original_directory": str(ORIGINAL.relative_to(ROOT)),
                  "current_directory": str(CURRENT.relative_to(ROOT)),
                  "comparison": "Every per-document output except timings and elapsed_seconds; includes kind, probabilities, field status/value/evidence, rows, business findings/calculations and scores",
                  "profiles": {}}
    for profile in ("baseline", "local-linear"):
        before, before_paths = records(ORIGINAL, profile)
        after, after_paths = records(CURRENT, profile)
        keys = before.keys() | after.keys()
        rows = []
        for key in sorted(keys):
            left, right = semantic(before.get(key)), semantic(after.get(key))
            changed = sorted(k for k in left.keys() | right.keys() if left.get(k) != right.get(k)) if left and right else ["missing_record"]
            rows.append({"input_sha256": key[0], "repeat": key[1], "equal": left == right,
                         "changed_top_level_fields": changed,
                         "original_record_sha256": sha(before_paths[key]) if key in before_paths else None,
                         "current_record_sha256": sha(after_paths[key]) if key in after_paths else None})
        old_summary = read(ORIGINAL / "summary.json")["profiles"][profile]
        new_summary = read(CURRENT / "summary.json")["profiles"][profile]
        excluded = {"latency_seconds", "stage_latency_seconds"}
        old_metrics = {k:v for k,v in old_summary.items() if k not in excluded}
        new_metrics = {k:v for k,v in new_summary.items() if k not in excluded}
        comparison["profiles"][profile] = {
            "original_documents": len(before), "current_documents": len(after),
            "identical_document_semantics": sum(row["equal"] for row in rows),
            "all_document_semantics_identical": bool(rows) and all(row["equal"] for row in rows),
            "summary_metrics_identical_excluding_latency": old_metrics == new_metrics,
            "records": rows}
    comparison["defaults_unchanged_on_all_72_executed_outputs"] = all(
        value["all_document_semantics_identical"] and value["summary_metrics_identical_excluding_latency"]
        and value["current_documents"] == 36 for value in comparison["profiles"].values())
    (OUT / "regression-comparison.json").write_text(json.dumps(comparison, sort_keys=True, indent=2) + "\n")
    unit_log = (OUT / "unittest.log").read_text()
    count, seconds = re.search(r"Ran (\d+) tests in ([\d.]+)s", unit_log).groups()
    commands = read(OUT / "orchestration-summary.json")
    unit = {"tests": int(count), "reported_seconds": float(seconds),
            "result": "OK" if unit_log.rstrip().endswith("OK") else "not_OK",
            "skips_reported": bool(re.search(r"(?:skipped=|\.\.\. skipped)", unit_log)),
            "groups": dict(Counter(re.search(r"\(([^.]+)\.", line).group(1)
                            for line in unit_log.splitlines() if line.startswith("test_") and re.search(r"\(([^.]+)\.", line)))}
    demos = {}
    for profile in ("baseline", "local-linear"):
        demo = read(OUT / f"demo-{profile}/result.json")
        verifier = next(record for record in commands["commands"] if record["stage"] == f"verify-demo-{profile}")
        demos[profile] = {
            "cases": len(demo["cases"]), "elapsed_seconds": demo["elapsed_seconds"],
            "jobs": dict(Counter(job["outcome"] for job in demo["jobs"])),
            "published_cases": sum("publication" in case for case in demo["cases"]),
            "restored_export_count": len(demo["restore"]["export_equality"]),
            "restored_exports_equal": all(demo["restore"]["export_equality"].values()),
            "database_integrity": demo["restore"]["database_integrity"],
            "strict_verifier_exit_code": verifier["exit_code"],
            "case_outcomes": [{"scenario": case["scenario"], "eligible": case["eligible"],
                               "reconciliation": case["final_reconciliation"]["status"],
                               "findings": case["final_reconciliation"]["findings"]} for case in demo["cases"]]}
    benchmark = read(OUT / "benchmark-1-2.json")
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "source_commit": commands["original_commit"],
              "source_files_unchanged": commands["source_files_unchanged"],
              "frozen_inputs_unchanged": commands["frozen_inputs_unchanged"],
              "unit_integration": unit, "demos": demos,
              "load": {"qualified_for_declared_smoke_budgets": benchmark["qualified_for_declared_smoke_budgets"],
                       "business_semantics_equal_across_worker_counts": benchmark["business_semantics_equal_across_worker_counts"],
                       "hardware": benchmark["hardware"],
                       "profiles": [{key: profile[key] for key in (
                           "workers_requested", "worker_pids_observed", "processing_wall_seconds_including_spawn",
                           "throughput_documents_per_second", "job_counts", "latency_seconds", "stage_latency_seconds",
                           "resources", "eligible_documents", "false_acceptances", "case_reconciliation_counts",
                           "publications", "duplicate_publications", "db_integrity", "checks")}
                           for profile in benchmark["profiles"]]},
              "default_rules_regression": {key:value for key,value in comparison.items() if key != "profiles"},
              "overall_requested_local_qualification_met": commands["all_command_exit_codes_zero"] and comparison["defaults_unchanged_on_all_72_executed_outputs"],
              "observed_failure": "Frozen local-linear demo abstains on the injection invoice subtotal because a footer line is also proposed as subtotal; 6 exports, required 7. No automatic fallback or model tuning was used.",
              "resource_limits": ["No cgroup memory/CPU counters were accessible; reported null.",
                                  "Visible sampled RSS omits inaccessible descendants and can double-count shared pages.",
                                  "Worker own and largest reaped-child peak RSS are reported separately; per-stage exclusive RSS is not measured.",
                                  "Stage timings are measured, including actual native parsing, OCR and extraction.",
                                  "Browser/container/Terraform/target deployment were not executed by this qualification."]}
    (OUT / "qualification-summary.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"tests": unit, "demos": {profile:{key:value for key,value in result.items() if key != "case_outcomes"} for profile,result in demos.items()},
                      "regression_equal": comparison["defaults_unchanged_on_all_72_executed_outputs"],
                      "overall_requested_local_qualification_met": report["overall_requested_local_qualification_met"]}, indent=2))


if __name__ == "__main__":
    main()
