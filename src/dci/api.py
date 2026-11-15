"""Authenticated ingestion and review API. Uploaded bytes are never executed in-process."""

import hashlib
import io
import json
import logging
from pathlib import Path
import threading
import time
from typing import Literal
import uuid
import zipfile

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .auth import Auth
from .config import Settings
from .preview import PreviewError, render_preview
from .store import Store, StoreError


EXPORT_UNCOMPRESSED_BUDGET = 50 * 1024 * 1024
_EXPORT_CHUNK_SIZE = 64 * 1024


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CaseRequest(Body):
    name: str = Field(min_length=1, max_length=160)


class CorrectionRequest(Body):
    field: str = Field(max_length=100)
    value: str = Field(max_length=200)
    reason: str = Field(min_length=1, max_length=1000)
    expected_revision: int = Field(ge=0)


class AcceptanceRequest(Body):
    expected_revision: int = Field(ge=0)
    reason: str = Field(min_length=1, max_length=1000)


class ClassificationReviewRequest(Body):
    kind: Literal["purchase_order", "delivery_note", "invoice", "unknown"]
    reason: str = Field(min_length=1, max_length=1000)
    expected_revision: int = Field(ge=0)


class PublicationRequest(Body):
    expected_revision: int = Field(ge=0)


class RetryRequest(Body):
    reason: str = Field(min_length=1, max_length=1000)


