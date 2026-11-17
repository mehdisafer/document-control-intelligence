# Qwen queued-job policy identity — source hardening

## Source-level defect

The processing-policy digest originally bound the package version, parser version,
model/config file bytes and resource budgets. It did **not** identify the effective
Qwen prompt. The 1.3 and rejected 1.4 prompt revisions kept the same package
version, so queued `local-llm` documents could potentially be claimed by a worker
running a different prompt without triggering `PROCESSING_POLICY_CHANGED`.

This correction binds the policy for the **local-llm profile only** to the
actual `PROMPT_VERSION`, SHA-256 of the effective `PROMPT`, pinned public
model/runtime SHA-256 constants, and hashes of the executing LLM and extraction
source modules. The stored policy contains only hashes and public version
strings, never raw credentials, model weights, a document or its source text.

The existing worker check compares the queued policy digest before parsing or
inference. A mismatch now fails closed rather than silently reprocessing. A
manual retry requires an explicit reason under the **new** source policy; no
jobs are automatically migrated. This is conservative: comment-only source
edits also invalidate the queue fingerprint.

## Reproduction and evidence boundary

`tests/test_llm_policy_fingerprint.py` contains seven deterministic tests:
actual prompt/identity hashing, prompt changes without a package-version bump,
prompt-version changes, LLM and extraction source changes, isolation of the
baseline/local-linear profiles, and a **real SQLite queued document** that
receives `PROCESSING_POLICY_CHANGED` before parsing or model inference after
a prompt mutation.

The synthetic queued payload is deliberately a test-only PDF header. It
demonstrates early policy fencing, **not extraction accuracy**, vendor document
authenticity or a correctly parsed PDF. No model is downloaded, no inference
request is made and no production host is accessed by this test.

This safeguard checks queued work at claim time. It does **not** establish
transactional hot reload, distributed worker coordination, or behavior of a
job already executing while deployment files change. Such guarantees require
separate authorized runtime qualification and operator acceptance.

The current source Qwen prompt remains **1.3**; rejected 1.4 stays unmerged.
Historical Qwen 1.2 (3/36 correct, 0 eligible), real Qwen 1.3 development
(7/12 correct, 4/12 eligible, below 50% coverage) and independent supplier/
production gates remain **unchanged and OPEN**. Public source `v0.1.0rc2`
remains immutable; this is later development source.
