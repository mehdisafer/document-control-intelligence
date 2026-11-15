"""Bounded, non-executable raster preview of a previously inspected PDF page.

Each request invokes the same Linux/seccomp sandbox policy as PDF extraction.
The API never imports pypdfium2 or decodes untrusted PDF bytes in-process.
Only one selected page is rendered; the original PDF is not modified.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile


PREVIEW_MAX_OUTPUT = 8 * 1024 * 1024
PREVIEW_MAX_PIXELS = 4_000_000


class PreviewError(RuntimeError):
    def __init__(self, code: str, message: str, status: int = 503):
        self.code, self.status = code, status
        super().__init__(message)


def render_preview_page(
    path: Path, expected_sha256: str, page: int, *,
    max_bytes: int, max_pages: int, memory_mb: int,
    timeout_seconds: float = 18,
) -> bytes:
    if not re.fullmatch(r"[a-f0-9]{64}", expected_sha256):
        raise ValueError("Invalid original content digest")
    if type(page) is not int or not 1 <= page <= max_pages:
        raise PreviewError("INVALID_PAGE", "Page is outside the configured limit", 422)
    if not 0 < timeout_seconds <= 30 or not 256 <= memory_mb <= 4096:
        raise ValueError("Invalid preview time or memory budget")
    if not path.is_file() or path.is_symlink():
        raise PreviewError("BLOB_INTEGRITY", "Original is missing or has an invalid storage type")
    if path.stat().st_size > max_bytes:
        raise PreviewError("BLOB_INTEGRITY", "Original exceeds its recorded budget")

    with tempfile.TemporaryDirectory(prefix="dci-preview-") as temporary:
        home = Path(temporary)
        destination = home / "page.png"
        result = home / "result.json"
        request = home / "request.json"
        request.write_text(json.dumps({
            "path": str(path), "sha256": expected_sha256, "page": page,
            "max_bytes": max_bytes, "max_pages": max_pages,
            "max_pixels": PREVIEW_MAX_PIXELS, "max_output": PREVIEW_MAX_OUTPUT,
            "memory_mb": memory_mb, "timeout_seconds": timeout_seconds,
            "png_path": str(destination), "result_path": str(result),
        }), encoding="utf-8")

        environment = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONPATH": str(Path(__file__).resolve().parent.parent),
            "LC_ALL": "C.UTF-8",
            "OMP_THREAD_LIMIT": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "TMPDIR": str(home),
        }
        with (home / "stdout.log").open("wb") as stdout, (home / "stderr.log").open("wb") as stderr:
            child = subprocess.Popen(
                [sys.executable, "-m", "dci._preview_child", str(request)],
                env=environment, stdout=stdout, stderr=stderr,
                start_new_session=True,
            )
            try:
                child.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired as exc:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
                raise PreviewError("PREVIEW_TIMEOUT", "Original page rendering exceeded its budget") from exc

        if not result.is_file() or result.stat().st_size > 4096:
            raise PreviewError("PREVIEW_FAILED", "Page renderer exited without a valid result")
        try:
            receipt = json.loads(result.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise PreviewError("PREVIEW_FAILED", "Page rendering result could not be read") from exc
        if "error" in receipt:
            error = receipt["error"]
            if not isinstance(error, dict) or error.get("code") not in {
                "sandbox_unavailable", "identity_mismatch", "raster_budget",
                "page_budget", "active_content", "encrypted_pdf", "corrupt_pdf",
                "size_budget", "time_budget", "memory_budget", "preview_failed",
            }:
                raise PreviewError("PREVIEW_FAILED", "Original page rendering failed")
            raise PreviewError(error["code"].upper(), "Original page rendering was refused")
        if child.returncode != 0 or receipt.get("page") != page:
            raise PreviewError("PREVIEW_FAILED", "Page renderer did not complete")
        if not destination.is_file() or destination.stat().st_size > PREVIEW_MAX_OUTPUT:
            raise PreviewError("PREVIEW_BUDGET", "Rendered page exceeds output budget")
        png = destination.read_bytes()
        if not png.startswith(b"\x89PNG\r\n\x1a\n") or hashlib.sha256(png).hexdigest() != receipt.get("png_sha256"):
            raise PreviewError("PREVIEW_FAILED", "Rendered page integrity check failed")
        if not (100 <= receipt.get("width", 0) <= 4000 and 100 <= receipt.get("height", 0) <= 4000
                and receipt["width"] * receipt["height"] <= PREVIEW_MAX_PIXELS):
            raise PreviewError("PREVIEW_BUDGET", "Rendered page geometry exceeds its budget")
        return png
