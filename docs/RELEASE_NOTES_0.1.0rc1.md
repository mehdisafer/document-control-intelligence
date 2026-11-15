# Document Control Intelligence 0.1.0rc1

A source prerelease for purchasing document control: receive PDFs, extract
source-supported fields locally, reconcile purchase orders, deliveries and
invoices, and preserve explicit human decisions in an auditable control dossier.

This is an executable **synthetic purchasing reference** with disclosed
qualification limits. It is not a production-readiness or general supplier
accuracy claim.

## What the candidate provides

- Authenticated PDF ingestion with immutable originals, stable document keys,
  corrected versions and duplicate handling.
- Native text extraction and real Tesseract OCR in bounded Linux parser
  processes, with persistent jobs, retries and recovery checkpoints.
- Page, exact quotation, text offsets and PDF coordinates for supported fields,
  alongside raw values, normalization steps and explicit abstentions.
- Deterministic financial controls and cumulative three-way matching, including
  supported partial-delivery and partial-invoice cases.
- Attributed field and document-type corrections, revision-bound acceptance by
  a separate approver where required, and idempotent publication with JSON/ZIP
  exports containing originals and audit history.
- A browser review interface, snapshot/restore operations, and reference
  Compose/Terraform configurations for a single-host deployment.

The latest application fixes fence stale UI responses, bind review dialogs to
the document/case revision originally selected, and apply the ZIP's **50 MiB
uncompressed-member budget** to dossier JSON, original PDFs and manifest JSON
together. See the [application source at `8839be77`](https://github.com/mehdisafer/document-control-intelligence/tree/8839be77ad24492702bcb2f53c4e74fffd7a78dd/src/dci).

## Executed qualification and its scope

On source commit [`8839be77ad24492702bcb2f53c4e74fffd7a78dd`](https://github.com/mehdisafer/document-control-intelligence/commit/8839be77ad24492702bcb2f53c4e74fffd7a78dd):

- **112 Python tests passed**, with no skips.
- **23 JavaScript state/unit tests passed**, with no skips. Their DOM and fetch
  implementations are mocked; these tests do not validate browser rendering.
- Lint, schema consistency, locked dependencies and known-secret/history checks
  completed successfully. The point-in-time Python dependency audit reported
  zero known vulnerabilities among 32 runtime packages.

The [qualification report](https://github.com/mehdisafer/document-control-intelligence/blob/3bf98d820e937706fb627a52ec8338a406bb0a6a/evidence/publication/run-8839be77/report.json)
and [original logs](https://github.com/mehdisafer/document-control-intelligence/tree/3bf98d820e937706fb627a52ec8338a406bb0a6a/evidence/publication/run-8839be77)
record the commands, source identities and outcomes. These checks are not a
security certification or a qualification of native container dependencies.

Earlier execution evidence remains attributed to
[`3ff93109f3ea0d9c5f4bdfd598dd35bbd4513439`](https://github.com/mehdisafer/document-control-intelligence/commit/3ff93109f3ea0d9c5f4bdfd598dd35bbd4513439):
107 Python tests, baseline/local-model workflow and restore exercises, and a
separate **36-check, 30-request HTTP qualification** using a loopback Uvicorn
server and a distinct worker process. That HTTP run covered one sequential
synthetic case, role denials, exact source/original bytes, ZIP export,
idempotency and request/audit/job correlation. It did not measure browser
interaction or concurrent HTTP capacity. The [HTTP report](https://github.com/mehdisafer/document-control-intelligence/blob/3bf98d820e937706fb627a52ec8338a406bb0a6a/evidence/qualification/http/run-3ff93109/report.json)
and [qualification record](https://github.com/mehdisafer/document-control-intelligence/tree/3bf98d820e937706fb627a52ec8338a406bb0a6a/evidence/qualification)
retain those original identities; they have not been relabeled as runs of the
later source.

## Local models: measured results and limits

The profiles are a deterministic baseline, a genuinely trained statistical
classifier with safe JSON weights, and a separately routed local Qwen/llama.cpp
profile. The trained classifier is **not an LLM**. Processing has no cloud-model
fallback.

The final synthetic set contains 36 PDFs, following 72 training and 36 tuning
PDFs. Document families and layouts are disjoint across splits, while all splits
share the same generator.

| Final metric | Baseline | Trained local classifier | Local Qwen |
|---|---:|---:|---:|
| Correct classification | 20/36 | 34/36 | 3/36 |
| Eligible for explicit human acceptance | 16/36 | 30/36 | 0/36 |
| Critical correctness among eligible documents | 16/16 | 30/30 | Not defined: no eligible documents |

The statistical profile meets the declared synthetic quality/coverage gate.
These denominators do not establish generalization to real supplier documents.
The bounded Qwen replay completed all 36 model requests but failed its quality
gate; the generative profile remains experimental. Its earlier failed runs are
also retained. See the [evaluation report](https://github.com/mehdisafer/document-control-intelligence/blob/3bf98d820e937706fb627a52ec8338a406bb0a6a/docs/EVALUATION.md)
and [original model evidence](https://github.com/mehdisafer/document-control-intelligence/tree/3bf98d820e937706fb627a52ec8338a406bb0a6a/evidence/evaluation).

The unchanged local-linear demonstration exports **six** dossiers, while the
baseline exports seven. An injection-footer example causes an additional
subtotal abstention, so the original seven-export assertion remains failed.
A separate, attributed human correction followed by a different approver's
decision produces seven restored exports. This establishes the review/recovery
path; it does not improve the model score or replace the adverse automatic
result. The [separate recovery report](https://github.com/mehdisafer/document-control-intelligence/blob/3bf98d820e937706fb627a52ec8338a406bb0a6a/evidence/qualification/manual-recovery-report.json)
preserves that distinction.

## Remaining qualification boundaries

At the preparation snapshot on **2026-11-15**, the latest hosted application CI
attempt failed before runner allocation and executed no job steps. It supplies
no passing application qualification.

Actual browser interaction/screenshots, container build and execution,
Terraform schema validation, and an intended-host rollout remain unqualified.
The JavaScript unit harness, local HTTP proof and infrastructure definitions do
not substitute for those executions. The [acceptance matrix](https://github.com/mehdisafer/document-control-intelligence/blob/main/docs/ACCEPTANCE.md)
and [open scope issue #1](https://github.com/mehdisafer/document-control-intelligence/issues/1)
track the remaining work.

The first contract covers bounded English/French PDF layouts and explicit
delimited purchasing tables. Credit notes, returns, freight/discounts, foreign
exchange, multiple orders and ambiguous repeated SKUs require an extended
contract. Hidden native-text discrepancies and document authenticity still
require human judgment. The measured workloads do not establish distributed
or production capacity.

## Start and inspect

Use the [README](https://github.com/mehdisafer/document-control-intelligence/blob/main/README.md)
for the locked installation, synthetic demonstration and review workspace.
The Linux parser requires Python 3.12, Tesseract English data and `libseccomp2`.
The [deployment guide](https://github.com/mehdisafer/document-control-intelligence/blob/main/docs/DEPLOYMENT.md)
describes provisioning and the optional local-model profiles. Source publication
does not deploy a business service.

## Licence

Original project code, documentation and synthetic assets use
[Apache-2.0](https://github.com/mehdisafer/document-control-intelligence/blob/3bf98d820e937706fb627a52ec8338a406bb0a6a/LICENSE),
with [project attribution](https://github.com/mehdisafer/document-control-intelligence/blob/3bf98d820e937706fb627a52ec8338a406bb0a6a/NOTICE)
to Mehdi Safer. Third-party dependencies, OCR components and model/runtime
artifacts retain their respective licences and notices, listed in the
[source inventory](https://github.com/mehdisafer/document-control-intelligence/blob/3bf98d820e937706fb627a52ec8338a406bb0a6a/docs/SOURCES.md).
