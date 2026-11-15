"""Actual sandboxed PDF page preview, authentication and resource limits."""

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


def sample_pdf(pages=2):
    output = io.BytesIO()
    canvas = Canvas(output, pagesize=(612, 792))
    for number in range(1, pages + 1):
        canvas.setFont("Helvetica", 17)
        canvas.drawString(60, 700, f"Original purchasing evidence page {number}")
        canvas.setFont("Helvetica", 12)
        for row in range(16):
            canvas.drawString(60, 665 - row * 27,
                              f"SKU-A{row:02d} quantity {row + 1} EUR: page {number} original source proof")
        canvas.showPage()
    canvas.save()
    return output.getvalue()


class OriginalPagePreviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="dci-preview-tests-")
        self.root = Path(self.temporary.name)
        self.token = secrets.token_urlsafe(32)
        identity = {
            "schema_version": "1.0", "actors": [{
                "name": "reader", "roles": ["reader"],
                "token_sha256": hashlib.sha256(self.token.encode()).hexdigest(),
            }],
        }
        self.authfile = self.root / "actors.json"
        self.authfile.write_text(json.dumps(identity))
        self.settings = Settings(home=self.root / "data", auth_file=self.authfile)
        self.app = create_app(self.settings)
        self.store = self.app.state.store
        self.client = TestClient(self.app)
        self.content = sample_pdf()
        row = self.store.create_case("Original preview synthetic", "test")
        self.case_id = row["id"]
        self.document_id = self.store.ingest(row["id"], "INV-PREVIEW", "original.pdf", self.content, "test")["document_id"]
        self.url = f"/api/documents/{self.document_id}/preview"
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def tearDown(self):
        self.client.close()
        self.temporary.cleanup()

    def process(self):
        result = process_one(self.store)
        self.assertIsNotNone(result)
        self.assertEqual(result["outcome"], "done", result)

    def test_original_preview_requires_inspection_and_authorized_identity(self):
        self.assertEqual(self.client.get(self.url).status_code, 401)
        self.assertEqual(self.client.get(self.url, headers=self.headers).status_code, 409)
        self.process()
        self.assertEqual(self.client.get(self.url).status_code, 401)
        self.assertEqual(self.client.get(self.url, headers={"Authorization": "Bearer wrong"}).status_code, 401)

    def test_two_readable_pages_are_real_distinct_rasters(self):
        self.process()
        hashes = []
        for page in (1, 2):
            response = self.client.get(self.url, params={"page": page}, headers=self.headers)
            self.assertEqual(response.status_code, 200, response.text[:120])
            self.assertTrue(response.content.startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertIn("image/png", response.headers["content-type"])
            self.assertEqual(response.headers["x-preview-page"], str(page))
            self.assertEqual(response.headers["x-original-sha256"], hashlib.sha256(self.content).hexdigest())
            self.assertEqual(response.headers["cache-control"], "no-store")
            self.assertEqual(response.headers["x-content-type-options"], "nosniff")
            self.assertIn("object-src 'none'", response.headers["content-security-policy"])
            hashes.append(hashlib.sha256(response.content).hexdigest())
            with Image.open(io.BytesIO(response.content)) as image:
                self.assertEqual(image.format, "PNG")
                self.assertGreaterEqual(image.width, 800)
                self.assertGreaterEqual(image.height, 1000)
                colors = image.convert("RGB").getcolors(maxcolors=100000)
                self.assertIsNotNone(colors)
                self.assertGreater(len(colors), 2, "A blank placeholder is not a readable page")
        self.assertNotEqual(hashes[0], hashes[1], "Distinct page content must produce distinct rasters")
        original = self.client.get(
            f"/api/documents/{self.document_id}/original", headers=self.headers,
        )
        self.assertEqual(original.status_code, 200)
        self.assertEqual(original.content, self.content, "Preview must never rewrite original bytes")

    def test_page_out_of_range_fails_before_invoking_renderer(self):
        self.process()
        for page in (-1, 0, 3, 200):
            with self.subTest(page=page):
                response = self.client.get(self.url, params={"page": page}, headers=self.headers)
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.json()["code"], "INVALID_PAGE")
        self.assertEqual(self.client.get(self.url, params={"page": "abc"}, headers=self.headers).status_code, 422)

    def test_tampered_original_cannot_be_rasterized(self):
        self.process()
        blob = self.store.blob_path(hashlib.sha256(self.content).hexdigest())
        blob.write_bytes(self.content + b"\nmalicious-change")
        response = self.client.get(self.url, headers=self.headers)
        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(response.json()["code"], "IDENTITY_MISMATCH")

    def test_concurrency_cap_rejects_and_preserves_existing_slots(self):
        self.process()
        slots = self.app.state.preview_slots
        self.assertTrue(slots.acquire(blocking=False))
        self.assertTrue(slots.acquire(blocking=False))
        try:
            response = self.client.get(self.url, headers=self.headers)
            self.assertEqual(response.status_code, 429)
            self.assertEqual(response.json()["code"], "PREVIEW_BUSY")
        finally:
            slots.release()
            slots.release()
        self.assertEqual(self.client.get(self.url, headers=self.headers).status_code, 200)


if __name__ == "__main__":
    unittest.main()
