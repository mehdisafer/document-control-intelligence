"""Bounded queue worker. Parsing and inference never run in the API request path."""

import hashlib
import json
import logging
from pathlib import Path
import signal
import time
import uuid

from .config import Settings
from .models import ParsedDocument
from .store import Store


LOG = logging.getLogger("dci.worker")


def process_one(store: Store, *, owner=None, stop_after_parse=False):
    """Process at most one leased job; the checkpoint stop supports crash qualification.

    stop_after_parse intentionally leaves the lease outstanding. It is a test harness
    seam, never a document-controlled instruction and never a reported success.
    """
    from .extraction import extract, validate_evidence
    from .parsing import ParseError, parse_document, runtime_version
    from .rules import check_document

    job = store.claim(owner or f"worker-{uuid.uuid4()}")
    if job is None:
        return None
    started, doc = time.monotonic(), job["document"]
    context = {"job_id": job["id"], "document_id": doc["id"], "case_id": doc["case_id"],
               "attempt": job["attempt"], "profile": doc["profile"]}
    try:
        if doc["policy_digest"] != store.settings.policy_digest():
            store.fail(job, "PROCESSING_POLICY_CHANGED")
            return {**context, "outcome": "policy_changed"}
        content_path = store.blob_path(doc["sha256"])
        if content_path.stat().st_size > store.settings.max_bytes:
            raise ParseError("size_budget", "Current byte budget exceeded")
        with content_path.open("rb") as handle:
            source_digest = hashlib.file_digest(handle, "sha256").hexdigest()
        if source_digest != doc["sha256"]:
            store.fail(job, "BLOB_INTEGRITY")
            return {**context, "outcome": "integrity_error"}
        parsed = ParsedDocument.model_validate_json(doc["parsed_json"]) if doc["parsed_json"] else None
        if parsed is not None:
            if parsed.sha256 != doc["sha256"]:
                raise ValueError("Checkpoint document mismatch")
            if len(parsed.pages) > store.settings.max_pages:
                raise ParseError("page_budget", "Current page budget exceeded by retained checkpoint")
            if parsed.parser_version != runtime_version():
                parsed = None
        if parsed is None:
            settings = store.settings
            parsed = parse_document(content_path, max_pages=settings.max_pages, max_bytes=settings.max_bytes,
                                    timeout_seconds=settings.parser_seconds, memory_mb=settings.parser_memory_mb,
                                    checkpoint_dir=store.checkpoints)
            if not store.checkpoint(job, parsed):
                return {**context, "outcome": "fenced"}
        if stop_after_parse:
            return {**context, "outcome": "checkpoint_only"}
        kwargs = {"profile": doc["profile"], "model_path": store.settings.model_path}
        if doc["profile"] == "local-llm":
            kwargs["llm_config"] = json.loads(Path(store.settings.llm_config_file).read_text())
        extraction = validate_evidence(parsed, extract(parsed, **kwargs))
        checks = check_document(extraction)
        elapsed = time.monotonic() - started
        written = store.finish(job, extraction, checks, elapsed)
        result = {**context, "outcome": "done" if written else "fenced",
                  "decision": checks.decision, "elapsed_seconds": round(elapsed, 6),
                  "pages": len(parsed.pages), "ocr_pages": sum(p.method == "ocr" for p in parsed.pages)}
    except Exception as exc:
        code = getattr(exc, "code", "PROCESSING_FAILED")
        # No document text, model prompt, provider response or token is logged.
        retryable = code in {"MODEL_UNAVAILABLE", "MODEL_TIMEOUT", "PARSE_TIMEOUT", "TIMEOUT"}
        written = store.fail(job, code, retryable=retryable)
        result = {**context, "outcome": "failed" if written else "fenced", "error_code": code,
                  "exception_type": type(exc).__name__, "elapsed_seconds": round(time.monotonic()-started, 6)}
    LOG.info(json.dumps(result, sort_keys=True))
    return result


def drain(store: Store, *, max_jobs=1000):
    results = []
    for _ in range(max_jobs):
        result = process_one(store)
        if result is None:
            break
        results.append(result)
    return results


def serve(settings: Settings, *, once=False):
    store, stopping = Store(settings), False

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    owner = f"worker-{uuid.uuid4()}"
    while not stopping:
        for _ in range(settings.batch_size):
            if stopping:
                break
            result = process_one(store, owner=owner)
            if result is None:
                break
        if once:
            return
        if not stopping:
            time.sleep(0.25)
