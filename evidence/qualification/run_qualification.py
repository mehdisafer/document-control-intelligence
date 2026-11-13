"""Frozen-source local qualification orchestrator. No source or training mutations."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PYTHON = str(ROOT / ".venv/bin/python")
EXPECTED_HEAD = "3ff93109f3ea0d9c5f4bdfd598dd35bbd4513439"
ENV = dict(os.environ, PYTHONPATH="src")


def now():
    return datetime.now(timezone.utc).isoformat()


def write(name, value):
    (OUT / name).write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def hashes():
    names = git("ls-files", "src", "tests", "scripts", "contracts", "prompts", "infra",
                ".github", "pyproject.toml", "requirements.lock", "uv.lock", "Dockerfile",
                "compose.yaml", "compose.llm.yaml").splitlines()
    values = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}
    return {"files": values, "tree_sha256": hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()}


def run(name, arguments, timeout=240):
    record = {"stage": name, "argv": [PYTHON, *arguments], "cwd": str(ROOT),
              "environment_overrides": {"PYTHONPATH": "src"}, "started_at": now(),
              "timeout_seconds": timeout, "log": f"{name}.log"}
    with (OUT / "commands.jsonl").open("a") as log:
        log.write(json.dumps({**record, "event": "started"}) + "\n")
    print(f"START {name} {record['started_at']}", flush=True)
    started = time.monotonic()
    with (OUT / record["log"]).open("x") as log:
        try:
            result = subprocess.run(record["argv"], cwd=ROOT, env=ENV, stdout=log,
                                    stderr=subprocess.STDOUT, timeout=timeout)
            record["exit_code"] = result.returncode
        except subprocess.TimeoutExpired:
            record["exit_code"] = None
            record["error"] = "orchestrator_timeout"
    record["finished_at"] = now()
    record["elapsed_seconds"] = round(time.monotonic() - started, 6)
    record["log_sha256"] = hashlib.sha256((OUT / record["log"]).read_bytes()).hexdigest()
    with (OUT / "commands.jsonl").open("a") as log:
        log.write(json.dumps({**record, "event": "finished"}) + "\n")
    print(f"END {name} exit={record['exit_code']} seconds={record['elapsed_seconds']}", flush=True)
    return record


def main():
    if (OUT / "commands.jsonl").exists():
        raise SystemExit("Refusing to overwrite an existing qualification run")
    assert git("rev-parse", "HEAD") == EXPECTED_HEAD, "Source freeze commit changed before start"
    before = hashes()
    write("source-before.json", {"at": now(), "commit": git("rev-parse", "HEAD"),
                                  "git_tree": git("rev-parse", "HEAD^{tree}"), **before})
    inputs = {"tmp/final-linear-model.json": "234c94149697cbeda761c22cae9c27aa0f57a8215422da906b32a6bc07148ff1",
              "tmp/final-corpus-seed42/manifest.json": "94161d71e2f704a7ea32ee01e07d46bd2538437c26ac972348bd4817211229fa"}
    assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest for path, digest in inputs.items())
    write("predeclared-plan.json", {"created_at": now(), "commit": EXPECTED_HEAD,
          "runtime": {"python": platform.python_version(), "platform": platform.platform(),
                      "thread_environment": {key: os.environ.get(key) for key in
                         ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")}},
          "frozen_inputs_sha256": inputs,
          "environment_overrides": {"PYTHONPATH": "src"},
          "required": {"unit_integration_exit_code": 0, "demo_cases_each": 9,
                       "demo_exports_restored_each": 7, "benchmark_worker_counts": [1, 2],
                       "benchmark_documents_per_count": 9,
                       "benchmark_false_acceptances": 0, "benchmark_duplicate_publications": 0,
                       "source_files_unchanged": True},
          "regression": "Frozen baseline/local-linear final split; no training, tuning, threshold change or LLM rerun",
          "limits": ["Synthetic PDFs and a single host", "Latency and throughput report-only",
                     "TestClient and Store load are not a network HTTP concurrency benchmark",
                     "Browser, container, Terraform and real deployment are not qualified by this run",
                     "Absent resource measurements are null, never zero"]})
    commands = []
    commands.append(run("unittest", ["-m", "unittest", "discover", "-s", "tests", "-v"], 240))
    for profile in ("baseline", "local-linear"):
        target = OUT / f"demo-{profile}"
        args = ["-m", "dci.cli", "demo", "--output", str(target), "--profile", profile]
        if profile == "local-linear":
            args += ["--model-path", str(ROOT / "tmp/final-linear-model.json")]
        commands.append(run(f"demo-{profile}", args, 120))
        commands.append(run(f"verify-demo-{profile}", ["scripts/verify_demo.py", str(target / "result.json")], 30))
    commands.append(run("benchmark", ["scripts/benchmark.py", "--cases", "3", "--workers", "1", "2",
                    "--batch-size", "2", "--timeout-seconds", "120", "--output", str(OUT / "benchmark-1-2.json")], 240))
    evaluation_code = ("from pathlib import Path; import json; from dci.evaluation import evaluate_manifest; "
        "summary = evaluate_manifest(Path('tmp/final-corpus-seed42/manifest.json'), "
        "Path('outputs/evidence-final/evaluation-regression'), profiles=('baseline','local-linear'), "
        "model_path=Path('tmp/final-linear-model.json')); print(json.dumps(summary, sort_keys=True, indent=2))")
    commands.append(run("evaluation-regression", ["-c", evaluation_code], 240))
    after = hashes()
    write("source-after.json", {"at": now(), "commit": git("rev-parse", "HEAD"),
                                 "git_tree": git("rev-parse", "HEAD^{tree}"), **after})
    changed = sorted(name for name in before["files"].keys() | after["files"].keys()
                     if before["files"].get(name) != after["files"].get(name))
    inputs_after = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in inputs}
    report = {"finished_at": now(), "commands": commands, "source_files_unchanged": not changed,
              "source_files_changed": changed, "frozen_inputs_unchanged": inputs_after == inputs,
              "all_command_exit_codes_zero": all(record["exit_code"] == 0 for record in commands),
              "original_commit": EXPECTED_HEAD}
    write("orchestration-summary.json", report)
    print(json.dumps({key: value for key, value in report.items() if key != "commands"}), flush=True)
    return 0 if report["all_command_exit_codes_zero"] and not changed and inputs_after == inputs else 1


if __name__ == "__main__":
    sys.exit(main())
