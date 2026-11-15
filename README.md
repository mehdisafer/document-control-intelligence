# Document Control Intelligence

**Evidence-linked purchasing-document control, with explicit human review.**

This Linux reference processes synthetic purchase orders, delivery notes and invoices. It preserves original PDF bytes, extracts bounded evidence, checks arithmetic and cross-document consistency, and binds correction, acceptance and publication to current document versions. A model proposal cannot directly authorize publication.

## Delivery status — 15 November 2026

**The local reference has passed its complete hosted qualification**, not only the initial smoke suite. Current qualified runtime revision:

`c451deba5f790a0b0207b6f3dd1931f597e04cc7`

| Gate | Executed observation |
|---|---|
| Full Python suite | 122 tests, including real parsing/OCR and concurrent SQLite startup regressions |
| JavaScript state suite | 23 state/regression tests; separate from browser rendering |
| Actual browser workflow | Synthetic PDFs uploaded through the UI; distinct roles, acceptance, publication and downloaded export verified |
| Rendered desktop/mobile | Real captures, 390 px mobile viewport, no observed document-level overflow or unexpected JavaScript errors |
| Reference image | Built and ran document processing, review/export and restoration inside the actual image |
| Compose / Terraform | Both Compose profiles validated; Terraform formatting/provider-schema validation executed without cloud apply |
| Security/dependencies | Lint, schema drift, known-secret/history checks, dependency and component-licence controls executed |

[Current acceptance](docs/ACCEPTANCE.md) · [Full CircleCI qualification](https://app.circleci.com/workflow/872295c2-9e38-4d00-90d5-1c7b9e4e1807) · [Versioned evidence](evidence/)

The project remains a **reference candidate (`0.1.0rc1`)**. The local-linear automatic seven-case delivery criterion is not met without an attributed human repair, and the larger Qwen profile has not met its accuracy gate. A successful controlled workflow does not erase those negative model results or establish production-target acceptance.

## Reproduce the deterministic reference

Use Linux, Python 3.12, uv 0.13.6, Tesseract with English data and libseccomp2. Native parser and OCR isolation prerequisites are mandatory, not silently bypassed.

```bash
uv sync --frozen --group audit
uv run --frozen --group audit ruff check src tests scripts
uv run --frozen python scripts/export_schemas.py --check
uv run --frozen python -m unittest discover -s tests -v
node --test tests/test_ui_state.mjs
uv run --frozen dci demo --output outputs/demo-baseline
uv run --frozen python scripts/verify_demo.py outputs/demo-baseline/result.json
```

Use a fresh output directory. The demo creates synthetic identities and runtime state; keep its `runtime/` credentials and databases private. Do not publish them as evidence.

The actual image can be built and exercised without external inference:

```bash
docker build --tag dci:local .
docker run --rm dci:local --help
```

The full executable image, read-only filesystem, bounded temporary storage, disabled network, export and restore exercise are specified in `.github/workflows/ci.yml`. Operational guidance and exact optional model commands remain in [documentation](docs/).

## Business controls

Original PDF blobs are immutable and content-addressed. Page offsets and citations remain linked to original evidence; human corrections retain their reason and actor. Arithmetic checks do not invent missing invoice data. Reconciliation evaluates current document versions and records abstention or review where evidence is insufficient.

Acceptance is explicit and revision-bound. An actor who corrected a current document cannot approve that correction. A new version invalidates earlier acceptance; publication binds the exact current fingerprint. Invoice identity prevents duplicate publication across cases. Exported dossiers preserve current evidence, audit and original-byte digests, with explicit consumer upsert semantics rather than payment instructions.

Workers use leases, fencing tokens, bounded retries and cancellation. A late worker result cannot overwrite a newer attempt. Backups and restoration preserve state, review and retry budgets. SQLite is a single-host WAL design, not a distributed ledger and not suitable for NFS/SMB database files.

## Models and negative results

The deterministic parser/rules reference and local model profiles are separate qualifications. The local-linear profile uses a versioned 72/36/36 synthetic train/development/holdout corpus. Its recorded holdout classification is 34/36, compared with 20/36 for the deterministic classification baseline; the eligible-field evidence and abstention results have their own denominators.

The automatic local-linear demonstration exported **six**, not the required seven, dossiers. An attributed human correction enabled seven in a separate repaired run. That repaired result is not automatic-model acceptance. The recorded Qwen profile processed 36 requests but classified only three correctly and produced no eligible dossier. It is not a quality-approved fallback.

The retained evidence and [acceptance record](docs/ACCEPTANCE.md) preserve these limits and their exact source versions. Synthetic benchmark results are not a claim about arbitrary supplier PDFs, arbitrary languages or real purchasing decisions.

## CI and corrections

`.circleci/config.yml` remains the fast Smarter Testing profile; the complete `.github/workflows/ci.yml` runs as a separate full qualification. A fast green badge does not cover every parser, browser or deployment gate.

The complete run exposed and corrected bounded SQLite initialization contention. Ten new tests cover simultaneous threads, independent processes, lock deadlines, schema rollback and failure handling. The browser harness now verifies mutations through authenticated readback rather than relying on an evictable Chromium response body. Locator-based polling preserves the application's restrictive Content Security Policy. No application security policy was relaxed for the test.

Historical failed attempts remain in CI and evidence. The new acceptance record identifies the corrected source and does not retrospectively mark older failures as successful.

## Licence, publication and remaining acceptance

Original project code is under [Apache-2.0](LICENSE); [NOTICE](NOTICE) preserves relevant attribution and limitations. Third-party components retain their own terms. No client documents or client infrastructure were used.

The reference's application, OCR, browser, container and Terraform-schema gates are now executed. Remaining acceptance concerns are model-profile quality, the automatic local-linear target, a named production deployment and its operator acceptance, and maintainer-controlled visibility/protections. No stable production `v1.0.0` tag or unqualified full-project acceptance is asserted.
