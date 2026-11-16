# Source publication, release provenance and owner-side controls

This handoff describes the current public GitHub source state and preserves the original UI procedure below as historical audit material. The maintainer operates repository Settings and Releases; the connected GitHub workflow performs readbacks, source/documentation PRs and CI verification only.

## Current source-release state — observed 17 November 2026

The repository is **Public**, with its original source under **Apache-2.0**, matching About description and ten topics. Both GitHub prereleases are published and marked **Pre-release**:

| Tag | Immutable source commit | Publication |
|---|---|---|
| [`v0.1.0rc1`](https://github.com/mehdisafer/document-control-intelligence/releases/tag/v0.1.0rc1) | `5c1f3e43f50c6d4056baabcafd5c39c40609f39b` | 15 November 2026 |
| [`v0.1.0rc2`](https://github.com/mehdisafer/document-control-intelligence/releases/tag/v0.1.0rc2) | `db42dd7c7668d70deb8cf5ea6512abcd94a36510` | 16 November 2026, 23:44:38 UTC |

[GitHub Actions run #43979529670](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43979529670) completed all three real jobs successfully at the **exact rc2 tag commit**. CircleCI `build-and-test` also succeeded. The original run included **139 Python, 24 JavaScript and 36/36 real Chrome checks**, plus an independent same-generator 36-PDF replay and the corrected 7/7 frozen-model local-linear demo. Older failed six-export and Qwen results remain historical evidence and unresolved wider acceptance boundaries; see [ACCEPTANCE.md](ACCEPTANCE.md).

## Remaining owner-side tasks — do not repeat publication

1. **Protect `main`** using [section 4](#4-protect-main-with-a-branch-ruleset) and re-read the actual saved **Active** ruleset. As of this read, GitHub returns `main.protected=false` and no active rulesets. Before requiring checks, confirm their exact emitted PR names and preserve an actionable single-maintainer review path.
2. **Correct the description of the existing `v0.1.0rc2` release**, not its tag. The GitHub Release body currently names the earlier `599bff76773f02d72ee1ded32a55c08631f52f7a` as final source, quotes the earlier **135** passing Python tests, and has duplicated Markdown link wrappers. Replace only the editable release description with verified facts from [RELEASE_NOTES_0.1.0rc2.md](RELEASE_NOTES_0.1.0rc2.md): tagged `db42dd7c`, **139/24/36** actual tests, corrected **7/7** and 36-PDF synthetic replay with separate limitations. Do not delete, move or republish either tag.
3. Independently verify signed-out rendering of both release URLs, README and evidence links when accessible. Authenticated GitHub API visibility is already confirmed; a separate signed-out current-release check is not inferred here.
4. Keep [issue #1](https://github.com/mehdisafer/document-control-intelligence/issues/1) open for Qwen model quality, independent supplier generalization and authorized target deployment/restore/operator acceptance. GitHub releases do not deploy a public purchasing API.

All instructions below describing the initial private/no-release state are dated historical preparation records, not outstanding tasks to replay.

## Observed starting state — 2026-11-15 (historical)

| Item | Observed state |
|---|---|
| Repository | Private |
| Default branch | `main` |
| Integrated candidate | [`84b06caf6452c746ef27a615575c2a0f4c7fd0c9`](https://github.com/mehdisafer/document-control-intelligence/commit/84b06caf6452c746ef27a615575c2a0f4c7fd0c9) |
| Project licence recognized by GitHub | Apache-2.0 |
| Repository description and topics | Empty |
| `main` protection | Not enabled |
| GitHub releases | None |

This is an observation, not a claim that the settings below have been applied.
The final documentation commit may advance `main`; use the final delivered head
when creating the release tag.

The connector exposes source, issue, PR and workflow operations, but no writer
for repository visibility, About metadata, rulesets or releases. A protection
read returns an integration-permission error. The private-repository ruleset
read says the feature becomes available by making the repository public or
upgrading the plan. The public route below does not require a plan upgrade.

## 1. Make the repository public

Open [repository settings](https://github.com/mehdisafer/document-control-intelligence/settings).
In **General**, find **Danger Zone**, then **Change repository visibility**.
Choose **Public**, confirm the repository identity and complete GitHub's
acknowledgement. Verify the Public badge and open the repository without a
signed-in session to check anonymous access to its source and licence.

GitHub's [visibility instructions](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility)
describe the confirmation sequence. Source, repository history and Actions
history/logs become publicly visible. The retained
[disclosure review](https://github.com/mehdisafer/document-control-intelligence/blob/3bf98d820e937706fb627a52ec8338a406bb0a6a/evidence/publication/review/review-8839be77.json)
records its exact scope and limitations; later preparation changes have their
own review and source mapping.

## 2. Set the About metadata

On the [repository home page](https://github.com/mehdisafer/document-control-intelligence),
use the gear beside **About**. Enter this description:

> Evidence-linked purchasing document control with local ML, PDF/OCR, three-way matching and audited human review.

Add these topics:

```text
document-ai
data-engineering
mlops
local-first
fastapi
ocr
document-processing
human-in-the-loop
data-quality
python
```

Save the changes and verify the visible description and topic chips.
GitHub documents the editor and topic constraints in
[Classifying your repository with topics](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics).

## 3. Execute the existing workflow on public main

Open **Actions**, select **Document control checks**, choose **Run workflow**,
select **main**, and run it. The workflow already declares `workflow_dispatch`
on the default branch. See GitHub's
[manual workflow instructions](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow).

Inspect these three jobs and their actual steps:

```text
smoke-and-integration
container-integration
terraform-schema
```

The first job includes the real browser harness; inspect the resulting report
and screenshots if it executes. The other jobs must show an actual container
build/demo and Terraform validation. A successful Dependabot check does not
replace them.

At the latest observation, [run 43602643545, attempt 2](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43602643545/attempts/2)
again ended before runner allocation: all three jobs have `runner_id: 0`, an
empty runner name and `steps: []`. The latest
[smoke-and-integration job](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43602643545/job/132935245932)
is `132935245932`. Log retrieval returned HTTP 404, and the connector cannot
retrieve the annotation endpoint. The rejection cause is **unknown**.

If the new public run still fails, open its latest failed job and read the exact
failure annotation in the GitHub interface. Preserve its text, run/attempt URL,
job ID and commit SHA before deciding what to change. A visibility change does
not establish that the prior rejection was a billing problem or has been fixed.

The configured `ubuntu-24.04` jobs use standard GitHub-hosted runners. Their
compute is free for public repositories; artifact/cache allowances are separate.
This follows GitHub's [Actions billing documentation](https://docs.github.com/en/billing/concepts/product-billing/github-actions).

## 4. Protect main with a branch ruleset

After making the repository public, open **Settings → Rules → Rulesets** and
choose **New ruleset → New branch ruleset**. Use the name `main-protection`,
set enforcement to **Active**, and target the exact branch pattern `main`.
Leave the bypass list empty.

GitHub Free supports branch rulesets for public repositories. Follow the
[ruleset creation instructions](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository)
and apply this policy:

| Setting | Value |
|---|---|
| Require a pull request before merging | Enabled |
| Required approvals | **0** while no other eligible reviewer is available |
| Require conversation resolution before merging | Enabled |
| Restrict deletions | Enabled |
| Block force pushes | Enabled |
| Require status checks | Enabled; add all three names listed above |
| Require branches to be up to date before merging | Enabled |
| Code-owner review and approval of the most recent push | Disabled for the current single-maintainer setup |
| Restrict updates | Disabled |
| Bypass list | Empty |

Finish adding each check to the requirement list. Select **GitHub Actions** as
the expected check source when offered. Click **Create**, then reopen the
ruleset to verify its active state, branch target and saved requirements.

Requiring a PR does not require an approving review. Zero required approvals
keeps the change record and CI gate usable by a single maintainer. Authors
cannot approve their own PRs; an assisted author review is not independent
approval. Add an approval requirement when a real eligible reviewer is
available. GitHub explains these distinctions in
[Available rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
and [Approving a PR](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews).

The separate update-restriction rule would permit updates only by bypass actors,
so it is not part of this policy. Once the ruleset is active, missing or failed
required checks block future merges. Keep the failure visible and resolve its
cause; creating the ruleset does not qualify an unexecuted workflow.

## 5. Completed: publish updated source prerelease (historical procedure)

This operation was **completed on 16 November 2026**. The existing [`v0.1.0rc2` GitHub prerelease](https://github.com/mehdisafer/document-control-intelligence/releases/tag/v0.1.0rc2) targets **`db42dd7c7668d70deb8cf5ea6512abcd94a36510`**. The old `v0.1.0rc1` tag remains fixed at `5c1f3e43f50c6d4056baabcafd5c39c40609f39b`. **Do not run the New Release procedure again** or move either tag to correct release-description text.

The only outstanding release-editor action is to open [the existing release](https://github.com/mehdisafer/document-control-intelligence/releases/tag/v0.1.0rc2), select **Edit**, correct its description using the exact tagged-source qualification in [RELEASE_NOTES_0.1.0rc2.md](RELEASE_NOTES_0.1.0rc2.md), and save. The published body previously displayed redundant bracketed Markdown link syntax; use one Markdown link per destination. Verify the final rendered body and tag SHA without changing the immutable tag.

## Record the resulting state

Retain the public repository URL, applied About metadata, verified tag commits,
exact-source hosted workflow links and both public release URLs. Record the
active ruleset URL **only after** it is created and checked; the current repo
has no active ruleset. The GitHub connector can re-read releases, tag objects,
workflow results and permitted ruleset metadata after the maintainer's actions.

Keep [issue #1](https://github.com/mehdisafer/document-control-intelligence/issues/1)
open for its unresolved criteria. Public availability and a prerelease label do not close model-quality or
intended-host deployment gates. The bounded synthetic browser, container
and Terraform-schema checks have since passed on the later source, as
recorded in [ACCEPTANCE.md](ACCEPTANCE.md). No business service endpoint is deployed by these steps.
