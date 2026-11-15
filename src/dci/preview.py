"""Authenticated original-page rasterization in a bounded, network-denied child.

Untrusted PDF engines must never be imported into the API process. Every preview
revalidates the original hash and the strict PDF object safety policy before
rasterization. These images are a display of the original, not extraction proof.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MAX_PREVIEW_PIXELS = 2_500_000
MAX_PREVIEW_BYTES = 5 * 1024 * 1024
PREVIEW_TIMEOUT_SECONDS = 12


class PreviewError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code.lower()


def render_preview(
    path: Path, *, sha256: str, page_number: int, max_pages: int,
    max_bytes: int, timeout_seconds: float = PREVIEW_TIMEOUT_SECONDS,
    memory_mb: int = 768,
) -> bytes:
    """Return verified PNG bytes, never rendering a PDF within this process."""
    if not re.fullmatch(r"[a-f0-9]{64}", sha256):
        raise PreviewError("INVALID_DIGEST", "Invalid source digest")
    if not isinstance(page_number, int) or isinstance(page_number, bool) or not 1 <= page_number <= max_pages:
        raise PreviewError("PAGE_OUT_OF_RANGE", "Requested page is outside the inspected document")
    if not 0 < timeout_seconds <= 30 or not 256 <= memory_mb <= 4096:
        raise ValueError("Invalid preview process budget")
    source = Path(path).resolve(strict=True)
    if not source.is_file() or source.stat().st_size > max_bytes:
        raise PreviewError("SIZE_BUDGET", "Original is absent or exceeds the configured byte budget")
    with tempfile.TemporaryDirectory(prefix="dci-preview-") as temp:
        root = Path(temp)
        request = root / "request.json"
        result = root / "result.json"
        image = root / "preview.png"
        request.write_text(json.dumps({
            "path": str(source), "sha256": sha256, "page_number": page_number,
            "max_pages": max_pages, "max_bytes": max_bytes,
            "memory_mb": memory_mb, "timeout_seconds": timeout_seconds,
            "image_path": str(image), "result_path": str(result),
        }), encoding="utf-8")
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONPATH": str(Path(__file__).resolve().parent.parent),
            "LC_ALL": "C.UTF-8", "OMP_THREAD_LIMIT": "1",
            "OPENBLAS_NUM_THREADS": "1", "TMPDIR": str(root),
        }
        process = subprocess.Popen(
            [sys.executable, "-m", "dci.preview", "--child", str(request)],
            env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, start_new_session=True,
        )
        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise PreviewError("PREVIEW_TIMEOUT", "PDF preview exceeded its wall-clock budget") from exc
        if not result.is_file() or result.stat().st_size > 2048:
            raise PreviewError("PREVIEW_FAILED", "Isolated renderer did not produce a bounded result")
        try:
            envelope = json.loads(result.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise PreviewError("PREVIEW_FAILED", "Isolated renderer produced invalid metadata") from exc
        if "error" in envelope:
            failure = envelope["error"]
            raise PreviewError(failure["code"], failure["message"])
        if process.returncode != 0 or envelope.get("page_number") != page_number or envelope.get("sha256") != sha256:
            raise PreviewError("PREVIEW_FAILED", "Renderer result is inconsistent with the requested page")
        if not image.is_file() or not 32 <= image.stat().st_size <= MAX_PREVIEW_BYTES:
            raise PreviewError("PREVIEW_BUDGET", "Rendered image size exceeds the preview budget")
        image_bytes = image.read_bytes()
        width, height = int.from_bytes(image_bytes[16:20], "big"), int.from_bytes(image_bytes[20:24], "big")
        if (not image_bytes.startswith(PNG_MAGIC) or not 1 <= width <= 4096 or not 1 <= height <= 4096
                or width * height > MAX_PREVIEW_PIXELS
                or hashlib.sha256(image_bytes).hexdigest() != envelope.get("png_sha256")
                or (width, height) != (envelope.get("width"), envelope.get("height"))):
            raise PreviewError("PREVIEW_INTEGRITY", "Rendered PNG failed its size or integrity checks")
        return image_bytes


def _child(request_path: Path) -> int:
    # No PDF engine, image decoder, or document data is loaded before seccomp.
    from ._parse_child import ChildFailure, _atomic_json, inspect_pdf, install_limits
    from .parsing import MAX_PAGE_POINTS

    config = json.loads(request_path.read_text(encoding="utf-8"))
    result = Path(config["result_path"])
    try:
        install_limits(config)
        source = Path(config["path"])
        if not source.is_file() or source.stat().st_size > int(config["max_bytes"]):
            raise ChildFailure("size_budget", "Original exceeds the preview byte budget")
        with source.open("rb") as handle:
            content = handle.read(int(config["max_bytes"]) + 1)
        if len(content) > int(config["max_bytes"]) or hashlib.sha256(content).hexdigest() != config["sha256"]:
            raise ChildFailure("identity_mismatch", "Original changed after it was admitted")
        del content
        count = inspect_pdf(source, int(config["max_pages"]))
        number = int(config["page_number"])
        if not 1 <= number <= count:
            raise ChildFailure("page_out_of_range", "Requested page is not in the original")
        import pypdfium2 as pdfium

        with pdfium.PdfDocument(str(source)) as document:
            page = document[number - 1]
            try:
                width_points, height_points = page.get_size()
                if not (math.isfinite(width_points) and math.isfinite(height_points)
                        and 0 < width_points <= MAX_PAGE_POINTS
                        and 0 < height_points <= MAX_PAGE_POINTS):
                    raise ChildFailure("raster_budget", "PDF page dimensions exceed the supported budget")
                scale = min(1.6, math.sqrt(MAX_PREVIEW_PIXELS / (width_points * height_points)))
                if scale <= 0 or math.ceil(width_points * scale) * math.ceil(height_points * scale) > MAX_PREVIEW_PIXELS:
                    raise ChildFailure("raster_budget", "PDF preview would exceed the pixel budget")
                bitmap = page.render(scale=scale, may_draw_forms=False)
                try:
                    rendered = bitmap.to_pil()
                    try:
                        image_path = Path(config["image_path"])
                        rendered.save(image_path, format="PNG")
                        dimensions = rendered.size
                    finally:
                        rendered.close()
                finally:
                    bitmap.close()
            finally:
                page.close()
        if not 0 < image_path.stat().st_size <= MAX_PREVIEW_BYTES:
            raise ChildFailure("preview_budget", "Rendered PNG exceeds the byte budget")
        _atomic_json(result, {
            "sha256": config["sha256"], "page_number": number,
            "width": dimensions[0], "height": dimensions[1],
            "png_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
        })
        return 0
    except MemoryError:
        failure = {"code": "memory_budget", "message": "Preview exceeded its memory budget"}
    except ChildFailure as exc:
        failure = {"code": exc.code, "message": str(exc)}
    except Exception:
        # Do not leak original document contents or library exceptions to clients.
        failure = {"code": "preview_failed", "message": "Isolated PDF preview could not be rendered"}
    _atomic_json(result, {"error": failure})
    return 1


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "--child":
        raise SystemExit(2)
    raise SystemExit(_child(Path(sys.argv[2])))
