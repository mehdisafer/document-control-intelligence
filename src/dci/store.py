"""SQLite state machine, immutable document bytes and transaction-bound review.

This is a single-host deployment. SQLite WAL files must never live on NFS/SMB.
Every publication binds the complete set of current document versions/revisions.
Leased work uses fencing tokens, so a late result cannot overwrite a new attempt.
"""

from contextlib import contextmanager, closing
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import uuid

from .config import Settings
from .models import Extraction, Finding, ParsedDocument


class StoreError(Exception):
    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code, self.status = code, status


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def uid() -> str:
    return str(uuid.uuid4())


class Store:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.home = settings.home.resolve()
        self.home.mkdir(parents=True, exist_ok=True)
        self.blobs = self.home / "blobs"
        self.blobs.mkdir(exist_ok=True)
        self.checkpoints = self.home / "checkpoints"
        self.checkpoints.mkdir(exist_ok=True)
        self.db = self.home / "control.db"
        self.migrate()

    def connect(self, *, timeout=10.0):
        conn = sqlite3.connect(self.db, timeout=timeout, isolation_level=None)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute(f"PRAGMA busy_timeout={max(1, int(timeout * 1000))}")
            conn.execute("PRAGMA synchronous=FULL")
            return conn
        except BaseException:
            conn.close()
            raise

    @contextmanager
    def transaction(self):
        conn = self.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def migrate(self, *, timeout_seconds=10.0):
        """Initialize atomically, retrying only bounded SQLite lock contention.

        Changing journal mode can return SQLITE_BUSY without honoring the full
        busy timeout. A failed attempt is rolled back and its connection closed
        before retrying. Schema errors and unsupported WAL never get retried.
        """
        if not 0 < timeout_seconds <= 10:
            raise ValueError("Migration lock budget must be greater than zero and at most 10 seconds")
        deadline = time.monotonic() + timeout_seconds
        while True:
            conn = None
            try:
                remaining = max(0.001, deadline - time.monotonic())
                conn = self.connect(timeout=min(0.1, remaining))
                mode = conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
                if str(mode).lower() != "wal":
                    raise StoreError("WAL_UNAVAILABLE", "Database storage must support SQLite WAL", 503)
                conn.execute("BEGIN IMMEDIATE")
                version = conn.execute("PRAGMA user_version").fetchone()[0]
                if version > 1:
                    raise StoreError("SCHEMA_TOO_NEW", "Database needs a newer application", 503)
                if version == 0:
                    script = (Path(__file__).parent / "migrations/001_initial.sql").read_text()
                    statement = ""
                    for line in script.splitlines(keepends=True):
                        statement += line
                        if sqlite3.complete_statement(statement):
                            conn.execute(statement)
                            statement = ""
                    conn.execute("INSERT INTO schema_migrations VALUES(1,?)", (time.time(),))
                    conn.execute("PRAGMA user_version=1")
                conn.commit()
                return
            except sqlite3.OperationalError as exc:
                code = getattr(exc, "sqlite_errorcode", None)
                busy = code is not None and (code & 0xFF) in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED)
                if not busy or time.monotonic() >= deadline:
                    raise
            finally:
                if conn is not None:
                    try:
                        if conn.in_transaction:
                            conn.rollback()
                    finally:
                        conn.close()
            time.sleep(min(0.02, max(0.0, deadline - time.monotonic())))

    @staticmethod
    def _audit(conn, actor, action, case_id, document_id=None, revision=None, **details):
        conn.execute("INSERT INTO audit(at,actor,action,case_id,document_id,revision,details_json) "
                     "VALUES(?,?,?,?,?,?,?)", (time.time(), actor, action, case_id, document_id,
                                               revision, canonical(details)))

    @staticmethod
    def _invalidate(conn, case_id):
        conn.execute("UPDATE cases SET revision=revision+1,accepted_fingerprint=NULL,"
                     "accepted_by=NULL,accepted_at=NULL,acceptance_reason=NULL,"
                     "published_fingerprint=NULL WHERE id=?", (case_id,))

    @staticmethod
    def _case(conn, case_id):
        row = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        if row is None:
            raise StoreError("NOT_FOUND", "Case not found", 404)
        return dict(row)

    @staticmethod
    def _document(conn, document_id):
        row = conn.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
        if row is None:
            raise StoreError("NOT_FOUND", "Document not found", 404)
        return dict(row)

    @staticmethod
    def _current_rows(conn, case_id):
        return [dict(r) for r in conn.execute(
            "SELECT d.* FROM documents d WHERE d.case_id=? AND d.version="
            "(SELECT MAX(x.version) FROM documents x WHERE x.case_id=d.case_id "
            "AND x.document_key=d.document_key) ORDER BY d.document_key", (case_id,))]

    @staticmethod
    def _is_current(conn, doc):
        return doc["version"] == conn.execute(
            "SELECT MAX(version) FROM documents WHERE case_id=? AND document_key=?",
            (doc["case_id"], doc["document_key"])).fetchone()[0]

    def create_case(self, name, actor):
        if not name.strip() or len(name) > 160:
            raise StoreError("INVALID_NAME", "A case name must have 1–160 characters", 422)
        case_id = uid()
        with self.transaction() as conn:
            conn.execute("INSERT INTO cases(id,name,created_at) VALUES(?,?,?)",
                         (case_id, name.strip(), time.time()))
            self._audit(conn, actor, "case.created", case_id, name=name.strip())
        return self.case(case_id)

    def list_cases(self):
        with closing(self.connect()) as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM cases ORDER BY created_at DESC")]

    def blob_path(self, sha):
        if not re.fullmatch(r"[a-f0-9]{64}", sha):
            raise StoreError("INVALID_DIGEST", "Invalid content digest", 422)
        return self.blobs / sha[:2] / f"{sha}.pdf"

    def _put_blob(self, content, sha):
        target = self.blob_path(sha)
        target.parent.mkdir(exist_ok=True)
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest() != sha:
                raise StoreError("BLOB_INTEGRITY", "Stored content failed integrity check", 503)
            return
        temporary = target.parent / f".{uid()}.partial"
        try:
            with temporary.open("xb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            # Link does not overwrite an already committed immutable object.
            try:
                os.link(temporary, target)
            except FileExistsError:
                if hashlib.sha256(target.read_bytes()).hexdigest() != sha:
                    raise StoreError("BLOB_INTEGRITY", "Stored content changed", 503)
            directory = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            temporary.unlink(missing_ok=True)

    def ingest(self, case_id, document_key, filename, content: bytes, actor, *, request_id=None):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", document_key):
            raise StoreError("INVALID_KEY", "Document key must be a short stable identifier", 422)
        if len(content) > self.settings.max_bytes:
            raise StoreError("SIZE_BUDGET", "Document exceeds byte limit", 413)
        if not content.startswith(b"%PDF-"):
            raise StoreError("UNSUPPORTED_MEDIA", "Only PDF documents are accepted", 415)
        sha, now = hashlib.sha256(content).hexdigest(), time.time()
        with self.transaction() as conn:
            self._case(conn, case_id)
            existing = conn.execute("SELECT id,document_key FROM documents WHERE case_id=? AND sha256=?",
                                    (case_id, sha)).fetchone()
            if existing:
                if existing["document_key"] != document_key:
                    raise StoreError("DUPLICATE_CONTENT", "This content already exists under a different document key")
                return {"document_id": existing["id"], "duplicate": True}
            depth = conn.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('queued','running')").fetchone()[0]
            if depth >= self.settings.max_pending:
                raise StoreError("QUEUE_FULL", "Processing queue is full; retry after capacity is available", 429)
            key_exists = conn.execute("SELECT 1 FROM documents WHERE case_id=? AND document_key=?",
                                      (case_id, document_key)).fetchone()
            key_count = conn.execute("SELECT COUNT(DISTINCT document_key) FROM documents WHERE case_id=?",
                                     (case_id,)).fetchone()[0]
            case_bytes = conn.execute("SELECT COALESCE(SUM(size),0) FROM documents WHERE case_id=?",
                                      (case_id,)).fetchone()[0]
            if (not key_exists and key_count >= self.settings.max_case_documents) or case_bytes + len(content) > self.settings.max_case_bytes:
                raise StoreError("CASE_BUDGET", "Case document count or retained-byte budget exceeded", 413)
            version = conn.execute("SELECT COALESCE(MAX(version),0)+1 FROM documents WHERE "
                                   "case_id=? AND document_key=?", (case_id, document_key)).fetchone()[0]
            if version > self.settings.max_document_versions:
                raise StoreError("VERSION_BUDGET", "Document version budget exceeded", 413)
            self._put_blob(content, sha)
            # A new version fences old in-flight jobs before it becomes the current document.
            conn.execute("UPDATE jobs SET status='cancelled',lease_token=NULL,lease_until=NULL "
                         "WHERE status IN ('queued','running') AND document_id IN "
                         "(SELECT id FROM documents WHERE case_id=? AND document_key=?)",
                         (case_id, document_key))
            conn.execute("UPDATE documents SET status='superseded' WHERE case_id=? AND "
                         "document_key=? AND status IN ('queued','processing')", (case_id, document_key))
            document_id, job_id = uid(), uid()
            conn.execute("INSERT INTO documents(id,case_id,document_key,version,sha256,filename,size,"
                         "created_at,profile,policy_digest,status) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                         (document_id, case_id, document_key, version, sha,
                          Path(filename).name[:180], len(content), now, self.settings.profile,
                          self.settings.policy_digest(), "queued"))
            conn.execute("INSERT INTO jobs(id,document_id,status,available_at,created_at) VALUES(?,?,?,?,?)",
                         (job_id, document_id, "queued", now, now))
            self._invalidate(conn, case_id)
            self._audit(conn, actor, "document.ingested", case_id, document_id, 0,
                        sha256=sha, version=version, document_key=document_key,
                        profile=self.settings.profile, policy_digest=self.settings.policy_digest(),
                        request_id=request_id, job_id=job_id)
        return {"document_id": document_id, "job_id": job_id, "version": version, "duplicate": False}

    def claim(self, owner):
        now = time.time()
        with self.transaction() as conn:
            expired = conn.execute("SELECT j.*,d.case_id FROM jobs j JOIN documents d ON d.id=j.document_id "
                                   "WHERE j.status='running' AND j.lease_until<?", (now,)).fetchall()
            for row in expired:
                terminal = row["attempt"] >= self.settings.max_attempts
                conn.execute("UPDATE jobs SET status=?,owner=NULL,lease_token=NULL,lease_until=NULL,"
                             "available_at=?,last_error='WORKER_LEASE_EXPIRED' WHERE id=?",
                             ("failed" if terminal else "queued", now, row["id"]))
                conn.execute("UPDATE documents SET status=?,error_code='WORKER_LEASE_EXPIRED' WHERE id=?",
                             ("review" if terminal else "queued", row["document_id"]))
                self._audit(conn, "worker", "job.lease_expired", row["case_id"], row["document_id"],
                            attempt=row["attempt"], terminal=terminal)
            exhausted = conn.execute("SELECT j.id,j.document_id,d.case_id FROM jobs j JOIN documents d ON d.id=j.document_id WHERE j.status='queued' AND j.attempt>=?", (self.settings.max_attempts,)).fetchall()
            for row in exhausted:
                conn.execute("UPDATE jobs SET status='failed',last_error='ATTEMPTS_EXHAUSTED' WHERE id=?", (row["id"],))
                conn.execute("UPDATE documents SET status='review',error_code='ATTEMPTS_EXHAUSTED' WHERE id=?", (row["document_id"],))
                self._audit(conn, "worker", "job.attempt_budget_exhausted", row["case_id"], row["document_id"])
            running = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='running'").fetchone()[0]
            if running >= self.settings.max_workers:
                return None
            row = conn.execute(
                "SELECT j.*,d.size,d.case_id FROM jobs j JOIN documents d ON d.id=j.document_id "
                "WHERE j.status='queued' AND j.available_at<=? "
                "ORDER BY CASE WHEN ?-j.created_at>60 THEN -1 ELSE d.size/1048576 END,j.created_at LIMIT 1",
                (now, now)).fetchone()
            if row is None:
                return None
            token = uid()
            conn.execute("UPDATE jobs SET status='running',attempt=attempt+1,owner=?,lease_token=?,"
                         "lease_until=? WHERE id=?", (owner, token, now+self.settings.lease_seconds, row["id"]))
            conn.execute("UPDATE documents SET status='processing',error_code=NULL WHERE id=?",
                         (row["document_id"],))
            result = dict(conn.execute("SELECT * FROM jobs WHERE id=?", (row["id"],)).fetchone())
            result["document"] = self._document(conn, row["document_id"])
            return result

    @staticmethod
    def _owns(conn, job_id, token):
        return conn.execute("SELECT 1 FROM jobs WHERE id=? AND status='running' AND lease_token=? "
                            "AND lease_until>=?", (job_id, token, time.time())).fetchone() is not None

    def checkpoint(self, job, parsed: ParsedDocument):
        with self.transaction() as conn:
            if not self._owns(conn, job["id"], job["lease_token"]):
                return False
            doc = self._document(conn, job["document_id"])
            if parsed.sha256 != doc["sha256"]:
                raise StoreError("CHECKPOINT_MISMATCH", "Parser returned a different document digest")
            conn.execute("UPDATE documents SET parsed_json=? WHERE id=?",
                         (parsed.model_dump_json(), job["document_id"]))
            conn.execute("UPDATE jobs SET stage='extract' WHERE id=?", (job["id"],))
            return True

    def finish(self, job, extraction, checks, elapsed):
        with self.transaction() as conn:
            if not self._owns(conn, job["id"], job["lease_token"]):
                return False
            doc = self._document(conn, job["document_id"])
            if extraction.document_sha256 != doc["sha256"] or not self._is_current(conn, doc):
                raise StoreError("RESULT_MISMATCH", "Result does not refer to the current document")
            conn.execute("UPDATE documents SET status='ready',extraction_json=?,checks_json=?,error_code=NULL "
                         "WHERE id=?", (extraction.model_dump_json(), checks.model_dump_json(), doc["id"]))
            conn.execute("UPDATE jobs SET status='done',stage='done',lease_token=NULL,lease_until=NULL,"
                         "elapsed_seconds=?,finished_at=? WHERE id=?", (elapsed, time.time(), job["id"]))
            self._invalidate(conn, doc["case_id"])
            self._audit(conn, "worker", "document.processed", doc["case_id"], doc["id"], doc["revision"],
                        attempt=job["attempt"], decision=checks.decision, profile=extraction.profile,
                        model_version=extraction.model_version, elapsed_seconds=elapsed,
                        source_version=doc["version"], classification_proposal={
                            "kind": extraction.kind, "confidence": extraction.classification_confidence,
                            "model_version": extraction.model_version, "profile": extraction.profile})
            return True

    def fail(self, job, code, retryable=False):
        with self.transaction() as conn:
            if not self._owns(conn, job["id"], job["lease_token"]):
                return False
            retry = retryable and job["attempt"] < self.settings.max_attempts
            conn.execute("UPDATE jobs SET status=?,last_error=?,lease_token=NULL,lease_until=NULL,"
                         "available_at=? WHERE id=?", ("queued" if retry else "failed", code,
                          time.time() + self.settings.retry_seconds * (2 ** (job["attempt"]-1)), job["id"]))
            doc = self._document(conn, job["document_id"])
            conn.execute("UPDATE documents SET status=?,error_code=? WHERE id=?",
                         ("queued" if retry else "review", code, doc["id"]))
            self._audit(conn, "worker", "job.failed", doc["case_id"], doc["id"],
                        error_code=code, retry_scheduled=retry, attempt=job["attempt"])
            return True

    def document(self, document_id):
        with closing(self.connect()) as conn:
            # Document values, job state and their classification audit must come
            # from the same read snapshot while an operator submits a review.
            conn.execute("BEGIN")
            result = self._document(conn, document_id)
            classification = self._classification_state(conn, result)
            result["current"] = self._is_current(conn, result)
            result["job"] = dict(conn.execute("SELECT * FROM jobs WHERE document_id=?", (document_id,)).fetchone())
            for key in ("parsed", "extraction", "checks"):
                result[key] = json.loads(result.pop(key + "_json")) if result[key + "_json"] else None
            # Lease secrets are internal fencing capabilities, never sent to an operator.
            result["job"].pop("lease_token", None)
            result.update(self._classification_public(classification))
            return result

    @staticmethod
    def _classification_public(state):
        return {"classification_proposal": state["proposal"], "classification_review": state["review"],
                "classification_provenance_status": state["status"]}

    @staticmethod
    def _classification_state(conn, document, extraction=None):
        """Bind current kind to immutable model output and the complete review chain.

        This context is assembled from authenticated service audit events. It is
        never supplied by an extraction model or accepted from an API request.
        """
        state = {"proposal": None, "review": None, "status": "unavailable",
                 "reviewed": False, "review_chain_digest": None}
        if extraction is None and document["extraction_json"]:
            extraction = Extraction.model_validate_json(document["extraction_json"])
        if extraction is None:
            return state
        processed = conn.execute("SELECT * FROM audit WHERE document_id=? AND action='document.processed' "
                                 "ORDER BY id DESC LIMIT 1", (document["id"],)).fetchone()
        if processed is None:
            return state
        try:
            details = json.loads(processed["details_json"])
        except (TypeError, ValueError):
            state["status"] = "mismatch"
            return state
        if not isinstance(details, dict):
            state["status"] = "mismatch"
            return state
        proposal = details.get("classification_proposal")
        if proposal is None:
            return state
        allowed = {"purchase_order", "delivery_note", "invoice", "unknown"}
        state["proposal"] = proposal
        state["status"] = "mismatch"
        if (not isinstance(proposal, dict) or set(proposal) != {"kind", "confidence", "model_version", "profile"}
                or not isinstance(proposal["kind"], str) or proposal["kind"] not in allowed
                or not isinstance(proposal["confidence"], (int, float)) or isinstance(proposal["confidence"], bool)
                or not 0 <= proposal["confidence"] <= 1
                or details.get("source_version") != document["version"]
                or not isinstance(processed["revision"], int) or processed["revision"] < 0):
            return state
        kind, revision, chain, valid = proposal["kind"], processed["revision"], [], True
        reviews = conn.execute("SELECT * FROM audit WHERE document_id=? AND action='classification.reviewed' "
                               "AND id>? ORDER BY id", (document["id"], processed["id"])).fetchall()
        for event in reviews:
            try:
                review = json.loads(event["details_json"])
            except (TypeError, ValueError):
                return state
            if not isinstance(review, dict):
                return state
            expected = {"old_kind", "new_kind", "model_proposal", "reason", "source_version", "source_revision"}
            if (set(review) != expected or review.get("old_kind") != kind
                    or not isinstance(review.get("new_kind"), str) or review.get("new_kind") not in allowed
                    or review.get("model_proposal") != proposal
                    or review.get("source_version") != document["version"]
                    or type(review.get("source_revision")) is not int
                    or review["source_revision"] < revision
                    or event["revision"] != review["source_revision"]+1
                    or event["revision"] > document["revision"]
                    or not isinstance(review.get("reason"), str) or not review["reason"].strip()
                    or not event["actor"]):
                valid = False
            kind, revision = review.get("new_kind"), event["revision"]
            public = {"id": event["id"], "actor": event["actor"], "at": event["at"],
                      "revision": event["revision"], "source_version": review.get("source_version"),
                      "old_kind": review.get("old_kind"), "new_kind": review.get("new_kind"),
                      "reason": review.get("reason"), "model_proposal": review.get("model_proposal")}
            chain.append(public)
            state["review"] = {**public, "provenance_valid": False}
        valid = valid and (extraction.kind == kind and extraction.classification_confidence == proposal["confidence"]
                           and extraction.model_version == proposal["model_version"] and extraction.profile == proposal["profile"])
        state["review_chain_digest"] = digest(chain)
        state["status"] = "verified" if valid else "mismatch"
        if state["review"] is not None:
            state["review"]["provenance_valid"] = valid
        state["reviewed"] = valid and bool(chain) and kind != "unknown"
        return state

    @staticmethod
    def _snapshot(conn, case_id):
        from .rules import check_document, reconcile
        case = Store._case(conn, case_id)
        docs = Store._current_rows(conn, case_id)
        ready = [d for d in docs if d["extraction_json"] and d["status"] == "ready"]
        extractions = [Extraction.model_validate_json(d["extraction_json"]) for d in ready]
        classification = {d["id"]: Store._classification_state(conn, d) for d in docs}
        reviewed = {d["sha256"] for d in ready if classification[d["id"]]["reviewed"]}
        reconciliation = reconcile(extractions, reviewed_classifications=reviewed)
        # Recompute from current values, never trust cached check JSON at acceptance.
        checks = [check_document(extraction, classification_reviewed=classification[doc["id"]]["reviewed"])
                  for doc, extraction in zip(ready, extractions, strict=True)]
        for document, check in zip(ready, checks, strict=True):
            status = classification[document["id"]]["status"]
            if status != "verified":
                finding = Finding(code=f"classification_provenance_{status}", severity="warning" if status == "unavailable" else "error",
                                  message="Classification requires an intact original proposal and review chain.", document_id=document["id"])
                check.findings.append(finding)
                check.decision = "rejected" if status == "mismatch" or check.decision == "rejected" else "review"
                reconciliation.findings.append(finding)
                reconciliation.status = "review"
        eligible = bool(docs) and len(extractions) == len(docs) and all(
            check.decision == "eligible" for check in checks) and reconciliation.status in ("matched", "partial")
        bound = [{"id": d["id"], "sha256": d["sha256"], "version": d["version"],
                  "revision": d["revision"], "extraction_digest": digest(json.loads(d["extraction_json"]))
                  if d["extraction_json"] else None, "status": d["status"],
                  "classification": classification[d["id"]]} for d in docs]
        fingerprint = digest({"case_id": case_id, "documents": bound,
                              "reconciliation": reconciliation.model_dump(mode="json"),
                              "checks": [check.model_dump(mode="json") for check in checks]})
        return case, docs, reconciliation, eligible, fingerprint

    def case(self, case_id):
        with closing(self.connect()) as conn:
            conn.execute("BEGIN")
            case, docs, reconciliation, eligible, fingerprint = self._snapshot(conn, case_id)
            case.update({"documents": [{k: v for k, v in doc.items() if not k.endswith("_json")}
                                       for doc in docs],
                         "reconciliation": reconciliation.model_dump(mode="json"),
                         "eligible_for_acceptance": eligible, "fingerprint": fingerprint,
                         "accepted": case["accepted_fingerprint"] == fingerprint,
                         "published": case["published_fingerprint"] == fingerprint})
            return case

    def audit(self, case_id):
        with closing(self.connect()) as conn:
            self._case(conn, case_id)
            rows = [dict(r) for r in conn.execute("SELECT * FROM audit WHERE case_id=? ORDER BY id", (case_id,))]
            for row in rows:
                row["details"] = json.loads(row.pop("details_json"))
            return rows

    def _verify_sources(self, conn, documents):
        from .extraction import validate_evidence
        for document in documents:
            path = self.blob_path(document["sha256"])
            if not path.is_file():
                raise StoreError("BLOB_INTEGRITY", "A current original is missing", 503)
            with path.open("rb") as handle:
                actual = hashlib.file_digest(handle, "sha256").hexdigest()
            if actual != document["sha256"]:
                raise StoreError("BLOB_INTEGRITY", "A current original failed integrity verification", 503)
            parsed = ParsedDocument.model_validate_json(document["parsed_json"])
            extraction = Extraction.model_validate_json(document["extraction_json"])
            classification = self._classification_state(conn, document, extraction)
            if classification["status"] != "verified":
                raise StoreError("CLASSIFICATION_PROVENANCE", "Classification proposal or review chain is unavailable or inconsistent", 503)
            if parsed.sha256 != actual or extraction.document_sha256 != actual:
                raise StoreError("SOURCE_MISMATCH", "Result and source document do not agree", 503)
            verified = validate_evidence(parsed, extraction.model_copy(deep=True))
            if verified.kind != extraction.kind:
                raise StoreError("EVIDENCE_CHANGED", "Stored classification no longer passes validation", 503)
            fields = [(key, field, verified.fields[key]) for key, field in extraction.fields.items()]
            for index, line in enumerate(extraction.line_items):
                fields.extend((f"line_items.{index}.{key}", field, verified.line_items[index].fields[key])
                              for key, field in line.fields.items())
            for key, field, checked in fields:
                if field.origin == "extracted":
                    if field.model_dump() != checked.model_dump():
                        raise StoreError("EVIDENCE_CHANGED", "Stored extraction no longer passes evidence validation", 503)
                else:
                    changes = conn.execute("SELECT details_json FROM audit WHERE document_id=? AND action='field.corrected' ORDER BY id DESC", (document["id"],)).fetchall()
                    latest = next((json.loads(row[0]) for row in changes if json.loads(row[0])["field"] == key), None)
                    if latest is None or latest["new"] != field.model_dump(mode="json"):
                        raise StoreError("CORRECTION_AUDIT_MISMATCH", "Human value has no matching correction record", 503)

    def correct(self, document_id, field, value, reason, actor, expected_revision):
        from .extraction import normalize_value
        from .models import ExtractedField
        from .rules import check_document
        if not reason.strip() or len(reason) > 1000:
            raise StoreError("JUSTIFICATION_REQUIRED", "A correction requires a concise justification", 422)
        with self.transaction() as conn:
            doc = self._document(conn, document_id)
            if not self._is_current(conn, doc) or doc["revision"] != expected_revision:
                raise StoreError("STALE_REVISION", "Refresh the current document before correcting it")
            if doc["status"] != "ready" or not doc["extraction_json"]:
                raise StoreError("NOT_REVIEWABLE", "Only a processed current document can be corrected")
            extraction = Extraction.model_validate_json(doc["extraction_json"])
            if field.startswith("line_items."):
                match = re.fullmatch(r"line_items\.(\d+)\.(sku|quantity|unit_price|net_amount|tax_rate)", field)
                if not match or int(match[1]) >= len(extraction.line_items):
                    raise StoreError("INVALID_FIELD", "Invalid line field", 422)
                target, name = extraction.line_items[int(match[1])].fields, match[2]
            else:
                if field not in {"document_id", "purchase_order_id", "supplier_id", "currency",
                                 "subtotal", "tax", "total", "document_date"}:
                    raise StoreError("INVALID_FIELD", "Unknown critical field", 422)
                target, name = extraction.fields, field
            old = target.get(name, ExtractedField())
            try:
                normalized, transformations = normalize_value(name, value)
            except (ValueError, ArithmeticError) as exc:
                raise StoreError("INVALID_VALUE", str(exc), 422) from exc
            corrected = ExtractedField(raw=value, normalized=normalized, origin="human", status="corrected",
                                       evidence=old.evidence, transformations=transformations,
                                       reason=reason.strip())
            target[name] = corrected
            context = self._classification_state(conn, doc, extraction)
            checks = check_document(extraction, classification_reviewed=context["reviewed"])
            revision = doc["revision"] + 1
            conn.execute("UPDATE documents SET extraction_json=?,checks_json=?,revision=? WHERE id=?",
                         (extraction.model_dump_json(), checks.model_dump_json(), revision, document_id))
            self._invalidate(conn, doc["case_id"])
            self._audit(conn, actor, "field.corrected", doc["case_id"], document_id, revision,
                        field=field, old=old.model_dump(mode="json"), new=corrected.model_dump(mode="json"),
                        justification=reason.strip(), source_version=doc["version"])
        return self.document(document_id)

    def review_classification(self, document_id, kind, reason, actor, expected_revision):
        from .rules import check_document
        if kind not in {"purchase_order", "delivery_note", "invoice", "unknown"}:
            raise StoreError("INVALID_KIND", "Choose a supported document type", 422)
        if not reason.strip() or len(reason) > 1000:
            raise StoreError("JUSTIFICATION_REQUIRED", "Classification review requires a concise justification", 422)
        with self.transaction() as conn:
            document = self._document(conn, document_id)
            if not self._is_current(conn, document) or document["revision"] != expected_revision:
                raise StoreError("STALE_REVISION", "Refresh the current document before reviewing its type")
            if document["status"] != "ready" or not document["extraction_json"]:
                raise StoreError("NOT_REVIEWABLE", "Only a processed current document can be reviewed")
            extraction = Extraction.model_validate_json(document["extraction_json"])
            context = self._classification_state(conn, document, extraction)
            if context["status"] != "verified":
                raise StoreError("CLASSIFICATION_PROVENANCE", "Reprocess under the current runtime before reviewing classification", 503)
            old_kind = extraction.kind
            extraction.kind = kind
            # Keep the model score unchanged. Only the verified human context
            # permits bypassing its threshold; unknown remains an abstention.
            checks = check_document(extraction, classification_reviewed=kind != "unknown")
            revision = document["revision"]+1
            conn.execute("UPDATE documents SET extraction_json=?,checks_json=?,revision=? WHERE id=?",
                         (extraction.model_dump_json(), checks.model_dump_json(), revision, document_id))
            self._invalidate(conn, document["case_id"])
            self._audit(conn, actor, "classification.reviewed", document["case_id"], document_id, revision,
                        old_kind=old_kind, new_kind=kind, model_proposal=context["proposal"], reason=reason.strip(),
                        source_version=document["version"], source_revision=document["revision"])
        return self.document(document_id)

    def accept(self, case_id, actor, reason, expected_revision):
        if not reason.strip():
            raise StoreError("JUSTIFICATION_REQUIRED", "Acceptance requires a reason", 422)
        with self.transaction() as conn:
            case, docs, reconciliation, eligible, fingerprint = self._snapshot(conn, case_id)
            if case["revision"] != expected_revision:
                raise StoreError("STALE_REVISION", "Case changed; review its current revision")
            if not eligible:
                raise StoreError("NOT_ELIGIBLE", "Every current document and the reconciliation must pass")
            self._verify_sources(conn, docs)
            current_ids = {d["id"] for d in docs}
            corrections = conn.execute("SELECT document_id FROM audit WHERE case_id=? AND actor=? "
                                       "AND action IN ('field.corrected','classification.reviewed')", (case_id, actor)).fetchall()
            if any(row[0] in current_ids for row in corrections):
                raise StoreError("SELF_APPROVAL", "A different approver must review the corrected documents", 403)
            if case["accepted_fingerprint"] != fingerprint:
                conn.execute("UPDATE cases SET accepted_fingerprint=?,accepted_by=?,accepted_at=?,"
                             "acceptance_reason=? WHERE id=?", (fingerprint, actor, time.time(), reason.strip(), case_id))
                self._audit(conn, actor, "case.accepted", case_id, revision=case["revision"],
                            fingerprint=fingerprint, reason=reason.strip(), status=reconciliation.status)
        return self.case(case_id)

    def publish(self, case_id, actor, expected_revision):
        with self.transaction() as conn:
            case, docs, reconciliation, eligible, fingerprint = self._snapshot(conn, case_id)
            if case["revision"] != expected_revision:
                raise StoreError("STALE_REVISION", "Case changed before publication")
            if not eligible or case["accepted_fingerprint"] != fingerprint:
                raise StoreError("NOT_ACCEPTED", "Explicit acceptance of the current revision is required")
            self._verify_sources(conn, docs)
            existing = conn.execute("SELECT * FROM publications WHERE case_id=? AND fingerprint=?",
                                    (case_id, fingerprint)).fetchone()
            if existing:
                return {"id": existing["id"], "fingerprint": fingerprint, "duplicate": True}
            for doc in docs:
                extraction = Extraction.model_validate_json(doc["extraction_json"])
                if extraction.kind == "invoice":
                    supplier, invoice = (extraction.fields[n].normalized for n in ("supplier_id", "document_id"))
                    owner = conn.execute("SELECT case_id FROM published_invoices WHERE supplier_id=? AND invoice_id=?",
                                         (supplier, invoice)).fetchone()
                    if owner and owner[0] != case_id:
                        raise StoreError("INVOICE_ALREADY_PUBLISHED", "Invoice identity has already been published in another case")
                    conn.execute("INSERT OR IGNORE INTO published_invoices VALUES(?,?,?)", (supplier, invoice, case_id))
            publication_id, now = uid(), time.time()
            previous = conn.execute("SELECT id FROM publications WHERE case_id=? ORDER BY published_at DESC LIMIT 1",
                                    (case_id,)).fetchone()
            self._audit(conn, actor, "case.published", case_id, revision=case["revision"],
                        publication_id=publication_id, fingerprint=fingerprint)
            audit = [dict(r) for r in conn.execute("SELECT * FROM audit WHERE case_id=? ORDER BY id", (case_id,))]
            for entry in audit:
                entry["details"] = json.loads(entry.pop("details_json"))
            payload = {"schema_version": "control-dossier-1.0", "publication_id": publication_id,
                       "case_id": case_id, "case_name": case["name"], "case_revision": case["revision"],
                       "fingerprint": fingerprint, "published_at": now, "published_by": actor,
                       "supersedes_publication_id": previous[0] if previous else None,
                       "consumer_semantics": "upsert by case_id; do not treat revisions as new payment instructions",
                       "accepted_by": case["accepted_by"], "accepted_at": case["accepted_at"],
                       "acceptance_reason": case["acceptance_reason"],
                       "reconciliation": reconciliation.model_dump(mode="json"), "audit": audit,
                       "documents": [{"id": d["id"], "document_key": d["document_key"], "sha256": d["sha256"],
                                      "version": d["version"], "revision": d["revision"],
                                      "parsed": json.loads(d["parsed_json"]),
                                      "extraction": json.loads(d["extraction_json"]),
                                      "checks": json.loads(d["checks_json"]),
                                      **self._classification_public(self._classification_state(conn, d))} for d in docs]}
            conn.execute("INSERT INTO publications VALUES(?,?,?,?,?,?)", (publication_id, case_id, fingerprint,
                         now, actor, canonical(payload)))
            conn.execute("UPDATE cases SET published_fingerprint=? WHERE id=?", (fingerprint, case_id))
            return {"id": publication_id, "fingerprint": fingerprint, "duplicate": False}

    def export(self, case_id):
        with closing(self.connect()) as conn:
            conn.execute("BEGIN")
            case, _, _, _, fingerprint = self._snapshot(conn, case_id)
            if case["published_fingerprint"] != fingerprint:
                raise StoreError("NOT_PUBLISHED", "The current revision has not been published")
            row = conn.execute("SELECT payload_json FROM publications WHERE case_id=? AND fingerprint=?",
                               (case_id, fingerprint)).fetchone()
            return json.loads(row[0])

    def cancel(self, document_id, actor):
        with self.transaction() as conn:
            doc = self._document(conn, document_id)
            job = conn.execute("SELECT * FROM jobs WHERE document_id=?", (document_id,)).fetchone()
            if job["status"] == "cancelled":
                return {"cancelled": True}
            if job["status"] not in ("queued", "running"):
                raise StoreError("NOT_CANCELLABLE", "Only pending/running jobs can be cancelled")
            conn.execute("UPDATE jobs SET status='cancelled',lease_token=NULL,lease_until=NULL WHERE id=?", (job["id"],))
            conn.execute("UPDATE documents SET status='cancelled' WHERE id=?", (document_id,))
            self._invalidate(conn, doc["case_id"])
            self._audit(conn, actor, "job.cancelled", doc["case_id"], document_id)
        return {"cancelled": True}

    def retry(self, document_id, actor, reason):
        if not reason.strip():
            raise StoreError("JUSTIFICATION_REQUIRED", "A manual retry requires a reason", 422)
        with self.transaction() as conn:
            doc = self._document(conn, document_id)
            job = conn.execute("SELECT * FROM jobs WHERE document_id=?", (document_id,)).fetchone()
            if not self._is_current(conn, doc) or job["status"] not in ("failed", "cancelled"):
                raise StoreError("NOT_RETRYABLE", "Only failed/cancelled current versions can be manually retried")
            depth = conn.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('queued','running')").fetchone()[0]
            if depth >= self.settings.max_pending:
                raise StoreError("QUEUE_FULL", "Processing queue is full", 429)
            conn.execute("UPDATE jobs SET status='queued',attempt=0,owner=NULL,lease_token=NULL,lease_until=NULL,"
                         "available_at=?,last_error=NULL WHERE id=?", (time.time(), job["id"]))
            conn.execute("UPDATE documents SET status='queued',error_code=NULL,profile=?,policy_digest=?,"
                         "revision=revision+1 WHERE id=?", (self.settings.profile, self.settings.policy_digest(), document_id))
            self._invalidate(conn, doc["case_id"])
            self._audit(conn, actor, "job.manually_retried", doc["case_id"], document_id,
                        reason=reason, previous_attempts=job["attempt"],
                        old_policy_digest=doc["policy_digest"], new_policy_digest=self.settings.policy_digest())
        return self.document(document_id)

    def metrics(self):
        with closing(self.connect()) as conn:
            rows = conn.execute("SELECT status,COUNT(*) AS n FROM jobs GROUP BY status").fetchall()
            oldest = conn.execute("SELECT MIN(created_at) FROM jobs WHERE status='queued'").fetchone()[0]
            done = conn.execute("SELECT COUNT(*),COALESCE(SUM(elapsed_seconds),0) FROM jobs WHERE status='done'").fetchone()
            return {"jobs": {r[0]: r[1] for r in rows}, "oldest_queued_seconds": time.time()-oldest if oldest else 0,
                    "completed_count": done[0], "processing_seconds_sum": done[1],
                    "publications": conn.execute("SELECT COUNT(*) FROM publications").fetchone()[0]}
