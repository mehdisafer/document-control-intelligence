"""Real PDF/API/queue/review integration, without mocked parser or inference.

Only generated demo inputs are used. Database lease expiry and byte corruption
are explicitly injected faults; they are not simulated success paths. Baseline
extraction is exercised here. Local-model execution has its separate qualification.
"""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import hashlib
import io
import json
from pathlib import Path
import secrets
import sqlite3
import tempfile
import time
import unittest
import zipfile

from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter

from dci.api import create_app
from dci.auth import Auth
from dci.config import Settings
from dci.corpus import generate_demo
from dci.models import Extraction, ParsedDocument
from dci.parsing import runtime_version
from dci.rules import check_document
from dci.store import Store
from dci.worker import drain, process_one


class WorkflowIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = tempfile.TemporaryDirectory(prefix="dci-workflow-fixtures-")
        cls.corpus_root = Path(cls.fixtures.name)
        cls.manifest = generate_demo(cls.corpus_root, seed=744)

    @classmethod
    def tearDownClass(cls):
        cls.fixtures.cleanup()

    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory(prefix="dci-workflow-state-")
        self.root = Path(self.workspace.name)
        self.tokens = {name: secrets.token_urlsafe(32) for name in
                       ("operator", "approver", "publisher", "reader", "dual")}
        roles = {"operator": ["operator"], "approver": ["approver"],
                 "publisher": ["publisher"], "reader": ["reader"],
                 "dual": ["operator", "approver"]}
        self.auth_file = self.root / "actors.json"
        self.auth_file.write_text(json.dumps({"schema_version": "1.0", "actors": [
            {"name": name, "roles": roles[name],
             "token_sha256": hashlib.sha256(token.encode()).hexdigest()}
            for name, token in self.tokens.items()
        ]}))
        self.start_app()

    def tearDown(self):
        self.client.close()
        self.workspace.cleanup()

    def start_app(self, **settings):
        if hasattr(self, "client"):
            self.client.close()
        self.settings = Settings(home=self.root / "state", auth_file=self.auth_file, **settings)
        self.app = create_app(self.settings)
        self.store = self.app.state.store
        self.client = TestClient(self.app)

    def headers(self, actor="operator", **extra):
        return {"Authorization": f"Bearer {self.tokens[actor]}", **extra}

    def records(self, scenario, *, version=None):
        return [record for record in self.manifest["documents"]
                if record["scenario"] == scenario and not record.get("resubmission")
                and (version is None or record["version"] == version)]

    def upload(self, case_id, record, **kwargs):
        content = kwargs.pop("content", (self.corpus_root / record["path"]).read_bytes())
        return self.client.post(f"/api/cases/{case_id}/documents", params={
            "document_key": kwargs.pop("document_key", record["document_key"]),
            "filename": "../../untrusted-name.pdf",
        }, content=content, headers=self.headers(**{"Content-Type": "application/pdf"}), **kwargs)

    def new_case(self, scenario="accepted", *, process=True, version=None):
        response = self.client.post("/api/cases", json={"name": f"Synthetic {scenario}"}, headers=self.headers())
        self.assertEqual(response.status_code, 201, response.text)
        case_id = response.json()["id"]
        docs = []
        for record in self.records(scenario, version=version):
            response = self.upload(case_id, record)
            self.assertEqual(response.status_code, 202, response.text)
            docs.append((record, response.json()["document_id"]))
        if process:
            results = drain(self.store, max_jobs=100)
            self.assertEqual(len(results), len(docs))
            self.assertTrue(all(result["outcome"] == "done" for result in results), results)
        return case_id, docs

    def get_case(self, case_id):
        response = self.client.get(f"/api/cases/{case_id}", headers=self.headers("reader"))
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def get_document(self, document_id):
        response = self.client.get(f"/api/documents/{document_id}", headers=self.headers("reader"))
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def accept(self, case_id, *, actor="approver", revision=None):
        current = self.get_case(case_id)
        return self.client.post(f"/api/cases/{case_id}/accept", headers=self.headers(actor), json={
            "expected_revision": current["revision"] if revision is None else revision,
            "reason": "Reviewed the synthetic originals, source citations and reconciliation.",
        })

    def publish(self, case_id, *, revision=None):
        current = self.get_case(case_id)
        return self.client.post(f"/api/cases/{case_id}/publish", headers=self.headers("publisher"), json={
            "expected_revision": current["revision"] if revision is None else revision,
        })

    def test_api_authentication_roles_body_budget_and_unknown_fields(self):
        self.assertEqual(self.client.get("/api/cases").status_code, 401)
        self.assertEqual(self.client.get("/api/cases", headers={"Authorization": "Bearer invalid"}).status_code, 401)
        denied = self.client.post("/api/cases", json={"name": "Reader cannot mutate"}, headers=self.headers("reader"))
        self.assertEqual(denied.status_code, 403)
        invalid = self.client.post("/api/cases", json={"name": "Strict", "accepted_by": "attacker"}, headers=self.headers())
        self.assertEqual(invalid.status_code, 422)
        oversize = self.client.post("/api/cases", content=b'"' + b"x" * 17_000 + b'"',
                                   headers=self.headers(**{"Content-Type": "application/json"}))
        self.assertEqual(oversize.status_code, 413)
        self.assertEqual(oversize.json()["code"], "JSON_BODY_BUDGET")
        invalid_length = self.client.post("/api/cases", content=b"{}",
            headers=self.headers(**{"Content-Type": "application/json", "Content-Length": "invalid"}))
        self.assertEqual(invalid_length.status_code, 400)
        self.assertEqual(invalid_length.json()["code"], "INVALID_CONTENT_LENGTH")

    def test_auth_configuration_rejects_actor_with_no_role(self):
        data = json.loads(self.auth_file.read_text())
        data["actors"][0]["roles"] = []
        self.auth_file.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            Auth(self.auth_file)

    def test_real_pdf_review_explicit_acceptance_idempotent_publication_and_export(self):
        case_id, docs = self.new_case(process=False)
        before = self.client.get(f"/api/documents/{docs[0][1]}/original", headers=self.headers("reader"))
        self.assertEqual(before.status_code, 409)
        self.assertEqual(before.json()["code"], "NOT_INSPECTED")
        self.assertEqual(self.accept(case_id).json()["code"], "NOT_ELIGIBLE")
        results = drain(self.store)
        self.assertTrue(all(result["outcome"] == "done" and result["decision"] == "eligible" for result in results), results)
        current = self.get_case(case_id)
        self.assertTrue(current["eligible_for_acceptance"])
        self.assertFalse(current["accepted"])
        self.assertFalse(current["published"])
        self.assertEqual(self.publish(case_id).json()["code"], "NOT_ACCEPTED")
        self.assertEqual(self.accept(case_id, actor="operator").status_code, 403)
        for record, document_id in docs:
            result = self.get_document(document_id)
            self.assertEqual(result["filename"], "untrusted-name.pdf")
            self.assertNotIn("lease_token", result["job"])
            self.assertEqual(result["extraction"]["kind"], record["expected_kind"])
            pages = {page["number"]: page for page in result["parsed"]["pages"]}
            for field in result["extraction"]["fields"].values():
                for citation in field["evidence"]:
                    self.assertEqual(pages[citation["page"]]["text"][citation["start"]:citation["end"]], citation["quote"])
            original = self.client.get(f"/api/documents/{document_id}/original", headers=self.headers("reader"))
            self.assertEqual(original.status_code, 200)
            self.assertEqual(hashlib.sha256(original.content).hexdigest(), record["sha256"])
            self.assertEqual(original.headers["x-content-type-options"], "nosniff")
        self.assertEqual(self.accept(case_id).status_code, 200)
        first, second = self.publish(case_id), self.publish(case_id)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()["id"], second.json()["id"])
        self.assertFalse(first.json()["duplicate"])
        self.assertTrue(second.json()["duplicate"])
        payload = self.client.get(f"/api/cases/{case_id}/export", headers=self.headers("reader")).json()
        self.assertEqual(payload["publication_id"], first.json()["id"])
        self.assertEqual(payload["accepted_by"], "approver")
        self.assertEqual(payload["published_by"], "publisher")
        self.assertEqual(len(payload["documents"]), 3)
        archive = self.client.get(f"/api/cases/{case_id}/export.zip", headers=self.headers("reader"))
        self.assertEqual(archive.status_code, 200, archive.text[:100] if archive.status_code != 200 else "")
        with zipfile.ZipFile(io.BytesIO(archive.content)) as zipped:
            manifest = json.loads(zipped.read("manifest.json"))
            self.assertEqual(len(manifest), 3)
            for name, expected_hash in manifest.items():
                self.assertEqual(hashlib.sha256(zipped.read(name)).hexdigest(), expected_hash)
        self.assertEqual(self.store.metrics()["publications"], 1)
        audit = self.client.get(f"/api/cases/{case_id}/audit", headers=self.headers("reader")).json()
        self.assertEqual(sum(event["action"] == "case.published" for event in audit), 1)
        self.assertEqual(sum(event["action"] == "case.accepted" for event in audit), 1)

    def test_human_correction_audit_and_distinct_approver(self):
        case_id, docs = self.new_case("correction")
        record, document_id = next(pair for pair in docs if pair[0]["expected_kind"] == "invoice")
        self.assertFalse(self.get_case(case_id)["eligible_for_acceptance"])
        correction = {**record["correction"], "expected_revision": 0}
        denied = self.client.post(f"/api/documents/{document_id}/corrections", json=correction, headers=self.headers("reader"))
        self.assertEqual(denied.status_code, 403)
        invalid = self.client.post(f"/api/documents/{document_id}/corrections", json={**correction, "actor": "forged"}, headers=self.headers("dual"))
        self.assertEqual(invalid.status_code, 422)
        changed = self.client.post(f"/api/documents/{document_id}/corrections", json=correction, headers=self.headers("dual"))
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(changed.json()["revision"], 1)
        self.assertEqual(changed.json()["extraction"]["fields"]["total"]["origin"], "human")
        stale = self.client.post(f"/api/documents/{document_id}/corrections", json=correction, headers=self.headers("dual"))
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()["code"], "STALE_REVISION")
        self_approval = self.accept(case_id, actor="dual")
        self.assertEqual(self_approval.status_code, 403)
        self.assertEqual(self_approval.json()["code"], "SELF_APPROVAL")
        self.assertEqual(self.accept(case_id).status_code, 200)
        self.assertEqual(self.publish(case_id).status_code, 200)
        audit = self.store.audit(case_id)
        event = next(item for item in audit if item["action"] == "field.corrected")
        self.assertEqual(event["actor"], "dual")
        self.assertEqual(event["revision"], 1)
        self.assertGreater(event["at"], 0)
        self.assertEqual(event["details"]["old"]["normalized"], record["expected_fields"]["total"])
        self.assertEqual(event["details"]["new"]["normalized"], record["correction"]["value"])
        self.assertEqual(event["details"]["source_version"], 1)
        self.assertEqual(event["details"]["justification"], record["correction"]["reason"])

    def test_replacement_version_invalidates_acceptance_and_export(self):
        case_id, docs = self.new_case("versioned", version=1)
        _, old_id = next(pair for pair in docs if pair[0]["expected_kind"] == "invoice")
        replacement = self.records("versioned", version=2)[0]
        corrected = self.client.post(f"/api/documents/{old_id}/corrections", headers=self.headers(), json={
            "field": "total", "value": replacement["expected_fields"]["total"],
            "reason": "Explicit operator correction for the version-replacement qualification.", "expected_revision": 0,
        })
        self.assertEqual(corrected.status_code, 200)
        self.assertEqual(self.accept(case_id).status_code, 200)
        publication = self.publish(case_id).json()
        old_revision = self.get_case(case_id)["revision"]
        uploaded = self.upload(case_id, replacement)
        self.assertEqual(uploaded.status_code, 202)
        self.assertEqual(uploaded.json()["version"], 2)
        current = self.get_case(case_id)
        self.assertFalse(current["accepted"])
        self.assertFalse(current["published"])
        self.assertFalse(self.get_document(old_id)["current"])
        self.assertEqual(self.publish(case_id, revision=old_revision).json()["code"], "STALE_REVISION")
        self.assertEqual(self.client.get(f"/api/cases/{case_id}/export", headers=self.headers("reader")).json()["code"], "NOT_PUBLISHED")
        outdated = self.client.post(f"/api/documents/{old_id}/corrections", headers=self.headers(), json={
            "field": "total", "value": replacement["expected_fields"]["total"],
            "reason": "Must not change a superseded original.", "expected_revision": 1,
        })
        self.assertEqual(outdated.json()["code"], "STALE_REVISION")
        self.assertEqual(process_one(self.store)["outcome"], "done")
        self.assertEqual(self.accept(case_id).status_code, 200)
        second = self.publish(case_id).json()
        self.assertNotEqual(second["id"], publication["id"])
        payload = self.store.export(case_id)
        self.assertEqual(payload["supersedes_publication_id"], publication["id"])
        self.assertEqual(len(payload["documents"]), 3)
        invoice = next(doc for doc in payload["documents"] if doc["extraction"]["kind"] == "invoice")
        self.assertEqual(invoice["version"], 2)
        self.assertEqual(invoice["id"], uploaded.json()["document_id"])

    def test_redelivery_deduplicates_and_cross_case_invoice_publication_is_blocked(self):
        case_id, docs = self.new_case()
        record, document_id = docs[-1]
        before = self.get_case(case_id)["revision"]
        repeated = self.upload(case_id, record)
        self.assertEqual(repeated.status_code, 202)
        self.assertTrue(repeated.json()["duplicate"])
        self.assertEqual(repeated.json()["document_id"], document_id)
        self.assertEqual(self.get_case(case_id)["revision"], before)
        alias = self.upload(case_id, record, document_key="different-key")
        self.assertEqual(alias.json()["code"], "DUPLICATE_CONTENT")
        self.assertEqual(self.accept(case_id).status_code, 200)
        self.assertEqual(self.publish(case_id).status_code, 200)
        another, _ = self.new_case()
        self.assertEqual(self.accept(another).status_code, 200)
        denied = self.publish(another)
        self.assertEqual(denied.status_code, 409)
        self.assertEqual(denied.json()["code"], "INVOICE_ALREADY_PUBLISHED")
        self.assertEqual(self.store.metrics()["publications"], 1)

    def test_contradiction_abstention_partial_and_printed_instruction(self):
        for scenario, status, eligible in [
            ("contradictory", "contradictory", False),
            ("abstention", "review", False),
            ("partial", "partial", True),
            ("injection", "matched", True),
        ]:
            with self.subTest(scenario=scenario):
                case_id, docs = self.new_case(scenario)
                current = self.get_case(case_id)
                self.assertEqual(current["reconciliation"]["status"], status)
                self.assertEqual(current["eligible_for_acceptance"], eligible)
                self.assertFalse(current["accepted"])
                self.assertFalse(current["published"])
                if not eligible:
                    self.assertEqual(self.accept(case_id).json()["code"], "NOT_ELIGIBLE")
                if scenario == "injection":
                    record, document_id = next(pair for pair in docs if pair[0]["expected_kind"] == "invoice")
                    doc = self.get_document(document_id)
                    self.assertIn("SYSTEM OVERRIDE", doc["parsed"]["pages"][0]["text"])
                    self.assertTrue(any("untrusted_instruction_text_ignored" in warning for warning in doc["extraction"]["warnings"]))
                    self.assertEqual(doc["extraction"]["fields"]["total"]["normalized"], record["expected_fields"]["total"])
                    self.assertEqual(doc["profile"], "baseline")

    def test_crash_after_real_ocr_checkpoint_recovers_and_fences_old_attempt(self):
        record = next(item for item in self.records("scanned") if item["expected_kind"] == "invoice")
        case_id = self.store.create_case("OCR crash qualification", "operator")["id"]
        uploaded = self.upload(case_id, record).json()
        stopped = process_one(self.store, owner="crashed-worker", stop_after_parse=True)
        self.assertEqual(stopped["outcome"], "checkpoint_only")
        before = self.get_document(uploaded["document_id"])
        self.assertEqual(before["parsed"]["pages"][0]["method"], "ocr")
        self.assertIsNone(before["extraction"])
        with self.store.transaction() as conn:
            old_job = dict(conn.execute("SELECT * FROM jobs WHERE id=?", (uploaded["job_id"],)).fetchone())
            # Fault injection: a crashed worker's actual lease is made expired.
            conn.execute("UPDATE jobs SET lease_until=? WHERE id=?", (time.time()-1, uploaded["job_id"]))
        resumed = process_one(self.store, owner="recovery-worker")
        self.assertEqual(resumed["outcome"], "done", resumed)
        after = self.get_document(uploaded["document_id"])
        self.assertEqual(after["job"]["attempt"], 2)
        self.assertEqual(after["parsed"], before["parsed"], "The successful OCR checkpoint must be reused unchanged.")
        extraction = Extraction.model_validate(after["extraction"])
        self.assertFalse(self.store.finish(old_job, extraction, check_document(extraction), 0.01))
        self.assertFalse(self.store.checkpoint(old_job, ParsedDocument.model_validate(before["parsed"])))
        self.assertFalse(self.store.fail(old_job, "LATE_FAILURE"))
        self.assertEqual(self.get_document(uploaded["document_id"]), after)
        self.assertTrue(any(event["action"] == "job.lease_expired" for event in self.store.audit(case_id)))

    def test_cancellation_and_manual_retry_are_audited_and_fenced(self):
        record = self.records("accepted")[0]
        case_id = self.store.create_case("Cancellation", "operator")["id"]
        uploaded = self.upload(case_id, record).json()
        self.assertEqual(process_one(self.store, stop_after_parse=True)["outcome"], "checkpoint_only")
        with closing(self.store.connect()) as conn:
            old_job = dict(conn.execute("SELECT * FROM jobs WHERE id=?", (uploaded["job_id"],)).fetchone())
        path = f"/api/documents/{uploaded['document_id']}"
        self.assertEqual(self.client.post(path+"/cancel", headers=self.headers("reader")).status_code, 403)
        self.assertEqual(self.client.post(path+"/cancel", headers=self.headers()).status_code, 200)
        cancelled = self.get_document(uploaded["document_id"])
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertIsNone(process_one(self.store))
        self.assertFalse(self.store.fail(old_job, "TOO_LATE"))
        retry = self.client.post(path+"/retry", headers=self.headers(), json={"reason": "Explicit manual retry after operator cancellation."})
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(process_one(self.store)["outcome"], "done")
        events = {event["action"] for event in self.store.audit(case_id)}
        self.assertIn("job.cancelled", events)
        self.assertIn("job.manually_retried", events)

    def test_queue_backpressure_bytes_versions_and_page_limits(self):
        self.start_app(max_pending=1, max_pages=1, max_document_versions=1)
        case_id = self.store.create_case("Bounded queue", "operator")["id"]
        records = self.records("accepted")
        first = self.upload(case_id, records[0])
        self.assertEqual(first.status_code, 202)
        full = self.upload(case_id, records[1])
        self.assertEqual(full.status_code, 429)
        self.assertEqual(full.json()["code"], "QUEUE_FULL")
        self.assertEqual(full.headers["retry-after"], "5")
        self.assertEqual(process_one(self.store)["outcome"], "done")
        version = self.upload(case_id, records[0], content=(self.corpus_root/records[0]["path"]).read_bytes()+b"\n% New immutable version\n")
        self.assertEqual(version.json()["code"], "VERSION_BUDGET")
        writer = PdfWriter()
        reader = PdfReader(self.corpus_root/records[1]["path"])
        writer.add_page(reader.pages[0])
        writer.add_page(reader.pages[0])
        buffer = io.BytesIO()
        writer.write(buffer)
        many = self.upload(case_id, records[1], content=buffer.getvalue())
        self.assertEqual(many.status_code, 202)
        result = process_one(self.store)
        self.assertEqual(result["outcome"], "failed")
        self.assertEqual(result["error_code"], "page_budget")
        self.assertEqual(self.get_document(many.json()["document_id"])["status"], "review")
        self.start_app(max_bytes=1024)
        too_big = self.upload(case_id, records[2])
        self.assertEqual(too_big.status_code, 413)
        self.assertEqual(too_big.json()["code"], "SIZE_BUDGET")

    def test_corrupt_pdf_and_unavailable_local_model_never_publish(self):
        case_id = self.store.create_case("Corrupt input", "operator")["id"]
        record = self.records("accepted")[0]
        corrupt = self.upload(case_id, record, content=b"%PDF-1.7\ncorrupt object graph\n%%EOF")
        self.assertEqual(corrupt.status_code, 202)
        result = process_one(self.store)
        self.assertEqual(result["outcome"], "failed")
        self.assertEqual(result["error_code"], "corrupt_pdf")
        self.assertEqual(self.accept(case_id).json()["code"], "NOT_ELIGIBLE")
        self.start_app(profile="local-linear", model_path=self.root/"deliberately-unprovisioned.json",
                       max_attempts=2, retry_seconds=0)
        case_id = self.store.create_case("Unavailable local model", "operator")["id"]
        uploaded = self.upload(case_id, record)
        self.assertEqual(uploaded.status_code, 202)
        for _ in range(2):
            result = process_one(self.store)
            self.assertEqual(result["outcome"], "failed")
            self.assertEqual(result["error_code"], "MODEL_UNAVAILABLE")
        self.assertIsNone(process_one(self.store), "The retry budget must terminate.")
        doc = self.get_document(uploaded.json()["document_id"])
        self.assertEqual(doc["profile"], "local-linear")
        self.assertEqual(doc["status"], "review")
        self.assertEqual(doc["job"]["attempt"], 2)
        self.assertEqual(doc["job"]["status"], "failed")
        self.assertEqual(doc["error_code"], "MODEL_UNAVAILABLE")
        self.assertIsNotNone(doc["parsed"])
        self.assertIsNone(doc["extraction"], "No baseline/cloud output may be substituted after model failure.")
        self.assertEqual(self.publish(case_id).json()["code"], "NOT_ACCEPTED")

    def test_blob_tampering_cannot_be_published_or_downloaded(self):
        case_id, docs = self.new_case()
        self.assertEqual(self.accept(case_id).status_code, 200)
        record, document_id = docs[-1]
        blob = self.store.blob_path(record["sha256"])
        # Fault injection: out-of-band damage to a previously inspected original.
        blob.write_bytes(blob.read_bytes()+b"\n% injected storage corruption\n")
        original = self.client.get(f"/api/documents/{document_id}/original", headers=self.headers("reader"))
        self.assertEqual(original.status_code, 503)
        self.assertEqual(original.json()["code"], "BLOB_INTEGRITY")
        publication = self.publish(case_id)
        self.assertEqual(publication.status_code, 503, publication.text)
        self.assertEqual(publication.json()["code"], "BLOB_INTEGRITY")
        self.assertEqual(self.store.metrics()["publications"], 0)

    def test_changed_citation_is_revalidated_before_acceptance(self):
        case_id, docs = self.new_case()
        _, document_id = docs[-1]
        result = self.get_document(document_id)
        changed = result["extraction"]
        evidence = changed["fields"]["total"]["evidence"][0]
        # Fault injection: corrupt persisted proof while preserving its length and
        # arithmetically valid amount, so financial checks alone cannot detect it.
        evidence["quote"] = "X" + evidence["quote"][1:]
        with self.store.transaction() as conn:
            conn.execute("UPDATE documents SET extraction_json=? WHERE id=?", (json.dumps(changed), document_id))
        response = self.accept(case_id)
        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(response.json()["code"], "EVIDENCE_CHANGED")
        self.assertFalse(self.get_case(case_id)["accepted"])

    def test_queued_document_policy_cannot_change_silently(self):
        case_id = self.store.create_case("Processing policy binding", "operator")["id"]
        uploaded = self.upload(case_id, self.records("accepted")[0]).json()
        changed = self.settings.model_copy(update={"max_pages": self.settings.max_pages-1})
        worker_store = Store(changed)
        result = process_one(worker_store)
        self.assertEqual(result["outcome"], "policy_changed")
        document = self.get_document(uploaded["document_id"])
        self.assertEqual(document["error_code"], "PROCESSING_POLICY_CHANGED")
        self.assertIsNone(document["extraction"])
        self.assertFalse(self.get_case(case_id)["eligible_for_acceptance"])

    def test_manual_retry_reapplies_page_budget_to_existing_checkpoint(self):
        case_id = self.store.create_case("New budget on retry", "operator")["id"]
        record = self.records("accepted")[0]
        writer = PdfWriter()
        reader = PdfReader(self.corpus_root/record["path"])
        writer.add_page(reader.pages[0])
        writer.add_page(reader.pages[0])
        buffer = io.BytesIO()
        writer.write(buffer)
        uploaded = self.upload(case_id, record, content=buffer.getvalue()).json()
        self.assertEqual(process_one(self.store, stop_after_parse=True)["outcome"], "checkpoint_only")
        self.assertEqual(len(self.get_document(uploaded["document_id"])["parsed"]["pages"]), 2)
        path = f"/api/documents/{uploaded['document_id']}"
        self.assertEqual(self.client.post(path+"/cancel", headers=self.headers()).status_code, 200)
        self.start_app(max_pages=1)
        response = self.client.post(path+"/retry", headers=self.headers(), json={"reason": "Apply the stricter current page budget."})
        self.assertEqual(response.status_code, 200)
        result = process_one(self.store)
        self.assertEqual(result["outcome"], "failed", result)
        self.assertEqual(result["error_code"], "page_budget")
        self.assertIsNone(self.get_document(uploaded["document_id"])["extraction"])

    def test_obsolete_parser_checkpoint_is_reparsed_after_manual_retry(self):
        case_id = self.store.create_case("Parser version on retry", "operator")["id"]
        record = self.records("accepted")[0]
        uploaded = self.upload(case_id, record).json()
        self.assertEqual(process_one(self.store, stop_after_parse=True)["outcome"], "checkpoint_only")
        path = f"/api/documents/{uploaded['document_id']}"
        self.assertEqual(self.client.post(path+"/cancel", headers=self.headers()).status_code, 200)
        parsed = self.get_document(uploaded["document_id"])["parsed"]
        # Fault injection models a persisted checkpoint from an older deployment.
        parsed["parser_version"] = "obsolete-parser-runtime"
        with self.store.transaction() as conn:
            conn.execute("UPDATE documents SET parsed_json=? WHERE id=?", (json.dumps(parsed), uploaded["document_id"]))
        response = self.client.post(path+"/retry", headers=self.headers(), json={"reason": "Reprocess using the current parser runtime."})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(process_one(self.store)["outcome"], "done")
        self.assertEqual(self.get_document(uploaded["document_id"])["parsed"]["parser_version"], runtime_version())

    def test_transactional_duplicate_admission_concurrent_claims_and_audit_immutability(self):
        case_id = self.store.create_case("Concurrent admission", "operator")["id"]
        record = self.records("accepted")[0]
        raw = (self.corpus_root/record["path"]).read_bytes()
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.store.ingest(case_id, record["document_key"], "fixture.pdf", raw, "operator"), range(8)))
        self.assertEqual(sum(not result["duplicate"] for result in results), 1)
        self.assertEqual(len({result["document_id"] for result in results}), 1)
        for item in self.records("accepted")[1:]:
            self.assertEqual(self.upload(case_id, item).status_code, 202)
        with ThreadPoolExecutor(max_workers=4) as pool:
            claimed = list(pool.map(lambda index: self.store.claim(f"concurrent-{index}"), range(8)))
        claimed = [job for job in claimed if job is not None]
        self.assertEqual(len(claimed), self.settings.max_workers)
        self.assertEqual(len({job["id"] for job in claimed}), len(claimed))
        with self.assertRaises(sqlite3.IntegrityError):
            with self.store.transaction() as conn:
                conn.execute("UPDATE audit SET actor='forged' WHERE case_id=?", (case_id,))
        with self.assertRaises(sqlite3.IntegrityError):
            with self.store.transaction() as conn:
                conn.execute("DELETE FROM audit WHERE case_id=?", (case_id,))

    def test_concurrent_initial_migration_is_atomic(self):
        settings = Settings(home=self.root/"migration-race", auth_file=self.auth_file)
        with ThreadPoolExecutor(max_workers=4) as pool:
            stores = list(pool.map(lambda _: Store(settings), range(4)))
        with closing(stores[0].connect()) as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0], 1)
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")


if __name__ == "__main__":
    unittest.main()
