# Acceptance matrix

Updated 15 November 2026. This record distinguishes implementation, actual execution and acceptance. **The synthetic local reference is qualified through its full hosted parser/OCR, browser, image and Terraform-schema profiles. The entire P04 scope is not unconditionally accepted.** The local-linear automatic seven-export target, larger-model quality and intended production deployment remain separate gates.

Application version `0.1.0rc1` remains a reference candidate; no stable production `v1.0.0` is asserted. [Issue #1](https://github.com/mehdisafer/document-control-intelligence/issues/1) must remain open until its remaining criteria are resolved without rewriting failed results.

## Latest hosted original-page qualification — GitHub Actions

**Qualified runtime source:** `948d82ba90af3f3049b48e7846eea56ad3a45dcf`, [run #43770874796](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43770874796). This is the latest standalone preview-fix source, not the immutable `v0.1.0rc1` release commit. All three jobs completed successfully: `smoke-and-integration`, `container-integration`, and `terraform-schema`.

| Gate | Executed result | Qualification boundary |
|---|---|---|
| Python | **126 tests passed** in 30.042 seconds, including real multipage PNG rendering, authenticated preview, active/encrypted-PDF rejection and blob tampering | Synthetic Linux inputs, not arbitrary supplier layouts |
| JavaScript | **25 tests passed**, without skips, including stale preview request fencing and logout URL revocation | State-only tests with a mocked DOM; browser checked separately |
| Real browser | **35/35 checks passed** in Chrome 157.0.8103.50, with a decoded **953 × 1348** raster page, page identity, authentic original download, business approvals, publication and export | Real desktop/mobile captures; independent human review not implied |
| Mobile UI | Actual 390 px screenshot; document/body width both 390 px, no horizontal overflow | No general accessibility certification |
| Container | Reference image built and completed parsing, review/export and restoration under the configured constraints | Not an intended-host rollout |
| Terraform | Formatting, initialization and provider-schema validation succeeded | No resource apply or target-host approval |
| Security/integrity | Strict CSP retained; no unexpected page errors or external document requests; private cloned state removed | A point-in-time source and dependency check |

This was a **real rasterized original**, not a merely created `blob:` URL. The PNG is rendered from a SHA-256-verified source using a separately sandboxed PDFium child with wall-clock, address-space, page, image-size and concurrency bounds. Rendering is a visual aid; the original PDF bytes and source citations remain authoritative. [Issue #11](https://github.com/mehdisafer/document-control-intelligence/issues/11) documents the earlier broken native iframe and the acceptance proof.

Original [check/browser artifact #14184372240](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43770874796/artifacts/14184372240) was downloaded and inspected. The retained bytes have these SHA-256 digests:

| Original artifact member | SHA-256 |
|---|---|
| `tests.txt` | `05135324c3bbf45f06b9dcdbee8770f041c163f09fce577f3019a631a7954257` |
| `ui-state-tests.txt` | `ea00fabe93d48b50d65bfd3fc226d5594edf8195e176896529c248b9823d6c58` |
| `browser/report.json` | `934cd6b94a6a75fb943fe27cda99553930b7af4ff8957902d9ce38195d6f47f9` |
| `browser/desktop-review.png` | `643e609a95fcf57769de91c8a1e71db695453c125119ab20088776cb436677c9` |
| `browser/mobile-review.png` | `2aff82d54eeb6c26ec840ab175e219dc4e5b8c0746869b50018886e22d4e486a` |

The previous native PDF iframe produced an unreadable document icon in the Chrome evidence despite returning correct PDF bytes. That limitation is **resolved on the preview-fix branch**, not retroactively on the older release/tag. A new CircleCI run and integration on `main` must still be distinguished from this successful GitHub Actions run.

## Earlier hosted CircleCI execution — before isolated raster previews

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
3. GitHub public visibility, repository description/topics, Apache-2.0 and the original source prerelease have been read back as published. Activate and verify the appropriate `main` ruleset through [PUBLISHING.md](PUBLISHING.md); the GitHub connector cannot write repository administration settings. No paid feature or public business service is authorized by this source-publication task.

The maintainer-selected project licence is [Apache-2.0](../LICENSE), with [NOTICE](../NOTICE); third-party software retains its own terms. Licence selection is no longer pending. Public source publication, local reference qualification, model-quality acceptance and production operation are four separate decisions.
