"""Raster child entrypoint: apply sandbox before importing any PDF engine."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys

from ._parse_child import ChildFailure, _atomic_json, inspect_pdf, install_limits


def render(config: dict) -> dict:
    from .parsing import MAX_PAGE_POINTS

    path = Path(config["path"])
    maximum = int(config["max_bytes"])
    if not path.is_file() or path.stat().st_size > maximum:
        raise ChildFailure("size_budget", "Original exceeds its byte limit")
    with path.open("rb") as stream:
        identity = hashlib.sha256(stream.read(maximum + 1)).hexdigest()
    if identity != config["sha256"]:
        raise ChildFailure("identity_mismatch", "Original does not match its recorded digest")
    count = inspect_pdf(path, int(config["max_pages"]))
    page_no = int(config["page"])
    if not 1 <= page_no <= count:
        raise ChildFailure("page_budget", "Page is outside the validated document")

    import pypdfium2 as pdfium

    with pdfium.PdfDocument(str(path)) as document:
        page = document[page_no - 1]
        try:
            width, height = map(float, page.get_size())
            if not (math.isfinite(width) and math.isfinite(height)
                    and 0 < width <= MAX_PAGE_POINTS and 0 < height <= MAX_PAGE_POINTS):
                raise ChildFailure("raster_budget", "Unsupported original-page dimensions")
            maximum_pixels = int(config["max_pixels"])
            scale = min(1.65, math.sqrt(maximum_pixels / (width * height)) * 0.98)
            bitmap = page.render(scale=scale)
            try:
                image = bitmap.to_pil().convert("RGB")
                try:
                    if image.width * image.height > maximum_pixels:
                        raise ChildFailure("raster_budget", "Page exceeds pixel budget")
                    image.save(config["png_path"], format="PNG", compress_level=6)
                    if Path(config["png_path"]).stat().st_size > int(config["max_output"]):
                        raise ChildFailure("raster_budget", "Page exceeds output byte budget")
                    with Path(config["png_path"]).open("rb") as stream:
                        png_hash = hashlib.file_digest(stream, "sha256").hexdigest()
                    return {"page": page_no, "width": image.width, "height": image.height,
                            "png_sha256": png_hash}
                finally:
                    image.close()
            finally:
                bitmap.close()
        finally:
            page.close()


def main() -> int:
    config = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    output = Path(config["result_path"])
    try:
        install_limits(config)
        receipt = render(config)
        _atomic_json(output, receipt)
        return 0
    except MemoryError:
        error = {"code": "memory_budget"}
    except ChildFailure as exc:
        error = {"code": exc.code}
    except Exception:
        # The API never exposes native parser messages or PDF-supplied strings.
        error = {"code": "preview_failed"}
    _atomic_json(output, {"error": error})
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
