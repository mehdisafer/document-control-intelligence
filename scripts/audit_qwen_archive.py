"""Offline Qwen historical-trace audit. Never runs inference or rewrites evidence."""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import tarfile
import unicodedata

TRACE = "runs/attempt-03-bounded-cache/model-traces/"
RECORD = "runs/attempt-03-bounded-cache/evaluation/documents/local-llm/"
PARSED = "runs/attempt-03-bounded-cache/evaluation/parsed/"
SNAPSHOT = "source-snapshot/src/dci/extraction.py"
TRACE_NAME = re.compile(r"([0-9a-f]{64})-[0-9]+\.json\Z")


def canonical_label(text: str) -> str:
    chars = unicodedata.normalize("NFKD", text)
    chars = "".join(c for c in chars if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9%]+", " ", chars.lower()).split())


def read_literal(source: str, name: str) -> dict:
    nodes = [n for n in ast.parse(source).body
             if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]
    if len(nodes) != 1:
        raise ValueError("Historical source constant missing or ambiguous: " + name)
    result = ast.literal_eval(nodes[0].value)
    if not isinstance(result, dict) or not result:
        raise ValueError("Historical source constant is not a literal dict")
    return result


def exact_title(parsed: dict, titles: dict) -> str:
    canonical = {canonical_label(alias): kind for kind, aliases in titles.items()
                 for alias in aliases}
    kinds = {canonical[canonical_label(line)] for p in parsed.get("pages", [])
             for line in p.get("text", "").splitlines()
             if canonical_label(line) in canonical}
    return next(iter(kinds)) if len(kinds) == 1 else "unknown"


def load_verified(archive: bytes, index: dict) -> dict[str, bytes]:
    meta = index["archive"]
    if len(archive) != meta["bytes"] or hashlib.sha256(archive).hexdigest() != meta["sha256"]:
        raise ValueError("Original archive digest or size mismatch")
    expect = {row["member"]: row for row in meta["members"]}
    if len(expect) != meta["member_count"] or meta["uncompressed_bytes"] > 32_000_000:
        raise ValueError("Invalid original archive index")
    result = {}
    total = 0
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        for entry in tar.getmembers():
            path = PurePosixPath(entry.name)
            if (entry.name not in expect or entry.name in result or path.is_absolute()
                    or ".." in path.parts or not entry.isfile() or entry.size > 5_000_000):
                raise ValueError("Unexpected or unsafe archive entry")
            handle = tar.extractfile(entry)
            if handle is None:
                raise ValueError("Missing archive payload")
            data = handle.read(5_000_001)
            if (len(data) != entry.size or len(data) != expect[entry.name]["bytes"]
                    or hashlib.sha256(data).hexdigest() != expect[entry.name]["sha256"]):
                raise ValueError("Original member digest or size mismatch")
            result[entry.name] = data
            total += len(data)
    if result.keys() != expect.keys() or total != meta["uncompressed_bytes"]:
        raise ValueError("Original archive membership mismatch")
    return result


def confusion(rows: list[dict], key: str) -> dict:
    result = defaultdict(Counter)
    for row in rows:
        result[row["truth"]][row[key]] += 1
    return {kind: dict(sorted(v.items())) for kind, v in sorted(result.items())}


