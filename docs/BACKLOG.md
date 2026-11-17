# Prioritized backlog and current limits

Last reconciled: **17 November 2026**. This is the current backlog;
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
- [x] **Publish the updated source prerelease:** [`v0.1.0rc2`](https://github.com/mehdisafer/document-control-intelligence/releases/tag/v0.1.0rc2) is live as **Pre-release**, with immutable tag SHA `db42dd7c7668d70deb8cf5ea6512abcd94a36510`. [Exact tagged-source CI](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43979529670) passed all three GitHub Actions jobs; CircleCI also succeeded. The public body has since been updated to the correct source and 139-test run (readback 17 November 2026, 00:24:23 UTC). Preserve the older `v0.1.0rc1` tag.
- [ ] **Normalize four nested reference links in the existing rc2 release body (owner UI):** change `[[label](URL)](URL)` to `[label](URL)`, leaving correct source facts, release identity, quality limits and both tags untouched; see [publishing guide](PUBLISHING.md).
- [x] **Resolve the extra local-linear abstention on the bounded synthetic
  demonstration at the new source.** [PR #19](https://github.com/mehdisafer/document-control-intelligence/pull/19)
  prevented unsupported URL-footer proposals from masking a genuine subtotal
  without weakening repeated recognized-label conflict checks. The frozen
  model passed **7/7** eligible and explicitly test-role-published/restored
  dossiers; 36/36 existing synthetic final PDFs were replayed with **30/36**
  eligible, **30/30** eligible critical quality and **zero false eligible**.
  The original 6/7 failure and separately audited human repair remain intact.
  **PR #19 is now merged to `main` and the exact tagged-source CI has passed**:
  **139 Python, 24 JavaScript and 36/36 Chrome checks**, including
  new source-label tests and a complete synthetic 36-PDF replay. This is a
  bounded generator-derived qualification, not independent supplier validation.
- [ ] **Resolve generative model quality and generalization.** Qwen had
  **3/36** correct classifications and **0/36** eligible in its bounded
  execution. A new independent supplier/layout holdout is still absent;
  the local-linear replay uses the original generator and seed. Do not
  reclassify Qwen or arbitrary supplier performance as qualified, or
  silently narrow the P04 scope. A new evaluation or explicit maintainer
  decision is needed.
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

- Evaluate unseen *independent* supplier labels and injection/footer layouts
  beyond the versioned synthetic source contract. The completed source-label
  guard is a conservative regression correction, not a retrained model or a
  claim about new supplier document families.
- Add independently generated layouts, labels, scan conditions and table
  geometry; publish coverage and critical-field quality together.
- [ ] Execute and review the [independent-renderer synthetic holdout](INDEPENDENT_LAYOUT_QUALIFICATION.md) on both source profiles. This supplies independent **generation code** and negative unsupported-layout abstention cases, **not independently sourced supplier documents** or a Qwen fix. Close only the narrow safety gate after real CI proof; retain supplier and model gates open.
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
