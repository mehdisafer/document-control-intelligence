"""Guard the offline Qwen forensic parser without invoking a model."""
import hashlib
import io
import tarfile
import unittest

from scripts.audit_qwen_archive import (
    canonical_label, confusion, exact_title, load_verified, read_literal,
)


class QwenArchiveAuditTests(unittest.TestCase):
    def test_french_label_canonicalization(self):
        self.assertEqual(canonical_label(" Référence  document: "), "reference document")

    def test_static_historical_constants_not_executed(self):
        self.assertEqual(read_literal("TITLES = {'invoice': ('FACTURE',)}", "TITLES"),
                         {"invoice": ("FACTURE",)})
        with self.assertRaises((ValueError, TypeError)):
            read_literal("TITLES = unsafe_code()", "TITLES")

    def test_strict_title_not_body_reference(self):
        titles = {"invoice": ("INVOICE",), "purchase_order": ("PURCHASE ORDER",)}
        parsed = {"pages": [{"text": "INVOICE\nPurchase order: PO-1"}]}
        self.assertEqual(exact_title(parsed, titles), "invoice")
        parsed["pages"][0]["text"] += "\nPURCHASE ORDER"
        self.assertEqual(exact_title(parsed, titles), "unknown")

    def test_original_proposal_and_final_confusion_differ(self):
        rows = [{"truth": "invoice", "proposal": "invoice", "verified": "unknown"},
                {"truth": "invoice", "proposal": "unknown", "verified": "unknown"}]
        self.assertEqual(confusion(rows, "proposal")["invoice"], {"invoice": 1, "unknown": 1})
        self.assertEqual(confusion(rows, "verified")["invoice"], {"unknown": 2})

    def fixture(self, path="tests/sample.json"):
        content = b"{}"
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode="w:gz") as tar:
            member = tarfile.TarInfo(path)
            member.size = len(content)
            tar.addfile(member, io.BytesIO(content))
        archive = output.getvalue()
        return archive, {"archive": {
            "bytes": len(archive), "sha256": hashlib.sha256(archive).hexdigest(),
            "member_count": 1, "uncompressed_bytes": len(content),
            "members": [{"member": path, "bytes": len(content),
                         "sha256": hashlib.sha256(content).hexdigest()}]}}

    def test_valid_indexed_archive(self):
        archive, index = self.fixture()
        self.assertEqual(load_verified(archive, index), {"tests/sample.json": b"{}"})

    def test_wrong_archive_digest_fails(self):
        archive, index = self.fixture()
        index["archive"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "digest"):
            load_verified(archive, index)

    def test_wrong_member_digest_fails(self):
        archive, index = self.fixture()
        index["archive"]["members"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "member"):
            load_verified(archive, index)

    def test_path_traversal_fails(self):
        archive, index = self.fixture("../escape")
        with self.assertRaisesRegex(ValueError, "unsafe"):
            load_verified(archive, index)


if __name__ == "__main__":
    unittest.main()
