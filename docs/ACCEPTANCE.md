# Acceptance matrix

Updated 15 November 2026. This record distinguishes implementation, actual execution and acceptance. **The synthetic local reference is qualified through its full hosted parser/OCR, browser, image and Terraform-schema profiles. The entire P04 scope is not unconditionally accepted.** The local-linear automatic seven-export target, larger-model quality and intended production deployment remain separate gates.

Application version `0.1.0rc1` remains a reference candidate; no stable production `v1.0.0` is asserted. [Issue #1](https://github.com/mehdisafer/document-control-intelligence/issues/1) must remain open until its remaining criteria are resolved without rewriting failed results.

## Original-page visibility correction — latest P0 evidence

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

The immutable tag `v0.1.0rc1` remains attached to its original source. This
corrective PR needs an exact-head merge and post-merge verification before the
latest preview can be treated as the default-branch delivery. Full P04
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
| Attributed human repair | Seventh dossier published after documented subtotal correction and separate approval; restored state consistent | Human-assisted workflow evidence, not automatic-model acceptance |
| Larger Qwen/llama.cpp profile | 36 real requests, 3/36 correct classifications, 0/36 eligible; original resource/response records retained | Quality gate **not met** |

The original `overall_requested_local_qualification_met: false` is preserved in [qualification evidence](../evidence/qualification/). Neither a human-repaired run nor the new complete deterministic/browser run changes that recorded outcome. Improvement requires an explicit new evaluation, preserving the original frozen results; acceptance of a narrower model scope is a maintainer decision, not an implicit change made by CI.

## Remaining gates and publication

1. Resolve the automatic local-linear target and generative-model quality criteria, or explicitly approve a narrower reference scope while retaining all negative results.
2. Select and authorize the actual deployment target, inspect the plan, exercise its service/restore/monitoring and obtain operator acceptance. Hosted CI containers are not a production rollout.
3. Apply and read back public visibility, repository metadata and appropriate protections through [PUBLISHING.md](PUBLISHING.md). Source publication was previously authorized; it does not authorize a paid feature or public business service. No visibility change is inferred from a passing build.

The maintainer-selected project licence is [Apache-2.0](../LICENSE), with [NOTICE](../NOTICE); third-party software retains its own terms. Licence selection is no longer pending. Public source publication, local reference qualification, model-quality acceptance and production operation are four separate decisions.
