# Release candidate 0.1.0rc1

## Purpose

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

## Prepared repository metadata

Description:

> Evidence-linked purchasing document control with local ML, PDF/OCR, three-way matching and audited human review.

Topics: `document-ai`, `data-engineering`, `mlops`, `local-first`, `fastapi`, `ocr`,
`document-processing`, `human-in-the-loop`, `data-quality`, `python`.

The 2026-11-15 connector observation still reports a private repository, empty
description/topics, unprotected `main` and no GitHub releases. Apache-2.0 is
recognized. The available connector can edit source and track issues/PRs, but
has no writer for visibility, metadata, rulesets or releases.

The maintainer explicitly owns the remaining GitHub UI actions. Agent browser
access is neither needed nor part of this handoff. Follow the
[maintainer publishing guide](PUBLISHING.md) for exact settings, then use the
[prepared prerelease body](RELEASE_NOTES_0.1.0rc1.md). These are prepared values;
the current observation does not assert that they have been applied.

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

## Latest CI and dependency observations

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

