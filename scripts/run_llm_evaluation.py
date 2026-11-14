#!/usr/bin/env python3
"""Run a pinned local model and held-out evaluation in one process namespace.

No download, cloud request or automatic provider fallback. Provision the pinned
model/runtime first. All model outputs, server logs and resource observations stay
under the explicitly supplied output directory. Any subset is marked incomplete.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import resource
import signal
import socket
import subprocess
import threading
import time

from dci.evaluation import evaluate_manifest
from dci.llm import LlamaConfig, MODEL_ID, MODEL_SHA256


RESOURCE_PROFILE = "local-llm-bounded-1.0"
SERVER_ADDRESS_SPACE_BYTES = 4096 * 1024 * 1024
SERVER_CPU_SECONDS = 1800


def _child_limits() -> None:
    # Applied before exec of the already digest-verified runtime. Address space
    # is not resident memory; both the exact limit and observed RSS are reported.
    resource.setrlimit(resource.RLIMIT_AS, (SERVER_ADDRESS_SPACE_BYTES, SERVER_ADDRESS_SPACE_BYTES))
    resource.setrlimit(resource.RLIMIT_CPU, (SERVER_CPU_SECONDS, SERVER_CPU_SECONDS + 5))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (1024, 1024))


def _available_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _rss_kib(pid: int) -> int | None:
    try:
        status = Path(f"/proc/{pid}/status").read_text()
        return next(int(line.split()[1]) for line in status.splitlines() if line.startswith("VmHWM:"))
    except (OSError, StopIteration, ValueError):
        return None


def _sample_process(pid: int, elapsed: float) -> dict:
    sample = {"elapsed_seconds": round(elapsed, 3), "pid": pid}
    try:
        status = Path(f"/proc/{pid}/status").read_text()
        for label in ("VmRSS", "VmHWM", "VmSize", "Threads"):
            value = next((line.split()[1] for line in status.splitlines() if line.startswith(label + ":")), None)
            sample[label] = int(value) if value is not None else None
        # The comm field can contain spaces; positions after its final ')' are stable.
        stat = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        sample["cpu_seconds"] = round((int(stat[11]) + int(stat[12])) / os.sysconf("SC_CLK_TCK"), 3)
    except (OSError, ValueError, IndexError) as exc:
        sample["proc_unavailable"] = type(exc).__name__
    try:
        memory = dict((line.split(":", 1)[0], int(line.split()[1])) for line in Path("/proc/meminfo").read_text().splitlines() if line.split(":", 1)[0] in {"MemTotal", "MemAvailable", "MemFree"})
        sample["host_memory_kib"] = memory
    except (OSError, ValueError):
        sample["host_memory_kib"] = None
    return sample


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--linear-model", type=Path)
    parser.add_argument("--profiles", nargs="+", choices=("baseline", "local-linear", "local-llm"))
    parser.add_argument("--max-documents", type=int)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--threads", type=int, default=4, choices=range(1, 17))
    parser.add_argument("--timeout-seconds", type=float, default=90)
    parser.add_argument("--wall-budget-seconds", type=int, default=900)
    args = parser.parse_args()
    if args.profiles and "local-llm" not in args.profiles:
        parser.error("This harness requires local-llm; use the standard evaluation command for CPU profiles")
    if not 60 <= args.wall_budget_seconds <= 3600:
        parser.error("--wall-budget-seconds must be between 60 and 3600")
    server = args.server.resolve(strict=True)
    model = args.model.resolve(strict=True)
    if args.output.exists() and any(args.output.iterdir()):
        raise SystemExit("Output directory is not empty; choose a new run directory")
    if not server.is_file() or not model.is_file():
        raise SystemExit("A local server executable and GGUF model file are required")
    with model.open("rb") as stream:
        model_digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if model_digest != MODEL_SHA256:
        raise SystemExit("Model digest differs from pinned Qwen3-0.6B Q4_K_M")
    env = dict(os.environ)
    env["LD_LIBRARY_PATH"] = str(server.parent)
    env["HF_HUB_OFFLINE"] = "1"
    env["OMP_NUM_THREADS"] = str(args.threads)
    version = subprocess.run([str(server), "--version"], capture_output=True, text=True, timeout=15, env=env)
    version_text = (version.stdout + version.stderr).strip()
    if version.returncode or "12359" not in version_text or "b1b770d" not in version_text:
        raise SystemExit("Runtime does not match verified llama.cpp b12359 / b1b770d")
    args.output.mkdir(parents=True, exist_ok=True)
    port = _available_port()
    command = [str(server), "--model", str(model), "--alias", MODEL_ID,
               "--host", "127.0.0.1", "--port", str(port), "--threads", str(args.threads),
               "--ctx-size", "8192", "--parallel", "1", "--reasoning", "off", "--no-webui",
               "--cache-ram", "0", "--no-cache-prompt", "--ctx-checkpoints", "0",
               "--batch-size", "512", "--ubatch-size", "128"]
    started = time.perf_counter()
    metadata = {"command": command, "runtime_version_output": version_text,
                "runtime_binary_sha256": hashlib.sha256(server.read_bytes()).hexdigest(),
                "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "model_sha256": model_digest, "network_binding": "127.0.0.1", "server_peak_rss_kib": None,
                "resource_profile": RESOURCE_PROFILE,
                "resource_correction": "Disable prompt/idle cache and context checkpoints; reduce batching. Model, prompt, seed, context and inference threads are unchanged from prior failed attempts.",
                "limits": {"address_space_bytes": SERVER_ADDRESS_SPACE_BYTES, "cpu_soft_seconds": SERVER_CPU_SECONDS,
                           "cpu_hard_seconds": SERVER_CPU_SECONDS + 5, "wall_seconds": args.wall_budget_seconds}}
    outcome = 1
    with (args.output / "server.log").open("wb") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True,
                                   preexec_fn=_child_limits)
        try:
            metadata["server_process_limits"] = Path(f"/proc/{process.pid}/limits").read_text()
        except OSError as exc:
            metadata["server_process_limits_unavailable"] = type(exc).__name__
        monitor_stop = threading.Event()
        samples = []

        def monitor():
            with (args.output / "server-resource-timeline.jsonl").open("w", encoding="utf-8") as timeline:
                while not monitor_stop.is_set():
                    sample = _sample_process(process.pid, time.perf_counter() - started)
                    sample["exit_code"] = process.poll()
                    samples.append(sample)
                    timeline.write(json.dumps(sample, sort_keys=True) + "\n")
                    timeline.flush()
                    if sample["exit_code"] is not None:
                        return
                    if time.perf_counter() - started > args.wall_budget_seconds:
                        metadata["harness_wall_budget_exceeded"] = True
                        os.killpg(process.pid, signal.SIGTERM)
                        return
                    monitor_stop.wait(0.5)

        monitor_thread = threading.Thread(target=monitor, name="llama-resource-observer", daemon=True)
        monitor_thread.start()
        try:
            ready = False
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(f"Local runtime exited before readiness: {process.returncode}")
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
                try:
                    connection.request("GET", "/health")
                    response = connection.getresponse()
                    response.read(4096)
                    if response.status == 200:
                        ready = True
                        break
                except (OSError, http.client.HTTPException):
                    pass
                finally:
                    connection.close()
                time.sleep(0.2)
            if not ready:
                raise RuntimeError("Local runtime did not become healthy within 90 seconds")
            metadata["server_startup_seconds"] = round(time.perf_counter() - started, 6)
            config_args = {"model_path": model, "port": port, "timeout_seconds": args.timeout_seconds,
                           "trace_dir": args.output / "model-traces"}
            if "runtime_binary" in LlamaConfig.model_fields:
                config_args["runtime_binary"] = server
            config = LlamaConfig(**config_args)
            profiles = tuple(args.profiles) if args.profiles else (("baseline", "local-linear", "local-llm") if args.linear_model else ("baseline", "local-llm"))
            summary = evaluate_manifest(args.manifest, args.output / "evaluation", profiles=profiles,
                                        model_path=args.linear_model, llm_config=config,
                                        max_documents=args.max_documents, repeats=args.repeats)
            metadata["server_peak_rss_kib"] = _rss_kib(process.pid)
            metadata["evaluation_summary"] = "evaluation/summary.json"
            metadata["observed_profiles"] = {name: {"documents": value["documents"], "failures": value["failures"], "eligible_coverage": value["eligible_coverage"], "eligible_critical_quality": value["eligible_critical_quality"], "policy_gate_met": value["policy_gate_met"]} for name, value in summary["profiles"].items()}
            outcome = 0
        except Exception as exc:
            metadata["error"] = {"type": type(exc).__name__, "message": str(exc)}
            raise
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
            monitor_stop.set()
            monitor_thread.join(timeout=3)
            metadata["observed_server_peak_rss_kib"] = max((sample["VmRSS"] for sample in samples if sample.get("VmRSS") is not None), default=None)
            metadata["observed_server_peak_hwm_kib"] = max((sample["VmHWM"] for sample in samples if sample.get("VmHWM") is not None), default=None)
            metadata["observed_server_cpu_seconds"] = max((sample["cpu_seconds"] for sample in samples if sample.get("cpu_seconds") is not None), default=None)
            metadata["resource_sample_count"] = len(samples)
            metadata["server_exit_code"] = process.returncode
            metadata["wall_seconds"] = round(time.perf_counter() - started, 6)
            (args.output / "harness.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "profiles": metadata.get("observed_profiles")}, indent=2))
    return outcome


if __name__ == "__main__":
    raise SystemExit(main())
