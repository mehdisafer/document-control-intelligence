# Prioritized backlog and current limits

## P0 — Close candidate evidence and release decisions

- Keep generative classification unqualified unless an independently evaluated
  quality/coverage gate is met on an untouched holdout. Original Qwen failures
  and all 36-request completion records remain available.
- Resolve the frozen local-linear run's original six-versus-seven automatic
  export criterion, or explicitly accept a narrower reference profile without
  rewriting its recorded failure. Its human-repaired run is a different result.
- Integrate the [isolated original-page preview fix](https://github.com/mehdisafer/document-control-intelligence/issues/11)
  through reviewed PRs and re-run the full CI on the integrated `main` source.
  [GitHub Actions run 43770874796](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43770874796)
  qualified 126 Python, 25 JavaScript and 35 real browser checks on preview-fix
  source `948d82ba`, with visibly decoded pages. Earlier blank PDF viewer
  screenshots remain genuine historical evidence.
- Reconcile the [CircleCI reference pipeline](https://app.circleci.com/pipelines/circleci/Um5XQQtD4BE9Jcfy4XTzBb/7UEpXuXKNt1osYC3PaUwEV)
  after integration, preserving failed older heads and verifying the actual new
  source ref. A green GitHub Actions run is not a CircleCI run.
- Activate and read back the `main` branch ruleset via authenticated GitHub
  repository administration. GitHub public visibility, description/topics,
  Apache-2.0 licence and the original `v0.1.0rc1` prerelease are already
  verified. The source-publication task does not deploy a public business service.
- Agree an intended deployment host, inspect its concrete plan, exercise service,
  restoration and monitoring with explicit authorization, and obtain operator
  acceptance. CI workers are not a production deployment.
- Qualify five open Dependabot upgrades separately. In
  [PR #5](https://github.com/mehdisafer/document-control-intelligence/pull/5),
  regenerate `requirements.lock` from the changed `uv.lock` before trusting the
  dependency-audit input. Current-main test results do not transfer to these PRs.

## P1 — Extend useful purchasing coverage

- Resolve the frozen local-linear label model's injection-footer confusion using
  a separately designed training/tuning set and a new holdout. It currently treats
  an unrelated URL-footer line as a second subtotal candidate and safely abstains.
  The original six-export demo, its failed seven-export assertion and a separate
  attributed human repair yielding seven restored exports are retained.
- Add a new independent holdout with unseen field labels, table geometry and scan
  acquisition before improving classification or extraction further.
- Replace the first contract's pipe-delimited table assumption with independently
  evaluated geometric table extraction. Publish abstention/coverage together.
- Define credit-note/return signs, discounts/freight, FX sources, multiple orders
  and explicit line identities for repeated SKUs before accepting those cases.
- Assess visual/text-layer discrepancies on pure-native PDFs and keep document
  authenticity separate from extraction evidence.
- Add enterprise identity federation, scoped access to dossiers and tested session
  lifecycle before a broader organization deployment.

## P2 — Grow operations from measured demand

- Exercise a longer workload on the intended host with agreed document size and
  OCR proportions. Measure host quotas, disk pressure and recovery under load.
- Introduce multi-host state/queue infrastructure only when measured capacity or
  availability needs justify it. Re-prove publication/version invariants.
- Agree retention, archival and legal-hold rules before implementing deletion.
  The current retention setting is a policy signal, not an automatic purge.
- Produce a native-image SBOM and preserve build provenance/digests for a deployed
  image. Python inventory and known-vulnerability checks cover a narrower scope.

These items are visible scope limits. They are not hidden behind a generic
"production-ready" label or represented by unexecuted integrations.

## Completed candidate evidence

The [evidence index](../evidence/) links historical source hashes, real
PDF/OCR demos, original model failures, seven baseline exports, the separate
human-repaired run, tested restoration, 72 identical semantic regression
outputs, worker load, and real HTTP/separate-worker execution. Historical
results are never rewritten when later fixes pass.

Public candidate source `8839be77` ran 112 Python and 23 JavaScript
state tests. Subsequent hosted `c451deba` ran 122 Python, 23 JavaScript and
33 real-browser checks, and exposed a blank original-PDF native iframe despite
correct blob bytes. The latest preview-fix source `948d82ba` ran **126 Python,
25 JavaScript and 35 real-browser checks** without failures or skips, along
with a successful container integration and Terraform schema validation.
Desktop/mobile captures show a genuine rasterized source page. Exact
run/artifact links, hashes and limits are in [ACCEPTANCE.md](ACCEPTANCE.md).

The corrections also fence late document/PDF/audit responses, require
revision-safe dialogs, bound complete ZIP exports, preserve strict CSP, and
render original pages only through a resource-bounded, network-denied child.
Security and model-quality limits above remain in force; a successful isolated
reference is not proof of production readiness.
