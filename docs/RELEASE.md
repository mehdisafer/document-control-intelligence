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

Source and evidence changes are reviewed together in
[PR #2](https://github.com/mehdisafer/document-control-intelligence/pull/2).
Author-side assisted review is identified as such; it is not an independent
approval. Integration of the source candidate does not turn a failed or
runnerless CI workflow into a passed check or establish production readiness.

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

The available GitHub connector exposes source/issue/PR operations but no repository
metadata, visibility or protection writer. These values are prepared, not asserted
to have been applied. At the prepublication observation the repository is still
private, and the isolated cloud browser is at GitHub's sign-in page. Authentication
to that administration surface is the remaining access prerequisite; the public
visibility decision itself is already authorized. No personal workstation or
other repository is used as a workaround.

## Prepared protection policy

For `main`, require a PR and the actual applicable integration, container and
Terraform checks; prevent force pushes/deletion; require conversation resolution.
Require an independent reviewer only when a real eligible reviewer is available.
Never manufacture an approval or buy a plan to enable a setting without permission.
After applying settings through an authorized administration surface, read them
back and record what the account's available plan actually supports.

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
3. Integrate the locally qualified candidate without bypassing a required branch
   rule. Preserve all CI failures and keep unresolved integration gates explicit.
4. Apply the authorized visibility change, description/topics and available
   repository protections, then read back their actual state and verify anonymous
   access to the repository, licence and source.
5. Re-run GitHub checks after publication and inspect the resulting job steps,
   browser screenshots, container execution and Terraform output when runners
   become available. Do not assume that visibility alone resolves the rejection.
6. Identify any GitHub release as a prerelease and retain the remaining scope
   limits. A stable operational release requires its additional qualification.

No public business endpoint is created by changing repository visibility. A target
deployment remains a separately inspected operational action.

## Candidate reproduction

Use the locked installation and real demo commands in the README. Preserve the
generated `result.json`, control dossiers, exact source/model/parser hashes and
execution logs. The evidence index distinguishes original executions from later
publication mapping and CI results. Do not replace an adverse report with a
successful replay or backdate a commit into original metadata.
