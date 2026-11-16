# Document Control Intelligence 0.1.0rc2

**Source prerelease — Apache License 2.0**

This second release candidate packages the already public purchasing-document
control reference with the subsequently merged CircleCI/SQLite reliability
improvements and a visibly rendered, evidence-linked original-page preview.
It is a **synthetic Linux reference**, not a certified procurement service
or a production-host deployment.

## Packaging and upgrade identity

The `0.1.0rc2` source aligns `pyproject.toml`, the editable package in
`uv.lock`, the application version, API and `/healthz` metadata, Docker
Compose image tags and the local Terraform image-ID example. A dedicated
version-coherence test protects against future mismatches.

The persisted processing-policy identity includes the application version.
When upgrading a retained reference installation, back up first, review
queued jobs and handle any old-policy work explicitly; do not silently
replay queued documents or transfer accepted decisions between revisions.
No production host migration has been performed as part of this release.

## What changed since `v0.1.0rc1`

- **Readable source-page preview:** a verified original PDF is rasterized
  by a separate, resource-bounded, network-denied PDFium subprocess and
  returned as an authenticated PNG. Page selection remains tied to cited
  evidence, and the original PDF can still be downloaded byte-for-byte.
  The browser does not depend on executing embedded PDF functionality.
- **Strict browser security:** Playwright checks use CSP-compatible locator
  polling. Authenticated write readbacks replace fragile browser response-
  body inspection; session and document selection fence stale results.
- **SQLite startup:** bounded retry of real lock contention during WAL
  initialization, with atomic migration, rollback and negative-path tests.
- **Local-linear evidence selection:** high-confidence predictions from
  unsupported printed labels no longer contaminate a verified critical field.
  The independent known-label/citation verifier, abstention for genuine
  repeated conflicts, and original frozen model are unchanged. A new strict
  nine-scenario [PR #19 demo](https://github.com/mehdisafer/document-control-intelligence/pull/19)
  passed with seven explicit test-role publications/restored exports; a complete
  36-PDF same-generator regression preserved the predeclared quality gate
  and zero false eligibility. Historical six-export evidence remains intact.
- **CI and reproducibility:** a focused CircleCI test suite plus three full
  GitHub Actions jobs for real parser/OCR, API, browser, Docker and Terraform
  schema checks; source-linked reports and authentic screenshots remain
  available for inspection.

## Current integrated source qualification

The [`v0.1.0rc2`-versioned code](https://github.com/mehdisafer/document-control-intelligence/commit/e9e7f0f2f92a183539a36198b4ce34bde20c3307)
has completed its [GitHub Actions main run #43961711842](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43961711842).
All three actual jobs passed: `smoke-and-integration`,
`container-integration`, and `terraform-schema`. The smoke log records
**135 Python tests passing**, **24 JavaScript tests passing**, and **36 real
Chrome browser checks passing**, including visible original-PDF raster
and the audit/export workflow.

The earlier [PR #16](https://github.com/mehdisafer/document-control-intelligence/pull/16)
has also integrated five reviewed Dependabot updates: `pdfplumber 0.11.10`,
`pdfminer-six 20260107`, `pip-audit 2.10.1`, `pip-licenses 5.5.5`,
and pinned UV/Terraform GitHub Actions. Its regenerated `requirements.lock`
is now aligned with `uv.lock`, with three dependency-lock tests.
The later [PR #17](https://github.com/mehdisafer/document-control-intelligence/pull/17)
adds four release identity tests, all passed on the integrated source.

These are time- and source-bound results on synthetic documents, not a new
ML evaluation, independent human approval or a production deployment.

## Earlier original-page qualification

On [source `32fb196b`](https://github.com/mehdisafer/document-control-intelligence/commit/32fb196bcc496b31071d87d02453dd6936b98ccf),
[GitHub Actions run 43774003311](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43774003311)
recorded **128 passing Python tests**, **24 passing JavaScript state tests**
and **36 passing real-browser checks**, including a decoded, nonblank PDF-page
image visible during genuine Chrome desktop/mobile captures.

The [post-merge `main` run 43774277074](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43774277074)
completed the three `smoke-and-integration`, `container-integration` and
`terraform-schema` jobs successfully. These verify the configured tests
on the merged code; they are not an independent human approval or a
production-load qualification. See the
[acceptance ledger](ACCEPTANCE.md) and
[original-page evidence](ORIGINAL_PAGE_PREVIEW.md).

## Known limitations and negative results

- The **original** frozen `local-linear` demonstration produced **six**
  dossiers against a target of **seven**, and the subsequent manual-repair
  exercise obtained seven with a distinct actor. Both historical reports
  remain unchanged. New source-label gating, with the **same frozen model**,
  subsequently produced **seven eligible dossiers and seven explicit
  test-role publications/restored exports** on a new CI run. The matched
  source regression still must be distinguished from general supplier
  validation or independent human approval.
- The experimental local Qwen profile completed 36 requests but classified
  **3/36** documents correctly and made **0/36** eligible. It is not an
  approved fallback or production model.
- The holdout shares conventions of the synthetic generator. Results do not
  establish arbitrary supplier-document accuracy, forgery detection, full
  accessibility or organizational security.
- No authorized production target, production backup/restore exercise or
  public business API is delivered by this source release.
- Branch protection and an updated GitHub release tag are maintainer-owned
  repository administration operations. The
  [acceptance issue #1](https://github.com/mehdisafer/document-control-intelligence/issues/1)
  remains open for those and the model/operating decisions.

## Reproduce

Use Linux with Python 3.12, `uv==0.13.6`, Tesseract English trained data
and `libseccomp2`.

```bash
uv sync --frozen --group audit
uv run --frozen --group audit ruff check src tests scripts
uv run --frozen python -m unittest discover -s tests -v
node --test tests/test_ui_state.mjs
uv run --frozen dci demo --output outputs/demo-baseline
uv run --frozen python scripts/verify_demo.py outputs/demo-baseline/result.json
```

Use a new output directory for every run. Demo artifacts are synthetic;
keep all credentials and runtime databases private. See
[deployment instructions](DEPLOYMENT.md),
[architecture](ARCHITECTURE.md) and
[operational limitations](BACKLOG.md).

## Release metadata and provenance

Use **new tag** `v0.1.0rc2`, mark **Pre-release**, and target the
**final reviewed `main` SHA** after the current documentation PR is
merged and checked. Verify the actual tag commit before publishing.
The original `v0.1.0rc1` tag stays fixed at
[`5c1f3e4`](https://github.com/mehdisafer/document-control-intelligence/commit/5c1f3e43f50c6d4056baabcafd5c39c40609f39b).
Do not claim this new release is already published.

Project source is [Apache-2.0](../LICENSE), with [NOTICE](../NOTICE).
Third-party libraries, runtimes and model artifacts retain their own
licences and notices. Neither this prerelease nor its tests authorize
deployment of a public processing service.
