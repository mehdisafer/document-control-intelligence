"""Independent page-raster acceptance: real Linux sandbox, limits and identity."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import secrets
import tempfile
import unittest

from fastapi.testclient import TestClient
from PIL import Image
from reportlab.pdfgen.canvas import Canvas

from dci.api import create_app
from dci.config import Settings
from dci.worker import process_one


def two_page_pdf():
    output = io.BytesIO()
    canvas = Canvas(output, pagesize=(612, 792))
    for page in (1, 2):
        canvas.setFont("Helvetica", 17)
        canvas.drawString(60, 710, f"Original purchasing record, page {page}")
        canvas.setFont("Helvetica", 12)
        for row in range(16):
            canvas.drawString(
                60, 670 - row * 28,
                f"INV-TEST row {row + 1} quantity {row + 2} EUR, page {page} source evidence",
            )
        canvas.showPage()
    canvas.save()
    return output.getvalue()


class PreviewLimitsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dci-raster-limits-")
        self.root = Path(self.temp.name)
        self.token = secrets.token_urlsafe(32)
        auth = self.root / "auth.json"
        auth.write_text(json.dumps({
            "schema_version": "1.0",
            "actors": [{
                "name": "reader",
                "roles": ["reader"],
                "token_sha256": hashlib.sha256(self.token.encode()).hexdigest(),
            }],
        }))
        app = create_app(Settings(home=self.root / "state", auth_file=auth))
        self.client, self.store = TestClient(app), app.state.store
        self.slots = app.state.preview_slots
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.content = two_page_pdf()
        case_id = self.store.create_case("Preview independent", "synthetic")["id"]
        self.document_id = self.store.ingest(
            case_id, "INV-PREVIEW-TEST", "original.pdf", self.content, "synthetic"
        )["document_id"]
        self.route = f"/api/documents/{self.document_id}/preview"

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def process(self):
        result = process_one(self.store)
        self.assertIsNotNone(result)
        self.assertEqual(result["outcome"], "done", result)

    def test_auth_required_and_uninspected_original_denied(self):
        self.assertEqual(self.client.get(self.route).status_code, 401)
        self.assertEqual(self.client.get(self.route, headers=self.headers).status_code, 409)
        self.process()
        self.assertEqual(self.client.get(self.route).status_code, 401)
        self.assertEqual(self.client.get(self.route, headers={
            "Authorization": "Bearer invalid",
        }).status_code, 401)

    def test_two_different_real_pages_decoded_and_original_untouched(self):
        self.process()
        digests = []
        for page in (1, 2):
            response = self.client.get(self.route, params={"page": page}, headers=self.headers)
            self.assertEqual(response.status_code, 200, response.text[:120])
            self.assertEqual(response.headers["content-type"], "image/png")
            self.assertEqual(response.headers["x-document-page"], str(page))
            self.assertEqual(response.headers["cache-control"], "no-store")
            self.assertIn("object-src 'none'", response.headers["content-security-policy"])
            self.assertTrue(response.content.startswith(b"\x89PNG\r\n\x1a\n"))
            digests.append(hashlib.sha256(response.content).hexdigest())
            with Image.open(io.BytesIO(response.content)) as image:
                self.assertEqual(image.format, "PNG")
                self.assertGreaterEqual(image.width, 750)
                self.assertGreaterEqual(image.height, 950)
                self.assertIsNotNone(image.convert("RGB").getcolors(maxcolors=100000))
        self.assertNotEqual(digests[0], digests[1])
        original = self.client.get(
            f"/api/documents/{self.document_id}/original", headers=self.headers
        )
        self.assertEqual(original.status_code, 200)
        self.assertEqual(original.content, self.content)

    def test_out_of_bounds_page_rejected_without_renderer(self):
        self.process()
        for page in (-1, 0, 3, 100):
            with self.subTest(page=page):
                self.assertEqual(
                    self.client.get(self.route, params={"page": page},
                                    headers=self.headers).status_code, 422
                )

    def test_modified_immutable_source_is_service_integrity_error(self):
        self.process()
        blob = self.store.blob_path(hashlib.sha256(self.content).hexdigest())
        blob.write_bytes(self.content + b"\nunauthorized mutation")
        response = self.client.get(self.route, headers=self.headers)
        self.assertEqual(response.status_code, 503, response.text)
        self.assertIn("identity_mismatch", response.json()["detail"])

    def test_global_per_worker_admission_is_bounded_and_recovers(self):
        self.process()
        self.assertTrue(self.slots.acquire(blocking=False))
        self.assertTrue(self.slots.acquire(blocking=False))
        try:
            response = self.client.get(self.route, headers=self.headers)
            self.assertEqual(response.status_code, 429)
            self.assertEqual(response.json()["code"], "PREVIEW_BUSY")
            self.assertEqual(response.headers["retry-after"], "5")
        finally:
            self.slots.release()
            self.slots.release()
        self.assertEqual(self.client.get(self.route, headers=self.headers).status_code, 200)


if __name__ == "__main__":
    unittest.main()
