# Document Control Intelligence

**Evidence-linked purchasing-document control, with explicit human review.**

This Linux reference processes synthetic purchase orders, delivery notes and invoices. It preserves original PDF bytes, extracts bounded evidence, checks arithmetic and cross-document consistency, and binds correction, acceptance and publication to current document versions. A model proposal cannot directly authorize publication.

## Published source and acceptance — 17 November 2026

The public [`v0.1.0rc2` source prerelease](https://github.com/mehdisafer/document-control-intelligence/releases/tag/v0.1.0rc2) is **published** and its immutable tag points to [`db42dd7c7668d70deb8cf5ea6512abcd94a36510`](https://github.com/mehdisafer/document-control-intelligence/commit/db42dd7c7668d70deb8cf5ea6512abcd94a36510). The previous `v0.1.0rc1` tag remains at `5c1f3e43`. Publishing source is not deploying a business service.

| Gate | Executed observation at the tagged source |
|---|---|
| Full Python test suite | **139 passed**, including PDF/OCR, 4 source-label regressions, release identity, dependency locks and SQLite recovery |
| JavaScript state tests | **24 passed** |
| Actual rendered Chrome reference | **36/36 checks passed**, including original-page raster visibility, role isolation, acceptance, publication and exports |
| Local-linear scripted nine-scenario demo | **7/7 eligible, explicitly test-role published and restored exports**, using the **unchanged frozen model** |
| Frozen-model synthetic 36-PDF replay | **34/36 correct classes**, **30/36 eligible**, **30/30 eligible critical quality**, **0 false eligible**; same generator and seed, not independent supplier data |
| Docker, Compose and Terraform | Real reference container and Terraform schema jobs **passed**; no target-host deployment |
| Security and dependency checks | Source/history scan and current installed dependency advisory checks executed; point-in-time scope only |

[Exact tagged-source GitHub Actions run](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43979529670) · [Original job artifact](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43979529670/artifacts/14281402594) · [Original-page visual evidence](docs/ORIGINAL_PAGE_PREVIEW.md) · [Current acceptance](docs/ACCEPTANCE.md) · [Evaluation limits](docs/EVALUATION.md)

**Historical and external limits remain visible.** The earlier frozen local-linear run achieved only 6/7 automatic exports and is not retroactively relabelled a pass. The new source-label guard was tested and integrated through [PR #19](https://github.com/mehdisafer/document-control-intelligence/pull/19); it does not retrain the classifier. The separate Qwen profile still fails its 3/36 correct, 0/36 eligible quality result. The successful synthetic profile neither proves arbitrary supplier-document accuracy nor establishes production readiness.

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

## Qwen historical failure diagnosis (post-rc2)

An [offline 36-response forensic audit](docs/QWEN_TRACE_FORENSICS.md) now checks all **406 original evidence members** and confirms **3/36 correct classification, 0/36 eligible**, **30/36 raw unknown-class proposals** and **35/272 source-label misassignments**. The [executed PR #23 run](https://github.com/mehdisafer/document-control-intelligence/actions/runs/44161099199) and [original aggregate artifact](https://github.com/mehdisafer/document-control-intelligence/actions/runs/44161099199/artifacts/14363287699) retain this source-specific diagnosis. It performed no new Qwen inference and **does not close the generative-model quality gate**.

## Additional independent-renderer safety probe (post-rc2)

An [independently implemented Node.js PDF generator](docs/INDEPENDENT_LAYOUT_QUALIFICATION.md) creates twelve fictional purchasing PDFs outside the original ReportLab generator: six known-label controls and six unsupported alias/geometric-table cases. The parser/model/verifier regression measures coverage, citations and abstentions without silently accepting unsupported layouts. **This is not an independently sourced supplier benchmark, a Qwen quality improvement, or a deployment.** The published `v0.1.0rc2` source tag is unchanged; subsequent CI observations belong to the later commit. [New independent-renderer CI run #43990896317](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43990896317) passed the **separate synthetic safety gate** on **12/12 files** for both baseline and frozen local-linear: six known-contract eligible, six unsupported layouts blocked, zero false eligibility and 100% citation/semantic evidence validity. The [original artifact](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43990896317/artifacts/14287562182) was downloaded and integrity checked. This is a post-rc2 development commit, not a modification of the published source tag.

## CI and corrections

`.circleci/config.yml` remains the fast Smarter Testing profile; the complete `.github/workflows/ci.yml` runs as a separate full qualification. A fast green badge does not cover every parser, browser or deployment gate.

The complete run exposed and corrected bounded SQLite initialization contention. Ten new tests cover simultaneous threads, independent processes, lock deadlines, schema rollback and failure handling. The browser harness now verifies mutations through authenticated readback rather than relying on an evictable Chromium response body. Locator-based polling preserves the application's restrictive Content Security Policy. No application security policy was relaxed for the test.

Historical failed attempts remain in CI and evidence. The new acceptance record identifies the corrected source and does not retrospectively mark older failures as successful.

## Published source prereleases

The historical [`v0.1.0rc1`](https://github.com/mehdisafer/document-control-intelligence/releases/tag/v0.1.0rc1) prerelease remains fixed at commit `5c1f3e43f50c6d4056baabcafd5c39c40609f39b`. The new [`v0.1.0rc2`](https://github.com/mehdisafer/document-control-intelligence/releases/tag/v0.1.0rc2) prerelease is published from the verified `db42dd7c` source, with all three full GitHub Actions jobs and CircleCI green. Source releases are not a live purchasing service.

**Current GitHub release description (readback 17 November 2026, 00:24:23 UTC):** the existing [`v0.1.0rc2` prerelease](https://github.com/mehdisafer/document-control-intelligence/releases/tag/v0.1.0rc2) already identifies the correct tagged `db42dd7c` source, **139 Python / 24 JavaScript / 36 Chrome** checks, the corrected **7/7** local-linear demonstration and the same-generator 36-PDF replay. Only **four nested Markdown link wrappers** remain malformed in the editable release body. The maintainer should normalize these links **in the existing release only**, without moving, recreating or republishing either tag. See the [source-bound release notes](docs/RELEASE_NOTES_0.1.0rc2.md) and [publishing guide](docs/PUBLISHING.md).

## Licence, publication and remaining acceptance

Original project code is under [Apache-2.0](LICENSE); [NOTICE](NOTICE) preserves relevant attribution and limitations. Third-party components retain their own terms. No client documents or client infrastructure were used.

The reference's application, OCR, browser, container and Terraform-schema gates are now executed. Remaining acceptance concerns are the unqualified generative profile, independent-supplier generalization, a named production deployment and its operator acceptance, the still-unprotected main branch, and the release-description correction. The original 6/7 local-linear failure remains historical; the source-gated 7/7 regression is separately qualified on PR #19. No stable production `v1.0.0` tag or unqualified full-project acceptance is asserted.
