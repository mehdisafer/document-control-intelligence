import json
import tempfile
import unittest
from pathlib import Path

from dci.extraction import LABELS, SCALAR_KEYS
from dci.llm import LlamaConfig, ModelUnavailable, _validate_proposal
from dci.local_model import ARTIFACT_VERSION, LinearHead, LocalModel, ModelError, _fit
from pydantic import ValidationError


class LocalLinearTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        texts = []
        labels = []
        for key, variants in LABELS.items():
            for label in variants:
                texts.extend([label] * 3)
                labels.extend([key] * 3)
        cls.field, cls.metrics = _fit(texts, labels)
        titles = ["purchase order", "bon de commande", "delivery note", "bon de livraison", "invoice", "facture"]
        kinds = ["purchase_order", "purchase_order", "delivery_note", "delivery_note", "invoice", "invoice"]
        cls.document, _ = _fit(titles * 3, kinds * 3)

    def artifact(self):
        return {"format": ARTIFACT_VERSION, "metadata": {"training_split": "train"},
                "thresholds": {"document": .8, "label": .7},
                "document": self.document, "field": self.field}

    def test_real_fitted_field_inference_matches_semantics(self):
        head = LinearHead(self.field, set(SCALAR_KEYS))
        for label, expected in [("Total TTC", "total"), ("Fournisseur", "supplier_id"), ("Subtotal", "subtotal")]:
            kind, probability = head.predict(label)
            self.assertEqual(kind, expected)
            self.assertGreater(probability, .7)
        self.assertLess(self.metrics["safe_runtime_max_probability_delta"], 1e-10)

    def test_json_roundtrip_no_pickle_or_executable_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.json"
            path.write_text(json.dumps(self.artifact()))
            model = LocalModel.load(path)
            self.assertEqual(model.classify_label("Currency")[0], "currency")
            data = self.artifact()
            data["field"] = dict(data["field"], callable="os.system")
            path.write_text(json.dumps(data))
            with self.assertRaises(ModelError):
                LocalModel.load(path)

    def test_reject_nonfinite_or_wrong_shape_weights(self):
        for key, value in [("idf", [float("nan")]), ("coefficients", [[1.0]])]:
            data = dict(self.field)
            data[key] = value
            with self.assertRaises(ModelError):
                LinearHead(data, set(SCALAR_KEYS))

    def test_model_training_split_must_be_explicit(self):
        data = self.artifact()
        data["metadata"] = {"training_split": "test"}
        with self.assertRaises(ModelError):
            LocalModel(data, "0" * 64)


class LlmBoundaryTests(unittest.TestCase):
    def test_model_route_is_allowlisted_and_export_policy_fixed(self):
        for overrides in [{"provider": "cloud"}, {"base_url": "https://example.org"},
                          {"model_id": "unapproved"}, {"max_external_cost_usd": 1},
                          {"export_policy": "allow_cloud"}, {"port": 443}]:
            with self.subTest(overrides=overrides), self.assertRaises(ValidationError):
                LlamaConfig(model_path=Path("unused.gguf"), **overrides)

    def test_schema_rejects_invented_ids_and_duplicate_rows(self):
        proposal = {"kind": "invoice", "fields": {key: None for key in SCALAR_KEYS}, "line_rows": ["r1"]}
        # The source contract now authorizes IDs *per printed field*.
        allowed = {key: [] for key in SCALAR_KEYS}
        allowed["total"] = ["c1"]
        _validate_proposal(proposal, allowed, {"r1"})
        proposal["fields"]["total"] = "invented"
        with self.assertRaises(ModelUnavailable):
            _validate_proposal(proposal, allowed, {"r1"})
        proposal["fields"]["total"] = "c1"
        proposal["line_rows"] = ["r1", "r1"]
        with self.assertRaises(ModelUnavailable):
            _validate_proposal(proposal, allowed, {"r1"})


if __name__ == "__main__":
    unittest.main()
