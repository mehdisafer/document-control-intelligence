"""Consistent snapshots and non-destructive restore to a new destination."""

from contextlib import closing
import hashlib
import json
import shutil
import sqlite3
import time
from pathlib import Path

from .config import Settings
from .store import Store, StoreError


def backup(store: Store, target: Path):
    target = Path(target).resolve()
    if target.exists():
        raise ValueError("Backup destination must not already exist")
    if target == store.home or store.home in target.parents:
        raise ValueError("Backup must be outside the live data directory")
    target.mkdir(parents=True)
    with closing(store.connect()) as source, closing(sqlite3.connect(target / "control.db")) as destination:
        source.backup(destination)
    # Copy exactly the immutable originals referenced by the DB snapshot. New
    # ingestions after the backup transaction do not enter this snapshot.
    with closing(sqlite3.connect(target / "control.db")) as conn:
        digests = [row[0] for row in conn.execute("SELECT DISTINCT sha256 FROM documents")]
    files = {}
    for sha in digests:
        original = store.blob_path(sha)
        output = target / "blobs" / sha[:2] / f"{sha}.pdf"
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, output)
        with output.open("rb") as handle:
            actual = hashlib.file_digest(handle, "sha256").hexdigest()
        if actual != sha:
            raise StoreError("BACKUP_INTEGRITY", "Source blob changed or is corrupt", 503)
        files[output.relative_to(target).as_posix()] = actual
    files["control.db"] = hashlib.sha256((target / "control.db").read_bytes()).hexdigest()
    manifest = {"schema_version": "backup-1.0", "created_at": time.time(), "files": files,
                "secrets_included": False, "model_artifacts_included": False,
                "restore_policy": "new destination only; interrupted jobs requeued; actor/model provisioning required"}
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def restore(snapshot: Path, target: Path):
    snapshot, target = Path(snapshot).resolve(), Path(target).resolve()
    if target.exists():
        raise ValueError("Restore destination must not already exist")
    manifest = json.loads((snapshot / "manifest.json").read_text())
    if manifest.get("schema_version") != "backup-1.0" or not isinstance(manifest.get("files"), dict):
        raise ValueError("Unsupported backup manifest")
    if "control.db" not in manifest["files"]:
        raise ValueError("Backup manifest must include the database")
    for relative, expected in manifest["files"].items():
        path = (snapshot / relative).resolve()
        if snapshot not in path.parents or not path.is_file() or path.is_symlink():
            raise ValueError("Invalid backup file path")
        if relative != "control.db" and not relative.startswith("blobs/"):
            raise ValueError("Unexpected backup member")
        with path.open("rb") as handle:
            actual = hashlib.file_digest(handle, "sha256").hexdigest()
        if actual != expected:
            raise ValueError("Backup integrity mismatch")
    with closing(sqlite3.connect(f"file:{snapshot / 'control.db'}?mode=ro", uri=True)) as conn:
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Backup database integrity check failed")
        if conn.execute("PRAGMA user_version").fetchone()[0] != 1:
            raise ValueError("Restore supports schema version 1 only")
        expected_paths = {"control.db"}
        for (sha,) in conn.execute("SELECT DISTINCT sha256 FROM documents"):
            import re
            if not isinstance(sha, str) or re.fullmatch(r"[0-9a-f]{64}", sha) is None:
                raise ValueError("Backup database contains an invalid object digest")
            relative = f"blobs/{sha[:2]}/{sha}.pdf"
            expected_paths.add(relative)
            if manifest["files"].get(relative) != sha:
                raise ValueError("Manifest is missing a referenced original or has an inconsistent digest")
        if set(manifest["files"]) != expected_paths:
            raise ValueError("Manifest must contain exactly the database and its referenced originals")
    target.mkdir(parents=True)
    for relative in manifest["files"]:
        output = target / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(snapshot / relative, output)
    store = Store(Settings(home=target))
    with store.transaction() as conn:
        active = conn.execute("SELECT j.id,j.document_id,d.case_id FROM jobs j JOIN documents d "
                              "ON j.document_id=d.id WHERE j.status='running'").fetchall()
        for row in active:
            conn.execute("UPDATE jobs SET status='queued',owner=NULL,lease_token=NULL,lease_until=NULL,available_at=? "
                         "WHERE id=?", (time.time(), row["id"]))
            conn.execute("UPDATE documents SET status='queued' WHERE id=?", (row["document_id"],))
            store._audit(conn, "restore-operator", "job.restored", row["case_id"], row["document_id"])
    return {"restored_files": len(manifest["files"]), "interrupted_jobs_requeued": len(active),
            "target": str(target), "secrets_restored": False, "models_restored": False}
