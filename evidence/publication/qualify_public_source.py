#!/usr/bin/env python3
"""Record bounded local checks for an exact already-published Git source.

This harness records original outputs. It does not execute a browser, build a
container, validate Terraform, retune a model or claim target deployment.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def git(repo, *arguments):
    return subprocess.check_output(["git", *arguments], cwd=repo).decode().strip()


def snapshot(repo):
    paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=repo).decode().split("\0")
    return {p: hashlib.sha256((repo / p).read_bytes()).hexdigest()
            for p in sorted(filter(None, paths))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo, output = args.repo.resolve(), args.output.resolve()
    if git(repo, "rev-parse", "HEAD") != args.source:
        raise SystemExit("HEAD does not match the supplied source commit")
    if git(repo, "status", "--porcelain"):
        raise SystemExit("Refusing to qualify a dirty tracked or untracked worktree")
    output.mkdir(parents=True, exist_ok=False)
    before = snapshot(repo)
    (output / "source-before.json").write_text(json.dumps(before, indent=2) + "\n")
    records = []
    commands = [
        ("python-version", ["uv", "run", "--frozen", "python", "--version"]),
        ("node-version", ["node", "--version"]),
        ("locked-dependencies", ["uv", "lock", "--check", "--offline"]),
        ("ruff", ["uv", "run", "--frozen", "--group", "audit", "ruff", "check", "src", "tests", "scripts"]),
        ("schemas", ["uv", "run", "--frozen", "python", "scripts/export_schemas.py", "--check"]),
        ("javascript-syntax", ["node", "--check", "src/dci/static/app.js"]),
        ("unittest", ["uv", "run", "--frozen", "python", "-m", "unittest", "discover", "-s", "tests", "-v"]),
        ("ui-state", ["node", "--test", "tests/test_ui_state.mjs"]),
        ("known-secrets-history", ["uv", "run", "--frozen", "python", "scripts/check_secrets.py", "--history"]),
        ("dependency-audit", ["uv", "run", "--frozen", "--group", "audit", "pip-audit", "--disable-pip", "--no-deps", "-r", "requirements.lock", "--format=json", "--output=" + str(output / "dependency-audit.json")]),
        ("component-inventory", ["uv", "run", "--frozen", "python", "scripts/check_licenses.py"]),
    ]
    started = utc_now()
    for name, command in commands:
        start, monotonic = utc_now(), time.monotonic()
        timed_out = False
        try:
            process = subprocess.run(command, cwd=repo, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, timeout=180)
            content, exit_code = process.stdout, process.returncode
        except subprocess.TimeoutExpired as error:
            content, exit_code, timed_out = error.stdout or b"", None, True
        elapsed = round(time.monotonic() - monotonic, 6)
        (output / (name + ".log")).write_bytes(content)
        record = {"name": name, "argv": command, "cwd": str(repo), "started_at": start,
                  "finished_at": utc_now(), "wall_seconds": elapsed,
                  "exit_code": exit_code, "timed_out": timed_out,
                  "log_sha256": hashlib.sha256(content).hexdigest()}
        records.append(record)
        (output / "commands.json").write_text(json.dumps(records, indent=2) + "\n")
        print(json.dumps({"name": name, "exit_code": exit_code,
                          "timed_out": timed_out, "wall_seconds": elapsed}), flush=True)
    after = snapshot(repo)
    (output / "source-after.json").write_text(json.dumps(after, indent=2) + "\n")
    unit_text = (output / "unittest.log").read_text(errors="replace")
    unit_match = re.search(r"Ran (\d+) tests in ([\d.]+)s", unit_text)
    js_text = (output / "ui-state.log").read_text(errors="replace")
    js_counts = {key: int(value) for key, value in re.findall(
        r"# (tests|pass|fail|cancelled|skipped|todo) (\d+)", js_text)}
    report = {"schema_version": "1.0", "source_commit": args.source,
              "source_tree": git(repo, "rev-parse", "HEAD^{tree}"),
              "started_at": started, "finished_at": utc_now(),
              "tracked_files": len(before), "tracked_source_unchanged": before == after,
              "worktree_status_after": git(repo, "status", "--porcelain"),
              "commands": records,
              "unittest": {"tests": int(unit_match[1]) if unit_match else None,
                           "reported_seconds": float(unit_match[2]) if unit_match else None,
                           "result_line": next((line for line in reversed(unit_text.splitlines())
                                                if line.startswith(("OK", "FAILED"))), None)},
              "javascript_state_unit": js_counts,
              "all_recorded_commands_succeeded": all(r["exit_code"] == 0 and not r["timed_out"] for r in records),
              "limitations": ["JavaScript tests use a mocked DOM/fetch harness, not a browser.",
                              "Python integration tests include actual parser/OCR/API/storage paths.",
                              "No browser rendering, container build/run, Terraform validation or target deployment is established.",
                              "Historical model, HTTP and demo reports retain their original source identities.",
                              "Known-secret and dependency checks have bounded, point-in-time scope."]}
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(output.iterdir()) if p.is_file()}
    (output / "artifacts.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"report": str(output / "report.json"),
                      "all_recorded_commands_succeeded": report["all_recorded_commands_succeeded"],
                      "source_unchanged": before == after}), flush=True)
    return 0 if report["all_recorded_commands_succeeded"] and before == after else 1


if __name__ == "__main__":
    raise SystemExit(main())
