# Publish the source candidate

This is a maintainer handoff for the GitHub interface. Public-source publication
of `mehdisafer/document-control-intelligence` is already authorized. The
maintainer performs the interface actions below; repository preparation and
readback use the GitHub connector. The assistant does not operate a browser or
access an account session for this handoff.

Publishing the repository and a source prerelease is separate from qualifying a
business service deployment. Browser, container, Terraform and intended-host
gates remain tracked in [issue #1](https://github.com/mehdisafer/document-control-intelligence/issues/1).

## Current release-scope note — 15 November 2026

The earlier private/unlicensed/no-runner snapshot below is retained as
**historical**. The GitHub API now reports this repository **public**, with
Apache-2.0 and a published source prerelease `v0.1.0rc1`. The original-preview correction has been merged into `main` through PR #10
at `24cad9d17b400fca01ae901d97082ebbd45bc59c` and its post-merge three-job workflow succeeded. Branch
protection and a new version tag are separate owner-side release controls.
The tested visual raster fix at `32fb196bcc496b31071d87d02453dd6936b98ccf` has its
[source-bound record](ORIGINAL_PAGE_PREVIEW.md); the old tag is immutable.

## Remaining owner-side tasks — 16 November 2026

GitHub metadata and the public `v0.1.0rc1` source release are already applied.
**Do not repeat** the visibility change or recreate/repoint the old tag.
The [full post-merge run](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43774277074)
succeeded, with additional [visual preview proof](ORIGINAL_PAGE_PREVIEW.md).
Only these release-administration steps remain:

1. Create and inspect the **Active** `main-protection` branch ruleset from
   [section 4](#4-protect-main-with-a-branch-ruleset), including the three
   actual check names, and reopen it to verify the saved settings. On the
   16 November API read, `main.protected=false` and the ruleset list was empty.
2. For the updated source, create a **new**, explicitly marked prerelease
   `v0.1.0rc2` using [prepared notes](RELEASE_NOTES_0.1.0rc2.md) and the
   final reviewed `main` commit. Verify the tag object and release status.
   The GitHub connector cannot perform repository administration/release
   creation; these remain maintainer UI actions.
3. Keep the broader P04 [acceptance issue](https://github.com/mehdisafer/document-control-intelligence/issues/1)
   open until the model-quality and operating-host criteria are resolved.
   Public source code is **not** a publicly deployed purchasing API.

All steps below describing the initial private/no-release state are retained
as **historical publication instructions** for audit, not as actions to redo.

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

## 5. Publish the updated source prerelease (after final CI)

Open [the new release form](https://github.com/mehdisafer/document-control-intelligence/releases/new).
Use:

| Field | Value |
|---|---|
| Tag | `v0.1.0rc2` (new tag; never move `v0.1.0rc1`) |
| Target | Exact final reviewed `main` SHA **after** CI |
| Release title | `Document Control Intelligence 0.1.0rc2` |
| Release description | The body in [RELEASE_NOTES_0.1.0rc2.md](RELEASE_NOTES_0.1.0rc2.md) |
| This is a pre-release | Selected |

Create the **new** `v0.1.0rc2` tag only after the final CI and integrated
package/health/Compose version checks have succeeded. If that tag already
exists, inspect it and stop rather than re-pointing it. Publish the prerelease
only after confirming its commit matches the final reviewed `main` SHA;
verify the release page and source archive without an authenticated session.
The historical `v0.1.0rc1` remains immutable. These instructions do not
claim that the new release has been published.

If fresh hosted checks execute before publication, add their specific outcomes
and evidence links to the release notes while retaining the earlier reports
and their source attribution.

GitHub's [release instructions](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)
cover tag selection, target selection and the prerelease option.

## Record the resulting state

Retain the public repository URL, saved About metadata, active ruleset URL,
latest workflow URL/results, release URL and tag commit. The connector can read
back repository metadata, rulesets where accessible, workflow results and
releases after the maintainer's actions.

Keep [issue #1](https://github.com/mehdisafer/document-control-intelligence/issues/1)
open for its unresolved criteria. Public availability and a prerelease label do not close model-quality or
intended-host deployment gates. The bounded synthetic browser, container
and Terraform-schema checks have since passed on the later source, as
recorded in [ACCEPTANCE.md](ACCEPTANCE.md). No business service endpoint is deployed by these steps.
