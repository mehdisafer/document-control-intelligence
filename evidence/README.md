# Execution evidence

This directory contains selected original qualification artifacts and a publication
map to the delivered source. The complete application generates its own evidence:
the demo parses actual PDFs, runs the selected local model, records human decisions,
exports dossiers and compares them after a real restore.

Evidence is divided by execution. Adverse model runs, local environment blockers
and original denominators are retained. A runtime failure is not converted into a
successful abstention. No screenshots are created when the browser cannot run.

Raw credentials, authentication configurations, live databases and personal/client
documents are excluded. Published document examples are synthetic. Historical
reports with `git_commit: null` retain that value and their original source hashes;
a subsequent mapping identifies the commit with those bytes without pretending
that the commit existed at execution time.

See [evaluation](../docs/EVALUATION.md) for metric definitions and limitations,
[acceptance](../docs/ACCEPTANCE.md) for separate implementation/execution gates,
and the PR for the final source and actual CI links. A hash establishes content
agreement, not an independent audit or certification.

## Read the evidence

| Record | What it establishes |
|---|---|
| [Published rc2 source and actual Actions run](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43979529670) / [original ZIP artifact](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43979529670/artifacts/14281402594) | **Tag `v0.1.0rc2` at `db42dd7c`**: all three hosted jobs PASS, 139 Python + 24 JavaScript + 36/36 real Chrome; same-generator frozen local-linear 7/7 explicitly published and restored, 36-PDF full synthetic replay 34/36 classification, 30/36 eligible, 30/30 eligible critical quality, zero false eligible. Downloaded ZIP integrity tested; no independent supplier/production acceptance claimed |
| [Publication map](publication-map.json) | At evidence commit `8dbe831`, the recorded runtime/configuration/test bytes match executed source `3ff93109`; earlier snapshots retain their actual identities |
| [Public-source qualification](publication/) | On fixed source `8839be77`: 112 Python tests, 23 JavaScript state/unit tests, complete ZIP-budget and asynchronous UI regressions, dependency and disclosure review; not browser-rendering evidence |
| [Historical source qualification](qualification/) | On source `3ff93109`: 107 tests, original baseline/linear demos, restoration, supplemental human repair, 72-output regression and one/two-worker load |
| [Real HTTP report](qualification/http/run-3ff93109/report.json) | 36 checks across 30 loopback requests, separate model worker, role denials, source/ZIP equality, publication idempotency and trace joins |
| [Frozen model evaluation](evaluation/) | Disjoint synthetic splits, trained safe-JSON model, all three Qwen attempts, raw responses, source snapshots and original denominators |
| [Dependency audit](platform/dependency-audit.json) and [component inventory](platform/component-inventory.json) | Point-in-time checks of 32 installed Python runtime packages; not a native-image or legal certification |
| [Apache-2.0 packaging check](platform/apache-2.0-packaging.json) | Later licence adoption: unchanged dependency lock, explicit SPDX metadata and identical LICENSE/NOTICE bytes in the wheel and source distribution; not an application or container requalification |
| [GitHub Actions observation](platform/github-actions-blocked.json) | Three jobs failed with no runner and no steps; underlying reason remains unknown |
| [Browser blocker](platform/browser-runtime-blocked.json) and [Terraform blocker](platform/terraform-validate-blocked.json) | Browser reports an AF_UNIX denial; Terraform fails provider schema loading with cause unconfirmed in its retained diagnostic; neither path is qualified |

The **historical** local aggregate is **false** because the original frozen local-linear demo published six dossiers against a target of seven. Baseline published seven. A separate attributed human correction obtained seven but did not alter that model result. The later, **tagged `v0.1.0rc2` source-label guard** produced 7/7 explicit test-role publications and restored exports without retraining, and a full 36-document same-generator synthetic replay met its declared quality/coverage gate. Neither successful run overwrites the historical failure or qualifies Qwen and independent supplier documents.

## Preservation and reproduction

Apache-2.0 adoption on 2026-11-14 subsequently updates package licence metadata
and Docker licence-file inputs. That change does not rewrite this publication map,
the exact-source HTTP harness or any original execution result. That licensing
commit leaves application code and the dependency lock unchanged. The subsequent
UI/export fixes have their own [publication qualification](publication/); they do
not inherit or rewrite the old HTTP/model reports. See
[qualification reproduction](qualification/README.md) for the original source.

[Evaluation index](evaluation/index.json) and [qualification index](qualification/index.json)
record copied-file and archive-member SHA-256 values. The HTTP run has its own
[artifact manifest](qualification/http/run-3ff93109/artifacts.json). Archives
contain original synthetic inputs and outputs; large model/runtime binaries,
authentication files and live databases are excluded.

Use the reproduction commands in each section with **new output directories**.
Historical orchestration scripts are retained to explain their original commands
and paths, not to overwrite the committed proof. Training a fresh artifact,
changing a prompt or altering thresholds creates a new evaluation recipe; it
does not inherit the frozen model's result.