def create_app(settings: Settings | None = None):
    settings = settings or Settings.from_env()
    store, auth = Store(settings), Auth(settings.auth_file)
    app = FastAPI(title="Document Control Intelligence", version="0.1.0rc1", docs_url=None, redoc_url=None,
                  openapi_url=None)
    app.state.store = store
    log = logging.getLogger("dci.api")
    # Bound per-process preview concurrency; all PDF engines run in child processes.
    preview_slots = threading.BoundedSemaphore(2)

    def actor(authorization: str | None = Header(default=None)):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "A bearer token is required", headers={"WWW-Authenticate": "Bearer"})
        identity = auth.identify(authorization[7:])
        if identity is None:
            raise HTTPException(401, "Invalid bearer token", headers={"WWW-Authenticate": "Bearer"})
        return identity

    def role(required):
        def check(identity=Depends(actor)):
            if required not in identity.roles:
                raise HTTPException(403, f"The {required} role is required")
            return identity
        return check

    @app.middleware("http")
    async def trace(request, call_next):
        trace_id, started = str(uuid.uuid4()), time.monotonic()
        request.state.trace_id = trace_id
        # Bound JSON too, before FastAPI attempts to decode any request body.
        length = request.headers.get("content-length")
        try:
            if length is not None and (int(length) < 0 or int(length) > settings.max_bytes):
                return JSONResponse({"code": "SIZE_BUDGET"}, 413)
        except ValueError:
            return JSONResponse({"code": "INVALID_CONTENT_LENGTH"}, 400)
        if request.method in {"POST", "PUT", "PATCH"} and not request.url.path.endswith("/documents"):
            body = bytearray()
            async for chunk in request.stream():
                if len(body) + len(chunk) > 16_384:
                    return JSONResponse({"code": "JSON_BODY_BUDGET"}, 413)
                body.extend(chunk)
            request._body = bytes(body)
        response = await call_next(request)
        response.headers.update({"X-Request-ID": trace_id, "X-Content-Type-Options": "nosniff",
                                 "Referrer-Policy": "no-referrer", "Cache-Control": "no-store",
                                 "Content-Security-Policy": "default-src 'self'; script-src 'self'; "
                                 "style-src 'self'; img-src 'self' blob: data:; frame-src blob:; "
                                 "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"})
        log.info(json.dumps({"trace_id": trace_id, "method": request.method,
                             "status": response.status_code, "duration_seconds": round(time.monotonic()-started, 6)}))
        return response

    @app.exception_handler(StoreError)
    async def store_error(_request, error):
        headers = {"Retry-After": "5"} if error.status == 429 else {}
        return JSONResponse({"code": error.code, "message": str(error)}, error.status, headers=headers)

    @app.get("/healthz")
    def health():
        return {"status": "alive", "version": "0.1.0rc1"}

    @app.get("/api/ready")
    def ready(_identity=Depends(actor)):
        metrics = store.metrics()
        return {"database": "reachable", "queue": metrics,
                "profile": settings.profile, "worker_readiness": "inspect queue age and worker logs"}

    @app.get("/api/me")
    def me(identity=Depends(actor)):
        return {"name": identity.name, "roles": identity.roles}

    @app.get("/api/openapi.json")
    def schema(_identity=Depends(actor)):
        return app.openapi()

    @app.get("/api/cases")
    def cases(_identity=Depends(actor)):
        return store.list_cases()

    @app.post("/api/cases", status_code=201)
    def new_case(body: CaseRequest, identity=Depends(role("operator"))):
        return store.create_case(body.name, identity.name)

    @app.get("/api/cases/{case_id}")
    def get_case(case_id: str, _identity=Depends(actor)):
        return store.case(case_id)

    @app.post("/api/cases/{case_id}/documents", status_code=202)
    async def upload(case_id: str, request: Request, document_key: str, filename: str = "document.pdf",
                     identity=Depends(role("operator"))):
        if request.headers.get("content-type", "").split(";")[0] != "application/pdf":
            raise HTTPException(415, "Send the raw PDF body with Content-Type application/pdf")
        data = bytearray()
        async for chunk in request.stream():
            if len(data) + len(chunk) > settings.max_bytes:
                raise StoreError("SIZE_BUDGET", "Document exceeds byte limit", 413)
            data.extend(chunk)
        # Store state change is short, but runs off the event loop like sync endpoints.
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(store.ingest, case_id, document_key, filename, bytes(data),
                                       identity.name, request_id=request.state.trace_id)

    @app.get("/api/documents/{document_id}")
    def document(document_id: str, _identity=Depends(actor)):
        return store.document(document_id)

    @app.get("/api/documents/{document_id}/original")
    def original(document_id: str, _identity=Depends(actor)):
        doc = store.document(document_id)
        if doc["parsed"] is None:
            raise StoreError("NOT_INSPECTED", "Original preview is available only after parser inspection")
        path = store.blob_path(doc["sha256"])
        with path.open("rb") as handle:
            actual = hashlib.file_digest(handle, "sha256").hexdigest()
        if actual != doc["sha256"]:
            raise StoreError("BLOB_INTEGRITY", "Original failed integrity verification", 503)
        return FileResponse(path, media_type="application/pdf", filename=f"{document_id}.pdf",
                            content_disposition_type="inline")

    @app.get("/api/documents/{document_id}/preview/{page_number}")
    def original_preview(document_id: str, page_number: int, _identity=Depends(actor)):
        doc = store.document(document_id)
        if doc["parsed"] is None:
            raise StoreError("NOT_INSPECTED", "Preview is available only after parser inspection")
        if not 1 <= page_number <= len(doc["parsed"]["pages"]):
            raise StoreError("PAGE_OUT_OF_RANGE", "Requested page does not exist", 422)
        if not preview_slots.acquire(blocking=False):
            raise StoreError("PREVIEW_BUSY", "Preview capacity is busy; retry later", 429)
        try:
            try:
                content = render_preview(
                    store.blob_path(doc["sha256"]), sha256=doc["sha256"],
                    page_number=page_number, max_pages=settings.max_pages,
                    max_bytes=settings.max_bytes,
                    timeout_seconds=min(12, settings.parser_seconds),
                    memory_mb=min(768, settings.parser_memory_mb),
                )
            except PreviewError as exc:
                raise StoreError(exc.code.upper(), str(exc), 503) from exc
        finally:
            preview_slots.release()
        return Response(content, media_type="image/png", headers={
            "X-Original-SHA256": doc["sha256"],
            "X-Preview-Page": str(page_number),
        })

    @app.post("/api/documents/{document_id}/corrections")
    def correction(document_id: str, body: CorrectionRequest, identity=Depends(role("operator"))):
        return store.correct(document_id, body.field, body.value, body.reason, identity.name, body.expected_revision)

    @app.post("/api/documents/{document_id}/classification-review")
    def classification_review(document_id: str, body: ClassificationReviewRequest,
                              identity=Depends(role("operator"))):
        return store.review_classification(document_id, body.kind, body.reason,
                                           identity.name, body.expected_revision)

    @app.post("/api/documents/{document_id}/cancel")
    def cancel(document_id: str, identity=Depends(role("operator"))):
        return store.cancel(document_id, identity.name)

    @app.post("/api/documents/{document_id}/retry")
    def retry(document_id: str, body: RetryRequest, identity=Depends(role("operator"))):
        return store.retry(document_id, identity.name, body.reason)

    @app.get("/api/cases/{case_id}/audit")
    def audit(case_id: str, _identity=Depends(actor)):
        return store.audit(case_id)

    @app.post("/api/cases/{case_id}/accept")
    def accept(case_id: str, body: AcceptanceRequest, identity=Depends(role("approver"))):
        return store.accept(case_id, identity.name, body.reason, body.expected_revision)

    @app.post("/api/cases/{case_id}/publish")
    def publish(case_id: str, body: PublicationRequest, identity=Depends(role("publisher"))):
        return store.publish(case_id, identity.name, body.expected_revision)

    @app.get("/api/cases/{case_id}/export")
    def export(case_id: str, _identity=Depends(actor)):
        return store.export(case_id)

    @app.get("/api/cases/{case_id}/export.zip")
    def export_zip(case_id: str, _identity=Depends(actor)):
        payload = store.export(case_id)
        buffer = io.BytesIO()
        limit, used = EXPORT_UNCOMPRESSED_BUDGET, 0

        def budget_error():
            return StoreError("EXPORT_BUDGET", "Use JSON export for dossiers above the ZIP uncompressed byte budget", 413)

        def write_chunk(target, content):
            nonlocal used
            if used + len(content) > limit:
                raise budget_error()
            target.write(content)
            used += len(content)

        def write_json(archive, name, value, *, ensure_ascii=True):
            encoder = json.JSONEncoder(indent=2, ensure_ascii=ensure_ascii)
            with archive.open(name, "w") as target:
                for text in encoder.iterencode(value):
                    for offset in range(0, len(text), _EXPORT_CHUNK_SIZE):
                        write_chunk(target, text[offset:offset + _EXPORT_CHUNK_SIZE].encode("utf-8"))

        # Count actual uncompressed member bytes, including both JSON members.
        # This is not an RSS or final ZIP-size limit: the payload is already loaded,
        # and ZIP framing/compression has overhead. Encode the dossier incrementally.
        if sum(store.blob_path(d["sha256"]).stat().st_size for d in payload["documents"]) > limit:
            raise budget_error()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            write_json(archive, "control-dossier.json", payload, ensure_ascii=False)
            manifest = {}
            for doc in payload["documents"]:
                name = f"originals/{doc['id']}.pdf"
                digest = hashlib.sha256()
                with store.blob_path(doc["sha256"]).open("rb") as source, archive.open(name, "w") as target:
                    while content := source.read(_EXPORT_CHUNK_SIZE):
                        write_chunk(target, content)
                        digest.update(content)
                if digest.hexdigest() != doc["sha256"]:
                    raise StoreError("BLOB_INTEGRITY", "Export original failed integrity verification", 503)
                manifest[name] = doc["sha256"]
            write_json(archive, "manifest.json", manifest)
        return Response(buffer.getvalue(), media_type="application/zip", headers={
            "Content-Disposition": f'attachment; filename="control-dossier-{case_id}.zip"'})

    @app.get("/metrics")
    def metrics(_identity=Depends(actor)):
        data = store.metrics()
        lines = ["# TYPE dci_jobs gauge"]
        lines.extend(f'dci_jobs{{status="{name}"}} {count}' for name, count in sorted(data["jobs"].items()))
        lines += [f'dci_queue_oldest_seconds {data["oldest_queued_seconds"]}',
                  f'dci_processing_seconds_sum {data["processing_seconds_sum"]}',
                  f'dci_processing_seconds_count {data["completed_count"]}',
                  f'dci_publications {data["publications"]}']
        return Response("\n".join(lines)+"\n", media_type="text/plain; version=0.0.4")

    static = Path(__file__).parent / "static"
    app.mount("/assets", StaticFiles(directory=static), name="assets")

    @app.get("/")
    def index():
        return FileResponse(static / "index.html", media_type="text/html")

    return app
