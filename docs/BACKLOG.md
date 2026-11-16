# Prioritized backlog and current limits

Last reconciled: **16 November 2026**. This is the current backlog; the
original failures, model reports and earlier release notes remain preserved.
See the [acceptance matrix](ACCEPTANCE.md) and
[original-page evidence](ORIGINAL_PAGE_PREVIEW.md).

## P0 — Current release and acceptance gates

- [x] Publish the repository under **Apache-2.0** with About metadata and
  [source prerelease `v0.1.0rc1`](https://github.com/mehdisafer/document-control-intelligence/releases/tag/v0.1.0rc1).
  The old tag is immutable and predates later runtime fixes.
- [x] Exercise the deterministic reference in CI. The
  [merged-source GitHub Actions run](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43774277074)
  completed all three real jobs, including parser/OCR, API, browser, image,
  Compose and Terraform-schema checks. No target deployment is implied.
- [x] Replace the unreadable native PDF frame with an authenticated,
  source-hash-verified, isolated page raster. The
  [visual qualification](ORIGINAL_PAGE_PREVIEW.md) includes real Chrome
  desktop/mobile screenshots and checks at screenshot time; issue
  [#11](https://github.com/mehdisafer/document-control-intelligence/issues/11)
  is closed for the bounded synthetic reference, not supplier-general use.
- [ ] **Protect `main`** using the prepared branch ruleset: require PR,
  conversation resolution, prevent force-push/deletion, and require the
  actual `smoke-and-integration`, `container-integration` and
  `terraform-schema` checks. The GitHub API read on 16 November found no
  ruleset and `main.protected=false`. The connector has no repository
  administration writer; this remains an owner-side UI action.
- [ ] **Publish an updated source prerelease** after reviewing the final
  integrated SHA. [`v0.1.0rc2` notes](RELEASE_NOTES_0.1.0rc2.md) are
  prepared; no new tag or release has been created by this documentation work.
- [ ] **Resolve the model-quality decisions.** The frozen local-linear demo
  produced **6** automatic exports against the original target of **7**;
  an attributed human correction produced the seventh in a **separate** run.
  The bounded Qwen profile classified **3/36** documents correctly and made
  **0/36** eligible. Do not mark those failed gates passed or silently narrow
  the original scope. Improve and re-evaluate on a new untouched holdout,
  or obtain an explicit maintainer decision to ship only the qualified
  deterministic/reference profiles.
- [ ] **Define an authorized target host** before deployment. Inspect the
  concrete rollout plan, backups, restoration, monitoring, network exposure
  and operating acceptance. Passing CI containers is not a deployed service.
- [x] The five Dependabot upgrade requests were reconciled and superseded
  by [PR #16](https://github.com/mehdisafer/document-control-intelligence/pull/16),
  merged at `1c6b39f`: `pdfplumber==0.11.10`, `pdfminer-six==20260107`,
  `pip-audit==2.10.1`, `pip-licenses==5.5.5`, and pinned GitHub Actions
  updates. `requirements.lock` was regenerated to match the installed
  `uv.lock` dependency graph, with three new consistency tests.
  All three [main jobs](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43960638742)
  passed. The five original bot PRs are now closed, not independently merged.
  Future dependency upgrades still require their own lock and CI review.
- [x] `0.1.0rc2` source version is merged through
  [PR #17](https://github.com/mehdisafer/document-control-intelligence/pull/17)
  at `e9e7f0f2`. The [merged-main CI](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43961711842)
  passed **135 Python, 24 JavaScript and 36 real-browser checks**, plus Docker
  and Terraform, with four additional release identity tests.
  This does not change any frozen ML evaluation or authorize a host rollout.

## P1 — Extend supported purchasing cases

- Improve the local-linear model's injection-footer confusion with a
  new train/tuning split and independent holdout. Preserve the original
  abstention and failed seven-export assertion as historical proof.
- Add independently generated layouts, labels, scan conditions and table
  geometry; publish coverage and critical-field quality together.
- Evaluate geometric table extraction rather than presuming pipe-delimited
  synthetic table geometry.
- Define explicit contracts for returns/credit notes, freight, discounts,
  FX rates, multiple orders and repeated-SKU line identities before accepting
  these cases.
- Assess native PDF visual/text-layer discrepancies and forged supplier
  content. A source hash is evidence of byte identity, not authenticity.
- Add federated identity, dossier-level access control and session lifecycle
  testing before any organization-wide deployment.

## P2 — Operations when the target is agreed

- Exercise realistic workload sizes and OCR mixes on the authorized host;
  measure rate, P95 latencies, process/memory/disk budgets, restart and
  backpressure with the actual resource limits.
- Introduce multi-host queue/storage only when measured capacity demands it;
  re-prove versioning and idempotent publication invariants first.
- Define retention, archival and legal-hold behavior. The current
  `retention_days` policy setting is not an implemented automatic purge.
- Retain image SBOM/digest/build provenance for any deployed image. The
  current Python dependency and licence inventory has a narrower scope.

## Recorded evidence and boundaries

The [evidence index](../evidence/) retains the original 107/112-test
qualification results, failed raw local-linear demonstration, repaired
human-reviewed result, final synthetic evaluations, 72-output semantic
regression, real HTTP path, worker-load results and restored exports.
Later hosted runs qualify their own source revisions; they do not alter
those original reports.

The merged runtime has since passed **128 Python tests, 24 JavaScript
state tests and 36 real-browser checks**, including a visibly decoded
raster original, on [source `32fb196b`](https://github.com/mehdisafer/document-control-intelligence/commit/32fb196bcc496b31071d87d02453dd6936b98ccf).
The [post-merge workflow](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43774277074)
passed its three jobs. These facts establish a **bounded synthetic reference**,
not production readiness, third-party document authenticity, arbitrary supplier
accuracy or acceptance of the failed model profiles.
