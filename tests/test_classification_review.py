"""A real unknown-heading PDF can be reviewed without inventing model confidence."""

import hashlib
import io
import json
from pathlib import Path
import secrets
import tempfile
import unittest

from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from dci.api import create_app
from dci.config import Settings
from dci.corpus import generate_demo
from dci.models import Extraction
from dci.rules import check_document
from dci.worker import drain, process_one


def unknown_heading_invoice() -> bytes:
    output = io.BytesIO()
    pdf = canvas.Canvas(output, invariant=1)
    pdf.setTitle("Synthetic unclassified supplier document")
    pdf.setFont("Helvetica", 11)
    lines = [
        "SUPPLIER STATEMENT", "Document ID: INV-DEMO-001", "Purchase order: PO-DEMO-001",
        "Supplier ID: SYN-SUP-001", "Currency: EUR", "Document date: 2026-01-15",
        "SKU | Qty | Unit price | Net | Tax %", "PART-100 | 10 | 125.50 | 1255.00 | 20",
        "Subtotal: 1255.00", "Tax: 251.00", "Total: 1506.00",
        "Fictional purchasing document for explicit classification-review qualification.",
    ]
    for index, text in enumerate(lines):
        pdf.drawString(40, 780-index*30, text)
    pdf.showPage()
    pdf.save()
    return output.getvalue()


class ClassificationReviewIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = tempfile.TemporaryDirectory(prefix="dci-kind-fixtures-")
        cls.corpus = Path(cls.fixtures.name)
        cls.manifest = generate_demo(cls.corpus)
        cls.invoice_bytes = unknown_heading_invoice()

    @classmethod
    def tearDownClass(cls):
        cls.fixtures.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="dci-kind-state-")
        self.root = Path(self.temporary.name)
        roles = {"operator": ["operator"], "dual": ["operator", "approver"],
                 "approver": ["approver"], "publisher": ["publisher"], "reader": ["reader"]}
        self.tokens = {name: secrets.token_urlsafe(32) for name in roles}
        auth_file = self.root/"actors.json"
        auth_file.write_text(json.dumps({"schema_version": "1.0", "actors": [
            {"name": name, "roles": assigned, "token_sha256": hashlib.sha256(self.tokens[name].encode()).hexdigest()}
            for name, assigned in roles.items()
        ]}))
        self.app = create_app(Settings(home=self.root/"state", auth_file=auth_file))
        self.client = TestClient(self.app)
        self.store = self.app.state.store
        response = self.client.post("/api/cases", json={"name": "Unknown heading review"}, headers=self.headers())
        self.assertEqual(response.status_code, 201)
        self.case_id = response.json()["id"]
        for record in self.manifest["documents"]:
            if record["scenario"] != "accepted":
                continue
            content = self.invoice_bytes if record["expected_kind"] == "invoice" else (self.corpus/record["path"]).read_bytes()
            response = self.client.post(f"/api/cases/{self.case_id}/documents",
                params={"document_key": record["document_key"]}, content=content,
                headers={**self.headers(), "Content-Type": "application/pdf"})
            self.assertEqual(response.status_code, 202)
            if record["expected_kind"] == "invoice":
                self.document_id = response.json()["document_id"]
                self.document_key = record["document_key"]
                self.upload_trace_id = response.headers["X-Request-ID"]
                self.upload_job_id = response.json()["job_id"]
        results = drain(self.store)
        self.assertTrue(all(result["outcome"] == "done" for result in results), results)

    def tearDown(self):
        self.client.close()
        self.temporary.cleanup()

    def headers(self, actor="operator"):
        return {"Authorization": f"Bearer {self.tokens[actor]}"}

    def document(self):
        return self.client.get(f"/api/documents/{self.document_id}", headers=self.headers("reader")).json()

    def case(self):
        return self.client.get(f"/api/cases/{self.case_id}", headers=self.headers("reader")).json()

    def review(self, kind="invoice", actor="dual", revision=None, **extra):
        body = {"kind": kind, "reason": "The original is an invoice despite its generic supplier heading.",
                "expected_revision": self.document()["revision"] if revision is None else revision, **extra}
        return self.client.post(f"/api/documents/{self.document_id}/classification-review", headers=self.headers(actor), json=body)

    def accept(self, actor="approver"):
        return self.client.post(f"/api/cases/{self.case_id}/accept", headers=self.headers(actor), json={
            "reason": "Independent review of the synthetic source and explicit classification correction.",
            "expected_revision": self.case()["revision"],
        })

    def publish(self):
        return self.client.post(f"/api/cases/{self.case_id}/publish", headers=self.headers("publisher"),
                                json={"expected_revision": self.case()["revision"]})

    def test_unknown_kind_can_be_reviewed_accepted_and_exported_with_original_score(self):
        before = self.document()
        self.assertEqual(before["extraction"]["kind"], "unknown")
        self.assertEqual(before["extraction"]["classification_confidence"], 0)
        self.assertEqual(before["classification_proposal"]["kind"], "unknown")
        self.assertEqual(before["classification_provenance_status"], "verified")
        ingested = next(event for event in self.store.audit(self.case_id)
                        if event["action"] == "document.ingested" and event["document_id"] == self.document_id)
        self.assertEqual(ingested["details"]["request_id"], self.upload_trace_id)
        self.assertEqual(ingested["details"]["job_id"], self.upload_job_id)
        self.assertEqual(before["job"]["id"], self.upload_job_id)
        self.assertFalse(self.case()["eligible_for_acceptance"])
        changed = self.review()
        self.assertEqual(changed.status_code, 200, changed.text)
        document = changed.json()
        self.assertEqual(document["extraction"]["kind"], "invoice")
        self.assertEqual(document["extraction"]["classification_confidence"], 0)
        self.assertEqual(document["classification_proposal"], before["classification_proposal"])
        review = document["classification_review"]
        self.assertTrue(review["provenance_valid"])
        self.assertEqual(review["actor"], "dual")
        self.assertEqual(review["old_kind"], "unknown")
        self.assertEqual(review["new_kind"], "invoice")
        self.assertEqual(review["source_version"], 1)
        self.assertEqual(review["revision"], 1)
        self.assertGreater(review["at"], 0)
        self.assertEqual(document["checks"]["decision"], "eligible")
        # Without the authenticated Store audit context the ordinary model rule
        # still abstains; the evaluated model default has not been relaxed.
        self.assertEqual(check_document(Extraction.model_validate(document["extraction"])).decision, "review")
        self.assertTrue(self.case()["eligible_for_acceptance"])
        self.assertEqual(self.accept("dual").json()["code"], "SELF_APPROVAL")
        self.assertEqual(self.accept().status_code, 200)
        self.assertEqual(self.publish().status_code, 200)
        payload = self.client.get(f"/api/cases/{self.case_id}/export", headers=self.headers("reader")).json()
        exported = next(item for item in payload["documents"] if item["id"] == self.document_id)
        self.assertEqual(exported["classification_review"], review)
        self.assertEqual(exported["classification_proposal"]["confidence"], 0)
        self.assertEqual(exported["extraction"]["classification_confidence"], 0)
        self.assertTrue(any(event["action"] == "classification.reviewed" for event in payload["audit"]))

    def test_roles_invalid_kind_unknown_keys_and_stale_revision(self):
        self.assertEqual(self.review(actor="reader").status_code, 403)
        self.assertEqual(self.review(actor="approver").status_code, 403)
        self.assertEqual(self.review(kind="payment_authorization").status_code, 422)
        self.assertEqual(self.review(classification_confidence=1).status_code, 422)
        self.assertEqual(self.review(reason="   ").status_code, 422)
        self.assertEqual(self.review(revision=0).status_code, 200)
        self.assertEqual(self.review(revision=0).json()["code"], "STALE_REVISION")

    def test_review_to_unknown_preserves_abstention_and_invalidates_prior_acceptance(self):
        self.assertEqual(self.review().status_code, 200)
        self.assertEqual(self.accept().status_code, 200)
        self.assertEqual(self.publish().status_code, 200)
        fingerprint = self.case()["fingerprint"]
        changed = self.review(kind="unknown", reason="The evidence needs another classification review.")
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(changed.json()["extraction"]["classification_confidence"], 0)
        current = self.case()
        self.assertFalse(current["eligible_for_acceptance"])
        self.assertFalse(current["accepted"])
        self.assertFalse(current["published"])
        self.assertNotEqual(current["fingerprint"], fingerprint)
        self.assertEqual(self.publish().json()["code"], "NOT_ACCEPTED")

    def test_kind_review_does_not_replace_missing_field_evidence(self):
        # Explicit storage fault: preserve arithmetic, damage an actual citation.
        extraction = self.document()["extraction"]
        citation = extraction["fields"]["total"]["evidence"][0]
        citation["quote"] = "X"+citation["quote"][1:]
        with self.store.transaction() as conn:
            conn.execute("UPDATE documents SET extraction_json=? WHERE id=?", (json.dumps(extraction), self.document_id))
        self.assertEqual(self.review().status_code, 200)
        rejected = self.accept()
        self.assertEqual(rejected.status_code, 503)
        self.assertEqual(rejected.json()["code"], "EVIDENCE_CHANGED")

    def test_audit_free_override_and_tampered_confidence_cannot_be_accepted(self):
        extraction = self.document()["extraction"]
        extraction["kind"] = "invoice"
        extraction["classification_confidence"] = 1
        with self.store.transaction() as conn:
            conn.execute("UPDATE documents SET extraction_json=? WHERE id=?", (json.dumps(extraction), self.document_id))
        self.assertEqual(self.document()["classification_provenance_status"], "mismatch")
        self.assertFalse(self.case()["eligible_for_acceptance"])
        self.assertEqual(self.accept().json()["code"], "NOT_ELIGIBLE")
        self.assertEqual(self.review().json()["code"], "CLASSIFICATION_PROVENANCE")

    def test_tampered_review_chain_and_missing_original_proposal_are_blocked(self):
        self.assertEqual(self.review().status_code, 200)
        with self.store.transaction() as conn:
            # Deliberate out-of-band corruption bypasses the SQL immutability
            # trigger in this isolated test; no public route permits this edit.
            conn.execute("DROP TRIGGER audit_no_update")
            event = conn.execute("SELECT id,details_json FROM audit WHERE document_id=? AND action='classification.reviewed'", (self.document_id,)).fetchone()
            changed = json.loads(event["details_json"])
            changed["old_kind"] = "purchase_order"
            conn.execute("UPDATE audit SET details_json=? WHERE id=?", (json.dumps(changed), event["id"]))
        self.assertEqual(self.document()["classification_provenance_status"], "mismatch")
        self.assertFalse(self.document()["classification_review"]["provenance_valid"])
        self.assertFalse(self.case()["eligible_for_acceptance"])
        self.assertEqual(self.publish().json()["code"], "NOT_ACCEPTED")
        with self.store.transaction() as conn:
            processed = conn.execute("SELECT id,details_json FROM audit WHERE document_id=? AND action='document.processed'", (self.document_id,)).fetchone()
            details = json.loads(processed["details_json"])
            del details["classification_proposal"]
            conn.execute("UPDATE audit SET details_json=? WHERE id=?", (json.dumps(details), processed["id"]))
        self.assertEqual(self.document()["classification_provenance_status"], "unavailable")
        self.assertEqual(self.review().json()["code"], "CLASSIFICATION_PROVENANCE")

    def test_new_document_version_does_not_inherit_old_kind_review(self):
        self.assertEqual(self.review().status_code, 200)
        self.assertEqual(self.accept().status_code, 200)
        uploaded = self.client.post(f"/api/cases/{self.case_id}/documents", params={"document_key": self.document_key},
                                    content=self.invoice_bytes+b"\n% new immutable source version\n",
                                    headers={**self.headers(), "Content-Type": "application/pdf"})
        self.assertEqual(uploaded.status_code, 202)
        self.assertEqual(self.review(revision=1).json()["code"], "STALE_REVISION")
        self.assertEqual(process_one(self.store)["outcome"], "done")
        new_id = uploaded.json()["document_id"]
        new_doc = self.client.get(f"/api/documents/{new_id}", headers=self.headers("reader")).json()
        self.assertEqual(new_doc["version"], 2)
        self.assertEqual(new_doc["extraction"]["kind"], "unknown")
        self.assertIsNone(new_doc["classification_review"])
        self.assertFalse(self.case()["eligible_for_acceptance"])


if __name__ == "__main__":
    unittest.main()
