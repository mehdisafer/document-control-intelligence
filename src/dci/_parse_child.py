"""Internal sandbox entry point. Do not call PDF engines before install_limits()."""

from __future__ import annotations

import csv
import ctypes
import ctypes.util
import errno
import hashlib
import io
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time


class ChildFailure(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def install_limits(config: dict) -> None:
    memory = int(config["memory_mb"]) * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    cpu = max(1, math.ceil(float(config["timeout_seconds"])))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
    resource.setrlimit(resource.RLIMIT_FSIZE, (32 * 1024 * 1024, 32 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NOFILE, (96, 96))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    if sys.platform != "linux":
        raise ChildFailure("sandbox_unavailable", "The parser requires the Linux reference container")
    library = ctypes.util.find_library("seccomp")
    if not library:
        raise ChildFailure("sandbox_unavailable", "libseccomp is required for the parser sandbox")
    seccomp = ctypes.CDLL(library, use_errno=True)
    seccomp.seccomp_init.argtypes = [ctypes.c_uint32]
    seccomp.seccomp_init.restype = ctypes.c_void_p
    seccomp.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    seccomp.seccomp_syscall_resolve_name.restype = ctypes.c_int
    seccomp.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    seccomp.seccomp_rule_add.restype = ctypes.c_int
    seccomp.seccomp_load.argtypes = [ctypes.c_void_p]
    seccomp.seccomp_load.restype = ctypes.c_int
    seccomp.seccomp_release.argtypes = [ctypes.c_void_p]
    context = seccomp.seccomp_init(0x7FFF0000)  # SCMP_ACT_ALLOW
    if not context:
        raise ChildFailure("sandbox_unavailable", "Unable to initialize parser seccomp filter")
    try:
        for syscall in (
            "socket", "socketpair", "connect", "accept", "accept4", "bind", "listen",
            "sendto", "sendmsg", "sendmmsg", "recvfrom", "recvmsg", "recvmmsg",
            "ptrace", "process_vm_readv", "process_vm_writev", "mount", "umount2",
            "bpf", "userfaultfd", "io_uring_setup",
        ):
            number = seccomp.seccomp_syscall_resolve_name(syscall.encode("ascii"))
            if number >= 0 and seccomp.seccomp_rule_add(context, 0x00050000 | errno.EPERM, number, 0) != 0:
                raise ChildFailure("sandbox_unavailable", "Unable to install parser syscall policy")
        if seccomp.seccomp_load(context) != 0:
            raise ChildFailure("sandbox_unavailable", "Unable to activate parser syscall policy")
    finally:
        seccomp.seccomp_release(context)


def inspect_pdf(path: Path, max_pages: int) -> int:
    from pypdf import PdfReader
    from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject

    try:
        reader = PdfReader(str(path), strict=True)
        if reader.is_encrypted:
            raise ChildFailure("encrypted_pdf", "Encrypted PDFs are not accepted")
        seen: set[tuple[int, int] | int] = set()
        forbidden_keys = {
            "/JS", "/JavaScript", "/AA", "/OpenAction", "/EmbeddedFiles", "/XFA",
            "/AcroForm", "/Launch", "/RichMedia", "/SubmitForm", "/ImportData", "/A",
        }
        forbidden_values = {
            "/EmbeddedFile", "/Filespec", "/FileAttachment", "/RichMedia", "/Movie",
            "/Sound", "/Screen", "/Widget", "/JavaScript", "/Launch", "/URI", "/GoToR",
            "/GoToE", "/SubmitForm", "/ImportData",
        }

        def inspect(value, depth=0):
            if depth > 100 or len(seen) > 100_000:
                raise ChildFailure("object_budget", "PDF object graph exceeds the inspection budget")
            if isinstance(value, IndirectObject):
                identity = (value.idnum, value.generation)
                if identity in seen:
                    return
                seen.add(identity)
                value = value.get_object()
            if isinstance(value, DictionaryObject):
                identity = id(value)
                if identity in seen:
                    return
                seen.add(identity)
                for key, item in value.items():
                    if str(key) in forbidden_keys:
                        raise ChildFailure("active_content", "Active content, forms and attachments are refused")
                    if key in ("/Type", "/Subtype", "/S") and str(item) in forbidden_values:
                        raise ChildFailure("active_content", "Active content, forms and attachments are refused")
                    inspect(item, depth + 1)
            elif isinstance(value, ArrayObject):
                for item in value:
                    inspect(item, depth + 1)

        inspect(reader.trailer)
        count = len(reader.pages)
        if count == 0:
            raise ChildFailure("empty_pdf", "PDF has no pages")
        if count > max_pages:
            raise ChildFailure("page_budget", "PDF exceeds the configured page budget")
        return count
    except ChildFailure:
        raise
    except MemoryError:
        raise
    except Exception as exc:
        raise ChildFailure("corrupt_pdf", "PDF structure could not be validated") from exc


def _canonical_page(number: int, width: float, height: float, lines: list[list[dict]], method: str):
    from dci.models import Page, Word

    words = []
    pieces = []
    offset = 0
    for line in lines:
        for index, word in enumerate(line):
            value = str(word["text"]).replace("\x00", "").strip()
            if not value:
                continue
            if index and pieces and pieces[-1] != "\n":
                pieces.append(" ")
                offset += 1
            start = offset
            pieces.append(value)
            offset += len(value)
            box = tuple(round(float(v), 3) for v in word["bbox"])
            if not all(math.isfinite(v) for v in box) or not (0 <= box[0] < box[2] <= width + 1 and 0 <= box[1] < box[3] <= height + 1):
                raise ChildFailure("unsupported_geometry", "Text lies outside supported visible page coordinates")
            words.append(Word(text=value, start=start, end=offset, bbox=box, confidence=word.get("confidence")))
        if pieces and pieces[-1] != "\n":
            pieces.append("\n")
            offset += 1
    text = "".join(pieces).rstrip("\n")
    return Page(number=number, width=width, height=height, text=text, words=words, method=method)


def native_page(page, number: int):
    # Group geometrically rather than trusting PDF stream order. Line grouping is
    # deterministic and every character offset is rebuilt from retained tokens.
    raw_words = page.extract_words(x_tolerance=2, y_tolerance=3, keep_blank_chars=False, use_text_flow=False)
    rows: list[list[dict]] = []
    anchors: list[float] = []
    for item in sorted(raw_words, key=lambda word: (round(word["top"], 1), word["x0"])):
        if not rows or abs(float(item["top"]) - anchors[-1]) > 3.5:
            rows.append([])
            anchors.append(float(item["top"]))
        rows[-1].append({
            "text": item["text"],
            "bbox": (item["x0"], item["top"], item["x1"], item["bottom"]),
        })
    for row in rows:
        row.sort(key=lambda word: word["bbox"][0])
    return _canonical_page(number, float(page.width), float(page.height), rows, "native")


def ocr_page(path: Path, number: int, width: float, height: float, timeout: float):
    import pypdfium2 as pdfium
    from dci.parsing import MAX_RASTER_PIXELS, OCR_DPI

    scale = OCR_DPI / 72
    if width * height * scale * scale > MAX_RASTER_PIXELS:
        raise ChildFailure("raster_budget", "Page exceeds the OCR raster budget")
    with tempfile.TemporaryDirectory(prefix="dci-ocr-") as temp:
        image_path = Path(temp) / "page.png"
        with pdfium.PdfDocument(str(path)) as document:
            page = document[number - 1]
            try:
                bitmap = page.render(scale=scale)
                image = bitmap.to_pil()
                image.save(image_path)
                image.close()
                bitmap.close()
            finally:
                page.close()
        try:
            completed = subprocess.run(
                ["tesseract", str(image_path), "stdout", "-l", "eng", "--oem", "1", "--psm", "3", "tsv"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                timeout=max(0.1, timeout), check=False,
            )
        except FileNotFoundError as exc:
            raise ChildFailure("ocr_unavailable", "Tesseract is not installed") from exc
        except subprocess.TimeoutExpired as exc:
            raise ChildFailure("time_budget", "OCR exceeded the remaining wall-clock budget") from exc
        if completed.returncode != 0:
            raise ChildFailure("ocr_failed", "Tesseract did not complete successfully")
        if len(completed.stdout) > 4_194_304:
            raise ChildFailure("result_budget", "OCR output exceeds the page budget")
        lines: dict[tuple[str, str, str], list[dict]] = {}
        for item in csv.DictReader(io.StringIO(completed.stdout), delimiter="\t", quoting=csv.QUOTE_NONE):
            if item.get("level") != "5" or not item.get("text", "").strip():
                continue
            try:
                left, top = float(item["left"]), float(item["top"])
                right = left + float(item["width"])
                bottom = top + float(item["height"])
                confidence = max(0.0, min(1.0, float(item["conf"]) / 100))
            except (ValueError, KeyError) as exc:
                raise ChildFailure("ocr_failed", "Tesseract produced malformed word coordinates") from exc
            key = (item["block_num"], item["par_num"], item["line_num"])
            lines.setdefault(key, []).append({
                "text": item["text"], "bbox": (left / scale, top / scale, right / scale, bottom / scale),
                "confidence": confidence,
            })
        return _canonical_page(number, width, height, list(lines.values()), "ocr")


def _atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def parse(config: dict) -> dict:
    import pdfplumber
    from dci.models import Page, ParsedDocument
    from dci.parsing import MAX_PAGE_POINTS

    started = time.perf_counter()
    deadline = started + float(config["timeout_seconds"]) - 0.25
    path = Path(config["path"])
    if path.stat().st_size > int(config["max_bytes"]):
        raise ChildFailure("size_budget", "PDF exceeds its byte budget")
    with path.open("rb") as stream:
        digest = hashlib.sha256(stream.read(int(config["max_bytes"]) + 1)).hexdigest()
    if digest != config["sha256"]:
        raise ChildFailure("identity_mismatch", "Input changed after parser admission")
    page_count = inspect_pdf(path, int(config["max_pages"]))
    checkpoint = None
    if config.get("checkpoint_dir"):
        identity = hashlib.sha256(config["parser_version"].encode()).hexdigest()[:16]
        checkpoint = Path(config["checkpoint_dir"]) / f"{digest}-{identity}"
        checkpoint.mkdir(parents=True, exist_ok=True)
    pages = []
    timings = {"native_seconds": 0.0, "ocr_seconds": 0.0, "resumed_pages": 0.0}
    with pdfplumber.open(str(path)) as document:
        for index in range(page_count):
            if time.perf_counter() > deadline:
                raise ChildFailure("time_budget", "Parser exceeded its deadline")
            number = index + 1
            cached_path = checkpoint / f"page-{number:04d}.json" if checkpoint else None
            if cached_path and cached_path.exists():
                try:
                    envelope = json.loads(cached_path.read_text(encoding="utf-8"))
                    encoded = json.dumps(envelope["page"], ensure_ascii=False, sort_keys=True).encode()
                    cached = Page.model_validate(envelope["page"])
                    if envelope["sha256"] == digest and envelope["parser_version"] == config["parser_version"] and envelope["page_sha256"] == hashlib.sha256(encoded).hexdigest() and cached.number == number:
                        pages.append(cached)
                        timings["resumed_pages"] += 1
                        continue
                except (ValueError, KeyError, OSError):
                    pass  # Incomplete/corrupt checkpoints are recomputed, not trusted.
            source = document.pages[index]
            width, height = float(source.width), float(source.height)
            if not (0 < width <= MAX_PAGE_POINTS and 0 < height <= MAX_PAGE_POINTS):
                raise ChildFailure("raster_budget", "Page dimensions exceed the supported budget")
            stage = time.perf_counter()
            page = native_page(source, number)
            timings["native_seconds"] += time.perf_counter() - stage
            # A footer alone is not a usable native page. Image-heavy pages with
            # little native content are OCR'd so a scanned body is not ignored.
            meaningful = sum(character.isalnum() for character in page.text)
            image_area = sum(max(0, float(item["width"])) * max(0, float(item["height"])) for item in source.images)
            image_heavy = image_area > width * height * 0.35
            if meaningful < 40 or image_heavy:
                stage = time.perf_counter()
                page = ocr_page(path, number, width, height, deadline - time.perf_counter())
                timings["ocr_seconds"] += time.perf_counter() - stage
            if len(page.text) > 200_000 or len(page.words) > 40_000:
                raise ChildFailure("text_budget", "Extracted page text exceeds its budget")
            pages.append(page)
            if cached_path:
                value = page.model_dump(mode="json")
                encoded = json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
                _atomic_json(cached_path, {"sha256": digest, "parser_version": config["parser_version"], "page_sha256": hashlib.sha256(encoded).hexdigest(), "page": value})
            source.close()
    timings["parse_seconds"] = time.perf_counter() - started
    timings = {key: round(value, 6) for key, value in timings.items()}
    return ParsedDocument(sha256=digest, pages=pages, parser_version=config["parser_version"], timings=timings).model_dump(mode="json")


def main() -> int:
    config = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    output = Path(config["result_path"])
    try:
        install_limits(config)
        document = parse(config)
        _atomic_json(output, {"document": document})
        return 0
    except MemoryError:
        error = {"code": "memory_budget", "message": "Parser exceeded its memory budget"}
    except ChildFailure as exc:
        error = {"code": exc.code, "message": str(exc)}
    except Exception:
        # Untrusted text and raw library exceptions never enter application logs.
        error = {"code": "corrupt_pdf", "message": "Document parsing failed"}
    _atomic_json(output, {"error": error})
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
