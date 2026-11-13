from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from pypdf import PdfReader, PdfWriter
from pypdf.actions import JavaScript
from reportlab.pdfgen import canvas

from dci.corpus import generate_demo
from dci.parsing import ParseError, parse_document, runtime_version


class ParserIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="dci-parser-tests-")
        cls.root = Path(cls.temporary.name)
        cls.manifest = generate_demo(cls.root / "demo")
        cls.native = cls.root / "demo/documents/demo/demo-accepted-invoice-v1.pdf"
        cls.scan = cls.root / "demo/documents/demo/demo-scanned-invoice-v1.pdf"

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def assert_code(self, path, expected, **kwargs):
        with self.assertRaises(ParseError) as raised:
            parse_document(path, **kwargs)
        self.assertEqual(raised.exception.code, expected)

    def test_native_pdf_retains_exact_offsets_and_boxes(self):
        parsed = parse_document(self.native)
        self.assertEqual(parsed.sha256, hashlib.sha256(self.native.read_bytes()).hexdigest())
        page = parsed.pages[0]
        self.assertEqual(page.method, "native")
        self.assertIn("Document ID: INV-DEMO-001", page.text)
        self.assertGreater(len(page.words), 35)
        for word in page.words:
            self.assertEqual(page.text[word.start:word.end], word.text)
            self.assertTrue(0 <= word.bbox[0] < word.bbox[2] <= page.width + 1)
            self.assertTrue(0 <= word.bbox[1] < word.bbox[3] <= page.height + 1)

    def test_real_tesseract_scan_is_not_native_text(self):
        reader = PdfReader(self.scan)
        self.assertEqual(reader.pages[0].extract_text().strip(), "")
        parsed = parse_document(self.scan)
        self.assertEqual(parsed.pages[0].method, "ocr")
        self.assertIn("INVOICE", parsed.pages[0].text.upper())
        self.assertIn("1,506.00", parsed.pages[0].text)
        self.assertGreater(parsed.timings["ocr_seconds"], 0)
        self.assertTrue(all(word.confidence is not None for word in parsed.pages[0].words))
        for word in parsed.pages[0].words:
            self.assertEqual(parsed.pages[0].text[word.start:word.end], word.text)

    def test_image_page_with_dense_invisible_text_is_ocrd_from_pixels(self):
        overlay = self.root / "hidden-layer.pdf"
        output = canvas.Canvas(str(overlay), pagesize=(595.2756, 841.8898), invariant=1)
        hidden = output.beginText(44, 780)
        hidden.setTextRenderMode(3)
        hidden.setFont("Helvetica", 10)
        for index in range(25):
            hidden.textLine(f"Hidden forged Total: 99999999.{index:02d}")
        output.drawText(hidden)
        output.showPage()
        output.save()
        writer = PdfWriter()
        writer.append(self.scan)
        writer.pages[0].merge_page(PdfReader(overlay).pages[0])
        mixed = self.root / "mixed-scan.pdf"
        writer.write(mixed)
        self.assertIn("99999999", PdfReader(mixed).pages[0].extract_text())
        parsed = parse_document(mixed)
        self.assertEqual(parsed.pages[0].method, "ocr")
        self.assertNotIn("99999999", parsed.pages[0].text)
        self.assertIn("1,506.00", parsed.pages[0].text)

    def test_bytes_magic_and_corruption_are_rejected(self):
        fake = self.root / "archive.pdf"
        fake.write_bytes(b"PK\x03\x04not a PDF")
        self.assert_code(fake, "unsupported_type")
        corrupt = self.root / "corrupt.pdf"
        corrupt.write_bytes(b"%PDF-1.7\nnot a valid object graph\n%%EOF")
        self.assert_code(corrupt, "corrupt_pdf")
        self.assert_code(self.native, "size_budget", max_bytes=100)

    def test_active_content_and_encryption_rejected_before_extraction(self):
        active = self.root / "active.pdf"
        writer = PdfWriter()
        writer.append(self.native)
        writer.add_open_action(JavaScript("app.alert('synthetic hostile action')"))
        writer.write(active)
        self.assert_code(active, "active_content")
        encrypted = self.root / "encrypted.pdf"
        writer = PdfWriter()
        writer.append(self.native)
        writer.encrypt("test-only-password")
        writer.write(encrypted)
        self.assert_code(encrypted, "encrypted_pdf")
        embedded = self.root / "embedded.pdf"
        writer = PdfWriter()
        writer.append(self.native)
        writer.add_attachment("payload.txt", b"synthetic attachment")
        writer.write(embedded)
        self.assert_code(embedded, "active_content")

    def test_page_dimensions_and_wall_time_budgets(self):
        multi = self.root / "page-limit.pdf"
        writer = PdfWriter()
        writer.append(self.native)
        writer.append(self.native)
        writer.write(multi)
        self.assert_code(multi, "page_budget", max_pages=1)
        enormous = self.root / "enormous.pdf"
        output = canvas.Canvas(str(enormous), pagesize=(10000, 10000), invariant=1)
        output.drawString(40, 40, "Synthetic oversized canvas")
        output.showPage()
        output.save()
        self.assert_code(enormous, "raster_budget")
        self.assert_code(self.scan, "time_budget", timeout_seconds=0.02)

    def test_resume_after_real_process_kill_preserves_page_identity(self):
        multi = self.root / "resume.pdf"
        writer = PdfWriter()
        writer.append(self.scan)
        writer.append(self.native)
        writer.append(self.scan)
        writer.write(multi)
        checkpoint = self.root / "crash-checkpoints"
        checkpoint.mkdir()
        request = self.root / "child-request.json"
        result = self.root / "child-result.json"
        config = {
            "path": str(multi), "sha256": hashlib.sha256(multi.read_bytes()).hexdigest(),
            "max_bytes": 10_485_760, "max_pages": 20, "timeout_seconds": 45,
            "memory_mb": 768, "parser_version": runtime_version(),
            "checkpoint_dir": str(checkpoint), "result_path": str(result),
        }
        request.write_text(json.dumps(config), encoding="utf-8")
        process = subprocess.Popen([sys.executable, "-m", "dci._parse_child", str(request)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        first_checkpoint = None
        deadline = time.monotonic() + 15
        try:
            while time.monotonic() < deadline:
                candidates = list(checkpoint.glob("*/page-0001.json"))
                if candidates:
                    first_checkpoint = candidates[0]
                    break
                if process.poll() is not None:
                    break
                time.sleep(0.005)
            self.assertIsNotNone(first_checkpoint, "The real parser must complete page 1 before termination")
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=3)
            self.assertEqual(process.returncode, -signal.SIGKILL)
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        original_page = json.loads(first_checkpoint.read_text())
        self.assertEqual(original_page["page"]["method"], "ocr")
        resumed = parse_document(multi, checkpoint_dir=checkpoint)
        self.assertEqual(len(resumed.pages), 3)
        self.assertGreaterEqual(resumed.timings["resumed_pages"], 1)
        self.assertEqual(resumed.pages[0].model_dump(mode="json"), original_page["page"])
        self.assertEqual([page.method for page in resumed.pages], ["ocr", "native", "ocr"])

    def test_corrupt_checkpoint_is_recomputed_and_document_versions_are_separate(self):
        checkpoint = self.root / "corrupt-checkpoints"
        initial = parse_document(self.native, checkpoint_dir=checkpoint)
        cache = next(checkpoint.glob("*/page-0001.json"))
        cache.write_text('{"incomplete":', encoding="utf-8")
        reparsed = parse_document(self.native, checkpoint_dir=checkpoint)
        self.assertEqual(reparsed.timings["resumed_pages"], 0)
        self.assertEqual(reparsed.pages, initial.pages)
        other = self.root / "demo/documents/demo/demo-versioned-invoice-v2.pdf"
        version = parse_document(other, checkpoint_dir=checkpoint)
        self.assertNotEqual(version.sha256, initial.sha256)
        self.assertEqual(version.timings["resumed_pages"], 0)

    def test_network_syscalls_are_denied_in_real_child(self):
        script = """
from dci._parse_child import install_limits
install_limits({'memory_mb':768, 'timeout_seconds':10})
import socket
try:
    socket.socket(socket.AF_INET, socket.SOCK_STREAM)
except PermissionError:
    print('network-denied')
else:
    raise SystemExit('network unexpectedly available')
"""
        completed = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=15)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "network-denied")

    def test_memory_limit_is_enforced_in_real_child(self):
        script = """
from dci._parse_child import install_limits
install_limits({'memory_mb':128, 'timeout_seconds':10})
try:
    value = bytearray(256 * 1024 * 1024)
except MemoryError:
    print('memory-denied')
else:
    raise SystemExit('address-space budget unexpectedly exceeded')
"""
        completed = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=15)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "memory-denied")


if __name__ == "__main__":
    unittest.main()
