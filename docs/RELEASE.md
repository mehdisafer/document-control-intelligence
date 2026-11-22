# Release candidate 0.1.0rc1

## Current post-release state — reconciled 23 November 2026

This document originated as the **historical publication and qualification
record for `v0.1.0rc1`**. Text below describing a private repository,
unallocated GitHub runners, or pending browser/container checks reflects its
original 13–15 November preparation window, not today's status.

The repository is now **Public**, with Apache-2.0, the prepared About
description and ten topics. The `v0.1.0rc1` prerelease is published and its
tag is deliberately unchanged at
[`5c1f3e4`](https://github.com/mehdisafer/document-control-intelligence/commit/5c1f3e43f50c6d4056baabcafd5c39c40609f39b).

The later SQLite/CI improvements, real browser review and securely
rasterized original-page preview have been **merged to `main`**. Their
[original-page visual proof](ORIGINAL_PAGE_PREVIEW.md), the
[post-merge 3-job PASS](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43774277074)
and the [current acceptance ledger](ACCEPTANCE.md) supersede the historical
runnerless/browser-unqualified observations below **only for the newer
source revision**.

The subsequent [`v0.1.0rc2` prerelease](https://github.com/mehdisafer/document-control-intelligence/releases/tag/v0.1.0rc2) is **published** and tagged at source `db42dd7c7668d70deb8cf5ea6512abcd94a36510`, not at the earlier documentation-only `599bff76`. Its [exact-source CI](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43979529670) passed 139 Python, 24 JavaScript, 36 real Chrome checks and all three hosted integration jobs. A new local-linear semantic-label guard met the bounded 7/7 scripted demonstration, leaving the original 6/7 failure unchanged and Qwen unqualified. The **editable release body already reflects these correct source facts**, but four nested Markdown link wrappers still need formatting-only correction. As last read, `main` remains **unprotected**, and [issue #1](https://github.com/mehdisafer/document-control-intelligence/issues/1) stays open for independent supplier/LLM quality and authorized production-target decisions. Neither release implies production certification.

The latest inspected development qualification is **not a new release**:
[`2e8b3a6`](https://github.com/mehdisafer/document-control-intelligence/commit/2e8b3a6ec22c21dfdb121fd65488851ed4fdbc21)
passed [three exact-main Actions jobs](https://github.com/mehdisafer/document-control-intelligence/actions/runs/45080409953),
CircleCI, **198 Python / 24 JavaScript / 36 Chrome** checks and reference
container/restore. The [post-rc2 record](POST_RC2_QUALIFICATION.md) reconciles
queued-policy fencing, original paired-Qwen negative replay and dependency
lock/hash parity. Both published tags and their original evidence remain
unchanged; supplier, model and intended-host acceptance remain open.

## Purpose — original `0.1.0rc1` preparation record

This candidate delivers an executable synthetic purchasing workflow: PDF receipt,
native/OCR extraction, local models, verifiable source evidence, deterministic
controls, cumulative matching, human review, acceptance, publication and export.
It also supplies persistent queue/recovery behavior, restoration evidence,
container/Terraform references and an explicit acceptance matrix.

The trained statistical model meets the declared final synthetic quality/coverage
gate. The generative Qwen profile remains experimental. On 2026-11-14 the
maintainer explicitly requested end-to-end public publication of this repository,
following the Apache-2.0 choice. This is authorization to publish the source
candidate with its disclosed limitations. Browser, container, Terraform and
target-deployment gates remain open under
[issue #1](https://github.com/mehdisafer/document-control-intelligence/issues/1).

Source and evidence changes were integrated through
[PR #2](https://github.com/mehdisafer/document-control-intelligence/pull/2)
at merge commit `84b06caf6452c746ef27a615575c2a0f4c7fd0c9`. Its tree matches
the reviewed candidate `3bf98d82`. Author-side assisted review is identified as
such; it is not an independent approval. Integration of the source candidate
does not turn a failed or runnerless CI workflow into a passed check or establish
production readiness.

The initial implementation source is commit
[`3ff93109f3ea0d9c5f4bdfd598dd35bbd4513439`](https://github.com/mehdisafer/document-control-intelligence/commit/3ff93109f3ea0d9c5f4bdfd598dd35bbd4513439).
The following evidence/documentation commit, `8dbe831a243e66aad18c601086a8e62b3c496322`,
does not alter runtime code, contracts, tests, lockfiles or infrastructure. Its [publication map](../evidence/publication-map.json)
checks those bytes against the executed source and preserves the identity of
earlier runs. The [qualification record](../evidence/qualification/) contains
107 passing tests, the failed raw-linear demo assertion, separate human recovery,
72-output semantic regression, small load execution and real HTTP proof.

Commit `8839be77ad24492702bcb2f53c4e74fffd7a78dd` subsequently fixes stale UI
responses and captures mutation targets, and includes dossier/manifest JSON in
the ZIP's 50 MiB uncompressed-member budget. Its separate
[qualification](../evidence/publication/) records 112 passing Python tests and
23 passing JavaScript state/unit tests, both without skips, plus lint, schema,
dependency and known-secret/history checks. The JavaScript harness uses a mocked
DOM/fetch; it is not browser-rendering evidence. Model weights, prompts,
thresholds and original execution artifacts are unchanged.

## Prepared repository metadata — historical snapshot

Description:

> Evidence-linked purchasing document control with local ML, PDF/OCR, three-way matching and audited human review.

Topics: `document-ai`, `data-engineering`, `mlops`, `local-first`, `fastapi`, `ocr`,
`document-processing`, `human-in-the-loop`, `data-quality`, `python`.

The initial 2026-11-15 connector observation reported a private repository, empty
description/topics, unprotected `main` and no GitHub releases.
Those historical values have since changed as recorded above; only the lack of
an active branch-protection ruleset remains current. Apache-2.0 is
recognized. The available connector can edit source and track issues/PRs, but
has no writer for visibility, metadata, rulesets or releases.

The maintainer explicitly owns the remaining GitHub UI actions. Agent browser
access is neither needed nor part of this handoff. Follow the
[maintainer publishing guide](PUBLISHING.md) for exact settings, then use the
[prepared prerelease body](RELEASE_NOTES_0.1.0rc1.md). These are prepared values;
the historical observation did not assert that they had been applied at that point.

## Prepared protection policy

For `main`, require a PR and the actual `smoke-and-integration`,
`container-integration` and `terraform-schema` checks; prevent force
pushes/deletion; require conversation resolution and an up-to-date branch.
Use zero required approvals while no other eligible reviewer is available.
The PR record is not an independent approval. The prepared active ruleset has
no bypass actors; failed or missing required checks will block subsequent merges.
The [publishing guide](PUBLISHING.md) gives the maintainer's exact UI steps and
readback criteria. These protections are not yet observed as applied.

The pull-request workflow has no path filter, so documentation-only PRs can
report the required checks. GitHub documents that skipping a required workflow
with a path filter leaves its checks pending and blocks the PR:
[required-check guidance](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/skip-workflow-runs).
The later trigger-only adjustment does not change the application/tests executed
on `8839be77`; actual hosted execution remains separately observed.

## Apache-2.0 adoption

The maintainer explicitly selected Apache-2.0 on 2026-11-14. [LICENSE](../LICENSE)
contains the official unmodified text and [NOTICE](../NOTICE) records
`Copyright 2026 Mehdi Safer`. The package declares the SPDX expression and includes
both files; the Docker build copies them before installing the project.
Dependencies, OCR/runtime components and model weights retain their own notices.

This later licensing change updates `pyproject.toml` and Docker's packaging inputs.
It does not change application code, dependencies, model coefficients, thresholds
or historical execution artifacts. The original 107-test and HTTP reports remain
attributed to `3ff93109`; their hashes are not rewritten as results of this change.
The exact-source HTTP harness is replayed using the detached original checkout
described in the README. Container execution and the other open gates remain
unqualified by a licensing change.

## Public-release checklist

1. The Apache-2.0 licence choice and public-source authorization are resolved.
   Retain the official licence, project notice and verified distribution metadata.
2. Review the final source/history, issue/PR content, logs, synthetic dossiers and
   archives before exposing them. The [publication record](../evidence/publication/)
   identifies the checked source and the scope of the disclosure review.
3. The locally qualified candidate is integrated on `main` through PR #2.
   Its history, CI failures and unresolved integration gates are retained.
4. The maintainer applies the authorized visibility change, description/topics
   and prepared repository protections using [PUBLISHING.md](PUBLISHING.md),
   then verifies the saved settings and anonymous repository/licence/source access.
5. After public visibility, run the existing workflow on the final `main`.
   Inspect actual steps, browser screenshots, container execution and Terraform
   output. One connector rerun on 2026-11-15 still received no runners; visibility
   alone is not evidence that the rejection will resolve.
6. Publish `v0.1.0rc1` as a prerelease using the
   [prepared body](RELEASE_NOTES_0.1.0rc1.md), targeting the final delivered
   `main` commit. A stable operational release requires its additional qualification.

No public business endpoint is created by changing repository visibility. A target
deployment remains a separately inspected operational action.

## Historical CI and dependency observations — 15 November 2026

The single rerun of [main run 43602643545](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43602643545),
at attempt 2 on 2026-11-15, again ended with three failed jobs, `runner_id: 0`
and `steps: []`. All three log requests return `404 BlobNotFound`; no artifacts
are reported. The underlying cause remains unknown because check annotations
are unavailable through this connector. The
[CI observation](../evidence/publication/handoff-2026-11-15/ci-current.json)
keeps both attempts separate. The maintainer can inspect the latest
[smoke/integration annotation](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43602643545/job/132935245932)
in the UI. Successful Dependabot update workflows do not qualify the application.

Five Dependabot PRs (#3–#7) are open and unmerged. Their reviewed patches and
bodies introduce no identified disclosure blocker in the stated scope.
[PR #5](https://github.com/mehdisafer/document-control-intelligence/pull/5)
changes parser versions in `uv.lock` without regenerating `requirements.lock`;
merging it unchanged would audit older versions than those installed. Regenerate
that export and qualify the parser upgrade separately before merging. The
[dependency review](../evidence/publication/handoff-2026-11-15/dependabot-review.json)
records exact heads and limits; existing application results do not qualify
these proposed upgrades.

## Candidate reproduction

Use the locked installation and real demo commands in the README. Preserve the
generated `result.json`, control dossiers, exact source/model/parser hashes and
execution logs. The evidence index distinguishes original executions from later
publication mapping and CI results. Do not replace an adverse report with a
successful replay or backdate a commit into original metadata.

