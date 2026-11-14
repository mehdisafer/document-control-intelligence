"""Real PDF -> API -> leased worker -> human decision -> exported control dossier."""

from contextlib import closing
import hashlib
import json
import platform
import resource
import secrets
import time
from pathlib import Path

from fastapi.testclient import TestClient

from .api import create_app
from .config import Settings
from .corpus import generate_demo
from .operations import backup, restore
from .worker import drain


def provision_auth(home: Path):
    home = Path(home)
    home.mkdir(parents=True, exist_ok=True)
    auth = home / "auth.json"
    credentials = home / "credentials.json"
    if auth.exists() or credentials.exists():
        raise ValueError("Actor credentials already exist; refusing to overwrite them")
    actors, tokens = [], {}
    for name, role in [("demo-operator", "operator"), ("demo-approver", "approver"),
                       ("demo-publisher", "publisher"), ("demo-reader", "reader")]:
        value = secrets.token_urlsafe(32)
        tokens[role] = value
        actors.append({"name": name, "roles": [role], "token_sha256": hashlib.sha256(value.encode()).hexdigest()})
    auth.write_text(json.dumps({"schema_version": "1.0", "actors": actors}, indent=2) + "\n")
    credentials.write_text(json.dumps(tokens, indent=2) + "\n")
    auth.chmod(0o600)
    credentials.chmod(0o600)
    return auth, tokens


def run_demo(output: Path, *, profile="baseline", model_path=None, llm_config_file=None):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("Demo output must be a new directory; retain previous evidence")
    output.mkdir(parents=True)
    started = time.monotonic()
    manifest = generate_demo(output / "corpus")
    home = output / "runtime"
    auth, tokens = provision_auth(home)
    settings = Settings(home=home, auth_file=auth, profile=profile, model_path=model_path,
                        llm_config_file=llm_config_file, max_pending=64)
    (home / "config.json").write_text(settings.model_dump_json(indent=2))
    client = TestClient(create_app(settings))
    store = client.app.state.store
    headers = {role: {"Authorization": f"Bearer {token}"} for role, token in tokens.items()}

    def request(method, path, role="operator", **kwargs):
        response = client.request(method, path, headers={**headers[role], **kwargs.pop("headers", {})}, **kwargs)
        if response.status_code >= 400:
            raise RuntimeError(f"Demo HTTP {response.status_code} at {path}: {response.text[:500]}")
        return response

    cases, jobs = {}, []
    for case in manifest["cases"]:
        data = request("POST", "/api/cases", json={"name": f"Aster Procurement · {case['scenario']}"}).json()
        cases[case["case_key"]] = {"case_id": data["id"], "scenario": case["scenario"], "uploads": []}
    for document in manifest["documents"]:
        case = cases[document["case_key"]]
        result = request("POST", f"/api/cases/{case['case_id']}/documents",
                         params={"document_key": document["document_key"], "filename": Path(document["path"]).name},
                         headers={"Content-Type": "application/pdf"},
                         content=(output / "corpus" / document["path"]).read_bytes()).json()
        case["uploads"].append({**result, "source": document["path"]})
        if "correction" in document:
            case["correction"] = {"document_id": result["document_id"], **document["correction"]}
        # Exercise v1 processing before v2 replaces it, rather than only cancelling v1.
        if document["scenario"] == "versioned" and document["version"] == 1:
            jobs.extend(drain(store))
    jobs.extend(drain(store))
    for case in cases.values():
        case_id = case["case_id"]
        before = request("GET", f"/api/cases/{case_id}", "reader").json()
        case["initial_reconciliation"] = before["reconciliation"]
        if "correction" in case:
            c = case["correction"]
            document = request("GET", f"/api/documents/{c['document_id']}", "reader").json()
            if document["status"] == "ready":
                request("POST", f"/api/documents/{c['document_id']}/corrections",
                        json={"field": c["field"], "value": c["value"], "reason": c["reason"],
                              "expected_revision": document["revision"]})
        state = request("GET", f"/api/cases/{case_id}", "reader").json()
        case["final_reconciliation"] = state["reconciliation"]
        case["eligible"] = state["eligible_for_acceptance"]
        if state["eligible_for_acceptance"]:
            request("POST", f"/api/cases/{case_id}/accept", "approver",
                    json={"expected_revision": state["revision"],
                          "reason": "Synthetic demonstration: source evidence and current reconciliation reviewed explicitly."})
            publication = request("POST", f"/api/cases/{case_id}/publish", "publisher",
                                  json={"expected_revision": state["revision"]}).json()
            second = request("POST", f"/api/cases/{case_id}/publish", "publisher",
                             json={"expected_revision": state["revision"]}).json()
            case["publication"] = publication
            case["idempotent_publication"] = second["duplicate"] and second["id"] == publication["id"]
            exported = request("GET", f"/api/cases/{case_id}/export", "reader").json()
            (output / f"{case['scenario']}-dossier.json").write_text(json.dumps(exported, indent=2) + "\n")
            archive = request("GET", f"/api/cases/{case_id}/export.zip", "reader")
            (output / f"{case['scenario']}-dossier.zip").write_bytes(archive.content)
            case["export_sha256"] = hashlib.sha256(archive.content).hexdigest()
        case["audit"] = request("GET", f"/api/cases/{case_id}/audit", "reader").json()
    saved = backup(store, output / "backup")
    restored = restore(output / "backup", output / "restored")
    restored_store = type(store)(Settings(home=output / "restored"))
    restore_checks = {}
    for case in cases.values():
        if "publication" in case:
            original, recovered = store.export(case["case_id"]), restored_store.export(case["case_id"])
            restore_checks[case["scenario"]] = original == recovered
    with closing(store.connect()) as conn:
        database_integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    result = {"schema_version": "demo-evidence-1.0", "profile": profile,
              "synthetic": True, "transport": "FastAPI ASGI TestClient; real parser/OCR/model/storage",
              "elapsed_seconds": time.monotonic()-started,
              "hardware": {"platform": platform.platform(), "python": platform.python_version(),
                           "peak_parent_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},
              "manifest_sha256": hashlib.sha256((output / "corpus/manifest.json").read_bytes()).hexdigest(),
              "settings": settings.processing_policy(), "jobs": jobs, "cases": list(cases.values()),
              "restore": {"manifest": saved, "result": restored, "export_equality": restore_checks,
                          "database_integrity": database_integrity},
              "external_inference_requests": 0, "external_api_cost_usd": 0,
              "cost_note": "No paid API used. Host electricity/cloud-runner cost was not metered."}
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
