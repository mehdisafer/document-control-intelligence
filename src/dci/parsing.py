"""Bounded PDF parsing with native text, isolated OCR and resumable pages.

The public function never imports a PDF engine into the API/queue process. Linux
seccomp denies network syscalls in the child and all its descendants. Container
filesystem/mount isolation remains a separate deployment control.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
from functools import lru_cache

from dci.models import ParsedDocument


PARSER_REVISION = "native-ocr-1.0"
MAX_PAGE_POINTS = 2000
MAX_RASTER_PIXELS = 12_000_000
OCR_DPI = 160


class ParseError(RuntimeError):
    """A controlled parser failure with a stable machine-readable code."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@lru_cache(maxsize=1)
def runtime_version() -> str:
    """Checkpoint identity includes actual native/OCR dependency versions."""
    versions = [PARSER_REVISION]
    for package in ("pypdf", "pdfplumber", "pypdfium2", "Pillow"):
        try:
            versions.append(f"{package}={importlib.metadata.version(package)}")
        except importlib.metadata.PackageNotFoundError:
            versions.append(f"{package}=unavailable")
    try:
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C.UTF-8"}
        completed = subprocess.run(
            ["tesseract", "--version"], capture_output=True, text=True,
            timeout=5, check=False, env=env,
        )
        versions.append(completed.stdout.splitlines()[0].strip())
        languages = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True, timeout=5, check=False, env=env)
        location = re.search(r'"([^"]+)"', languages.stdout.splitlines()[0])
        traineddata = Path(location.group(1)) / "eng.traineddata" if location else None
        if traineddata is not None and traineddata.is_file():
            versions.append("eng.traineddata=" + hashlib.sha256(traineddata.read_bytes()).hexdigest())
        else:
            versions.append("eng.traineddata=unavailable")
    except (OSError, subprocess.TimeoutExpired, IndexError):
        versions.append("tesseract=unavailable")
    versions.extend((f"dpi={OCR_DPI}", "lang=eng", "oem=1", "psm=3"))
    return ";".join(versions)


def parse_document(
    path: Path,
    *,
    max_pages: int = 20,
    max_bytes: int = 10_485_760,
    timeout_seconds: float = 45,
    memory_mb: int = 768,
    checkpoint_dir: Path | None = None,
) -> ParsedDocument:
    """Parse a PDF in a separate process; enforce budgets before the first engine.

    Coordinates are PDF points with top-left origin. Text offsets refer to the
    canonical page text, not the raw PDF content stream. The content hash is
    rechecked in the child to reject a file replaced between admission and parse.
    """
    started = time.perf_counter()
    if not 1 <= max_pages <= 200 or not 1 <= max_bytes <= 104_857_600:
        raise ValueError("Invalid parser page or byte budget")
    if not 0 < timeout_seconds <= 600 or not 128 <= memory_mb <= 8192:
        raise ValueError("Invalid parser time or memory budget")
    path = Path(path).resolve(strict=True)
    if not path.is_file():
        raise ParseError("unsupported_type", "Input must be a regular PDF file")
    if path.stat().st_size > max_bytes:
        raise ParseError("size_budget", "PDF exceeds the configured byte budget")
    # Admission reads only bounded bytes, without invoking a document parser.
    with path.open("rb") as source:
        data = source.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ParseError("size_budget", "PDF exceeds the configured byte budget")
    if not data.startswith(b"%PDF-"):
        raise ParseError("unsupported_type", "Only PDF documents are accepted")
    digest = hashlib.sha256(data).hexdigest()
    del data
    if checkpoint_dir is not None:
        checkpoint_dir = Path(checkpoint_dir).resolve()
        checkpoint_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.TemporaryDirectory(prefix="dci-parser-") as temp:
        temp_path = Path(temp)
        config_path = temp_path / "request.json"
        result_path = temp_path / "result.json"
        config = {
            "path": str(path), "sha256": digest, "max_bytes": max_bytes,
            "max_pages": max_pages, "timeout_seconds": timeout_seconds,
            "memory_mb": memory_mb, "parser_version": runtime_version(),
            "checkpoint_dir": str(checkpoint_dir) if checkpoint_dir else None,
            "result_path": str(result_path),
        }
        config_path.write_text(json.dumps(config), encoding="utf-8")
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONPATH": str(Path(__file__).resolve().parent.parent),
            "LC_ALL": "C.UTF-8", "OMP_THREAD_LIMIT": "1",
            "OPENBLAS_NUM_THREADS": "1", "TMPDIR": temp,
        }
        with (temp_path / "stdout.log").open("wb") as stdout, (temp_path / "stderr.log").open("wb") as stderr:
            process = subprocess.Popen(
                [sys.executable, "-m", "dci._parse_child", str(config_path)],
                env=env, stdout=stdout, stderr=stderr, start_new_session=True,
            )
            try:
                process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired as exc:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                raise ParseError("time_budget", "Parser exceeded its wall-clock budget") from exc
        if not result_path.is_file():
            code = "parser_crash"
            if process.returncode == -signal.SIGXCPU:
                code = "time_budget"
            raise ParseError(code, f"Parser exited without a result (exit {process.returncode})")
        if result_path.stat().st_size > 16_777_216:
            raise ParseError("result_budget", "Parser output exceeds its budget")
        try:
            envelope = json.loads(result_path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            raise ParseError("parser_crash", "Parser result is incomplete") from exc
        if "error" in envelope:
            raise ParseError(envelope["error"]["code"], envelope["error"]["message"])
        if process.returncode != 0:
            raise ParseError("parser_crash", f"Parser exited with status {process.returncode}")
        document = ParsedDocument.model_validate(envelope["document"])
        if document.sha256 != digest or document.parser_version != config["parser_version"]:
            raise ParseError("identity_mismatch", "Parser result identity does not match the request")
        document.timings["wall_seconds"] = round(time.perf_counter() - started, 6)
        return document
