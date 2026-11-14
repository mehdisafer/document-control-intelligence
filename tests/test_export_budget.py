"""ZIP byte-budget regressions using real PDFs and a published temporary case.

Only the byte limit is reduced for inexpensive boundary checks. Authentication,
SQLite state, baseline processing, ZIP serialization and PDF bytes are real.
"""

import hashlib
import io
import json
from pathlib import Path
import secrets
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from fastapi.testclient import TestClient

from dci import api
from dci.config import Settings
from dci.corpus import _write_pdf
from dci.worker import process_one


class ExportBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory(prefix="dci-export-budget-")
        cls.addClassCleanup(temporary.cleanup)
        root = Path(temporary.name)
        token = secrets.token_urlsafe(32)
        auth = root / "auth.json"
        auth.write_text(json.dumps({"schema_version": "1.0", "actors": [{
            "name": "budget-reader", "roles": ["reader"],
            "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
        }]}), encoding="utf-8")
        auth.chmod(0o600)
        app = api.create_app(Settings(home=root / "runtime", auth_file=auth))
        cls.store = app.state.store
        cls.client = cls.enterClassContext(TestClient(app))
        cls.headers = {"Authorization": f"Bearer {token}"}
        case = cls.store.create_case("Café — export budget", "budget-operator")
        cls.case_id = case["id"]
        lines = [{"sku": "PART-EXPORT", "quantity": "2", "unit_price": "10.00",
                  "net_amount": "20.00", "tax_rate": "20"}]
        cls.originals = {}
        for kind, identifier in (("purchase_order", "PO-EXPORT-BUDGET"),
                                 ("delivery_note", "DN-EXPORT-BUDGET"),
                                 ("invoice", "INV-EXPORT-BUDGET")):
            path = root / f"{kind}.pdf"
            fields = {"document_id": identifier, "purchase_order_id": "PO-EXPORT-BUDGET",
                      "supplier_id": "SYN-SUP-BUDGET", "currency": "EUR",
                      "document_date": "2026-01-15", "subtotal": "20.00",
                      "tax": "4.00", "total": "24.00"}
            _write_pdf(path, kind=kind, fields=fields, lines=lines, layout="classic_en")
            content = path.read_bytes()
            ingested = cls.store.ingest(cls.case_id, identifier, path.name, content, "budget-operator")
            cls.originals[ingested["document_id"]] = content
            result = process_one(cls.store)
            if result is None or result["outcome"] != "done":
                raise AssertionError(f"Native PDF fixture did not process: {result}")
        case = cls.store.case(cls.case_id)
        if not case["eligible_for_acceptance"]:
            raise AssertionError(f"Synthetic case is not eligible: {case['reconciliation']}")
        cls.store.accept(cls.case_id, "budget-approver", "Vérifié: synthetic originals.", case["revision"])
        cls.store.publish(cls.case_id, "budget-publisher", case["revision"])
        cls.payload = cls.store.export(cls.case_id)
        cls.dossier_bytes = json.dumps(cls.payload, indent=2, ensure_ascii=False).encode("utf-8")
        cls.manifest = {f"originals/{doc['id']}.pdf": doc["sha256"] for doc in cls.payload["documents"]}
        cls.manifest_bytes = json.dumps(cls.manifest, indent=2).encode("utf-8")
        cls.original_size = sum(len(content) for content in cls.originals.values())
        cls.total_size = len(cls.dossier_bytes) + cls.original_size + len(cls.manifest_bytes)

    def export_with_limit(self, limit):
        with patch.object(api, "EXPORT_UNCOMPRESSED_BUDGET", limit):
            return self.client.get(f"/api/cases/{self.case_id}/export.zip", headers=self.headers)

    def assert_budget_response(self, response):
        self.assertEqual(response.status_code, 413, response.text)
        self.assertEqual(response.headers["content-type"], "application/json")
        self.assertEqual(response.json()["code"], "EXPORT_BUDGET")
        self.assertIn("uncompressed byte budget", response.json()["message"])

    def test_exact_total_boundary_preserves_json_and_originals(self):
        self.assertEqual(api.EXPORT_UNCOMPRESSED_BUDGET, 50 * 1024 * 1024)
        response = self.export_with_limit(self.total_size)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/zip")
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(archive.namelist(), ["control-dossier.json", *self.manifest, "manifest.json"])
            self.assertEqual(sum(member.file_size for member in archive.infolist()), self.total_size)
            self.assertEqual(archive.read("control-dossier.json"), self.dossier_bytes)
            self.assertEqual(archive.read("manifest.json"), self.manifest_bytes)
            for document_id, original in self.originals.items():
                name = f"originals/{document_id}.pdf"
                self.assertEqual(archive.read(name), original)
                self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), self.manifest[name])

    def test_manifest_makes_one_byte_over_total_budget_fail(self):
        limit = self.total_size - 1
        self.assertLessEqual(len(self.dossier_bytes) + self.original_size, limit)
        self.assert_budget_response(self.export_with_limit(limit))

    def test_metadata_is_bounded_even_when_all_originals_fit(self):
        limit = self.original_size + len(self.manifest_bytes)
        self.assertGreater(len(self.dossier_bytes), limit)
        self.assert_budget_response(self.export_with_limit(limit))

    def test_utf8_bytes_are_counted_instead_of_characters(self):
        character_size = len(self.dossier_bytes.decode("utf-8"))
        self.assertLess(character_size, len(self.dossier_bytes))
        limit = character_size + self.original_size + len(self.manifest_bytes)
        self.assert_budget_response(self.export_with_limit(limit))

    def test_streaming_still_rejects_changed_original(self):
        doc = self.payload["documents"][0]
        path = self.store.blob_path(doc["sha256"])
        original = path.read_bytes()
        try:
            path.write_bytes(original + b"changed synthetic bytes")
            response = self.client.get(f"/api/cases/{self.case_id}/export.zip", headers=self.headers)
            self.assertEqual(response.status_code, 503, response.text)
            self.assertEqual(response.json()["code"], "BLOB_INTEGRITY")
        finally:
            path.write_bytes(original)


if __name__ == "__main__":
    unittest.main()
