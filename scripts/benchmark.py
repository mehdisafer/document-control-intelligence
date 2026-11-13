#!/usr/bin/env python3
"""Bounded single-host load qualification with real PDFs and spawned workers.

This profile measures Store admission + actual worker processes. It is not an HTTP
load test, an LLM benchmark, a GPU benchmark, or evidence of multi-host scalability.
Only training-family layouts are selected; no held-out evaluation result is tuned.
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import multiprocessing
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import tempfile
import time

from dci.config import Settings
from dci.corpus import _line, _scan_pdf, _totals, _write_pdf, generate_corpus
from dci.models import Extraction
from dci.parsing import runtime_version
from dci.rules import check_document
from dci.store import Store, digest
from dci.worker import process_one


def _worker(settings_data, deadline, batch_size):
    store = Store(Settings.model_validate(settings_data))
    results = []
    while time.monotonic() < deadline:
        for _ in range(batch_size):
            if time.monotonic() >= deadline:
                return results
            before_claim = time.time()
            result = process_one(store, owner=f"load-worker-{os.getpid()}")
            if result is None:
                return results
            unit = 1 if sys.platform == "darwin" else 1024
            results.append({**result, "worker_pid": os.getpid(), "before_claim_at": before_claim,
                            "worker_peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*unit,
                            "largest_reaped_child_peak_rss_bytes": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss*unit})
    return results


def _read(path):
    try:
        return Path(path).read_text().strip()
    except (OSError, UnicodeError):
        return None


def _rss(pid):
    stat = _read(f"/proc/{pid}/statm")
    try:
        return int(stat.split()[1]) * os.sysconf("SC_PAGE_SIZE") if stat else None
    except (ValueError, IndexError):
        return None


def _process_tree(pid):
    children = _read(f"/proc/{pid}/task/{pid}/children")
    result = {pid}
    for child in (children or "").split():
        result.update(_process_tree(int(child)))
    return result


def _hardware():
    cpu = _read("/proc/cpuinfo") or ""
    model = next((line.split(":", 1)[1].strip() for line in cpu.splitlines()
                  if line.startswith("model name")), platform.processor())
    return {
        "platform": platform.platform(), "python": platform.python_version(),
        "cpu_model": model, "logical_cpu_count": os.cpu_count(),
        "affinity_cpu_count": len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None,
        "mem_total_kib": next((int(line.split()[1]) for line in (_read("/proc/meminfo") or "").splitlines()
                               if line.startswith("MemTotal:")), None),
        "cgroup": {name: _read(f"/sys/fs/cgroup/{name}") for name in
                   ("memory.max", "memory.current", "memory.peak", "cpu.max")},
        "gpu_used": False,
    }


def _source_identity():
    root = Path(__file__).resolve().parents[1]
    names = sorted([*root.glob("src/dci/*.py"), *root.glob("src/dci/migrations/*.sql"),
                    *root.glob("contracts/*.json"), Path(__file__).resolve()])
    sources = {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
               for path in names}
    def git(*args):
        result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else None
    return {"git_commit": git("rev-parse", "HEAD"),
            "working_tree_dirty": bool(git("status", "--porcelain")),
            "source_tree_sha256": digest(sources), "source_files": sources}


def _quantiles(values):
    values = sorted(values)
    if not values:
        return {"count": 0, "p50": None, "p95": None, "max": None}
    def percentile(fraction):
        position = (len(values)-1) * fraction
        low = int(position)
        high = min(low+1, len(values)-1)
        return round(values[low] + (values[high]-values[low])*(position-low), 6)
    return {"count": len(values), "p50": percentile(.5), "p95": percentile(.95),
            "max": round(values[-1], 6)}


def _inputs(root, cases, seed, include_scan):
    manifest = generate_corpus(root, seed=seed, per_split=max(1, (cases+1)//2))
    families = sorted({row["family_id"] for row in manifest["documents"] if row["split"] == "train"})[:cases]
    selected = [row for row in manifest["documents"] if row["family_id"] in families]
    # A new load fixture uses the training layout with enough unique rows to span
    # three pages. Truth is regenerated before ingestion, never read by the app.
    lines = [_line(f"LOAD-{i:03d}", str(i % 4 + 1), f"{25+i}.50") for i in range(21)]
    for row in selected:
        if row["family_id"] != families[0]:
            continue
        row["expected_fields"] = {**row["expected_fields"], **_totals(lines)}
        row["expected_lines"] = lines
        row["scenario"] = "load_multipage_scan" if include_scan and row["expected_kind"] == "invoice" else "load_multipage"
        path = root/row["path"]
        _write_pdf(path, kind=row["expected_kind"], fields=row["expected_fields"], lines=lines,
                   layout=row["layout"], notes=["Synthetic load qualification; no business transaction."])
        if include_scan and row["expected_kind"] == "invoice":
            _scan_pdf(path, seed=seed+100_000, degraded=False)
            row["scan"] = True
        row["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"seed": seed, "generator_version": manifest["generator_version"],
            "selection": "training_families_only; first family expanded to21lines/3pages; optional real invoice rasterization",
            "documents": selected}


def _run_profile(base, corpus_root, manifest, workers, batch_size, timeout):
    settings = Settings(home=base/f"workers-{workers}", max_workers=workers,
                        max_pending=min(1000, len(manifest["documents"])+1), batch_size=batch_size)
    store = Store(settings)
    case_ids, source_ids = {}, {}
    admission_started = time.monotonic()
    for record in manifest["documents"]:
        key = record["case_key"]
        if key not in case_ids:
            case_ids[key] = store.create_case(f"Load {key}", "load-operator")["id"]
        result = store.ingest(case_ids[key], record["document_key"], Path(record["path"]).name,
                              (corpus_root/record["path"]).read_bytes(), "load-operator")
        source_ids[result["document_id"]] = record
    admission_seconds = time.monotonic()-admission_started
    start = time.monotonic()
    deadline = start+timeout
    peak_parent, peak_children, peak_total, peak_count, samples = None, None, None, 0, 0
    tree_enumeration_available = _read(f"/proc/{os.getpid()}/task/{os.getpid()}/children") is not None
    observed, worker_errors = [], []
    with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn")) as executor:
        futures = [executor.submit(_worker, settings.model_dump(mode="json"), deadline, batch_size)
                   for _ in range(workers)]
        while not all(future.done() for future in futures):
            parent = _rss(os.getpid())
            descendants = _process_tree(os.getpid())-{os.getpid()}
            # Some isolated runtimes expose statm but not /proc/.../children. The
            # executor still knows its own worker PIDs; never report missing RSS
            # measurements as zero memory consumption.
            descendants.update(process.pid for process in (executor._processes or {}).values()
                               if process.pid is not None)
            sampled = [value for pid in descendants if (value := _rss(pid)) is not None]
            child_rss = sum(sampled) if sampled else None
            if parent is not None:
                peak_parent = max(peak_parent or 0, parent)
            if child_rss is not None:
                peak_children = max(peak_children or 0, child_rss)
            if parent is not None and child_rss is not None:
                peak_total = max(peak_total or 0, parent+child_rss)
            peak_count = max(peak_count, len(descendants))
            samples += 1
            if time.monotonic() > deadline+settings.parser_seconds+15:
                # Python3.12 has no public terminate_workers API. Terminate only
                # this executor's processes after its explicit hard deadline.
                for process in (executor._processes or {}).values():
                    process.terminate()
                worker_errors.append("SUPERVISOR_DEADLINE")
                break
            time.sleep(.05)
        for future in futures:
            try:
                observed.extend(future.result(timeout=5))
            except Exception as exc:
                worker_errors.append(type(exc).__name__)
    elapsed = time.monotonic()-start
    by_document = {entry["document_id"]: entry for entry in observed}
    details, semantic_cases, false_acceptances, eligible_documents = [], [], 0, 0
    for document_id, record in source_ids.items():
        document = store.document(document_id)
        result = by_document.get(document_id, {})
        job = document["job"]
        extraction = document["extraction"]
        correct = False
        if extraction:
            critical = ("document_id", "purchase_order_id", "supplier_id", "currency")
            if record["expected_kind"] in ("purchase_order", "invoice"):
                critical += ("subtotal", "tax", "total")
            correct = extraction["kind"] == record["expected_kind"] and all(
                extraction["fields"].get(key, {}).get("normalized") == record["expected_fields"][key]
                for key in critical)
            actual_lines = [{key: value["normalized"] for key, value in line["fields"].items()}
                            for line in extraction["line_items"]]
            correct = correct and actual_lines == record["expected_lines"]
            eligible = check_document(Extraction.model_validate(extraction)).decision == "eligible"
            eligible_documents += int(eligible)
            false_acceptances += int(eligible and not correct)
        parsed = document["parsed"] or {}
        details.append({"document_key": record["document_key"], "sha256": document["sha256"],
                        "status": document["status"], "job_status": job["status"], "attempts": job["attempt"],
                        "error_code": document["error_code"], "decision": (document["checks"] or {}).get("decision"),
                        "worker_pid": result.get("worker_pid"), "processing_seconds": job["elapsed_seconds"],
                        "queue_wait_seconds_approx": max(0, result["before_claim_at"]-job["created_at"]) if result else None,
                        "end_to_end_seconds": job["finished_at"]-job["created_at"] if job["finished_at"] else None,
                        "pages": len(parsed.get("pages", [])), "ocr_pages": sum(page["method"] == "ocr" for page in parsed.get("pages", [])),
                        "parse_timings": parsed.get("timings", {}), "extraction_timings": (extraction or {}).get("timings", {}),
                        "normalized_critical_and_line_values_correct": correct})
    expected_publications, duplicate_publications = 0, 0
    for key, case_id in sorted(case_ids.items()):
        case = store.case(case_id)
        documents = []
        for entry in case["documents"]:
            document = store.document(entry["id"])
            extraction = document["extraction"]
            if extraction:
                extraction = {name: value for name, value in extraction.items() if name != "timings"}
            documents.append({"key": document["document_key"], "sha256": document["sha256"],
                              "extraction": extraction, "checks": document["checks"]})
        semantic_cases.append({"case_key": key, "reconciliation": case["reconciliation"],
                               "eligible": case["eligible_for_acceptance"], "documents": documents})
        if case["eligible_for_acceptance"]:
            expected_publications += 1
            store.accept(case_id, "load-approver", "Explicit synthetic load qualification review.", case["revision"])
            first = store.publish(case_id, "load-publisher", case["revision"])
            second = store.publish(case_id, "load-publisher", case["revision"])
            duplicate_publications += int(first["id"] != second["id"] or not second["duplicate"])
    with closing(store.connect()) as conn:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    counts = Counter(detail["job_status"] for detail in details)
    metrics = store.metrics()
    return {
        "workers_requested": workers, "worker_pids_observed": sorted({row["worker_pid"] for row in observed}),
        "batch_size": batch_size, "admission_seconds": round(admission_seconds, 6),
        "processing_wall_seconds_including_spawn": round(elapsed, 6),
        "throughput_documents_per_second": round(counts["done"]/elapsed, 6),
        "job_counts": dict(counts), "worker_errors": worker_errors,
        "latency_seconds": {name: _quantiles([row[key] for row in details if row[key] is not None])
                            for name, key in (("processing", "processing_seconds"), ("queue_approx", "queue_wait_seconds_approx"),
                                              ("end_to_end", "end_to_end_seconds"))},
        "stage_latency_seconds": {
            "parse_wall": _quantiles([row["parse_timings"]["wall_seconds"] for row in details if "wall_seconds" in row["parse_timings"]]),
            "native": _quantiles([row["parse_timings"].get("native_seconds", 0) for row in details]),
            "ocr": _quantiles([row["parse_timings"].get("ocr_seconds", 0) for row in details]),
            "extraction": _quantiles([row["extraction_timings"]["extraction_seconds"] for row in details if "extraction_seconds" in row["extraction_timings"]]),
        },
        "resources": {"sample_period_seconds": .05, "samples": samples, "parent_peak_rss_bytes": peak_parent,
                      "sampled_descendant_peak_summed_rss_bytes": peak_children, "sampled_visible_tree_peak_summed_rss_bytes": peak_total,
                      "peak_known_descendant_count": peak_count, "process_tree_enumeration_available": tree_enumeration_available,
                      "worker_reported_peak_rss_bytes": {str(pid): max(row["worker_peak_rss_bytes"] for row in observed if row["worker_pid"] == pid)
                                                         for pid in {row["worker_pid"] for row in observed}},
                      "worker_reported_largest_reaped_child_peak_rss_bytes": {str(pid): max(row["largest_reaped_child_peak_rss_bytes"] for row in observed if row["worker_pid"] == pid)
                                                                              for pid in {row["worker_pid"] for row in observed}},
                      "method": "Visible Linux procfs RSS sampled over parent/known workers/available descendants; null means unavailable. Per-worker ru_maxrss reports own peak and largest reaped child peak separately. Summed RSS double-counts shared pages, is not unique physical RAM, and can omit inaccessible descendants."},
        "db_integrity": integrity, "eligible_documents": eligible_documents,
        "false_acceptances": false_acceptances, "case_reconciliation_counts": dict(Counter(row["reconciliation"]["status"] for row in semantic_cases)),
        "publications": metrics["publications"], "expected_publications": expected_publications,
        "duplicate_publications": duplicate_publications,
        "business_semantic_sha256": digest(semantic_cases), "documents": details,
        "worker_results": observed,
        "checks": {"all_jobs_done": counts["done"] == len(details), "no_worker_errors": not worker_errors,
                   "no_false_acceptance": false_acceptances == 0, "database_integrity": integrity == "ok",
                   "publication_idempotency": duplicate_publications == 0 and metrics["publications"] == expected_publications},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=int, default=3)
    parser.add_argument("--workers", type=int, nargs="+", choices=[1, 2, 4], default=[1, 2])
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--seed", type=int, default=744)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--scan", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.cases <= 50 or not 1 <= args.batch_size <= 32 or not 10 <= args.timeout_seconds <= 600:
        parser.error("Budgets: cases1..50; batch-size1..32; timeout-seconds10..600")
    if args.output.exists():
        parser.error("Output already exists; choose a new evidence path")
    budgets = {"no_failed_or_unprocessed_jobs": True, "false_acceptances": 0, "duplicate_publications": 0,
               "database_integrity": "ok", "business_semantics_equal_across_worker_counts": True,
               "latency_and_throughput": "report_only_no_scalability_or_production_SLO_claim",
               "profile_timeout_seconds": args.timeout_seconds, "hard_deadline_additional_seconds": 60,
               "source_unchanged_during_execution": True,
               "retries": "configured_bounded_policy; counted_as_observed_attempts"}
    print(json.dumps({"declared_before_execution": budgets}), file=sys.stderr, flush=True)
    report = {"schema_version": "load-evidence-1.0", "started_at": datetime.now(timezone.utc).isoformat(),
              "command": [sys.executable, *sys.argv], "scope": "Store admission and actual spawned baseline worker processes; synthetic inputs; single host",
              "hardware": _hardware(), "source": _source_identity(), "parser_runtime": runtime_version(),
              "dependencies": {name: importlib.metadata.version(name) for name in
                               ("fastapi", "pydantic", "pypdf", "pdfplumber", "pypdfium2", "Pillow", "reportlab")},
              "acceptance_budgets": budgets, "external_api_requests": 0,
              "observed_external_api_cost_usd": "0.00", "infrastructure_or_energy_cost": "not_measured"}
    with tempfile.TemporaryDirectory(prefix="dci-load-") as temp:
        root = Path(temp)
        inputs = _inputs(root/"corpus", args.cases, args.seed, args.scan)
        report["input_manifest"] = inputs
        report["profiles"] = []
        for workers in sorted(set(args.workers)):
            print(f"Running {workers} worker(s), {len(inputs['documents'])} real PDF documents.", file=sys.stderr, flush=True)
            report["profiles"].append(_run_profile(root/"state", root/"corpus", inputs, workers,
                                                  args.batch_size, args.timeout_seconds))
    report["business_semantics_equal_across_worker_counts"] = len({profile["business_semantic_sha256"] for profile in report["profiles"]}) == 1
    after = _source_identity()
    report["source_tree_sha256_after_execution"] = after["source_tree_sha256"]
    report["source_unchanged_during_execution"] = after["source_tree_sha256"] == report["source"]["source_tree_sha256"]
    report["qualified_for_declared_smoke_budgets"] = report["source_unchanged_during_execution"] and report["business_semantics_equal_across_worker_counts"] and all(
        all(profile["checks"].values()) for profile in report["profiles"])
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
    print(json.dumps({"output": str(args.output), "qualified_for_declared_smoke_budgets": report["qualified_for_declared_smoke_budgets"]}))
    return 0 if report["qualified_for_declared_smoke_budgets"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
