"""Trainable local linear models with a non-executable JSON artifact format.

Classification and semantic field assignment are fitted independently. Runtime
inference is a bounded TF-IDF/linear calculation; artifacts cannot name code.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
from collections import Counter
from pathlib import Path

import numpy as np

from .models import ParsedDocument

ARTIFACT_VERSION = "dci-local-linear-1.1"
ALLOWED_KINDS = ("delivery_note", "invoice", "purchase_order")
MAX_ARTIFACT_BYTES = 12_000_000
MAX_FEATURES = 18000


class ModelError(ValueError):
    """Invalid, unavailable or incompatible local model."""

    def __init__(self, message: str, code: str = "MODEL_INVALID"):
        super().__init__(message)
        self.code = code


def _features(text: str) -> dict[str, int]:
    # Same explicit feature map at fitting/inference; no serialized callables.
    from .extraction import label_text
    text = label_text(text[:12000])
    counts: Counter[str] = Counter()
    for word in text.split():
        counts["w:" + word] += 1
        padded = " " + word + " "
        for n in (2, 3, 4):
            for pos in range(max(1, len(padded) - n + 1)):
                counts[f"c{n}:" + padded[pos:pos+n]] += 1
    return dict(counts)


def _document_text(parsed: ParsedDocument) -> str:
    # Reinforce the document heading without consulting a title-to-kind lookup.
    text = "\n".join(page.text for page in parsed.pages)[:12000]
    lines = text.splitlines()
    heading = lines[0] if lines else ""
    first_lines = "\n".join(lines[:5])
    # The class is printed in the page heading. Tables shared across all three
    # classes otherwise swamp that signal as document length/layout changes.
    return (heading + "\n") * 8 + first_lines + "\n" + text[:600]


class LinearHead:
    def __init__(self, data: dict, allowed_classes: set[str]):
        if set(data) != {"features", "idf", "classes", "coefficients", "intercept"}:
            raise ModelError("Unexpected linear model keys")
        features = data["features"]
        classes = data["classes"]
        if not isinstance(features, list) or not 1 <= len(features) <= MAX_FEATURES:
            raise ModelError("Invalid feature count")
        if not all(isinstance(f, str) and 1 <= len(f) <= 200 for f in features) or len(set(features)) != len(features):
            raise ModelError("Invalid feature vocabulary")
        if not isinstance(classes, list) or len(classes) < 2 or len(set(classes)) != len(classes) or not set(classes) <= allowed_classes:
            raise ModelError("Invalid class vocabulary")
        try:
            idf = np.asarray(data["idf"], dtype=np.float64)
            coefficients = np.asarray(data["coefficients"], dtype=np.float64)
            intercept = np.asarray(data["intercept"], dtype=np.float64)
        except (TypeError, ValueError) as exc:
            raise ModelError("Invalid numeric weights") from exc
        n_rows = 1 if len(classes) == 2 else len(classes)
        if idf.shape != (len(features),) or coefficients.shape != (n_rows, len(features)) or intercept.shape != (n_rows,):
            raise ModelError("Model matrix dimensions do not match vocabulary/classes")
        if not all(np.isfinite(a).all() for a in (idf, coefficients, intercept)) or not (idf >= 1).all():
            raise ModelError("Nonfinite or invalid model weights")
        if np.abs(coefficients).max() > 1000 or np.abs(intercept).max() > 1000:
            raise ModelError("Model weights exceed bounds")
        self.vocabulary = {word: index for index, word in enumerate(features)}
        self.idf, self.coefficients, self.intercept = idf, coefficients, intercept
        self.classes = classes

    def predict(self, text: str) -> tuple[str, float]:
        vector = np.zeros(len(self.vocabulary), dtype=np.float64)
        for word, count in _features(text).items():
            index = self.vocabulary.get(word)
            if index is not None:
                vector[index] = (1 + math.log(count)) * self.idf[index]
        norm = float(np.linalg.norm(vector))
        if not norm:
            return "unknown", 0.0
        vector /= norm
        scores = self.coefficients @ vector + self.intercept
        if len(self.classes) == 2:
            p = 1 / (1 + math.exp(-max(-700, min(700, float(scores[0])))))
            probabilities = np.asarray([1 - p, p])
        else:
            probabilities = np.exp(scores - scores.max())
            probabilities /= probabilities.sum()
        index = int(probabilities.argmax())
        return self.classes[index], float(probabilities[index])


class LocalModel:
    def __init__(self, data: dict, digest: str):
        from .extraction import SCALAR_KEYS
        if data.get("format") != ARTIFACT_VERSION:
            raise ModelError("Unsupported model format")
        metadata = data.get("metadata", {})
        if metadata.get("training_split") != "train":
            raise ModelError("Model does not declare training-only provenance")
        self.document = LinearHead(data["document"], set(ALLOWED_KINDS))
        self.field = LinearHead(data["field"], set(SCALAR_KEYS))
        thresholds = data.get("thresholds", {})
        self.document_threshold = float(thresholds.get("document", 0.80))
        self.label_threshold = float(thresholds.get("label", 0.70))
        if not 0.5 <= self.document_threshold <= 1 or not 0.5 <= self.label_threshold <= 1:
            raise ModelError("Invalid model abstention thresholds")
        self.version = f"{ARTIFACT_VERSION}:{digest[:16]}"
        self.metadata = metadata

    @classmethod
    def load(cls, path: Path) -> "LocalModel":
        if path.stat().st_size > MAX_ARTIFACT_BYTES:
            raise ModelError("Model artifact is too large")
        raw = path.read_bytes()
        if len(raw) > MAX_ARTIFACT_BYTES:
            raise ModelError("Model artifact is too large")
        try:
            data = json.loads(raw)
            return cls(data, hashlib.sha256(raw).hexdigest())
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ModelError("Malformed model artifact") from exc

    def classify(self, parsed: ParsedDocument) -> tuple[str, float]:
        kind, confidence = self.document.predict(_document_text(parsed))
        return (kind if confidence >= self.document_threshold else "unknown"), confidence

    def classify_label(self, label: str) -> tuple[str, float]:
        return self.field.predict(label)


def _fit(texts: list[str], labels: list[str]) -> tuple[dict, dict]:
    from sklearn.feature_extraction import DictVectorizer
    from sklearn.feature_extraction.text import TfidfTransformer
    from sklearn.linear_model import LogisticRegression
    vectorizer = DictVectorizer(sparse=True)
    counts = vectorizer.fit_transform([_features(text) for text in texts])
    if counts.shape[1] > MAX_FEATURES:
        raise ModelError("Training vocabulary exceeds configured artifact bound")
    tfidf = TfidfTransformer(sublinear_tf=True)
    matrix = tfidf.fit_transform(counts)
    classifier = LogisticRegression(C=24.0, max_iter=600, random_state=42, solver="lbfgs")
    classifier.fit(matrix, labels)
    artifact = {
        "features": vectorizer.get_feature_names_out().tolist(),
        "idf": tfidf.idf_.tolist(),
        "classes": classifier.classes_.tolist(),
        "coefficients": classifier.coef_.tolist(),
        "intercept": classifier.intercept_.tolist(),
    }
    # Verify the safe inference implementation equals the trained estimator.
    head = LinearHead(artifact, set(labels))
    actual = [head.predict(text)[0] for text in texts]
    reference = classifier.predict(matrix).tolist()
    if actual != reference:
        raise ModelError("Safe runtime inference does not match fitted estimator")
    max_probability_delta = max(
        abs(head.predict(text)[1] - float(probabilities.max()))
        for text, probabilities in zip(texts, classifier.predict_proba(matrix), strict=True)
    )
    if max_probability_delta > 1e-10:
        raise ModelError("Safe runtime probabilities disagree with fitted estimator")
    return artifact, {"samples": len(texts), "features": counts.shape[1],
                      "training_accuracy": sum(a == b for a, b in zip(actual, labels, strict=True)) / len(labels),
                      "safe_runtime_max_probability_delta": max_probability_delta}


def train_model(manifest_path: Path, output_path: Path) -> dict:
    """Fit only actual parsed training documents and serialize safe JSON weights.

    Expected field values are supervision. Layout/family separation is checked
    from manifest metadata; tuning/test document bytes are never opened here.
    """
    from .extraction import LABEL_TO_KEY, candidates, label_text, normalize_value
    from .parsing import parse_document
    import importlib.metadata
    started = time.monotonic()
    manifest_path, output_path = Path(manifest_path), Path(output_path)
    manifest = json.loads(manifest_path.read_text())
    documents = manifest["documents"]
    if not isinstance(documents, list) or len(documents) > 10000:
        raise ModelError("Invalid bounded training manifest")
    groups = {}
    layouts = {}
    for item in documents:
        split = item["split"]
        if split not in {"train", "tune", "test"}:
            raise ModelError("Unknown split")
        for mapping, key in ((groups, "family_id"), (layouts, "layout")):
            group = item[key]
            if group in mapping and mapping[group] != split:
                raise ModelError(f"Cross-split {key} leakage")
            mapping[group] = split
    train = [item for item in documents if item["split"] == "train"]
    if len(train) < 6:
        raise ModelError("At least six real training documents are required")
    texts, kinds, field_texts, field_keys, inputs = [], [], [], [], []
    root = manifest_path.parent.resolve()
    for item in train:
        path = (root / item["path"]).resolve()
        if not path.is_relative_to(root):
            raise ModelError("Training path escapes corpus directory")
        parsed = parse_document(path)
        expected_kind = item["expected_kind"]
        if expected_kind not in ALLOWED_KINDS:
            continue
        texts.append(_document_text(parsed))
        kinds.append(expected_kind)
        expected = item["expected_fields"]
        for candidate in candidates(parsed):
            key = LABEL_TO_KEY.get(label_text(candidate.label))
            if key is None or key not in expected:
                continue
            truth = expected[key]
            if isinstance(truth, dict):
                truth = truth.get("normalized", truth.get("value"))
            if truth is None:
                continue
            try:
                observed, _ = normalize_value(key, candidate.raw)
                normalized_truth, _ = normalize_value(key, str(truth))
            except ValueError:
                continue
            if observed == normalized_truth:
                field_texts.append(candidate.label)
                field_keys.append(key)
        inputs.append({"path": item["path"], "sha256": parsed.sha256, "family_id": item["family_id"],
                       "layout": item["layout"], "kind": expected_kind})
    if set(kinds) != set(ALLOWED_KINDS):
        raise ModelError("Training set must contain all three purchasing classes")
    document_head, document_metrics = _fit(texts, kinds)
    field_head, field_metrics = _fit(field_texts, field_keys)
    training_digest = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
    data = {
        "format": ARTIFACT_VERSION,
        "metadata": {
            "training_split": "train", "training_inputs": inputs,
            "training_inputs_sha256": training_digest,
            "recipe": "character-word-counts/TF-IDF/sublinear-tf/LogisticRegression-C24-seed42",
            "document_feature_policy": "first-line-x8/first-five-lines/first-600-characters-v1",
            "sklearn_version": importlib.metadata.version("scikit-learn"),
            "numpy_version": importlib.metadata.version("numpy"),
            "training_metrics": {"document": document_metrics, "field": field_metrics},
            "evaluation_claim": "Training fit only; held-out accuracy must be measured separately",
        },
        "thresholds": {"document": 0.80, "label": 0.70},
        "document": document_head, "field": field_head,
    }
    raw = json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if len(raw) > MAX_ARTIFACT_BYTES:
        raise ModelError("Trained artifact exceeds bound")
    # Validate every dimension before atomically publishing the model artifact.
    LocalModel(data, hashlib.sha256(raw).hexdigest())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(output_path.name + ".tmp")
    temporary.write_bytes(raw)
    os.replace(temporary, output_path)
    return {"model_version": ARTIFACT_VERSION, "model_sha256": hashlib.sha256(raw).hexdigest(),
            "artifact_bytes": len(raw), "training_documents": len(texts), "training_fields": len(field_texts),
            "training_inputs_sha256": training_digest,
            "metrics": {"document": document_metrics, "field": field_metrics},
            "elapsed_seconds": time.monotonic() - started,
            "final_evaluation": "not_run"}
