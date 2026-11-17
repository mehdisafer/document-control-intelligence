# Post-v0.1.0rc2 source qualification — 17 November 2026

## Source identity and evidence

The **published source prerelease** v0.1.0rc2 remains at immutable git tag
`db42dd7c7668d70deb8cf5ea6512abcd94a36510`. Its original tested source,
release notes, original 139-test evidence and historical failed reports are
preserved. This document describes later **development main**, which is NOT
part of the already-published prerelease.

[Current post-rc2 main source](https://github.com/mehdisafer/document-control-intelligence/commit/b78104439c6614fbb8d3f2ab97e0899e4db047f6):
`b78104439c6614fbb8d3f2ab97e0899e4db047f6`, which includes merged [PR #22](https://github.com/mehdisafer/document-control-intelligence/pull/22) (new
independently generated synthetic safety fixture), merged
[PR #23](https://github.com/mehdisafer/document-control-intelligence/pull/23) (immutable original Qwen trace diagnosis)
and merged [PR #24](https://github.com/mehdisafer/document-control-intelligence/pull/24) (per-field Qwen semantic
candidate restriction).

The exact-source [GitHub Actions run #44165434992](https://github.com/mehdisafer/document-control-intelligence/actions/runs/44165434992) has **all three real
jobs success** (`smoke-and-integration`, `container-integration`,
`terraform-schema`). CircleCI `ci/circleci: build-and-test` also reports
**success** at the same source SHA.

The [original hosted source artifact #14364034272](https://github.com/mehdisafer/document-control-intelligence/actions/runs/44165434992/artifacts/14364034272) was downloaded
and verified: **43 members**, complete ZIP CRC check, SHA-256
`f3f0814c65781c7d8193bc46ba09b0e492b232bd4510cf7953d2977f57f92520`.
The retained logs/reports show **162 Python tests passed**, **24/24 JavaScript
tests** and **36/36 genuine Chrome browser checks passed**. The same run
rechecked strict seven-export local-linear demonstration, frozen 36-PDF
synthetic regression, independent Node-generated 12-PDF safety holdout,
offline Qwen forensic audit, reference container/Compose and Terraform schema.

## Scope-specific quality and acceptance matrix

| Gate / observation | Verified result | Acceptance boundary |
|---|---|---|
| Deterministic + frozen statistical reference | Original same-generator 36-PDF: **34/36** correct document classification for frozen local-linear, **30/36 eligible**, **30/30 eligible critical quality**, zero false eligibility; strict local-linear nine-scenario demo **7/7** restored exports | **Accepted only** as bounded original-generator synthetic reference; separate earlier 6/7 failure retained |
| Independently *rendered* synthetic layouts | 12 Node-authored PDF inputs; both baseline and frozen local-linear **6/6 known-label candidates eligible, 0/6 deliberately unsupported-label documents eligible**, 0 false eligibility, 100% source-citation and semantic validity | Narrow synthetic semantic abstention gate accepted; **not supplier population generalization** |
| Immutable original Qwen forensic audit | **406/406** original archived members hashed; **36/36** original raw/proposal/scored/parsed identities correlated; Qwen **3/36 correct, 0/36 eligible**, 30 unknown model proposals, 35/272 semantically wrong known-label candidate selections | Diagnostic provenance **accepted**, Qwen model quality **FAILED historically** |
| Per-field Qwen candidate schema restriction | PR #24 requires independently recognized printed source labels for a candidate ID to be selectable for each field; refuses unsupported URL labels; preserves genuine conflicting labels and explicit abstention; **eight new negative/positive tests passed** plus fixed legacy test | **Implementation and CI tests accepted**, but no *new Qwen inference*, no measured Qwen classification/coverage uplift; proposed Qwen prompt version is now 1.3 |
| Real suppliers, nonstandard invoices, third-party annotations, independent OCR acquisition | No independent acquired/annotated supplier benchmark, no claims on credit notes, returns, FX, repeated-SKU semantics or adversarial native-text authenticity | **OPEN** |
| Real target host, secrets, network, image/SBOM, load, backup/restore, monitoring and operator sign-off | Hosted CI container/restore and Terraform schema exercised only; **no explicitly authorized target host** | **OPEN** |
| Public GitHub administration | Repository public with Apache-2.0 and published prereleases; current `main.protected=false` and no rulesets; four nested Markdown links remain in existing rc2 release body | Owner-side branch ruleset and release-link formatting **OPEN** |

No model, CI, synthetic test or open-source publication authorizes autonomous
payment, customer document ingestion, or a production business service.
Scripted actor acceptance in demos is not independent operator approval.

## Next verifiable experiments (not executed)

- **Generative quality:** run the new source-constrained Qwen protocol 1.3
  under the pinned loopback model/runtime with real inference on a **development
  corpus**, then measure on a **fresh precommitted unused holdout**. Require
  actual classifications, supported evidence, critical accuracy, positive
  eligibility coverage, no false eligibility, resource limits, raw traces and
  reproducibility. Historical 36 original final PDFs **must not be silently
  repurposed** as a fresh unseen test split after failure analysis.
- **Supplier generalization:** obtain lawfully distributable, independently
  acquired/annotated supplier examples with distinct layouts and concrete
  purchasing contracts. Measure rejection and review correctly where
  unsupported, rather than expanding assumptions or inventing fields.
- **Operations:** choose and explicitly authorize a real Linux target and
  operator before trying host-level deploy, recovery and security acceptance.
- **Owner UI:** create and read back an Active `main-protection` ruleset and
  correct only the four malformed links in the existing rc2 release body.
  Neither action should move the released tags.

References: [acceptance matrix](ACCEPTANCE.md),
[Qwen source restriction](QWEN_SEMANTIC_GUARD.md),
[forensic original model evidence](QWEN_TRACE_FORENSICS.md),
[independent synthetic safety fixture](INDEPENDENT_LAYOUT_QUALIFICATION.md),
[operational instructions](OPERATIONS.md) and [publishing controls](PUBLISHING.md).
