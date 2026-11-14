# Document Control Intelligence

**Purchasing document control with traceable extraction, local inference and explicit human decisions.**

An operator should be able to answer three questions: where did this value come
from, do the order/delivery/invoice agree, and who accepted the current version?
This application connects those questions in one executable workflow.

It receives actual PDFs, extracts native text or runs OCR, links fields to source
spans and coordinates, checks amounts and cumulative quantities, and presents the
original alongside anomalies and evidence. Corrections are attributed and versioned.
Acceptance and publication are separate actions. The control dossier is exported
from persisted application state, with its originals and audit.

**Release candidate `0.1.0rc1`, licensed under [Apache 2.0](LICENSE).** This is an
executable synthetic purchasing reference. The complete
[acceptance scope](https://github.com/mehdisafer/document-control-intelligence/issues/1)
remains open: browser rendering, container execution, Terraform validation and
target deployment have separate unresolved gates. The candidate does not claim
production certification or broad supplier-document accuracy.

## Implemented capabilities

| Capability | Behavior |
|---|---|
| Ingestion | Authenticated PDF API, immutable content, stable keys, corrected versions, duplicate idempotency |
| Processing | Persistent bounded queue, separate workers, isolated Linux parser, native text first, real Tesseract OCR, page checkpoints |
| Extraction | Deterministic comparator; trained CPU document/field classifiers; separately routed local Qwen GGUF |
| Proof | Page, exact text span, quotation, PDF-point box, raw/normalized values, transformations and abstention |
| Business checks | Quantities, prices, taxes, totals, currency, identifiers, duplicate invoices and cumulative three-way matching |
| Review | Original, fields, all supporting quotations, anomalies, human correction, roles and revision-aware acceptance |
| Publication | One result per accepted fingerprint, cross-case invoice guard, supersession and JSON/ZIP export |
| Recovery | Fenced leases, bounded retry, cancellation, OCR checkpoints, consistent snapshot and tested restore |

All demo suppliers, orders and invoices are synthetic. No client documents,
personal workstation, cloud inference or external business systems are used.

## Run the complete demonstration

Use Linux with Python 3.12, Tesseract English trained data and `libseccomp2`.
The parser fails closed without its Linux isolation prerequisites. On Windows,
use the Linux container or an explicitly provisioned WSL2 environment.

```bash
git clone https://github.com/mehdisafer/document-control-intelligence.git
cd document-control-intelligence
python -m pip install 'uv==0.13.6'
uv sync --frozen --group audit
uv run dci demo --output outputs/demo
uv run python scripts/verify_demo.py outputs/demo/result.json
```

The demo generates and parses real native/scanned PDFs, calls the real API and
worker, records authenticated decisions, exports seven dossiers, snapshots the
state, restores it elsewhere and compares the recovered exports. It refuses to
overwrite an existing evidence directory.

The implementation, review and source history are recorded in
[PR #2](https://github.com/mehdisafer/document-control-intelligence/pull/2).
GitHub Actions was triggered, but the observed jobs failed before any runner or
step started. Local execution evidence and the unresolved CI checks are separated
in the [acceptance matrix](docs/ACCEPTANCE.md).

| Demo case | Expected outcome |
|---|---|
| Coherent order, delivery and invoice | Eligible, explicitly accepted, then published |
| Invoice exceeds ordered/delivered quantity | Contradiction; publication blocked |
| Missing invoice total | Abstention and review |
| Inconsistent printed total | Audited human correction, another actor accepts |
| Printed instruction to send data away | Untrusted text; no tool, provider or policy change |
| Partial delivery and invoice | Legitimate partial reconciliation |
| Corrected invoice version | New version; old result retained; acceptance invalidated |
| Scanned invoice | Actual OCR and source-linked fields |
| Exact resubmission | Existing document returned; no second publication |

## Open the review workspace

```bash
uv run dci serve --config outputs/demo/runtime/config.json
```

Open **http://127.0.0.1:8000**. Use an actor token from the private
`outputs/demo/runtime/credentials.json` file. Tokens are not printed by setup.
Switch identities to exercise operator, approver and publisher permissions.
For new uploads, run a worker in another terminal:

```bash
uv run dci worker --config outputs/demo/runtime/config.json
```

The UI shows current versions, originals, fields, all supporting quotations,
anomalies and decision history. Viewing a document does not approve it.
An operator can also review a document's type while retaining the original model
proposal. They cannot self-approve their own field or type correction.

## Execute the trained local model

```bash
uv run dci corpus --output outputs/corpus --seed 42 --per-split 12
uv run dci train --manifest outputs/corpus/manifest.json --output .data/models/local-linear.json
uv run dci demo --profile local-linear --model-path .data/models/local-linear.json --output outputs/demo-linear
```

This is genuine scikit-learn training and local numeric inference using safe JSON
weights. It is **not an LLM**. The Qwen3-0.6B/llama.cpp profile also executes locally
and is evaluated separately, without a cloud fallback. See the
[deployment and model provisioning guide](docs/DEPLOYMENT.md).

On the frozen model, the demo exports **six** dossiers. Its injection-footer
example causes an additional subtotal abstention and remains in review; the
baseline exports seven. The strict seven-export demo verifier therefore fails
for this local-linear execution, and that original result is retained. No value
is guessed or model confidence relaxed to force the scenario through.

A separate recovery exercise corrects that subtotal through the attributed
review API, rejects self-approval, obtains a different approver's decision and
publishes the seventh dossier. All seven exports then survive another restore.
This proves the correction workflow; it does not change the original model score
or turn the failed automatic demo assertion into a pass.

### Observed held-out results

The frozen synthetic corpus contains **72 training, 36 tuning and 36 final PDFs**.
Layout and document-family IDs are disjoint by split. The final set includes
multipage documents, French/English layouts, degraded scans, missing/conflicting
values and printed malicious instructions.

| Final metric, 36 documents | Baseline | Trained local classifier |
|---|---:|---:|
| Correct classification | 20/36 (55.56%) | 34/36 (94.44%) |
| Eligible for explicit acceptance | 16/36 (44.44%) | 30/36 (83.33%) |
| Critical quality among eligible | 16/16 (100%) | 30/30 (100%) |
| False eligible documents | 0 | 0 |
| Valid emitted citations | 2,448/2,448 | 2,448/2,448 |
| Present normalized fields correct | 1,349/1,364 (98.90%) | 1,349/1,364 (98.90%) |

The local classifier meets the declared synthetic quality/coverage gate. The
baseline misses its 50% coverage target. Every eligible result still requires a
human decision. These small synthetic denominators do not establish real-world
supplier accuracy. Qwen's bounded replay completed 36/36 actual requests at a
1.51 GiB peak RSS, but only 3/36 classifications were correct and all documents
remained in review. Earlier runtime failures and the bounded replay are retained in
the [evaluation report](docs/EVALUATION.md).

## Architecture and operation

FastAPI, SQLite WAL, immutable objects and a transactional leased queue form an
explicit single-host reference. Parsing/OCR, classification/extraction, citation
checks, financial rules, reconciliation and human decisions are separate stages.
This is not a distributed database or a scalability claim.

Read the [architecture](docs/ARCHITECTURE.md), [contracts](contracts/),
[deployment guide](docs/DEPLOYMENT.md), [incident/restore runbooks](docs/OPERATIONS.md),
[acceptance matrix](docs/ACCEPTANCE.md) and [official-source inventory](docs/SOURCES.md).
Compose and Terraform describe local Docker resources. They do not provision a
cloud account, change billing or publish a business service.

## Verify and reproduce

```bash
uv run --group audit ruff check src tests scripts
uv run python -m unittest discover -s tests -v
node --test tests/test_ui_state.mjs
uv run python scripts/check_secrets.py --history
uv run --group audit pip-audit --disable-pip --no-deps -r requirements.lock
uv run python scripts/check_licenses.py
uv run python scripts/benchmark.py --cases 3 --workers 1 2 --batch-size 2 --output outputs/load.json
```

Tests cover real parsing/OCR/API/storage integration, negative inputs, financial
edge cases, stale versions, duplicate submission/publication, lease recovery and
restoration. Browser and container qualification are separate. A mock, liveness
response or skipped test is never treated as an integration result. Original
reports, commands, source hashes and publication links are indexed in [evidence](evidence/).

The current application source, `8839be77ad24492702bcb2f53c4e74fffd7a78dd`, passed
**112 Python tests without skips** and **23 JavaScript state/unit tests without
skips**. The latter run the real UI script with a mocked DOM and deferred fetches;
they do not validate browser rendering. They were executed with Node 24.22.1,
which is needed only for JavaScript tests. The new checks cover stale document,
PDF, audit and actor responses, fixed mutation targets, and the complete ZIP
member byte budget. See the [public-source qualification](evidence/publication/).

On source commit `3ff93109f3ea0d9c5f4bdfd598dd35bbd4513439`, **107 tests passed
without skips**. A separate loopback HTTP execution passed **36 checks across
30 requests**, with a real Uvicorn server and a separate local-model worker.
It verified role denials, exact source spans, original PDF/ZIP bytes, idempotent
publication and request-to-audit-to-job correlation. The final baseline and
local-linear regression also reproduced all **72 semantic document outputs**,
excluding timing measurements. See the [qualification record](evidence/qualification/).

### Replay the original HTTP qualification

The retained HTTP harness checks the exact original source, including
`pyproject.toml`. The later Apache-2.0 packaging metadata intentionally changes
that file. Use a detached checkout of the executed source and supply the retained
harness/model from this checkout. Run from the repository root with new paths:

```bash
mkdir -p outputs
git worktree add --detach outputs/http-source-3ff93109 3ff93109f3ea0d9c5f4bdfd598dd35bbd4513439
env -u UV_PROJECT_ENVIRONMENT -u PYTHONPATH \
  uv run --frozen --project outputs/http-source-3ff93109 --python 3.12.14 python \
  "$PWD/evidence/qualification/http/qualify_http.py" \
  --repo "$PWD/outputs/http-source-3ff93109" \
  --model "$PWD/evidence/evaluation/local-linear-model.json" \
  --output "$PWD/outputs/http-qualification-new"
```

This requires a normal Git clone containing the executed commit. The source
guard and original reports remain unchanged; the replay records its own result.

| Qualification profile | Command | Scope |
|---|---|---|
| Smoke | `dci demo --output outputs/demo` | Nine real PDF/API/review scenarios, export and restore |
| Integration | `python -m unittest discover -s tests -v` | Contracts, parser/OCR, rules, transactions and negative/recovery paths |
| HTTP | [Frozen-source replay](#replay-the-original-http-qualification) | Loopback API, separate worker, roles, evidence, publication and trace joins |
| Load | `python scripts/benchmark.py --cases 3 --workers 1 2 --batch-size 2 --output outputs/load.json` | Parameterized actual PDFs and worker counts with business-outcome comparison |

The optional LLM evaluation is an explicit bounded command, not a costly job
triggered by every documentation edit.

## Current boundaries

The first contract handles PDF, English/French labels and explicit delimited
purchasing tables; arbitrary invoice-layout extraction is not claimed. Positive
purchase quantities in EUR/USD/GBP/CHF are supported. Credit notes, returns,
discount/freight, currency conversion, multiple orders and ambiguous repeated SKU
rows require an extended contract. Pure-native hidden text and document
authenticity remain human-review limitations.

Model quality, browser execution, container execution, Terraform validation and a
real target deployment have separate acceptance statuses. See the
[limitations and backlog](docs/BACKLOG.md). Public source publication was
authorized on 2026-11-14; its administrative status and the remaining service
qualification gates are recorded separately in the [release notes](docs/RELEASE.md).

## Licence

Copyright 2026 Mehdi Safer. Original project code, documentation and synthetic
assets are licensed under the [Apache License, Version 2.0](LICENSE).
See [NOTICE](NOTICE) for project attribution. Third-party dependencies, OCR/runtime
components and model weights retain their own licences and notices, documented
in the [upstream inventory](docs/SOURCES.md).
