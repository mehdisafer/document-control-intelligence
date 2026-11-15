# Public-source preparation and qualification

The maintainer selected Apache-2.0 and then explicitly authorized public source
publication on 2026-11-14. This record supports a reviewable `0.1.0rc1` source
candidate. It does not close the complete operational acceptance scope.

## Fixed and executed source

Commit: [`8839be77ad24492702bcb2f53c4e74fffd7a78dd`](https://github.com/mehdisafer/document-control-intelligence/commit/8839be77ad24492702bcb2f53c4e74fffd7a78dd).
Tree: `9ed8c7a1d8e9755f72ec4f061b500e125a9498b2`.

- UI responses are bound to the current actor/case/document request. An obsolete
  original PDF, field response or audit cannot replace the current selection.
  A newer revision/status also invalidates pending document metadata. Dialogs
  capture their mutation targets; stale/null field corrections are disabled.
- ZIP export counts UTF-8 dossier JSON, original PDFs and manifest JSON together
  under the 50 MiB uncompressed-member budget. Boundary, multibyte metadata and
  original-integrity checks exercise actual generated PDFs and application state.
- CI runs the JavaScript state/unit checks separately from real browser checks.

The following documentation/evidence change also removes the PR event's path
filter so future documentation-only PRs can report required checks. That
trigger-only delta is inspected separately; the application, tests, dependency
lock and original reports retain the executed `8839be77` bytes.

## Observed local results

| Check | Result and scope |
|---|---|
| Python unit/integration | 112 passed, no skips; unittest reports 34.791 seconds |
| JavaScript state/unit | 23 passed, 0 failed, 0 skipped; Node reports 152.342997 ms |
| Source preservation | All 208 tracked files have identical before/after SHA-256 values; clean worktree |
| Lint, exported schemas, JavaScript syntax and dependency lock | All commands exited 0 |
| Python dependency audit | 32 packages, zero known vulnerabilities at execution time |
| Component inventory | No unreviewed Python licence family; native/runtime/model notices remain separate |
| Known-secret/history check | 421 candidate/history object inspections, no findings for the declared patterns |

The original [command report](run-8839be77/report.json), [command ledger](run-8839be77/commands.json),
[Python log](run-8839be77/unittest.log), [JavaScript log](run-8839be77/ui-state.log)
and [artifact digests](run-8839be77/artifacts.json) are retained unchanged.
[summary.json](summary.json) derives counts from those logs. The original runner
expected TAP `#` counters, whereas Node 24 emitted `ℹ` counters; therefore its
`javascript_state_unit` field is empty. The raw log explicitly records all 23
results and zero failures/skips. The derived summary records this parsing
limitation rather than overwriting the original report or rerunning the suite.

Python is 3.12.14; Node is 24.22.1. The JavaScript harness executes the real app
script in `node:vm` with a small mocked DOM and deferred fetch responses. It is
not a browser, rendering engine, PDF viewer, accessibility check or HTTP test.
Two targeted development regressions failed against the exact preserved
`cf7d1b` UI baseline; the [original failure log](review/ui-baseline-regression.log)
is retained separately from the published-source execution.

## Disclosure and GitHub boundaries

The [disclosure review](review/review-8839be77.json) identifies the exact Git
history, candidate files, archive member hashes, synthetic PDFs and bounded
credential patterns inspected. It is a scoped automated/assisted review, not a
security certification or independent human approval.
The original review inventories and digest manifest are retained. Two
operator-specific scanner helpers are excluded from the source candidate; their
identities remain recorded in that original manifest. The
[final content check](final-content-check.json) closes the temporary missing
evidence link and confirms preservation of all 126 historical evidence files
apart from the two intentionally updated narrative indexes.

The [GitHub surface observation](review/github-surface.json) covers seven runs,
21 jobs, all available issue/PR comments and two author-side reviews. All 21 jobs
have `runner_id: 0`, an empty runner name and `steps: []`; all seven runs report
zero artifacts. Job-log retrieval returns `404 BlobNotFound`. The rejection
cause is unknown. Successful local checks do not mark these workflows passed.

The source/history and synthetic archive checks support public source release.
Real browser rendering, image build/in-container execution, Terraform schema
validation and an intended-host rollout remain unqualified. See the
[acceptance matrix](../../docs/ACCEPTANCE.md) and [release status](../../docs/RELEASE.md).
Changing repository visibility creates no public business-service endpoint.

## Maintainer handoff on 2026-11-15

PR #2 integrated the candidate at `84b06caf6452c746ef27a615575c2a0f4c7fd0c9`,
with the same tree as reviewed candidate `3bf98d82`. The fresh administrative
observation reports private visibility, recognized Apache-2.0, empty
metadata/topics, unprotected `main` and no release object. The maintainer owns
the remaining UI steps in [PUBLISHING.md](../../docs/PUBLISHING.md); agent browser
access is outside the task. Prepared instructions are not settings readback.

- [CI observation](handoff-2026-11-15/ci-current.json): original attempt and the
  single connector rerun of main run `43602643545` are separate. Attempt 2 again
  has three failed jobs with no runner or steps, missing logs and zero artifacts.
  The cause is unavailable; successful dynamic Dependabot runs are distinguished.
- [Dependabot review](handoff-2026-11-15/dependabot-review.json): five exact open
  PR heads, eight patches and their public-facing bodies/comments were inspected.
  No disclosure blocker was identified in that scope. PR #5 has an unregenerated
  runtime lock export; its upgrade must be corrected and qualified separately.
- [Handoff manifest](handoff-2026-11-15/manifest.json): report hashes, observation
  scope and outstanding UI actions. This adds no new application/model execution.

All historical execution logs, model artifacts and disclosure inventories remain
unchanged. Current-main qualification does not extend to unmerged dependency
updates. Public-source status and full operational acceptance remain separate.

## Reproduction and preservation

Use the README's frozen install and test commands for the current checkout.
The [original qualification runner](qualify_public_source.py) requires an exact
clean Git source and a new output directory. To reproduce this record, use a
detached checkout of `8839be77`, keep the runner outside it, and pass the source
SHA through `--source`. Its logs retain the actual execution identity.

The original `3ff93109` HTTP/model/demo evidence and its failed local-linear
seven-export assertion are unchanged. No model training, final-holdout tuning or
LLM replay was performed for these UI/export corrections. The dependency lock,
model coefficients, prompts and thresholds are unchanged.

