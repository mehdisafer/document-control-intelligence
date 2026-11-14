#!/usr/bin/env python3
"""Qualify the frozen service through real TCP HTTP and a separate queue worker.

Run from an installed project environment, for example:
  .venv/bin/python evidence/qualification/http/qualify_http.py \
    --repo . --model tmp/final-linear-model.json \
    --output evidence/qualification/http/run-3ff93109

The output directory must be new. Authentication material and the live database
are created in a temporary private directory, never copied into the evidence,
and removed after all child processes stop. No browser or model server is used.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from http.client import HTTPConnection
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import runpy
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlencode
import uuid
import zipfile


EXPECTED_COMMIT = "3ff93109f3ea0d9c5f4bdfd598dd35bbd4513439"
EXPECTED_MODEL_SHA256 = "234c94149697cbeda761c22cae9c27aa0f57a8215422da906b32a6bc07148ff1"
SOURCE_PATHS = ("src", "scripts", "tests", "pyproject.toml", "uv.lock", "requirements.lock")


class QualificationFailure(AssertionError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def check(report: dict, name: str, condition: bool, detail=None) -> None:
    report["checks"].append({"name": name, "status": "passed" if condition else "failed", "detail": detail})
    if not condition:
        raise QualificationFailure(name)


def git(repo: Path, *arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], cwd=repo, text=True).strip()


def source_hashes(repo: Path) -> dict:
    files = git(repo, "ls-files", "--", *SOURCE_PATHS).splitlines()
    return {name: digest((repo / name).read_bytes()) for name in files}


def json_log_records(path: Path) -> list[dict]:
    records = []
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                records.append(value)
    return records


def run(args) -> int:
    from dci.config import Settings
    from dci.parsing import runtime_version
    import dci

    repo, output = args.repo.resolve(), args.output.resolve()
    model = args.model.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {
        "schema_version": "real-http-qualification-1.0",
        "status": "started", "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "started_at_unix": time.time(),
        "scope": "Real HTTP/1.1 over loopback TCP to a Uvicorn child process; separate worker subprocess; local-linear inference",
        "browser_executed": False, "training_executed": False, "external_provider_used": False,
        "checks": [], "requests": [], "cleanup": {},
        "source_commit": EXPECTED_COMMIT, "workspace_head": git(repo, "rev-parse", "HEAD"),
        "harness_sha256": digest(Path(__file__).read_bytes()),
        "model_sha256": digest(model.read_bytes()),
        "model_path": str(model.relative_to(repo)) if model.is_relative_to(repo) else str(model),
        "environment": {
            "python": sys.version, "executable": sys.executable, "platform": platform.platform(),
            "project_import_path": str(Path(dci.__file__).resolve()),
            "cpu_affinity_count": len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else os.cpu_count(),
            "packages": {name: importlib.metadata.version(name) for name in
                         ("fastapi", "uvicorn", "pydantic", "numpy", "scikit-learn", "pypdf", "pdfplumber", "pypdfium2", "reportlab")},
            "parser_runtime": runtime_version(),
            "http_client": "stdlib http.client.HTTPConnection; does not discover proxy variables",
        },
    }
    tokens = {}
    temporary = server = server_log = worker_log = None
    exit_code = 1
    try:
        check(report, "runtime_sources_equal_frozen_commit",
              not git(repo, "diff", EXPECTED_COMMIT, "--", *SOURCE_PATHS))
        report["source_files_sha256"] = source_hashes(repo)
        check(report, "pinned_model_digest", report["model_sha256"] == EXPECTED_MODEL_SHA256)
        check(report, "project_imports_from_checked_repository", Path(dci.__file__).resolve().is_relative_to(repo / "src"))

        temporary = tempfile.TemporaryDirectory(prefix="dci-http-private-")
        private = Path(temporary.name)
        os.chmod(private, 0o700)
        roles = ("operator", "reader", "approver", "publisher")
        tokens = {role: secrets.token_urlsafe(40) for role in roles}
        auth_file = private / "auth.json"
        save_json(auth_file, {"schema_version": "1.0", "actors": [
            {"name": "http_" + role, "roles": [role], "token_sha256": digest(tokens[role].encode())}
            for role in roles]})
        os.chmod(auth_file, 0o600)
        settings = Settings(home=private / "runtime", auth_file=auth_file, profile="local-linear", model_path=model,
                            max_bytes=262144, max_pages=3, parser_seconds=30, parser_memory_mb=768,
                            max_case_documents=3, max_case_bytes=1048576, max_document_versions=2,
                            max_pending=3, max_workers=1, max_attempts=1, lease_seconds=60,
                            retry_seconds=0, batch_size=3)
        config = private / "config.json"
        config.write_text(settings.model_dump_json(indent=2) + "\n")
        os.chmod(config, 0o600)
        report["limits"] = {**settings.model_dump(mode="json", exclude={"home", "auth_file", "model_path", "llm_config_file"}),
                            "http_timeout_seconds": 10, "http_response_max_bytes": 12000000,
                            "worker_timeout_seconds": 90, "startup_timeout_seconds": 10,
                            "uvicorn_host": "127.0.0.1", "uvicorn_limit_concurrency": 32,
                            "uvicorn_limit_max_requests": 10000, "uvicorn_timeout_keep_alive_seconds": 5}
        report["processing_policy"] = settings.processing_policy()
        report["processing_policy_digest"] = settings.policy_digest()

        helper = runpy.run_path(str(repo / "scripts/browser_smoke.py"))
        fixture = helper["generate_browser_fixture"](output / "input-pdfs", "HTTP" + uuid.uuid4().hex[:12].upper())
        save_json(output / "fixture.json", fixture)
        report["fixture"] = fixture
        (output / "documents").mkdir()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        report["transport"] = {"scheme": "http", "host": "127.0.0.1", "port": port,
                               "client_pid": os.getpid(), "network": "loopback only"}
        child_env = os.environ.copy()
        for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy",
                     "DCI_HOME", "DCI_AUTH_FILE", "DCI_CONFIG"):
            child_env.pop(name, None)
        fixed_env = {"OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                     "NUMEXPR_NUM_THREADS": "1", "PYTHONUNBUFFERED": "1", "PYTHONNOUSERSITE": "1",
                     "PYTHONPATH": str(repo / "src"), "LC_ALL": "C.UTF-8", "NO_PROXY": "127.0.0.1,localhost"}
        child_env.update(fixed_env)
        report["child_environment_overrides"] = fixed_env
        base = [sys.executable, "-m", "dci.cli"]
        server_command = [*base, "serve", "--config", str(config), "--host", "127.0.0.1", "--port", str(port)]
        server_log = (output / "server.log").open("w")
        server = subprocess.Popen(server_command, cwd=repo, env=child_env, stdout=server_log, stderr=subprocess.STDOUT)
        report["transport"]["server_pid"] = server.pid
        report["server_command"] = [item if item != str(config) else "<ephemeral-private-config>" for item in server_command]

        def http(method, path, *, role=None, expected=200, body=None, json_body=None, extra_headers=None):
            headers = dict(extra_headers or {})
            if role:
                headers["Authorization"] = "Bearer " + tokens[role]
            if json_body is not None:
                body = json.dumps(json_body).encode()
                headers["Content-Type"] = "application/json"
            connection = HTTPConnection("127.0.0.1", port, timeout=10)
            started = time.monotonic()
            try:
                connection.request(method, path, body=body, headers=headers)
                response = connection.getresponse()
                content = response.read(12000001)
                request_id = response.getheader("X-Request-ID")
                record = {"method": method, "path": path, "actor_role": role,
                          "status": response.status, "expected_status": expected,
                          "x_request_id": request_id, "content_type": response.getheader("Content-Type"),
                          "response_bytes": len(content), "response_sha256": digest(content),
                          "elapsed_seconds": round(time.monotonic() - started, 6)}
                report["requests"].append(record)
                if len(content) > 12000000:
                    raise QualificationFailure("HTTP response byte budget exceeded")
                if response.status != expected:
                    record["error_body"] = content[:4000].decode(errors="replace")
                    raise QualificationFailure(f"{method} {path}: expected {expected}, observed {response.status}")
                if not request_id:
                    raise QualificationFailure("Response did not provide X-Request-ID")
                uuid.UUID(request_id)
                value = json.loads(content) if "application/json" in (record["content_type"] or "") else content
                return value, record
            finally:
                connection.close()

        started = time.monotonic()
        while time.monotonic() - started < 10:
            if server.poll() is not None:
                raise QualificationFailure("Uvicorn exited during startup")
            try:
                health, _ = http("GET", "/healthz")
                break
            except (ConnectionError, OSError):
                time.sleep(0.1)
        else:
            raise QualificationFailure("Uvicorn startup deadline exceeded")
        check(report, "real_loopback_uvicorn_ready", health["status"] == "alive" and server.pid != os.getpid())
        http("GET", "/api/cases", expected=401)
        for role in roles:
            actor, _ = http("GET", "/api/me", role=role)
            check(report, "authenticated_" + role, actor["name"] == "http_" + role and actor["roles"] == [role])
        case, _ = http("POST", "/api/cases", role="operator", expected=201,
                       json_body={"name": "Real HTTP qualification / synthetic purchasing family"})
        case_id = case["id"]
        report["case_id"] = case_id
        first = fixture["documents"][0]
        first_bytes = (output / "input-pdfs" / first["path"]).read_bytes()
        denied_path = f"/api/cases/{case_id}/documents?" + urlencode({"document_key": first["document_key"], "filename": first["path"]})
        http("POST", denied_path, role="reader", expected=403, body=first_bytes,
             extra_headers={"Content-Type": "application/pdf"})
        empty_case, _ = http("GET", f"/api/cases/{case_id}", role="reader")
        check(report, "reader_upload_denied_without_state_change", empty_case["documents"] == [] and empty_case["revision"] == 0)
        uploads = []
        for item in fixture["documents"]:
            content = (output / "input-pdfs" / item["path"]).read_bytes()
            path = f"/api/cases/{case_id}/documents?" + urlencode({"document_key": item["document_key"], "filename": item["path"]})
            uploaded, receipt = http("POST", path, role="operator", expected=202, body=content,
                                     extra_headers={"Content-Type": "application/pdf", "X-Request-ID": "untrusted-client-value"})
            uploads.append({**item, **uploaded, "upload_request_id": receipt["x_request_id"]})
        queued, _ = http("GET", f"/api/cases/{case_id}", role="reader")
        save_json(output / "case-queued.json", queued)
        check(report, "uploads_are_persisted_for_separate_worker", len(queued["documents"]) == 3
              and all(document["status"] == "queued" for document in queued["documents"]))
        http("GET", f"/api/documents/{uploads[0]['document_id']}/original", role="reader", expected=409)

        worker_command = [*base, "worker", "--config", str(config), "--once"]
        report["worker_command"] = [item if item != str(config) else "<ephemeral-private-config>" for item in worker_command]
        worker_log = (output / "worker.log").open("w")
        worker_start = time.monotonic()
        worker = subprocess.Popen(worker_command, cwd=repo, env=child_env, stdout=worker_log, stderr=subprocess.STDOUT)
        report["transport"]["worker_pid"] = worker.pid
        try:
            worker.wait(timeout=90)
        except subprocess.TimeoutExpired:
            worker.kill()
            worker.wait(timeout=10)
            raise QualificationFailure("Separate worker exceeded 90-second budget") from None
        worker_log.close()
        worker_log = None
        report["worker"] = {"exit_code": worker.returncode, "elapsed_seconds": round(time.monotonic() - worker_start, 6),
                            "same_interpreter_as_server": True, "separate_process": worker.pid not in {os.getpid(), server.pid}}
        events = json_log_records(output / "worker.log")
        report["worker"]["events"] = events
        check(report, "separate_worker_executes_all_three_local_model_jobs", worker.returncode == 0 and len(events) == 3
              and all(event.get("outcome") == "done" and event.get("decision") == "eligible" and event.get("profile") == "local-linear" for event in events))
        ready, _ = http("GET", f"/api/cases/{case_id}", role="reader")
        save_json(output / "case-ready.json", ready)
        check(report, "three_document_case_matches", ready["eligible_for_acceptance"] and ready["reconciliation"]["status"] == "matched"
              and len(ready["documents"]) == 3 and all(document["status"] == "ready" for document in ready["documents"]))

        observed_documents = {}
        for item in uploads:
            document, _ = http("GET", f"/api/documents/{item['document_id']}", role="reader")
            observed_documents[item["document_id"]] = document
            save_json(output / "documents" / (item["document_id"] + ".json"), document)
            extraction = document["extraction"]
            expected_fields = {"document_id": item["document_key"], "purchase_order_id": fixture["purchase_order_id"],
                               "supplier_id": fixture["supplier_id"], "currency": "EUR", "document_date": "2026-01-15",
                               "subtotal": "307.25", "tax": "61.45", "total": "368.70"}
            check(report, item["kind"] + "_normalized_fields", all(extraction["fields"][key]["normalized"] == value
                  for key, value in expected_fields.items()))
            proposal = document["classification_proposal"]
            check(report, item["kind"] + "_model_proposal_verified", document["classification_provenance_status"] == "verified"
                  and document["classification_review"] is None and proposal["kind"] == item["kind"]
                  and proposal["profile"] == "local-linear" and proposal["model_version"].startswith("dci-local-linear-1.1")
                  and proposal["confidence"] == extraction["classification_confidence"])
            fields = list(extraction["fields"].values()) + [field for line in extraction["line_items"] for field in line["fields"].values()]
            pages = {page["number"]: page["text"] for page in document["parsed"]["pages"]}
            check(report, item["kind"] + "_all_exact_source_spans", bool(fields)
                  and all(field["status"] == "supported" and field["evidence"] and all(
                      citation["quote"] and pages[citation["page"]][citation["start"]:citation["end"]] == citation["quote"]
                      for citation in field["evidence"]) for field in fields))
            original, original_receipt = http("GET", f"/api/documents/{item['document_id']}/original", role="reader")
            check(report, item["kind"] + "_original_bytes_preserved", original == (output / "input-pdfs" / item["path"]).read_bytes()
                  and digest(original) == item["sha256"] and original_receipt["content_type"] == "application/pdf")

        # Authorization and publication are exercised through sockets too.
        http("POST", f"/api/cases/{case_id}/accept", role="operator", expected=403,
             json_body={"expected_revision": ready["revision"], "reason": "Operator may not accept."})
        accepted, _ = http("POST", f"/api/cases/{case_id}/accept", role="approver",
                           json_body={"expected_revision": ready["revision"], "reason": "Verified synthetic originals, exact source spans, model proposals and reconciliation over real HTTP."})
        check(report, "approver_explicitly_accepts_current_revision", accepted["accepted"] and accepted["accepted_by"] == "http_approver")
        http("POST", f"/api/cases/{case_id}/publish", role="approver", expected=403,
             json_body={"expected_revision": accepted["revision"]})
        published, _ = http("POST", f"/api/cases/{case_id}/publish", role="publisher",
                            json_body={"expected_revision": accepted["revision"]})
        repeated, _ = http("POST", f"/api/cases/{case_id}/publish", role="publisher",
                           json_body={"expected_revision": accepted["revision"]})
        check(report, "repeated_publication_is_idempotent", not published["duplicate"] and repeated["duplicate"]
              and repeated["id"] == published["id"] and repeated["fingerprint"] == published["fingerprint"])
        report["publication"] = {"first": published, "second": repeated}
        final_case, _ = http("GET", f"/api/cases/{case_id}", role="reader")
        save_json(output / "case-published.json", final_case)
        check(report, "reader_observes_published_revision", final_case["published"] and final_case["accepted"])
        audit, _ = http("GET", f"/api/cases/{case_id}/audit", role="reader")
        save_json(output / "audit.json", audit)
        report["audit_joins"] = []
        server_events = json_log_records(output / "server.log")
        for item in uploads:
            ingestion = [event for event in audit if event["action"] == "document.ingested" and event["document_id"] == item["document_id"]]
            processing = [event for event in audit if event["action"] == "document.processed" and event["document_id"] == item["document_id"]]
            worker_events = [event for event in events if event.get("job_id") == item["job_id"]]
            traced = [event for event in server_events if event.get("trace_id") == item["upload_request_id"]]
            linked = (len(ingestion) == len(processing) == len(worker_events) == len(traced) == 1
                      and ingestion[0]["details"]["request_id"] == item["upload_request_id"]
                      and ingestion[0]["details"]["job_id"] == item["job_id"]
                      and ingestion[0]["actor"] == "http_operator" and processing[0]["actor"] == "worker"
                      and worker_events[0]["document_id"] == item["document_id"]
                      and traced[0]["method"] == "POST" and traced[0]["status"] == 202
                      and processing[0]["details"]["classification_proposal"] == observed_documents[item["document_id"]]["classification_proposal"])
            check(report, item["kind"] + "_request_audit_worker_join", linked)
            report["audit_joins"].append({"document_id": item["document_id"], "upload_request_id": item["upload_request_id"],
                                          "job_id": item["job_id"], "ingestion_audit_id": ingestion[0]["id"],
                                          "processing_audit_id": processing[0]["id"], "verified": linked})
        check(report, "audit_attributes_decisions_and_single_publication", len([event for event in audit if event["action"] == "case.published"]) == 1
              and any(event["action"] == "case.accepted" and event["actor"] == "http_approver" for event in audit)
              and any(event["action"] == "case.published" and event["actor"] == "http_publisher" for event in audit))
        archive_bytes, zip_receipt = http("GET", f"/api/cases/{case_id}/export.zip", role="reader")
        (output / "control-dossier.zip").write_bytes(archive_bytes)
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            exported = json.loads(archive.read("control-dossier.json"))
            manifest = json.loads(archive.read("manifest.json"))
            save_json(output / "export.json", exported)
            check(report, "reader_zip_contains_bound_originals", zip_receipt["content_type"] == "application/zip" and archive.testzip() is None
                  and len(manifest) == len(exported["documents"]) == 3
                  and all(digest(archive.read(path)) == value for path, value in manifest.items())
                  and {doc["sha256"] for doc in exported["documents"]} == {item["sha256"] for item in uploads}
                  and all(archive.read(f"originals/{item['document_id']}.pdf") == (output / "input-pdfs" / item["path"]).read_bytes() for item in uploads))
            check(report, "reader_zip_preserves_proposals_and_audit", exported["audit"] == audit
                  and exported["publication_id"] == published["id"] and exported["accepted_by"] == "http_approver"
                  and exported["published_by"] == "http_publisher"
                  and all(document["classification_provenance_status"] == "verified"
                          and document["classification_proposal"] == observed_documents[document["id"]]["classification_proposal"]
                          and document["parsed"]["sha256"] == document["sha256"]
                          and document["extraction"]["document_sha256"] == document["sha256"] for document in exported["documents"]))
        metrics, _ = http("GET", "/api/ready", role="reader")
        report["final_metrics"] = metrics
        check(report, "queue_drained_and_one_publication", metrics["queue"]["jobs"] == {"done": 3}
              and metrics["queue"]["publications"] == 1 and metrics["profile"] == "local-linear")
        check(report, "request_ids_are_unique_and_server_generated", len({record["x_request_id"] for record in report["requests"]}) == len(report["requests"])
              and all(record["x_request_id"] != "untrusted-client-value" for record in report["requests"]))
        check(report, "source_and_model_unchanged_after_execution", source_hashes(repo) == report["source_files_sha256"]
              and digest(model.read_bytes()) == EXPECTED_MODEL_SHA256)
        report["status"] = "passed"
        exit_code = 0
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = {"type": type(exc).__name__, "message": str(exc)[:8000]}
    finally:
        if worker_log:
            worker_log.close()
        if server and server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=10)
        if server_log:
            server_log.close()
        report["cleanup"]["server_stopped"] = bool(server and server.poll() is not None)
        report["cleanup"]["server_exit_code"] = server.returncode if server else None
        if temporary:
            private_path = Path(temporary.name)
            temporary.cleanup()
            report["cleanup"]["private_credentials_and_live_database_removed"] = not private_path.exists()
        else:
            report["cleanup"]["private_credentials_and_live_database_removed"] = True
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        report["elapsed_seconds"] = round(time.time() - report["started_at_unix"], 6)
        report["credentials_in_evidence"] = False
        save_json(output / "report.json", report)
        leaked = []
        for artifact in output.rglob("*"):
            if artifact.is_file():
                data = artifact.read_bytes()
                if any(token.encode() in data for token in tokens.values()):
                    leaked.append(str(artifact.relative_to(output)))
        if leaked:
            report["status"] = "failed"
            report["credentials_in_evidence"] = True
            report["credential_scan_failed_paths"] = leaked
            exit_code = 1
        report["credential_scan"] = "passed" if not leaked else "failed"
        if not report["cleanup"]["server_stopped"] or not report["cleanup"]["private_credentials_and_live_database_removed"]:
            report["status"] = "failed"
            exit_code = 1
        save_json(output / "report.json", report)
        save_json(output / "artifacts.json", {str(path.relative_to(output)): digest(path.read_bytes())
                                              for path in sorted(output.rglob("*")) if path.is_file() and path.name != "artifacts.json"})
    print(json.dumps({"status": report["status"], "checks": len(report["checks"]),
                      "http_requests": len(report["requests"]), "report": str(output / "report.json"),
                      "elapsed_seconds": report["elapsed_seconds"]}, indent=2))
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
