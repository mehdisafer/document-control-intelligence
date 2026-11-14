"""Explicit human repair of the frozen model's conservative demo abstention.

The original failed demo is read-only. All runtime databases/credentials are
temporary; only this harness, a synthetic audit report and raw log are retained.
This is a review-workflow proof, never a model-quality or automatic-success result.
"""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

from fastapi.testclient import TestClient

from dci.api import create_app
from dci.config import Settings
from dci.demo import provision_auth
from dci.operations import backup, restore
from dci.store import Store


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = OUT / "manual-recovery-report.json"
    if output.exists():
        raise SystemExit("Refusing to overwrite recovery evidence")
    original_result = OUT / "demo-local-linear/result.json"
    original_verifier = OUT / "verify-demo-local-linear.log"
    frozen_model = ROOT / "tmp/final-linear-model.json"
    originals = {str(path.relative_to(ROOT)): sha(path) for path in
                 (original_result, original_verifier, frozen_model)}
    source_before = json.loads((OUT / "source-before.json").read_text())["files"]
    original = json.loads(original_result.read_text())
    injection = next(case for case in original["cases"] if case["scenario"] == "injection")
    assert not injection["eligible"]
    assert len(original["restore"]["export_equality"]) == 6
    command = {"argv": [sys.executable, *sys.argv], "cwd": str(ROOT),
               "environment_overrides": {"PYTHONPATH": os.environ.get("PYTHONPATH")},
               "started_at": datetime.now(timezone.utc).isoformat(),
               "script_sha256": sha(Path(__file__)), "read_only_inputs_sha256": originals,
               "declared_scope": "One explicit source-based field repair, separate approval, idempotent publication and restoration; zero parser/model requests"}
    (OUT / "manual-recovery-command.json").write_text(json.dumps(command, indent=2) + "\n")
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="dci-human-recovery-") as temp:
        temp = Path(temp)
        first_restore = restore(OUT / "demo-local-linear/backup", temp / "runtime")
        auth_path, tokens = provision_auth(temp / "runtime")
        auth = json.loads(auth_path.read_text())
        # Give the correcting actor both roles so rejection proves the distinct-
        # actor rule, independently of ordinary role-based access control.
        next(actor for actor in auth["actors"] if actor["name"] == "demo-operator")["roles"].append("approver")
        auth_path.write_text(json.dumps(auth, indent=2) + "\n")
        settings = Settings(home=temp / "runtime", auth_file=auth_path, profile="local-linear",
                            model_path=frozen_model)
        with TestClient(create_app(settings)) as client:
            store = client.app.state.store
            requests = []
            def request(method, path, role="reader", expected=200, **kwargs):
                response = client.request(method, path, headers={"Authorization": f"Bearer {tokens[role]}"}, **kwargs)
                requests.append({"method": method, "path": path, "actor": f"demo-{role}",
                                 "expected_status": expected, "observed_status": response.status_code,
                                 "request_id": response.headers.get("X-Request-ID")})
                assert response.status_code == expected, response.text
                return response.json()
            case_id = injection["case_id"]
            initial = request("GET", f"/api/cases/{case_id}")
            assert not initial["eligible_for_acceptance"]
            invoice_id = next(document["id"] for document in initial["documents"] if document["document_key"] == "demo-injection-invoice")
            document = request("GET", f"/api/documents/{invoice_id}")
            old = document["extraction"]["fields"]["subtotal"]
            assert old["status"] == "abstained" and old["origin"] == "extracted"
            assert len(old["evidence"]) == 2
            source_quote = next(item for item in old["evidence"] if item["quote"] == "Subtotal: 1,255.00")
            page = next(page for page in document["parsed"]["pages"] if page["number"] == source_quote["page"])
            assert page["text"][source_quote["start"]:source_quote["end"]] == source_quote["quote"]
            reason = ("Human review of synthetic PDF page 1: the source explicitly reads 'Subtotal: 1,255.00'. "
                      "The unrelated footer is instruction text, not a monetary subtotal; confirmed 1255.00 against line amounts.")
            corrected = request("POST", f"/api/documents/{invoice_id}/corrections", "operator",
                                json={"field": "subtotal", "value": "1,255.00", "reason": reason,
                                      "expected_revision": document["revision"]})
            new = corrected["extraction"]["fields"]["subtotal"]
            assert new["normalized"] == "1255.00" and new["raw"] == "1,255.00"
            assert new["status"] == "corrected" and new["origin"] == "human" and new["reason"] == reason
            assert new["evidence"] == old["evidence"]
            assert corrected["version"] == document["version"] and corrected["revision"] == document["revision"] + 1
            assert corrected["classification_proposal"] == document["classification_proposal"]
            reviewed = request("GET", f"/api/cases/{case_id}")
            assert reviewed["eligible_for_acceptance"] and reviewed["reconciliation"]["status"] == "matched"
            denial = request("POST", f"/api/cases/{case_id}/accept", "operator", expected=403,
                             json={"expected_revision": reviewed["revision"], "reason": "Attempt to self-approve must be rejected."})
            assert denial["code"] == "SELF_APPROVAL"
            accepted = request("POST", f"/api/cases/{case_id}/accept", "approver",
                               json={"expected_revision": reviewed["revision"],
                                     "reason": "Independent review of the original subtotal quotation, human correction, retained conflict evidence and three-way controls."})
            assert accepted["accepted_by"] == "demo-approver"
            first = request("POST", f"/api/cases/{case_id}/publish", "publisher",
                            json={"expected_revision": reviewed["revision"]})
            second = request("POST", f"/api/cases/{case_id}/publish", "publisher",
                             json={"expected_revision": reviewed["revision"]})
            assert second["duplicate"] and first["id"] == second["id"]
            audit = request("GET", f"/api/cases/{case_id}/audit")
            event = next(entry for entry in reversed(audit) if entry["action"] == "field.corrected")
            assert event["actor"] == "demo-operator" and event["document_id"] == invoice_id
            assert event["details"]["old"] == old and event["details"]["new"] == new
            assert event["details"]["source_version"] == document["version"]
            assert event["details"]["justification"] == reason
            saved = backup(store, temp / "backup")
            restored = restore(temp / "backup", temp / "restored")
            restored_store = Store(Settings(home=temp / "restored"))
            exports = {}
            for case in original["cases"]:
                if "publication" in case or case["scenario"] == "injection":
                    left = store.export(case["case_id"])
                    right = restored_store.export(case["case_id"])
                    exports[case["scenario"]] = {"equal": left == right,
                        "payload_sha256": hashlib.sha256(json.dumps(left, sort_keys=True).encode()).hexdigest()}
            assert len(exports) == 7 and all(value["equal"] for value in exports.values())
            with closing(restored_store.connect()) as connection:
                integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            assert integrity == "ok" and store.metrics()["publications"] == 7
            report = {"schema_version": "human-recovery-evidence-1.0", "synthetic": True,
                      "source_commit": "3ff93109f3ea0d9c5f4bdfd598dd35bbd4513439",
                      "original_demo_strict_verifier_passed": False, "original_demo_published_cases": 6,
                      "supplemental_human_repair_passed": True, "publications_after_human_repair": 7,
                      "case_id": case_id, "document_id": invoice_id,
                      "source_version": document["version"], "source_sha256": document["sha256"],
                      "original_document_revision": document["revision"], "corrected_document_revision": corrected["revision"],
                      "source_quote": source_quote, "original_field": old, "corrected_field": new,
                      "classification_proposal_unchanged": document["classification_proposal"],
                      "correction_audit": event, "case_audit": audit,
                      "correcting_actor_roles": ["operator", "approver"],
                      "self_approval_denial": denial, "accepted_by": accepted["accepted_by"],
                      "publication": first, "repeated_publication": second,
                      "restored_exports": exports, "restored_database_integrity": integrity,
                      "backup_manifest": saved, "interrupted_jobs_requeued": restored["interrupted_jobs_requeued"],
                      "initial_restore_interrupted_jobs": first_restore["interrupted_jobs_requeued"],
                      "requests": requests, "parser_requests": 0, "model_requests": 0,
                      "credentials_or_live_database_retained": False,
                      "scope": "Explicit human repair of an abstention. This does not improve or replace the original model evaluation or failed automatic demo result."}
    report["original_evidence_and_model_unchanged"] = all(sha(ROOT / path) == digest for path, digest in originals.items())
    report["source_files_unchanged"] = all(sha(ROOT / path) == digest for path, digest in source_before.items())
    assert report["original_evidence_and_model_unchanged"] and report["source_files_unchanged"]
    report["elapsed_seconds"] = round(time.monotonic() - started, 6)
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: report[key] for key in ("original_demo_strict_verifier_passed", "supplemental_human_repair_passed",
          "publications_after_human_repair", "self_approval_denial", "accepted_by", "restored_database_integrity",
          "source_files_unchanged", "original_evidence_and_model_unchanged", "elapsed_seconds")}, indent=2))


if __name__ == "__main__":
    main()
