# Release candidate 0.1.0rc1

## Purpose

This candidate delivers an executable synthetic purchasing workflow: PDF receipt,
native/OCR extraction, local models, verifiable source evidence, deterministic
controls, cumulative matching, human review, acceptance, publication and export.
It also supplies persistent queue/recovery behavior, restoration evidence,
container/Terraform references and an explicit acceptance matrix.

The trained statistical model meets the declared final synthetic quality/coverage
gate. The generative Qwen profile remains experimental. The release is not tagged
as a stable deployment or published publicly while acceptance decisions remain
open. Source and evidence changes are reviewed together in
[PR #2](https://github.com/mehdisafer/document-control-intelligence/pull/2).
Author-side assisted review is identified as such; it is not an independent approval.

The implementation source is commit
[`3ff93109f3ea0d9c5f4bdfd598dd35bbd4513439`](https://github.com/mehdisafer/document-control-intelligence/commit/3ff93109f3ea0d9c5f4bdfd598dd35bbd4513439).
The following evidence/documentation commit, `8dbe831a243e66aad18c601086a8e62b3c496322`,
does not alter runtime code, contracts, tests, lockfiles or infrastructure. Its [publication map](../evidence/publication-map.json)
checks those bytes against the executed source and preserves the identity of
earlier runs. The [qualification record](../evidence/qualification/) contains
107 passing tests, the failed raw-linear demo assertion, separate human recovery,
72-output semantic regression, small load execution and real HTTP proof.

## Prepared repository metadata

Description:

> Evidence-linked purchasing document control with local ML, PDF/OCR, three-way matching and audited human review.

Topics: `document-ai`, `data-engineering`, `mlops`, `local-first`, `fastapi`, `ocr`,
`document-processing`, `human-in-the-loop`, `data-quality`, `python`.

The available GitHub connector exposes source/issue/PR operations but no repository
metadata or protection writer. These values are prepared, not asserted to have
been applied. The isolated-browser fallback is not authenticated to this private
repository. Do not use a personal workstation or another repository as a workaround.

## Prepared protection policy

For `main`, require a PR and the actual applicable integration, container and
Terraform checks; prevent force pushes/deletion; require conversation resolution.
Require an independent reviewer only when a real eligible reviewer is available.
Never manufacture an approval or buy a plan to enable a setting without permission.
After applying settings through an authorized administration surface, read them
back and record what the account's available plan actually supports.

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

Before a separately authorized public release:

1. Verify the Apache-2.0 licence/notice distribution and obtain authorization for
   the intended repository visibility.
2. Review the final source tree and Git history, issue/PR text, logs, exported
   dossiers and artifacts for secrets or client/personal data.
3. Confirm required checks for the delivered code revision and inspect actual
   browser screenshots, source-linked demo exports and restore evidence.
4. Record accepted limitations and unresolved gates in the release notes.
5. Apply the authorized visibility change and verify anonymous repository access.

No public business endpoint is created by changing repository visibility. A target
deployment remains a separately inspected operational action.

## Candidate reproduction

Use the locked installation and real demo commands in the README. Preserve the
generated `result.json`, control dossiers, exact source/model/parser hashes and
execution logs. The evidence index distinguishes original executions from later
publication mapping and CI results. Do not replace an adverse report with a
successful replay or backdate a commit into original metadata.
