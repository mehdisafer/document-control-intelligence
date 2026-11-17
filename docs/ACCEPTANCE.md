# Acceptance matrix

Updated 17 November 2026 from the immutable source tag, GitHub Actions execution and downloaded original test artifacts. This document distinguishes **implemented**, **executed**, **tested**, and **accepted within a named scope**. The bounded synthetic document-control reference is qualified; independent supplier accuracy, generative-model quality and a deployed business service are **not** accepted.

## Published source prerelease and exact-source CI

The [published GitHub prerelease `v0.1.0rc2`](https://github.com/mehdisafer/document-control-intelligence/releases/tag/v0.1.0rc2) is marked **Pre-release** and its tag object points directly to commit [`db42dd7c7668d70deb8cf5ea6512abcd94a36510`](https://github.com/mehdisafer/document-control-intelligence/commit/db42dd7c7668d70deb8cf5ea6512abcd94a36510). The older `v0.1.0rc1` tag remains at `5c1f3e43f50c6d4056baabcafd5c39c40609f39b`. Neither tag represents a deployed production service.

The source correction was integrated through [PR #19](https://github.com/mehdisafer/document-control-intelligence/pull/19), after the dependency and release-version reconciliation of PRs #16–#18. [GitHub Actions push run #43979529670](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43979529670) completed all **three** actual jobs successfully on the **exact tag SHA**: `smoke-and-integration`, `container-integration`, `terraform-schema`. The matching `ci/circleci: build-and-test` status is also successful.

The [original tagged-source GitHub Actions artifact](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43979529670/artifacts/14281402594) was downloaded and its ZIP integrity checked. The original contents show:
- **139 Python unit/integration tests passed**, including all four source-label contract tests; no Python failures.
- **24 Node JavaScript state tests passed**, zero failures and skips.
- **36/36 real Chrome checks passed**, including nonblank, decoded source-PDF raster visibility next to the extracted evidence.
- The original **baseline and local-linear nine-scenario demonstrations** passed the unchanged verifier: the corrected, frozen-model local-linear reference produced **7 eligible, 7 explicitly published by scripted separate test roles, and 7 restored-identical dossiers**. The contradictory cases remain blocked.
- The full **36-document synthetic final-split replay**, using the frozen statistical model with original seed 42 and generator, reports **34/36 correct classification, 30/36 eligible, 30/30 critical quality among eligible, zero false eligible, 100% citation and semantic evidence validity**; the predeclared synthetic reference gate passed.
- Real container execution and Terraform provider/schema validation succeeded. The installed dependency advisory check reported no known findings within the tested dependency set; it does not certify ongoing security.

This qualification is **source-specific**. Scripted test-role approvals are not independent human review. The 36-PDF population shares its generator and conventions with training; it is not an independent supplier distribution, forgery benchmark or production load test. No cloud or customer environment was exercised.

## Historical source and model qualifications remain retained

The earlier [`e9e7f0f2` merged-source run](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43961711842) passed 135 Python, 24 JavaScript and 36 browser checks, including the four release-version tests and three lock/export consistency tests. Its distinct test count and source SHA are retained rather than silently relabelled as the tagged source.

The original frozen local-linear demonstration published **6/7**, failed its unchanged strict assertion, and remains historical negative evidence. A distinct auditable human-repair exercise yielded seven, but that repair is not an automatic-model pass. The later PR #19 source-label guard prevented unsupported printed URL-label proposals from masking a verified subtotal **without retraining the model or weakening the independent known-label/citation verifier**. The new 7/7 source-level result does not overwrite any older failed file, measurement or denominator. The Qwen/llama.cpp profile remains unqualified: **3/36 correct classifications and 0/36 eligible**.

## GitHub release-description link formatting and outstanding source administration

The tag and release are correct and published. In the GitHub release-body readback of 17 November 2026 (release last updated 00:24:23 UTC), the editable description **already identifies** the tagged `db42dd7c7668d70deb8cf5ea6512abcd94a36510` source and records the correct **139 Python / 24 JavaScript / 36 Chrome** checks, corrected **7/7** synthetic local-linear demonstration and frozen 36-PDF replay. The earlier `599bff76` and 135-test references are **not present** in the current public body. Only **four malformed nested Markdown reference links** remain: replace `[[label](URL)](URL)` with `[label](URL)` in the **existing release description**, without altering release identity, quality limits or either immutable tag. The [reconciled source notes](RELEASE_NOTES_0.1.0rc2.md) retain the detailed scope.

GitHub still reports `main.protected=false` and zero active rulesets. Configuring and verifying the [owner-side branch ruleset](PUBLISHING.md) remains open. The broader [acceptance issue #1](https://github.com/mehdisafer/document-control-intelligence/issues/1) stays open for independent suppliers, failing Qwen quality, deployment, backup/restore and operator acceptance. Public visibility, licensing, prerelease publication and application acceptance are different gates.

## Original-page visibility correction — earlier P0 evidence

The earlier Chrome browser workflow correctly downloaded the PDF bytes and set a
`blob:` iframe URL, but its original-document area displayed an unreadable
plugin icon. A successful HTTP request and iframe attribute did **not** prove a
visible page. The initial isolated PNG replacement also exposed a transient
blank image when an operator selected another field on the same page. Both
defects were reproduced before the final client-side request coalescing change.

A source-bound, authenticated PNG raster adapter now checks the original
content hash and PDF structural restrictions in a separate seccomp-constrained
child, renders one page under page/pixel/time/memory/output budgets, and keeps
the exact original PDF available through its existing authenticated download.
The UI validates the current document/revision/session, deduplicates same-page
requests and rejects a late response from a previously selected document.

On [GitHub Actions run 43774003311](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43774003311)
for `32fb196bcc496b31071d87d02453dd6936b98ccf`:

- All three real hosted jobs succeeded: `smoke-and-integration`,
  `container-integration` and `terraform-schema`.
- Original `tests.txt`: **128 Python tests passed**, zero failures/errors.
- Original `ui-state-tests.txt`: **24 JavaScript tests passed**, zero failures/skips.
- Original `browser/report.json`: **36 checks passed**, including image decode,
  nonblank pixels, authentication and visible image immediately before each
  desktop/mobile screenshot.
- The original Chrome 157 screenshots were independently downloaded and visually
  inspected. Both display the synthetic invoice's printed fields inside the
  review workspace, beside the extracted evidence. The operator can see the
  document rather than a blank PDF viewer.
- The recorded console includes one **expected** failed-authentication HTTP 401
  during a negative test. There are no unexpected outbound requests, no page
  exceptions and no failed required browser checks.

CircleCI's separate fast `build-and-test` job also reported success on this
revision. The new API and raster worker have a bounded no-network subprocess
policy; these tests do not establish security of arbitrary hostile PDFs,
accessibility conformance, production capacity or all browser/operating-system
combinations. Prior failed screenshots and reports remain available and are not
relabeled as passes.

The immutable tag `v0.1.0rc1` remains attached to its original source. PR #10
was merged at `24cad9d17b400fca01ae901d97082ebbd45bc59c` and [the subsequent main workflow](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43774277074)
completed all three jobs successfully. Source code and tests were unchanged by
the merge; the original visual screenshot bytes were inspected on the tested PR. Full P04
acceptance still excludes the local-generative model's failed accuracy gates,
automatic linear-model acceptance without human correction and deployment to
an externally authorised operating environment. See
[original-page preview design and evidence](ORIGINAL_PAGE_PREVIEW.md).

## Earlier complete hosted execution — before the original-page visual fix

Qualified runtime: `c451deba5f790a0b0207b6f3dd1931f597e04cc7`.
CircleCI pipeline: `42d7852d-0e54-4243-a467-fc1d1c58dfe8`.
[Workflow](https://app.circleci.com/workflow/872295c2-9e38-4d00-90d5-1c7b9e4e1807).

All three jobs completed successfully: `smoke-and-integration`, `container-integration`, and `terraform-schema`. This was the complete existing workflow, not the smaller `.circleci/config.yml` starter suite. The output was downloaded and inspected.

| Gate | Actual observation | Boundary |
|---|---|---|
| Python unit/integration suite | 122 tests passed in 38.653 seconds, including real parser/OCR and new SQLite startup regressions | Tested Linux reference and synthetic fixtures |
| JavaScript state regressions | 23 passed; zero failures, skipped or cancelled tests | Separate from rendering |
| Browser workflow | 33 checks passed in Chrome 153.0.8010.52 | Fresh isolated browser and cloned synthetic state |
| Browser business result | Three original PDFs uploaded via forms; distinct roles; acceptance, publication and downloaded ZIP/original digest verification | Not independent human review or arbitrary supplier PDFs |
| Browser UI | Actual desktop/mobile captures; 390 px viewport without document overflow; no page errors or unexpected external requests | Bounded observed screens; not general accessibility certification |
| Actual image | Built pinned reference and ran document demo, export and restoration inside the image | No claim about an untested deployment target |
| Compose and Terraform | Both Compose profiles validated; Terraform format, backend-disabled init and provider-schema validation passed | No cloud or host-target apply |
| Security/dependencies | Lint, schema drift, known-secret/history scan, dependency and licence/component controls executed | Point-in-time tools, not a proof of absence of every vulnerability |

Server/browser shutdown and removal of private cloned test state were checked. Runtime credentials and databases were not included in the uploaded evidence paths. PC-Mehdi was used under task-specific authorization to control CircleCI and retain artifacts; application execution occurred on isolated CI workers.

## Evidence integrity

SHA-256 values computed from original downloaded artifacts:

| Artifact under `dci-checks-c451deba5f790a0b0207b6f3dd1931f597e04cc7/` | SHA-256 |
|---|---|
| `tests.txt` | `013eee3756ad572f3e309979234f0a9b840a6fea4e3e87bb11a1f92af61bc9b7` |
| `ui-state-tests.txt` | `a8e93e1eb195bcf7efcb218a43e6ec64f434d4dad2113cc8827cd3c55f0baa80` |
| `browser/report.json` | `2218c844bbefd08d92a8f919917e6fdcbf0514de23783ffd7efa08f1000c30cd` |

The full run also retains actual browser images, deterministic demo/export receipts, image identity and container logs. CircleCI retention is finite. Historical evidence under [evidence/](../evidence/) remains versioned with its own source and runtime; this summary does not fabricate replacement execution outputs.

## Corrections established by the full run

Concurrent SQLite initialization exposed a genuine lock race. Migration now retries only bounded SQLite BUSY/LOCKED contention, closes and rolls back failed attempts, validates WAL, and does not retry unrelated I/O/schema errors. Ten additional tests cover repeated simultaneous threads, independent processes, real exclusive locks, deadline expiry, rollback, unsupported WAL and future-schema protection. SQLite remains a single-host WAL design, not a network-filesystem or distributed database.

The browser harness no longer relies on Chromium retaining a POST response body after the original-PDF frame is released. The actual form mutation is followed by authenticated readback bound to the unique case and uploaded PDF digests. Locator-based polling works with the restrictive Content Security Policy. Application CSP was not relaxed to make tests pass.

Original failed CI attempts remain failures. Earlier GitHub Actions jobs stopped before runner allocation; their account-level cause was not established. Successful CircleCI execution closes the application's execution gaps, not the unrelated GitHub account diagnostic. The original [GitHub blocked-run record](../evidence/platform/github-actions-blocked.json) remains historical evidence.

## Other established controls and their limits

Immutable PDF blobs, page evidence, financial and cross-document rules, revision-bound corrections, independent acceptance, transactional publication, cross-case duplicate-invoice protection, cancellation, lease fencing, bounded retries and backup/restore remain implemented and exercised. New versions invalidate prior acceptance. Export consumers upsert superseding publications; the export is not a payment instruction.

Historical real HTTP tests measured 36 checks across 30 requests with original PDF/ZIP equality, denial/idempotency checks and trace joins. Historical bounded worker profiles used nine PDFs per run with one/two workers at 2.08/3.92 documents per second. These are attributed historical observations, not new hosted capacity measurements or a distributed-scale guarantee.

Parser authenticity for arbitrary pure-native hidden text, unsupported purchasing layouts, credit notes, returns, freight, foreign exchange and ambiguous repeated SKU contracts is not established by the current fixture set. Enterprise identity federation and deployment-specific recovery objectives remain target concerns.

## Model acceptance remains distinct

| Model/profile | Recorded evidence | Acceptance decision |
|---|---|---|
| Deterministic reference | Seven demo dossiers and corresponding restoration | Qualified within the documented reference scope |
| Local statistical model | Frozen synthetic corpus, 34/36 classification, 30/36 eligible and 30/30 eligible critical quality; zero false eligible in that set | Small generator-derived population; not general supplier accuracy |
| Raw local-linear demonstration | Six automatic exports against an original target of seven | Original strict seven-export gate **not met** |
| Source-gated local-linear demonstration (PR #19) | Seven eligible dossiers, seven explicit test-role publications, seven restored-identical exports; unchanged strict verifier | Merged, tagged `v0.1.0rc2` source qualification **met** on the synthetic demo; original six-export report still failed historically |
| Source-gated frozen final-set replay (36 generated PDFs) | 34/36 correct class, 30/36 eligible, 30/30 eligible critical quality, 0 false eligible, 100% supported citations | Existing synthetic policy gate met; no independent-supplier generalization claim |
| Attributed human repair | Seventh dossier published after documented subtotal correction and separate approval; restored state consistent | Human-assisted workflow evidence, not automatic-model acceptance |
| Larger Qwen/llama.cpp profile | 36 real requests, 3/36 correct classifications, 0/36 eligible; original resource/response records retained | Quality gate **not met** |

The original `overall_requested_local_qualification_met: false` remains preserved in [qualification evidence](../evidence/qualification/). Neither the scripted human repair nor the newer, now successful seven-export source-gated run rewrites that historical failure. A separately recorded, complete 36-PDF regression has been executed on the source-gated revision; it repeats the existing synthetic test split rather than supplying a new independent supplier holdout. Acceptance of Qwen or deployment scope still requires further evidence or explicit maintainer decisions.

## Remaining gates and publication

1. The original six-versus-seven local-linear run remains historically failed; the frozen-model 7/7 demonstration and 36-PDF same-generator synthetic regression now pass on the **published tagged main SHA**. Independently qualify new supplier layouts and the still-failed Qwen generative-model quality gate, or explicitly approve the narrower reference scope while retaining all negative results.
2. Select and authorize the actual deployment target, inspect the plan, exercise its service/restore/monitoring and obtain operator acceptance. Hosted CI containers are not a production rollout.
3. Public repository visibility, Apache-2.0, About metadata and **both published source prereleases** are verified. Apply and read back the **still-missing `main` ruleset** through [PUBLISHING.md](PUBLISHING.md); the current API read found `main.protected=false` and no rulesets. Normalize the four nested Markdown links in the **existing** public `v0.1.0rc2` release description; its exact tagged-source facts are already corrected. Neither tag needs to be moved. No paid feature or public business service is authorized by this source-publication task.

The maintainer-selected project licence is [Apache-2.0](../LICENSE), with [NOTICE](../NOTICE); third-party software retains its own terms. Licence selection is no longer pending. Public source publication, local reference qualification, model-quality acceptance and production operation are four separate decisions.
