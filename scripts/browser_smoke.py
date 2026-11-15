#!/usr/bin/env python3
"""Real isolated-browser smoke test; never connects to an existing user browser.

Install the optional Playwright test dependency and its Chromium binary first.
The application server, browser and requests run inside this one process tree.
The supplied demo state is cloned before any UI mutation. Tokens are never
printed, included in traces, or stored in screenshots/report JSON.

Example:
  uv run --frozen --group browser python scripts/browser_smoke.py \
    --config outputs/demo-baseline/runtime/config.json \
    --credentials outputs/demo-baseline/runtime/credentials.json --output outputs/browser

Exit status: 0 executed checks passed; 1 executed check failed; 2 runtime blocked.
No screenshot or visual PASS is fabricated when browser startup is unavailable.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import importlib.metadata
import json
import os
import platform
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import uuid
import zipfile
from pathlib import Path
from urllib.parse import urlparse


class SmokeFailure(AssertionError):
    pass


def check(report: dict, name: str, condition: bool, detail: str = "") -> None:
    report["checks"].append({"name": name, "status": "passed" if condition else "failed", "detail": detail})
    if not condition:
        report["issues"].append({"check": name, "detail": detail})


def request(port: int, path: str, token: str | None = None, *, binary=False):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        headers = {"Authorization": "Bearer " + token} if token else {}
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        body = response.read(12_000_000)
        if response.status != 200:
            raise SmokeFailure(f"Fixture lookup returned HTTP {response.status} for {path}")
        return body if binary else json.loads(body)
    finally:
        connection.close()


def clone_state(config_path: Path, output: Path) -> Path:
    config = json.loads(config_path.read_text())
    source = Path(config["home"]).resolve()
    state = output / "private-test-state"
    state.mkdir(mode=0o700)
    for name in ("blobs", "checkpoints"):
        if (source / name).exists():
            shutil.copytree(source / name, state / name)
    # SQLite online backup is consistent even if the supplied demo still has WAL.
    original = sqlite3.connect(f"file:{source / 'control.db'}?mode=ro", uri=True)
    copied = sqlite3.connect(state / "control.db")
    try:
        original.backup(copied)
    finally:
        original.close()
        copied.close()
    auth = Path(config["auth_file"]).resolve()
    shutil.copyfile(auth, state / "auth.json")
    os.chmod(state / "auth.json", 0o600)
    config["home"] = str(state)
    config["auth_file"] = str(state / "auth.json")
    target = state / "config.json"
    target.write_text(json.dumps(config, indent=2))
    return target


def generate_browser_fixture(directory: Path, fixture_id: str | None = None) -> dict:
    """Render a fresh, internally consistent trio; never reuse published invoices.

    The recorded namespace can be passed with --fixture-id to reproduce these
    exact PDF bytes. Its default is unique to this run, including the supplier,
    order and invoice identities used by the global duplicate-invoice guard.
    """
    from dci.corpus import GENERATOR_VERSION, _line, _totals, _write_pdf

    namespace = fixture_id or uuid.uuid4().hex[:12].upper()
    if not re.fullmatch(r"[A-Za-z0-9]{1,24}", namespace):
        raise ValueError("fixture-id must contain 1 to 24 ASCII letters or digits")
    directory.mkdir()
    order_id = f"PO-BROWSER-{namespace}"
    supplier_id = f"SUP-BROWSER-{namespace}"
    lines = [_line("PART-100", "2", "125.50"), _line("PART-200", "3", "18.75")]
    documents = []
    for kind, prefix in [("purchase_order", "PO"), ("delivery_note", "DN"), ("invoice", "INV")]:
        identifier = f"{prefix}-BROWSER-{namespace}"
        fields = {"document_id": identifier, "purchase_order_id": order_id,
                  "supplier_id": supplier_id, "currency": "EUR",
                  "document_date": "2026-01-15", **_totals(lines)}
        path = directory / f"{kind}.pdf"
        _write_pdf(path, kind=kind, fields=fields, lines=lines, layout="classic_en",
                   notes=["Isolated browser qualification fixture; no real transaction."])
        documents.append({"path": path.name, "kind": kind, "document_key": identifier,
                          "document_id": identifier, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return {"namespace": namespace, "generator_version": GENERATOR_VERSION, "layout": "classic_en",
            "supplier_id": supplier_id, "purchase_order_id": order_id, "documents": documents}


def run(args) -> tuple[dict, int]:
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if output.exists():
        raise ValueError("Output must be a new directory; existing proof is never overwritten")
    output.mkdir(parents=True, mode=0o700)
    report = {
        "schema_version": "browser-smoke-1.1", "status": "started",
        "started_at_unix": time.time(),
        "execution": "fresh isolated headless browser; cloned application state; real HTTP server",
        "python": sys.version.split()[0], "platform": platform.platform(),
        "viewport": {"desktop": {"width": 1365, "height": 1000}, "mobile": {"width": 390, "height": 1000}},
        "checks": [], "issues": [], "screenshots": [], "console_errors": [], "page_errors": [],
        "unexpected_outbound_requests": [], "credentials_in_report": False,
        "source_files_sha256": {
            str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((root / "src/dci/static").glob("*")) if path.is_file()
        },
    }
    server = browser = context = playwright = log = None
    credentials = {}
    exit_code = 2
    try:
        report["playwright_version"] = importlib.metadata.version("playwright")
        from playwright.sync_api import sync_playwright
        config = clone_state(args.config.resolve(), output)
        settings = json.loads(config.read_text())
        if settings.get("batch_size", 4) < 3:
            raise ValueError("Browser qualification requires batch_size >= 3 for worker --once")
        report["fixture"] = generate_browser_fixture(output / "input-pdfs", args.fixture_id)
        credentials = json.loads(args.credentials.resolve().read_text())
        if not {"operator", "approver", "publisher", "reader"} <= credentials.keys():
            raise ValueError("Four demo role credentials are required")
        executable = root / ".venv/bin/dci"
        if not executable.exists():
            located = shutil.which("dci")
            if not located:
                raise ValueError("Install the project before the browser smoke test")
            executable = Path(located)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        log = (output / "server.log").open("w")
        server = subprocess.Popen([str(executable), "serve", "--config", str(config), "--host", "127.0.0.1", "--port", str(port)],
                                  cwd=root, stdout=log, stderr=subprocess.STDOUT)
        for _ in range(100):
            if server.poll() is not None:
                raise SmokeFailure("Application server exited during startup")
            try:
                if request(port, "/healthz")["status"] == "alive":
                    break
            except (OSError, SmokeFailure):
                time.sleep(.1)
        else:
            raise SmokeFailure("Application readiness deadline exceeded")
        report["http_server"] = "started_and_reachable"
        playwright = sync_playwright().start()
        launch_options = {"headless": True}
        if args.browser_executable:
            launch_options["executable_path"] = args.browser_executable
        try:
            browser = playwright.chromium.launch(**launch_options)
        except Exception as exc:
            report["status"] = "blocked"
            report["blocker"] = {"stage": "browser_launch", "type": type(exc).__name__, "message": str(exc)[:8000]}
            report["checks"].append({"name": "real_browser_execution", "status": "blocked",
                                     "detail": "No UI interaction or screenshot was executed."})
            return report, 2
        report["browser_version"] = browser.version
        context = browser.new_context(viewport={"width": 1365, "height": 1000}, accept_downloads=True)
        page = context.new_page()
        page.set_default_timeout(8000)
        phase = {"name": "startup"}
        page.on("console", lambda message: report["console_errors"].append({"phase": phase["name"], "text": message.text[:1000], "location": message.location}) if message.type == "error" else None)
        page.on("pageerror", lambda error: report["page_errors"].append({"phase": phase["name"], "text": str(error)[:1000]}))

        def allow_local(route):
            target = urlparse(route.request.url)
            if target.scheme in {"http", "https"} and (target.hostname != "127.0.0.1" or target.port != port):
                report["unexpected_outbound_requests"].append(route.request.url[:500])
                route.abort()
            else:
                route.continue_()
        context.route("**/*", allow_local)
        page.goto(f"http://127.0.0.1:{port}", wait_until="networkidle")
        phase["name"] = "invalid_login"
        page.locator("#token").fill("intentionally-invalid-ui-test-token")
        page.locator("#login-form button").click()
        page.wait_for_function("!document.getElementById('notice').hidden")
        check(report, "invalid_token_is_rejected", page.locator("#login-panel").is_visible() and not page.locator("#workspace").is_visible(), page.locator("#notice").inner_text())

        def login(role: str):
            phase["name"] = "login_" + role
            if page.locator("#workspace").is_visible():
                page.locator("#switch-actor").click()
            page.locator("#token").fill(credentials[role])
            # The final audit response follows the first case render. Merely
            # seeing the workspace can otherwise observe the prior identity's
            # retained rows while its new refresh is still in flight.
            with page.expect_response(lambda response: re.fullmatch(r"/api/cases/[^/]+/audit", urlparse(response.url).path) is not None and response.status == 200):
                page.locator("#login-form button").click()
            page.locator("#workspace").wait_for(state="visible")
            page.wait_for_function("document.querySelectorAll('#case-list .case-row').length > 0")
            check(report, "authenticated_" + role, role in page.locator("#actor-roles").inner_text())

        def select_case(case: dict):
            phase["name"] = "select_case"
            row = page.locator("#case-list .case-row").filter(has=page.get_by_text(case["name"], exact=True))
            with page.expect_response(lambda response: response.url.endswith(f"/api/cases/{case['id']}") and response.status == 200):
                with page.expect_response(lambda response: response.url.endswith(f"/api/cases/{case['id']}/audit") and response.status == 200):
                    row.click()
            page.wait_for_function("expected => document.getElementById('case-name').textContent === expected", arg=case["name"])

        def source_document(case: dict):
            full = request(port, f"/api/cases/{case['id']}", credentials["operator"])
            document = next((d for d in full["documents"] if "invoice" in d["filename"].lower()), full["documents"][0])
            with page.expect_response(lambda response: response.url.endswith(f"/api/documents/{document['id']}") and response.status == 200):
                with page.expect_response(lambda response: response.url.endswith(f"/api/documents/{document['id']}/original") and response.status == 200):
                    page.locator("#document-list .doc-row").filter(has_text=document["filename"]).click()
            page.locator("#field-rows tr").first.wait_for(state="visible")
            page.wait_for_function("(document.getElementById('original-frame').getAttribute('src') || '').startsWith('blob:')")
            return request(port, f"/api/documents/{document['id']}", credentials["operator"])

        login("operator")
        cases = request(port, "/api/cases", credentials["operator"])
        accepted = next((case for case in cases if "accepted" in case["name"].lower()), None)
        if accepted is None:
            raise SmokeFailure("Demo must include the accepted scenario")
        select_case(accepted)
        original_case = request(port, f"/api/cases/{accepted['id']}", credentials["operator"])
        doc = source_document(accepted)
        scalar_key = "total"
        source_field = doc["extraction"]["fields"][scalar_key]
        scalar_row = page.locator("#field-rows tr").filter(has=page.get_by_text("total", exact=True))
        scalar_row.click()
        page.locator("#evidence").wait_for(state="visible")
        check(report, "scalar_evidence_matches_original", source_field["evidence"][0]["quote"] in page.locator("#evidence-quote").inner_text())
        check(report, "original_pdf_is_served", request(port, f"/api/documents/{doc['id']}/original", credentials["operator"], binary=True).startswith(b"%PDF-"))
        check(report, "original_pdf_frame_loaded", (page.locator("#original-frame").get_attribute("src") or "").startswith("blob:"))
        check(report, "operator_cannot_accept_or_publish", page.locator("#accept-case").is_disabled() and page.locator("#publish-case").is_disabled())
        phase["name"] = "correction_modal"
        page.locator("#correct-field").click()
        check(report, "correction_dialog_has_value_and_reason", page.locator("#dialog").is_visible() and page.locator("#dialog-value").is_visible() and page.locator("#dialog-reason").is_visible())
        page.locator("#dialog-cancel").click()
        after_cancel = request(port, f"/api/cases/{accepted['id']}", credentials["operator"])
        check(report, "cancelled_correction_preserves_revision", after_cancel["revision"] == original_case["revision"])
        page.locator("#correct-kind").click()
        check(report, "document_kind_correction_dialog_opens", page.locator("#dialog").is_visible()
              and page.locator("#dialog-kind").is_visible() and page.locator("#dialog-reason").is_visible()
              and page.locator("#dialog-kind").input_value() == doc["extraction"]["kind"]
              and page.locator("#dialog-kind option").count() == 4)
        page.locator("#dialog-cancel").click()
        after_kind_cancel = request(port, f"/api/cases/{accepted['id']}", credentials["operator"])
        check(report, "cancelled_kind_correction_preserves_revision", after_kind_cancel["revision"] == original_case["revision"])

        if doc["extraction"]["line_items"]:
            page.locator("#line-items tr").filter(has=page.get_by_text("quantity", exact=True)).first.click()
            line_field = doc["extraction"]["line_items"][0]["fields"]["quantity"]
            check(report, "line_item_evidence_includes_actual_row", all(ev["quote"] in page.locator("#evidence").inner_text() for ev in line_field["evidence"]),
                  "A table column heading alone does not prove the quantity; show the row quotation too.")
        scalar_row.click()
        page.locator("#review").scroll_into_view_if_needed()
        page.screenshot(path=str(output / "desktop-review.png"), full_page=True)
        report["screenshots"].append("desktop-review.png")

        phase["name"] = "identity_switch"
        page.locator("#switch-actor").click()
        check(report, "logout_disables_new_dossier", page.locator("#new-case").is_disabled())
        check(report, "logout_disables_kind_correction", page.locator("#correct-kind").is_disabled())
        check(report, "logout_releases_original_preview", not page.locator("#original-frame").get_attribute("src"))
        login("reader")
        select_case(accepted)
        doc = source_document(accepted)
        page.locator("#field-rows tr").filter(has=page.get_by_text("total", exact=True)).click()
        check(report, "reader_controls_disabled", all(page.locator(selector).is_disabled() for selector in ["#new-case", "#upload-document", "#correct-field", "#correct-kind", "#accept-case", "#publish-case"]))
        page.set_viewport_size({"width": 390, "height": 1000})
        page.locator("#review").scroll_into_view_if_needed()
        page.screenshot(path=str(output / "mobile-review.png"), full_page=True)
        report["screenshots"].append("mobile-review.png")
        dimensions = page.evaluate("({viewport:innerWidth, document:document.documentElement.scrollWidth, body:document.body.scrollWidth})")
        report["mobile_dimensions"] = dimensions
        check(report, "mobile_has_no_document_horizontal_overflow", dimensions["document"] <= dimensions["viewport"] + 1, json.dumps(dimensions))
        page.set_viewport_size({"width": 1365, "height": 1000})

        login("operator")
        phase["name"] = "xss_literal_case_name"
        attack_name = '<img src=x onerror="window.__dciXssExecuted=1">'
        page.locator("#new-case").click()
        page.locator("#dialog-name").fill(attack_name)
        page.locator("#dialog-submit").click()
        page.locator("#dialog").wait_for(state="hidden")
        page.wait_for_function("expected => document.getElementById('case-name').textContent === expected", arg=attack_name)
        check(report, "untrusted_case_name_is_literal_text", page.locator("#case-name").inner_text() == attack_name and page.locator("#case-name img").count() == 0 and page.evaluate("window.__dciXssExecuted === undefined"))

        # Full browser-driven upload/accept/publish against a new cloned-state
        # dossier. Fresh real PDFs have new supplier/order/invoice identities;
        # the original demo's global duplicate-invoice guard remains enabled.
        phase["name"] = "new_browser_workflow"
        workflow_name = "Browser smoke / real document workflow / " + report["fixture"]["namespace"]
        page.locator("#new-case").click()
        page.locator("#dialog-name").fill(workflow_name)
        with page.expect_response(lambda response: response.request.method == "POST" and urlparse(response.url).path == "/api/cases" and response.status == 201) as created:
            page.locator("#dialog-submit").click()
        page.locator("#dialog").wait_for(state="hidden")
        page.wait_for_function("expected => document.getElementById('case-name').textContent === expected", arg=workflow_name)
        # Chromium may evict a CDP response body when the prior PDF iframe is
        # released. Verify the actual UI write through an authenticated GET;
        # never replace the form submission with a test-side POST.
        matches = [case for case in request(port, "/api/cases", credentials["operator"])
                   if case["name"] == workflow_name]
        if len(matches) != 1:
            raise SmokeFailure("Browser case creation did not persist exactly one uniquely named case")
        workflow = matches[0]
        check(report, "browser_case_creation_persisted", created.value.status == 201 and bool(workflow["id"]))
        fixture_dir = output / "input-pdfs"
        for index, fixture in enumerate(report["fixture"]["documents"]):
            page.locator("#upload-document").click()
            page.locator("#dialog-key").fill(fixture["document_key"])
            page.locator("#dialog-file").set_input_files(fixture_dir / fixture["path"])
            with page.expect_response(lambda response: response.request.method == "POST" and urlparse(response.url).path == f"/api/cases/{workflow['id']}/documents" and response.status == 202) as uploaded:
                page.locator("#dialog-submit").click()
            page.locator("#dialog").wait_for(state="hidden")
            page.wait_for_function("count => document.querySelectorAll('#document-list .doc-row').length === count", arg=index + 1)
            observed = request(port, f"/api/cases/{workflow['id']}", credentials["operator"])
            documents = [document for document in observed["documents"]
                         if document["document_key"] == fixture["document_key"]
                         and document["sha256"] == fixture["sha256"]]
            if len(documents) != 1:
                raise SmokeFailure("Browser upload readback differs from the selected original PDF")
            fixture["uploaded_document_id"] = documents[0]["id"]
            check(report, "browser_upload_original_persisted", uploaded.value.status == 202,
                  fixture["document_key"] + ": " + fixture["sha256"])
        worker = subprocess.run([str(executable), "worker", "--config", str(config), "--once"], cwd=root, capture_output=True, text=True, timeout=120)
        (output / "worker.log").write_text(worker.stdout + worker.stderr)
        if worker.returncode:
            raise SmokeFailure("Real document worker failed in cloned browser workflow")
        workflow_detail = request(port, f"/api/cases/{workflow['id']}", credentials["operator"])
        report["workflow_case_id"] = workflow["id"]
        check(report, "browser_uploads_processed_and_matched", workflow_detail["eligible_for_acceptance"] and len(workflow_detail["documents"]) == 3
              and workflow_detail["reconciliation"]["status"] == "matched"
              and all(document["status"] == "ready" for document in workflow_detail["documents"]))
        login("approver")
        select_case(workflow)
        check(report, "approver_can_accept_but_not_publish", page.locator("#accept-case").is_enabled() and page.locator("#publish-case").is_disabled())
        if page.locator("#accept-case").is_enabled():
            page.locator("#accept-case").click()
            page.locator("#dialog-reason").fill("Isolated browser smoke: reviewed synthetic originals and current evidence.")
            page.locator("#dialog-submit").click()
            page.locator("#dialog").wait_for(state="hidden")
            page.wait_for_function("document.getElementById('case-status').textContent === 'accepted'")
        login("publisher")
        select_case(workflow)
        check(report, "publisher_can_publish_accepted_revision", page.locator("#publish-case").is_enabled() and page.locator("#accept-case").is_disabled())
        if page.locator("#publish-case").is_enabled():
            page.locator("#publish-case").click()
            page.locator("#dialog-submit").click()
            page.locator("#dialog").wait_for(state="hidden")
            page.wait_for_function("document.getElementById('case-status').textContent === 'published'")
        page.locator("#export-case").wait_for(state="visible")
        if page.locator("#export-case").is_enabled():
            with page.expect_download() as captured:
                page.locator("#export-case").click()
            captured.value.save_as(output / "browser-control-dossier.zip")
            check(report, "browser_export_downloaded", (output / "browser-control-dossier.zip").read_bytes().startswith(b"PK"))
            with zipfile.ZipFile(output / "browser-control-dossier.zip") as archive:
                dossier = json.loads(archive.read("control-dossier.json"))
                manifest = json.loads(archive.read("manifest.json"))
                exported_ids = {document["extraction"]["fields"]["document_id"]["normalized"] for document in dossier["documents"]}
                expected_ids = {document["document_id"] for document in report["fixture"]["documents"]}
                check(report, "export_contains_new_invoice_and_bound_originals", dossier["case_id"] == workflow["id"]
                      and exported_ids == expected_ids and len(manifest) == 3 and archive.testzip() is None
                      and all(hashlib.sha256(archive.read(path)).hexdigest() == digest for path, digest in manifest.items()))
        else:
            check(report, "browser_export_downloaded", False, "Export remained disabled")
        check(report, "no_javascript_page_errors", not report["page_errors"], json.dumps(report["page_errors"]))
        unexpected_console = [event for event in report["console_errors"] if not (event["phase"] == "invalid_login" and "401" in event["text"])]
        check(report, "no_unexpected_console_errors", not unexpected_console, json.dumps(unexpected_console))
        check(report, "no_external_document_requests", not report["unexpected_outbound_requests"])
        exit_code = 1 if report["issues"] else 0
        report["status"] = "failed" if exit_code else "passed"
        return report, exit_code
    except Exception as exc:
        report["status"] = "failed" if browser else "blocked"
        report["error"] = {"type": type(exc).__name__, "message": str(exc)[:8000]}
        return report, 1 if browser else 2
    finally:
        # A crashed browser must not prevent server shutdown or auth cleanup.
        cleanup_errors = []
        for name, resource, method in [("context", context, "close"), ("browser", browser, "close"),
                                       ("playwright", playwright, "stop")]:
            if resource:
                try:
                    getattr(resource, method)()
                except Exception as exc:
                    cleanup_errors.append({"resource": name, "message": str(exc)[:1000]})
        if server and server.poll() is None:
            try:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=10)
            except Exception as exc:
                cleanup_errors.append({"resource": "server", "message": str(exc)[:1000]})
        if log:
            log.close()
        report["server_stopped"] = bool(server and server.poll() is not None)
        report["browser_closed"] = bool(browser and not browser.is_connected())
        report["finished_at_unix"] = time.time()
        # The cloned auth file is a temporary fixture, never proof to publish.
        private_state = output / "private-test-state"
        if private_state.exists():
            try:
                shutil.rmtree(private_state)
            except Exception as exc:
                cleanup_errors.append({"resource": "private_test_state", "message": str(exc)[:1000]})
        report["private_cloned_state_removed"] = not private_state.exists()
        if cleanup_errors:
            report["cleanup_errors"] = cleanup_errors
            if report["status"] == "passed":
                report["status"] = "failed"
        def redact(value):
            if isinstance(value, dict):
                return {key: redact(item) for key, item in value.items()}
            if isinstance(value, list):
                return [redact(item) for item in value]
            if isinstance(value, str):
                for secret in credentials.values():
                    if isinstance(secret, str) and secret:
                        value = value.replace(secret, "[REDACTED]")
            return value
        safe_report = redact(report)
        report.clear()
        report.update(safe_report)
        for logfile in (output / "server.log", output / "worker.log"):
            if logfile.exists():
                logfile.write_text(redact(logfile.read_text()))
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--browser-executable", help="Optional isolated Chromium executable; never a remote-debugging address")
    parser.add_argument("--fixture-id", help="Optional ASCII letter/digit namespace to reproduce a recorded synthetic trio")
    args = parser.parse_args()
    report, exit_code = run(args)
    print(json.dumps({"status": report["status"], "checks_executed": len([c for c in report["checks"] if c["status"] != "blocked"]),
                      "screenshots": report["screenshots"], "report": str(args.output.resolve() / "report.json")}, indent=2))
    return 1 if exit_code == 0 and report["status"] != "passed" else exit_code


if __name__ == "__main__":
    raise SystemExit(main())
