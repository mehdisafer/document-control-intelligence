"""Restore must preserve the retry allowance, including an exhausted active lease."""
import tempfile
import unittest
from pathlib import Path

from dci.config import Settings
from dci.corpus import generate_demo
from dci.operations import backup, restore
from dci.store import Store


class RestoredBudgetTests(unittest.TestCase):
    def test_restored_last_attempt_does_not_gain_an_extra_automatic_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = generate_demo(root / "corpus")
            source = root / "corpus" / manifest["documents"][0]["path"]
            store = Store(Settings(home=root / "live", max_attempts=1))
            case = store.create_case("Retry budget", "operator")
            doc = store.ingest(case["id"], "order", "order.pdf", source.read_bytes(), "operator")
            job = store.claim("worker-before-snapshot")
            self.assertEqual(job["attempt"], 1)
            backup(store, root / "snapshot")
            restore(root / "snapshot", root / "restored")
            recovered = Store(Settings(home=root / "restored", max_attempts=1))
            self.assertIsNone(recovered.claim("worker-after-restore"))
            result = recovered.document(doc["document_id"])
            self.assertEqual(result["job"]["attempt"], 1)
            self.assertEqual(result["job"]["status"], "failed")
            self.assertEqual(result["error_code"], "ATTEMPTS_EXHAUSTED")
