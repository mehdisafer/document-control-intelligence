"""Real bounded PDFium preview and authenticated API qualification.

Only synthetic PDFs are used; no UI/document rendering is mocked here.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import secrets
import tempfile
import unittest

from fastapi.testclient import TestClient
from PIL import Image, ImageStat
from pypdf import PdfWriter
from pypdf.actions import JavaScript
from reportlab.pdfgen import canvas

from dci.api import create_app
from dci.config import Settings
from dci.preview import MAX_PREVIEW_PIXELS, PNG_MAGIC, PreviewError, render_preview
from dci.worker import drain


class PreviewRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="dci-preview-tests-")
        cls.root = Path(cls.temporary.name)
        cls.original = cls.root / "two-pages.pdf"
        drawing = canvas.Canvas(str(cls.original), pagesize=(595.2756, 841.8898), invariant=1)
        drawing.setFont("Helvetica", 18)
        drawing.drawString(65, 755, "SYNTHETIC ORIGINAL - PAGE ONE")
        drawing.drawString(65, 715, "Purchase order PO-PREVIEW-100")
        drawing.showPage()
        drawing.setFont("Helvetica", 18)
        drawing.drawString(65, 755, "SYNTHETIC ORIGINAL - PAGE TWO")
        drawing.drawString(65, 715, "Invoice total EUR 125.00")
        drawing.showPage()
        drawing.save()
        cls.sha = hashlib.sha256(cls.original.read_bytes()).hexdigest()

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def preview(self, *, path=None, sha=None, page=1, max_pages=20, max_bytes=10485760):
        return render_preview(
            path or self.original, sha256=sha or self.sha,
            page_number=page, max_pages=max_pages, max_bytes=max_bytes,
        )

    def test_real_native_two_page_pngs_are_legible_and_distinct(self):
        images = [self.preview(page=number) for number in (1, 2)]
        self.assertNotEqual(hashlib.sha256(images[0]).digest(), hashlib.sha256(images[1]).digest())
        for data in images:
            self.assertTrue(data.startswith(PNG_MAGIC))
            with Image.open(io.BytesIO(data)) as image:
                self.assertEqual(image.format, "PNG")
                self.assertGreater(image.width, 700)
                self.assertGreater(image.height, 900)
                self.assertLessEqual(image.width * image.height, MAX_PREVIEW_PIXELS)
                self.assertGreater(ImageStat.Stat(image.convert("L")).stddev[0], 0.5)

    def test_page_byte_and_identity_budgets_are_enforced(self):
        for page in (0, -1, 3):
            with self.subTest(page=page), self.assertRaises(PreviewError) as raised:
                self.preview(page=page)
            self.assertEqual(raised.exception.code, "page_out_of_range")
        with self.assertRaises(PreviewError) as raised:
            self.preview(max_bytes=100)
        self.assertEqual(raised.exception.code, "size_budget")
        with self.assertRaises(PreviewError) as raised:
            self.preview(sha="0" * 64)
        self.assertEqual(raised.exception.code, "identity_mismatch")
        with self.assertRaises(PreviewError) as raised:
            self.preview(page=1, max_pages=1)
        self.assertEqual(raised.exception.code, "page_budget")

    def test_active_and_encrypted_content_stays_rejected(self):
        active = self.root / "active.pdf"
        writer = PdfWriter()
        writer.append(self.original)
        writer.add_open_action(JavaScript("app.alert('synthetic payload')"))
        writer.write(active)
        with self.assertRaises(PreviewError) as raised:
            self.preview(path=active, sha=hashlib.sha256(active.read_bytes()).hexdigest())
        self.assertEqual(raised.exception.code, "active_content")
        encrypted = self.root / "encrypted.pdf"
        writer = PdfWriter()
        writer.append(self.original)
        writer.encrypt("synthetic-password")
        writer.write(encrypted)
        with self.assertRaises(PreviewError) as raised:
            self.preview(path=encrypted, sha=hashlib.sha256(encrypted.read_bytes()).hexdigest())
        self.assertEqual(raised.exception.code, "encrypted_pdf")

    def test_authenticated_api_requires_inspected_original_and_valid_page(self):
        with tempfile.TemporaryDirectory(prefix="dci-preview-api-") as folder:
            state = Path(folder)
            token = secrets.token_urlsafe(32)
            actors = state / "actors.json"
            actors.write_text(json.dumps({"schema_version": "1.0", "actors": [
                {"name": "preview-operator", "roles": ["operator", "reader"],
                 "token_sha256": hashlib.sha256(token.encode()).hexdigest()}
            ]}))
            app = create_app(Settings(home=state / "store", auth_file=actors))
            headers = {"Authorization": "Bearer " + token}
            with TestClient(app) as client:
                created = client.post("/api/cases", headers=headers, json={"name": "Synthetic preview"})
                self.assertEqual(created.status_code, 201, created.text)
                case_id = created.json()["id"]
                uploaded = client.post(
                    f"/api/cases/{case_id}/documents",
                    params={"document_key": "PREVIEW-01", "filename": "two-pages.pdf"},
                    content=self.original.read_bytes(),
                    headers={**headers, "Content-Type": "application/pdf"},
                )
                self.assertEqual(uploaded.status_code, 202, uploaded.text)
                document_id = uploaded.json()["document_id"]
                endpoint = f"/api/documents/{document_id}/preview/1"
                self.assertEqual(client.get(endpoint).status_code, 401)
                before = client.get(endpoint, headers=headers)
                self.assertEqual(before.status_code, 409, before.text)
                self.assertEqual(before.json()["code"], "NOT_INSPECTED")
                outcomes = drain(app.state.store, max_jobs=10)
                self.assertEqual(outcomes[0]["outcome"], "done", outcomes)
                for page in (1, 2):
                    response = client.get(f"/api/documents/{document_id}/preview/{page}", headers=headers)
                    self.assertEqual(response.status_code, 200, response.text[:200])
                    self.assertEqual(response.headers["content-type"], "image/png")
                    self.assertEqual(response.headers["x-preview-page"], str(page))
                    self.assertEqual(response.headers["x-original-sha256"], self.sha)
                    self.assertTrue(response.content.startswith(PNG_MAGIC))
                invalid = client.get(f"/api/documents/{document_id}/preview/3", headers=headers)
                self.assertEqual(invalid.status_code, 422, invalid.text)
                self.assertEqual(invalid.json()["code"], "PAGE_OUT_OF_RANGE")
                original = client.get(f"/api/documents/{document_id}/original", headers=headers)
                self.assertEqual(original.content, self.original.read_bytes())
                blob = app.state.store.blob_path(self.sha)
                blob.write_bytes(b"%PDF-1.7\nmodified original")
                corrupted = client.get(endpoint, headers=headers)
                self.assertEqual(corrupted.status_code, 503, corrupted.text)
                self.assertEqual(corrupted.json()["code"], "IDENTITY_MISMATCH")
