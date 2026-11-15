"""Isolated PNG renderer: reuse PDF active-content and seccomp admission rules."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import sys

from ._parse_child import ChildFailure, install_limits, inspect_pdf, _atomic_json

def render(config:dict) -> dict:
    import pypdfium2 as pdfium
    from .parsing import MAX_PAGE_POINTS

    path=Path(config["path"])
    max_bytes=int(config["max_bytes"])
    if path.stat().st_size>max_bytes:
        raise ChildFailure("size_budget","PDF exceeds preview byte budget")
    with path.open("rb") as reader:
        digest=hashlib.sha256(reader.read(max_bytes+1)).hexdigest()
    if digest!=config["sha256"]:
        raise ChildFailure("identity_mismatch","Preview PDF has changed after admission")
    count=inspect_pdf(path,int(config["max_pages"]))
    number=int(config["page"])
    if number<1 or number>count:
        raise ChildFailure("page_budget","Selected PDF page is out of range")
    with pdfium.PdfDocument(str(path)) as document:
        page=document[number-1]
        try:
            width,height=float(page.get_width()),float(page.get_height())
            if not (0<width<=MAX_PAGE_POINTS and 0<height<=MAX_PAGE_POINTS):
                raise ChildFailure("raster_budget","PDF page exceeds coordinate budget")
            max_pixels=int(config["max_pixels"])
            scale=min(1.5,math.sqrt(max_pixels/(width*height)))
            bitmap=page.render(scale=scale)
            try:
                image=bitmap.to_pil()
                try:
                    if image.width*image.height>max_pixels:
                        raise ChildFailure("raster_budget","Preview pixel limit exceeded")
                    converted=image.convert("RGB")
                    try:
                        converted.save(config["image_path"],format="PNG")
                    finally:
                        converted.close()
                    size=(image.width,image.height)
                finally:
                    image.close()
            finally:
                bitmap.close()
        finally:
            page.close()
    output=Path(config["image_path"])
    if output.stat().st_size>int(config["max_png_bytes"]):
        raise ChildFailure("raster_budget","Preview PNG exceeds the output budget")
    with output.open("rb") as data:
        digest=hashlib.sha256(data.read()).hexdigest()
    return {"page":number,"width":size[0],"height":size[1],"sha256":digest}

def main() -> int:
    config=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    result=Path(config["result_path"])
    try:
        install_limits(config)
        _atomic_json(result,{"preview":render(config)})
        return 0
    except MemoryError:
        error={"code":"memory_budget","message":"Preview memory budget exceeded"}
    except ChildFailure as exc:
        error={"code":exc.code,"message":"Document preview rejected"}
    except Exception:
        error={"code":"preview_failed","message":"Document preview could not complete"}
    _atomic_json(result,{"error":error})
    return 1

if __name__=="__main__":
    raise SystemExit(main())
