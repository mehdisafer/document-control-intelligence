"""Real snapshot/restore and queue-age qualification with explicit fault injection."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import hashlib
import io
import json
from pathlib import Path
import random
import sqlite3
import tempfile
import threading
import time
import unittest

from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from dci.config import Settings
from dci.corpus import generate_demo
from dci.models import Extraction
from dci.operations import backup, restore
from dci.rules import check_document
from dci.store import Store, StoreError
from dci.worker import drain, process_one


class OperationsIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = tempfile.TemporaryDirectory(prefix="dci-operations-inputs-")
        cls.corpus = Path(cls.fixtures.name)
        manifest = generate_demo(cls.corpus, seed=991)
        cls.records = [row for row in manifest["documents"] if row["scenario"] == "accepted"]

    @classmethod
    def tearDownClass(cls):
        cls.fixtures.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="dci-operations-state-")
        self.root = Path(self.temporary.name)
        self.settings = Settings(home=self.root/"live")
        self.store = Store(self.settings)

    def tearDown(self):
        self.temporary.cleanup()

    def ingest_case(self, *, process=False):
        case_id = self.store.create_case("Synthetic recovery qualification", "operator")["id"]
        docs = [self.store.ingest(case_id, row["document_key"], Path(row["path"]).name,
                                  (self.corpus/row["path"]).read_bytes(), "operator") for row in self.records]
        if process:
            results = drain(self.store)
            self.assertTrue(all(result["outcome"] == "done" for result in results), results)
        return case_id, docs

    def snapshot(self, name="snapshot"):
        destination = self.root/name
        manifest = backup(self.store, destination)
        return destination, manifest

    def test_restored_published_export_and_originals_equal_snapshot(self):
        case_id, _ = self.ingest_case(process=True)
        current = self.store.case(case_id)
        self.assertTrue(current["eligible_for_acceptance"])
        self.store.accept(case_id, "approver", "Synthetic restore qualification.", current["revision"])
        self.store.publish(case_id, "publisher", current["revision"])
        expected = self.store.export(case_id)
        # These are deliberate exclusions, not actual reusable credentials/models.
        (self.store.home/"auth.json").write_text('{"test_only_secret_marker":true}')
        (self.store.home/"model-artifact.bin").write_bytes(b"test-only marker")
        snapshot, manifest = self.snapshot()
        self.store.create_case("Created after snapshot", "operator")
        target = self.root/"restored"
        result = restore(snapshot, target)
        recovered = Store(Settings(home=target))
        self.assertEqual(recovered.export(case_id), expected)
        self.assertEqual(len(recovered.list_cases()), 1)
        self.assertEqual(result["interrupted_jobs_requeued"], 0)
        self.assertFalse(result["secrets_restored"])
        self.assertFalse(result["models_restored"])
        self.assertNotIn("auth.json", manifest["files"])
        self.assertNotIn("model-artifact.bin", manifest["files"])
        for document in expected["documents"]:
            actual = hashlib.sha256(recovered.blob_path(document["sha256"]).read_bytes()).hexdigest()
            self.assertEqual(actual, document["sha256"])

    def test_running_job_is_requeued_and_resumes_actual_parse_checkpoint(self):
        case_id = self.store.create_case("Interrupted worker", "operator")["id"]
        row = self.records[0]
        uploaded = self.store.ingest(case_id, row["document_key"], "fixture.pdf",
                                     (self.corpus/row["path"]).read_bytes(), "operator")
        self.assertEqual(process_one(self.store, stop_after_parse=True)["outcome"], "checkpoint_only")
        original = self.store.document(uploaded["document_id"])
        with closing(self.store.connect()) as conn:
            old_job = dict(conn.execute("SELECT * FROM jobs WHERE id=?", (uploaded["job_id"],)).fetchone())
        snapshot, _ = self.snapshot()
        target = self.root/"restored"
        result = restore(snapshot, target)
        self.assertEqual(result["interrupted_jobs_requeued"], 1)
        recovered = Store(Settings(home=target))
        queued = recovered.document(uploaded["document_id"])
        self.assertEqual(queued["status"], "queued")
        self.assertEqual(queued["job"]["attempt"], 1)
        self.assertEqual(process_one(recovered)["outcome"], "done")
        finished = recovered.document(uploaded["document_id"])
        self.assertEqual(finished["parsed"], original["parsed"])
        self.assertEqual(finished["job"]["attempt"], 2)
        extraction = Extraction.model_validate(finished["extraction"])
        self.assertFalse(recovered.finish(old_job, extraction, check_document(extraction), .01))
        self.assertTrue(any(event["action"] == "job.restored" for event in recovered.audit(case_id)))

    def test_restore_manifest_must_include_database_and_every_referenced_blob(self):
        self.ingest_case()
        snapshot, manifest = self.snapshot()
        blob_name = next(name for name in manifest["files"] if name.startswith("blobs/"))
        for index, omitted in enumerate(("control.db", blob_name)):
            with self.subTest(omitted=omitted):
                changed = json.loads(json.dumps(manifest))
                del changed["files"][omitted]
                (snapshot/"manifest.json").write_text(json.dumps(changed))
                target = self.root/f"incomplete-{index}"
                with self.assertRaises((ValueError, StoreError)):
                    restore(snapshot, target)
                self.assertFalse(target.exists(), "Incomplete backups must fail before destination creation.")

    def test_corrupt_manifest_or_retained_blob_fails_closed(self):
        self.ingest_case()
        snapshot, manifest = self.snapshot()
        (snapshot/"manifest.json").write_text('{"truncated":')
        with self.assertRaises(ValueError):
            restore(snapshot, self.root/"bad-json")
        (snapshot/"manifest.json").write_text(json.dumps({**manifest, "schema_version": "unknown"}))
        with self.assertRaises(ValueError):
            restore(snapshot, self.root/"bad-schema")
        (snapshot/"manifest.json").write_text(json.dumps(manifest))
        member = next(name for name in manifest["files"] if name.startswith("blobs/"))
        (snapshot/member).write_bytes((snapshot/member).read_bytes()+b"\n% storage fault\n")
        with self.assertRaises(ValueError):
            restore(snapshot, self.root/"bad-blob")
        for name in ("bad-json", "bad-schema", "bad-blob"):
            self.assertFalse((self.root/name).exists())

    def test_manifest_cannot_traverse_outside_snapshot(self):
        self.ingest_case()
        snapshot, manifest = self.snapshot()
        marker = self.root/"outside-marker.txt"
        marker.write_bytes(b"synthetic outside marker")
        manifest["files"]["../outside-marker.txt"] = hashlib.sha256(marker.read_bytes()).hexdigest()
        (snapshot/"manifest.json").write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):
            restore(snapshot, self.root/"traversal")
        self.assertEqual(marker.read_bytes(), b"synthetic outside marker")
        self.assertFalse((self.root/"traversal").exists())

    def test_existing_destination_is_refused_and_source_corruption_blocks_backup(self):
        _, documents = self.ingest_case()
        snapshot, _ = self.snapshot()
        target = self.root/"existing"
        target.mkdir()
        (target/"marker").write_text("preserve")
        with self.assertRaises(ValueError):
            restore(snapshot, target)
        with self.assertRaises(ValueError):
            backup(self.store, snapshot)
        self.assertEqual((target/"marker").read_text(), "preserve")
        document = self.store.document(documents[0]["document_id"])
        original = self.store.blob_path(document["sha256"])
        original.write_bytes(original.read_bytes()+b"\n% corruption\n")
        with self.assertRaises(StoreError) as error:
            backup(self.store, self.root/"failed-snapshot")
        self.assertEqual(error.exception.code, "BACKUP_INTEGRITY")
        self.assertFalse((self.root/"failed-snapshot/manifest.json").exists())

    def test_snapshot_remains_consistent_during_real_concurrent_ingestion(self):
        self.ingest_case()
        row = self.records[0]
        content = (self.corpus/row["path"]).read_bytes()
        gate = threading.Event()
        def writer():
            gate.wait(timeout=5)
            for index in range(15):
                case_id = self.store.create_case(f"Concurrent {index}", "operator")["id"]
                self.store.ingest(case_id, "po", "fixture.pdf", content, "operator")
        with ThreadPoolExecutor(max_workers=1) as pool:
            work = pool.submit(writer)
            gate.set()
            snapshot, manifest = self.snapshot()
            work.result(timeout=15)
        with closing(sqlite3.connect(snapshot/"control.db")) as conn:
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            referenced = {row[0] for row in conn.execute("SELECT DISTINCT sha256 FROM documents")}
            count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        blobs = {Path(name).stem for name in manifest["files"] if name.startswith("blobs/")}
        self.assertEqual(blobs, referenced)
        self.assertGreaterEqual(count, 3)
        self.assertLessEqual(count, 18)
        target = self.root/"restored-concurrent"
        restore(snapshot, target)
        with closing(sqlite3.connect(target/"control.db")) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0], count)

    def test_aged_large_document_cannot_starve_behind_new_small_documents(self):
        rng = random.Random(903)
        image = Image.frombytes("RGB", (710, 710), rng.randbytes(710*710*3))
        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, invariant=1)
        pdf.drawImage(ImageReader(image), 30, 30, width=500, height=500)
        pdf.drawString(30, 760, "Synthetic large-document queue qualification")
        pdf.showPage()
        pdf.save()
        image.close()
        large = buffer.getvalue()
        self.assertGreater(len(large), 1_048_576)
        case_id = self.store.create_case("Large queue input", "operator")["id"]
        uploaded = self.store.ingest(case_id, "large", "large.pdf", large, "operator")
        row = self.records[0]
        first_case = self.store.create_case("First small input", "operator")["id"]
        small = self.store.ingest(first_case, "small", "small.pdf", (self.corpus/row["path"]).read_bytes(), "operator")
        claimed = self.store.claim("scheduler-check")
        self.assertEqual(claimed["document_id"], small["document_id"])
        self.store.cancel(small["document_id"], "operator")
        another_case = self.store.create_case("New small input", "operator")["id"]
        self.store.ingest(another_case, "small", "small.pdf", (self.corpus/row["path"]).read_bytes(), "operator")
        with self.store.transaction() as conn:
            # Explicit clock-age injection avoids a61second sleep; size is the
            # actual1.8MB generated PDF, not a forged scheduling field.
            conn.execute("UPDATE jobs SET created_at=? WHERE id=?", (time.time()-61, uploaded["job_id"]))
        aged = self.store.claim("scheduler-check")
        self.assertEqual(aged["document_id"], uploaded["document_id"])


if __name__ == "__main__":
    unittest.main()
