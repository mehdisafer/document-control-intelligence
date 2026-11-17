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

## Published tag and current exact-source qualification — 16–17 November 2026

The [published `v0.1.0rc2` GitHub prerelease](https://github.com/mehdisafer/document-control-intelligence/releases/tag/v0.1.0rc2) is marked **Pre-release**. The immutable Git tag points directly to [`db42dd7c7668d70deb8cf5ea6512abcd94a36510`](https://github.com/mehdisafer/document-control-intelligence/commit/db42dd7c7668d70deb8cf5ea6512abcd94a36510), where [PR #19](https://github.com/mehdisafer/document-control-intelligence/pull/19) was merged. The historical `v0.1.0rc1` points to `5c1f3e43f50c6d4056baabcafd5c39c40609f39b` and has not moved.

[GitHub Actions push run #43979529670](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43979529670) completed **success** on the **exact tagged source** across all three jobs: `smoke-and-integration`, `container-integration`, and `terraform-schema`. CircleCI's `ci/circleci: build-and-test` status is separately successful on the same SHA.

The original [GitHub Actions artifact #14281402594](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43979529670/artifacts/14281402594) was downloaded and its ZIP integrity checked. It contains:

- **139 passing Python unit/integration tests**, including four new source-label contract regressions; no failed tests.
- **24 passing Node JavaScript state tests**.
- **36/36 passing real Chrome checks**, including nonblank original-page raster, role separation, correction and export.
- An executed **nine-scenario local-linear demonstration** with **7/7 eligible, explicitly test-role published and restored-identical dossiers**; the verifier's requirements were not relaxed.
- An original-generator **36-PDF frozen-model replay**: **34/36 correct document classifications**, **30/36 eligible**, **30/30 critical quality among eligible**, **0 false eligible**, 100% source-citation/semantic validity on this synthetic split. It is **not** a new independent supplier holdout, changed model or Qwen evaluation.
- Actual isolated Docker integration and Terraform schema checks. The dependency advisory result is bounded to its recorded package inventory and time.

The earlier [PR #17 main-source run #43961711842](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43961711842) passed **135 Python, 24 JavaScript and 36 browser** checks before PR #19. The updated 139-test total is bound to the later tagged source; the earlier test count remains historically correct. PRs [#16](https://github.com/mehdisafer/document-control-intelligence/pull/16) and [#17](https://github.com/mehdisafer/document-control-intelligence/pull/17) previously reconciled dependency locks and package/API/container release identity, respectively.

**Public release-body readback (17 November 2026):** the editable GitHub release body was updated at **00:24:23 UTC** and now identifies the **correct tagged source `db42dd7c`**, **139 Python**, **24 JavaScript**, **36 Chrome checks**, the corrected **7/7** local-linear demo and the frozen 36-PDF synthetic replay, with explicit Qwen and independent-supplier limitations. The old `599bff76` source and 135-test count are no longer in the public body. The only identified content presentation defect is **four nested Markdown reference links** of the form `[[label](URL)](URL)`. The maintainer should normalize those links in the **existing release description only**; no new release or tag retarget is needed. The immutable tagged source remains `db42dd7c`.

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
- The new prerelease tag is **already published and source-verified**; branch protection remains an unfulfilled owner-side repository setting. The
  [acceptance issue #1](https://github.com/mehdisafer/document-control-intelligence/issues/1)
  stays open for that setting, independent supplier generalization, failed Qwen quality and operating-target decisions.

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

The public [`v0.1.0rc2` prerelease](https://github.com/mehdisafer/document-control-intelligence/releases/tag/v0.1.0rc2) was published on 16 November 2026 at 23:44:38 UTC. Its tag resolves to **`db42dd7c7668d70deb8cf5ea6512abcd94a36510`**, with actual completed hosted qualification. The earlier [`v0.1.0rc1` tag](https://github.com/mehdisafer/document-control-intelligence/releases/tag/v0.1.0rc1) remains fixed at **`5c1f3e43f50c6d4056baabcafd5c39c40609f39b`**. Later documentation changes on `main` do not mutate either released snapshot. The editable public release body already reflects the correct source and measured results; only its four nested Markdown link wrappers remain to be corrected. Never move a released tag to repair description text.

Project source is [Apache-2.0](../LICENSE), with [NOTICE](../NOTICE).
Third-party libraries, runtimes and model artifacts retain their own
licences and notices. Neither this prerelease nor its tests authorize
deployment of a public processing service.
