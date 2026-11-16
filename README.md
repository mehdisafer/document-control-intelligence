# Document Control Intelligence

**Evidence-linked purchasing-document control, with explicit human review.**

This Linux reference processes synthetic purchase orders, delivery notes and invoices. It preserves original PDF bytes, extracts bounded evidence, checks arithmetic and cross-document consistency, and binds correction, acceptance and publication to current document versions. A model proposal cannot directly authorize publication.

## Delivery status — 16 November 2026

**The isolated reference and visible original-page preview are qualified on the merged source.** Executable preview revision `32fb196bcc496b31071d87d02453dd6936b98ccf` is included in `main` merge `24cad9d17b400fca01ae901d97082ebbd45bc59c`, whose full GitHub Actions workflow also passed. This is not a production-host deployment.

| Gate | Executed observation |
|---|---|
| Full Python suite | **135 passed** on merged `0.1.0rc2` source, including parsing/OCR, PDF raster limits, version/lock checks and SQLite concurrency |
| JavaScript state suite | **24 passed** on merged `0.1.0rc2` source, including stale-page suppression and same-page preview deduplication |
| Actual browser workflow | Synthetic PDFs uploaded through the UI; distinct roles, acceptance, publication and downloaded export verified |
| Rendered desktop/mobile | **36 real-browser checks passed** on merged `0.1.0rc2` source; real Chrome captures show a readable rasterized original beside its evidence |
| Reference image | Built and ran document processing, review/export and restoration inside the actual image |
| Compose / Terraform | Both Compose profiles validated; Terraform formatting/provider-schema validation executed without cloud apply |
| Security/dependencies | Lint, schema drift, known-secret/history checks, dependency and component-licence controls executed |

[Latest merged-source qualification](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43961711842) · [Original-page visual evidence](docs/ORIGINAL_PAGE_PREVIEW.md) · [Current acceptance](docs/ACCEPTANCE.md) · [Earlier CircleCI qualification](https://app.circleci.com/workflow/872295c2-9e38-4d00-90d5-1c7b9e4e1807) · [Versioned evidence](evidence/)

The current source is **candidate `0.1.0rc2`**, with its package, API and local container versions aligned. The only currently **published** prerelease remains the immutable historical `v0.1.0rc1` tag; `v0.1.0rc2` must be published separately after integration and full CI. The historical 6/7 local-linear demo failure is retained. A subsequent source-label guard in [PR #19](https://github.com/mehdisafer/document-control-intelligence/pull/19) has **actually produced seven eligible, explicitly published and restored dossiers**, with the unchanged model. Its separate 36-PDF synthetic regression replay retains 30/36 eligible, 30/30 critical quality and zero false eligibility. The new source still requires integration into `main`; Qwen has not met its quality gate. A successful controlled workflow does not establish production-target acceptance.

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

The **original** frozen local-linear demonstration exported **six**, not seven,
dossiers. The seventh was previously obtained through a separately audited
human correction; neither result was rewritten. A
[later source-contract correction](https://github.com/mehdisafer/document-control-intelligence/pull/19)
rejects high-confidence proposals from independently unsupported labels (including
the malicious URL footer) **before** critical field aggregation. On
[run 43977956360](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43977956360),
the identical frozen model produced **seven eligible dossiers**, all explicitly
accepted/published by separate test actors and restored identically. Genuine
conflicting recognized labels remain blocked. The frozen 36-PDF synthetic
replay still shows 34/36 classification, 30/36 eligible, 30/30 eligible
critical quality and zero false eligibility. No new supplier-independent
holdout was established. The local Qwen profile still fails its quality gate
(3/36 classifications, 0 eligible) and is not an approved fallback.

The retained evidence and [acceptance record](docs/ACCEPTANCE.md) preserve these limits and their exact source versions. Synthetic benchmark results are not a claim about arbitrary supplier PDFs, arbitrary languages or real purchasing decisions.

## CI and corrections

`.circleci/config.yml` remains the fast Smarter Testing profile; the complete `.github/workflows/ci.yml` runs as a separate full qualification. A fast green badge does not cover every parser, browser or deployment gate.

The complete run exposed and corrected bounded SQLite initialization contention. Ten new tests cover simultaneous threads, independent processes, lock deadlines, schema rollback and failure handling. The browser harness now verifies mutations through authenticated readback rather than relying on an evictable Chromium response body. Locator-based polling preserves the application's restrictive Content Security Policy. No application security policy was relaxed for the test.

Historical failed attempts remain in CI and evidence. The new acceptance record identifies the corrected source and does not retrospectively mark older failures as successful.

## Next source prerelease

The public `v0.1.0rc1` tag is an immutable snapshot from before the
original-page raster and SQLite/CI fixes. These changes are already merged
to `main`, with [original-page proof](docs/ORIGINAL_PAGE_PREVIEW.md) and
[post-merge CI results](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43774277074).
The `0.1.0rc2` runtime/package version is prepared with a locked editable
package, health endpoint, API and Compose alignment test; its GitHub
**source prerelease is not yet published**:
[release notes](docs/RELEASE_NOTES_0.1.0rc2.md).
Do not move the existing tag; the new tag must resolve to the final reviewed
`main` commit. This is a source release, not a hosted business service.

## Licence, publication and remaining acceptance

Original project code is under [Apache-2.0](LICENSE); [NOTICE](NOTICE) preserves relevant attribution and limitations. Third-party components retain their own terms. No client documents or client infrastructure were used.

The reference's application, OCR, browser, container and Terraform-schema gates are now executed. Remaining acceptance concerns are the unqualified generative profile, independent-supplier generalization, a named production deployment and its operator acceptance, and maintainer-controlled release/branch protection. The original 6/7 local-linear failure remains historical; the source-gated 7/7 regression is separately qualified on PR #19. No stable production `v1.0.0` tag or unqualified full-project acceptance is asserted.
