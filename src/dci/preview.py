"""Generate a bounded, verified original PDF-page PNG in an isolated subprocess.

No PDF renderer is imported into the API process. The child inherits the
existing seccomp network-deny / CPU / memory / file-size boundaries.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import struct
import subprocess
import sys
import tempfile
from .parsing import ParseError

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_PREVIEW_PIXELS = 3_000_000
MAX_PNG_BYTES = 5 * 1024 * 1024

def render_preview(path: Path, *, expected_sha256: str, page: int,
                   max_bytes: int, max_pages: int, timeout_seconds: int,
                   memory_mb: int) -> bytes:
    if (not isinstance(page, int) or isinstance(page, bool) or
            not 1 <= page <= max_pages <= 100):
        raise ValueError("Invalid preview page")
    if not isinstance(expected_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None:
        raise ValueError("Invalid preview identity")
    if not (1024 <= max_bytes <= 50*1024*1024 and 1 <= timeout_seconds <= 180
            and 256 <= memory_mb <= 4096):
        raise ValueError("Invalid preview budget")
    path = Path(path).resolve(strict=True)
    if not path.is_file() or path.stat().st_size > max_bytes:
        raise ParseError("size_budget", "Original is not a regular PDF within the budget")
    with path.open("rb") as source:
        content = source.read(max_bytes+1)
    if (len(content)>max_bytes or not content.startswith(b"%PDF-")
            or hashlib.sha256(content).hexdigest() != expected_sha256):
        raise ParseError("identity_mismatch", "Original PDF identity mismatch")
    del content
    with tempfile.TemporaryDirectory(prefix="dci-page-preview-") as tmp:
        root=Path(tmp)
        request=root/"request.json"
        result=root/"receipt.json"
        image=root/"page.png"
        request.write_text(json.dumps({
            "path":str(path),"sha256":expected_sha256,"page":page,
            "max_bytes":max_bytes,"max_pages":max_pages,
            "timeout_seconds":timeout_seconds,"memory_mb":memory_mb,
            "max_pixels":MAX_PREVIEW_PIXELS,"max_png_bytes":MAX_PNG_BYTES,
            "image_path":str(image),"result_path":str(result)
        }),encoding="utf-8")
        env={"PATH":os.environ.get("PATH","/usr/bin:/bin"),
             "PYTHONPATH":str(Path(__file__).resolve().parent.parent),
             "LC_ALL":"C.UTF-8","OMP_THREAD_LIMIT":"1",
             "OPENBLAS_NUM_THREADS":"1","TMPDIR":tmp}
        with (root/"out.log").open("wb") as stdout,(root/"err.log").open("wb") as stderr:
            process=subprocess.Popen([sys.executable,"-m","dci._preview_child",str(request)],
                     env=env,stdout=stdout,stderr=stderr,start_new_session=True)
            try:
                process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired as exc:
                os.killpg(process.pid,signal.SIGKILL)
                process.wait()
                raise ParseError("time_budget","Page preview exceeded its time budget") from exc
        if not result.is_file() or result.stat().st_size>4096:
            raise ParseError("preview_failed","Preview subprocess did not produce a valid receipt")
        try:
            receipt=json.loads(result.read_text(encoding="utf-8"))
        except (ValueError,OSError) as exc:
            raise ParseError("preview_failed","Preview receipt cannot be decoded") from exc
        if "error" in receipt:
            code=receipt["error"].get("code","preview_failed")
            if code not in {"sandbox_unavailable","active_content","encrypted_pdf",
                    "corrupt_pdf","identity_mismatch","page_budget","raster_budget",
                    "time_budget","memory_budget"}:
                code="preview_failed"
            raise ParseError(code,"Preview generation unavailable")
        if process.returncode!=0 or not image.is_file() or image.stat().st_size>MAX_PNG_BYTES:
            raise ParseError("preview_failed","Preview image missing or exceeds budget")
        with image.open("rb") as source:
            data=source.read(MAX_PNG_BYTES+1)
        if len(data)<24 or len(data)>MAX_PNG_BYTES or not data.startswith(PNG_SIGNATURE):
            raise ParseError("preview_failed","Preview image is not a bounded PNG")
        width,height=struct.unpack(">II",data[16:24])
        metadata=receipt.get("preview") or {}
        if (not 0<width*height<=MAX_PREVIEW_PIXELS or metadata.get("page")!=page
                or metadata.get("width")!=width or metadata.get("height")!=height
                or metadata.get("sha256")!=hashlib.sha256(data).hexdigest()):
            raise ParseError("preview_failed","Preview image identity or dimensions mismatch")
        return data
