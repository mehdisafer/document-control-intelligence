"""A queued local Qwen job must be bound to its effective source and prompt.

The short synthetic PDF header is deliberately not parseable; this exercises
policy fencing *before* parsing, without a model, a live host or a provider.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
from unittest import TestCase
from unittest.mock import patch

from dci import extraction, llm
from dci.config import Settings
from dci.store import Store
from dci.worker import process_one


class QwenQueuedPolicyIdentityTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dci-llm-policy-only-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.llm_file = self.root / "qwen.json"
        self.llm_file.write_text('{"test_only_marker":"NOT_A_CREDENTIAL"}', encoding="utf-8")
        self.settings = Settings(
            home=self.root / "state", profile="local-llm", llm_config_file=self.llm_file,
        )

    def test_prompt_and_source_hashes_are_in_local_llm_policy_only(self):
        policy = self.settings.processing_policy()
        identity = policy["local_llm_request_identity"]
        self.assertEqual(identity["prompt_version"], llm.PROMPT_VERSION)
        self.assertEqual(identity["prompt_sha256"],
                         hashlib.sha256(llm.PROMPT.encode("utf-8")).hexdigest())
        self.assertEqual(identity["model_sha256"], llm.MODEL_SHA256)
        self.assertEqual(identity["runtime_binary_sha256"], llm.RUNTIME_BINARY_SHA256)
        self.assertEqual(identity["llm_source_sha256"],
                         hashlib.sha256(Path(llm.__file__).read_bytes()).hexdigest())
        self.assertEqual(identity["extraction_source_sha256"],
                         hashlib.sha256(Path(extraction.__file__).read_bytes()).hexdigest())
        self.assertEqual(self.settings.policy_digest(), self.settings.policy_digest())
        self.assertNotIn("NOT_A_CREDENTIAL", str(policy))
        self.assertNotIn("local_llm_request_identity", Settings().processing_policy())

    def test_prompt_change_without_package_version_bump_changes_digest(self):
        before = self.settings.policy_digest()
        with patch.object(llm, "PROMPT", llm.PROMPT + "\nTEST_ONLY_CHANGED_PROMPT"):
            self.assertNotEqual(self.settings.policy_digest(), before)
        self.assertEqual(self.settings.policy_digest(), before)

    def test_prompt_version_change_with_identical_text_changes_digest(self):
        before = self.settings.policy_digest()
        with patch.object(llm, "PROMPT_VERSION", llm.PROMPT_VERSION + "-test"):
            self.assertNotEqual(self.settings.policy_digest(), before)

    def test_llm_source_contract_changes_even_with_constant_prompt(self):
        original = self.settings.policy_digest()
        fake = self.root / "synthetic-llm-source.py"
        fake.write_text("source_contract_v1\n", encoding="utf-8")
        with patch.object(llm, "__file__", str(fake)):
            first = self.settings.policy_digest()
            fake.write_text("source_contract_v2\n", encoding="utf-8")
            self.assertNotEqual(self.settings.policy_digest(), first)
        self.assertNotEqual(first, original)

    def test_field_label_source_change_invalidates_policy(self):
        original = self.settings.policy_digest()
        fake = self.root / "synthetic-extraction-source.py"
        fake.write_text("field_contract_v1\n", encoding="utf-8")
        with patch.object(extraction, "__file__", str(fake)):
            first = self.settings.policy_digest()
            fake.write_text("field_contract_v2\n", encoding="utf-8")
            self.assertNotEqual(self.settings.policy_digest(), first)
        self.assertNotEqual(first, original)

    def test_baseline_and_linear_profiles_do_not_depend_on_qwen_prompt(self):
        baseline = Settings(home=self.root / "baseline")
        model = self.root / "linear-model.json"
        model.write_text('{"synthetic":true}', encoding="utf-8")
        linear = Settings(home=self.root / "linear", profile="local-linear", model_path=model)
        before = (baseline.policy_digest(), linear.policy_digest())
        with patch.object(llm, "PROMPT", llm.PROMPT + "\nTEST_ONLY_CHANGED_PROMPT"):
            self.assertEqual((baseline.policy_digest(), linear.policy_digest()), before)

    def test_queued_qwen_document_fails_before_parser_or_model(self):
        store = Store(self.settings)
        case_id = store.create_case("Synthetic Qwen policy transition", "operator")["id"]
        uploaded = store.ingest(
            case_id, "purchase-order", "synthetic.pdf",
            b"%PDF-1.4\n% test-only queued-policy binding\n", "operator",
        )
        document_id = uploaded["document_id"]
        before = store.document(document_id)
        self.assertEqual(before["status"], "queued")
        previous_digest = before["policy_digest"]
        with patch.object(llm, "PROMPT", llm.PROMPT + "\nTEST_ONLY_CHANGED_PROMPT"):
            self.assertNotEqual(self.settings.policy_digest(), previous_digest)
            result = process_one(store)
        self.assertEqual(result["outcome"], "policy_changed")
        after = store.document(document_id)
        self.assertEqual(after["error_code"], "PROCESSING_POLICY_CHANGED")
        self.assertIsNone(after["extraction"])
        self.assertNotEqual(after["status"], "ready")


if __name__ == "__main__":
    import unittest
    unittest.main()