def audit(members: dict[str, bytes], index: dict, historical: dict, usage: dict) -> dict:
    frozen = members[SNAPSHOT].decode("utf-8")
    titles = read_literal(frozen, "TITLES")
    labels = read_literal(frozen, "LABELS")
    label_to_field = {canonical_label(label): field
                      for field, variants in labels.items() for label in variants}
    scores = [json.loads(members[p]) for p in sorted(members) if p.startswith(RECORD)]
    if len(scores) != 36 or len({r["input_sha256"] for r in scores}) != 36:
        raise ValueError("Missing or duplicate original document scores")
    by_hash = {r["input_sha256"]: r for r in scores}
    events = []
    fields, warnings = Counter(), Counter()
    for path in sorted(p for p in members if p.startswith(TRACE)):
        matched = TRACE_NAME.fullmatch(path.removeprefix(TRACE))
        if matched is None:
            raise ValueError("Unrecognized Qwen trace file")
        digest = matched.group(1)
        score = by_hash.get(digest)
        if score is None:
            raise ValueError("Trace does not match original document score")
        raw = json.loads(members[path])
        if raw["telemetry"]["document_sha256"] != digest:
            raise ValueError("Model telemetry identity mismatch")
        parsed = json.loads(members[PARSED + digest + ".json"])
        request = json.loads(raw["request"]["messages"][-1]["content"])
        if parsed["sha256"] != digest or request["document_sha256"] != digest:
            raise ValueError("Parsed/source proposal document identity mismatch")
        proposals = raw["proposal"]
        candidate_by_id = {v["id"]: v for v in request["candidates"]}
        for field, candidate_id in proposals["fields"].items():
            if candidate_id is None:
                fields["null_proposals"] += 1
                continue
            fields["selected_proposals"] += 1
            candidate = candidate_by_id.get(candidate_id)
            if candidate is None:
                raise ValueError("Unrecognized Qwen source candidate ID")
            observed = label_to_field.get(canonical_label(candidate["label"]))
            if observed is None:
                fields["unsupported_label_proposals"] += 1
            elif observed != field:
                fields["misassigned_recognized_label_proposals"] += 1
            else:
                fields["supported_label_proposals"] += 1
        for warning in score["extraction"].get("warnings", []):
            warnings[warning.split(":", 1)[0].split(";", 1)[0]] += 1
        final_kind = score["extraction"]["kind"]
        if final_kind != score["predicted_kind"]:
            raise ValueError("Stored extraction and scored classification mismatch")
        events.append({
            "hash": digest, "truth": score["expected_kind"],
            "proposal": proposals["kind"], "verified": final_kind,
            "title": exact_title(parsed, titles),
            "eligible": bool(score["eligible"]), "error": "error" in score,
        })
    if len(events) != 36 or len({e["hash"] for e in events}) != 36:
        raise ValueError("Expected full 36-trace one-to-one audit")
    proposal_counts = dict(sorted(Counter(r["proposal"] for r in events).items()))
    if proposal_counts != dict(sorted(usage["proposal_kind_distribution"].items())):
        raise ValueError("Original model proposal distribution mismatch")
    correct = sum(r["verified"] == r["truth"] for r in events)
    accepted = sum(r["eligible"] for r in events)
    errors = sum(r["error"] for r in events)
    profile = historical["profiles"]["local-llm"]
    if (correct != 3 or accepted or errors or profile["documents"] != 36
            or profile["classification_accuracy"] != 0.083333
            or profile["eligible_documents"] != 0
            or usage["successful_response_count"] != 36):
        raise ValueError("Original Qwen result differs from retained evidence")
    title_cases = [r for r in events if r["title"] != "unknown"]
    return {
        "schema_version": "1.0",
        "kind": "historical_qwen_trace_analysis_not_new_inference",
        "source": {"original_git_commit": historical["source"]["git_commit"],
                   "archive_sha256": index["archive"]["sha256"],
                   "indexed_original_members_sha256_checked": len(members)},
        "observed": {"documents": len(events), "raw_responses": len(events),
                     "new_model_inferences": 0, "historic_correct": correct,
                     "historic_eligible": accepted, "inference_failures": errors},
        "class_diagnostic": {
            "proposed_kinds": proposal_counts,
            "proposed_confusion": confusion(events, "proposal"),
            "verified_confusion": confusion(events, "verified"),
            "proposal_correct": sum(r["proposal"] == r["truth"] for r in events),
            "recognized_unambiguous_titles": len(title_cases),
            "recognized_titles_matching_truth": sum(r["title"] == r["truth"] for r in title_cases),
            "proposed_unknown_despite_recognized_title":
                sum(r["proposal"] == "unknown" for r in title_cases),
            "non_unknown_proposal_downgraded_to_unknown":
                sum(r["proposal"] != "unknown" and r["verified"] == "unknown" for r in events),
        },
        "field_proposals": dict(sorted(fields.items())),
        "warning_codes": dict(sorted(warnings.items())),
        "limits": [
            "Historical only: does not run the Qwen model or improve recorded model quality.",
            "An exact-title counterfactual would be a different policy, not approved fallback.",
            "3/36 classification and zero eligible remain an unqualified model profile.",
            "No new real supplier holdout, third-party annotations or target host deployment.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--archive", type=Path, default=Path("evidence/evaluation/raw-executions.tar.gz"))
    parser.add_argument("--index", type=Path, default=Path("evidence/evaluation/index.json"))
    parser.add_argument("--summary", type=Path, default=Path(
        "evidence/evaluation/attempt-03-bounded-cache/summary.json"))
    parser.add_argument("--usage", type=Path, default=Path(
        "evidence/evaluation/attempt-03-bounded-cache/model-usage.json"))
    options = parser.parse_args()
    if options.output.exists():
        raise FileExistsError("Historical audit output already exists; do not overwrite")
    index = json.loads(options.index.read_text(encoding="utf-8"))
    members = load_verified(options.archive.read_bytes(), index)
    historical = json.loads(options.summary.read_text(encoding="utf-8"))
    usage = json.loads(options.usage.read_text(encoding="utf-8"))
    result = audit(members, index, historical, usage)
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                              encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
