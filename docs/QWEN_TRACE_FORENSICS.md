# Historical Qwen 36-document forensic audit

## Verified execution — 17 November 2026

The [original PR #23 hosted run](https://github.com/mehdisafer/document-control-intelligence/actions/runs/44161099199) completed all three actual GitHub Actions jobs successfully. Its [downloaded JSON artifact](https://github.com/mehdisafer/document-control-intelligence/actions/runs/44161099199/artifacts/14363287699) passed ZIP CRC verification (**43 files**, archive SHA-256 `342928513bb9308bd4d5d839180b6b9a42379e46f884ee629bea942c1ee3b155`). The aggregated audit was inspected directly from the original archive, not just from CI status text.

The source evidence is `evidence/evaluation/raw-executions.tar.gz`, SHA-256 `6e0d417bc4244fd42486815ec3bcee34f147e8637567edf484482a67358e8817`. All **406** indexed archive entries were checked against their original individual SHA-256 and sizes. Exactly **36 unique raw Qwen response traces**, **36 scored evaluations** and **36 original parsed PDFs** were matched by input SHA-256, with no missing or duplicated documents. The source-version label and title maps were read as Python AST literals from the archived source, without executing archived code.

This is **offline forensic analysis** of the historical source commit `88ab43eeb7d27112cfc75aa450fb1f21a268f732`; it performed **zero new model inference requests**, changed **zero model weights/prompts**, and did not rewrite any historical report.

## Observed model proposals versus verified outputs

| Metric | Observed result |
|---|---:|
| Original bounded Qwen requests / failures | 36 / 0 |
| **Original correct classifications** | **3/36 (8.33%)** |
| **Original eligible documents** | **0/36** |
| Raw Qwen `unknown` proposals | 30/36 |
| Raw Qwen `invoice` proposals | 5/36 |
| Raw Qwen `purchase_order` proposals | 1/36 |
| Parsed PDF titles with exactly one versioned recognized class | 20/36 |
| Titles recognized correctly but raw Qwen answered `unknown` | **14 documents** |
| Non-`unknown` model proposals conservatively downgraded to `unknown` | **3 documents** |
| Proposed candidate IDs for scalar fields | 272 |
| Proposed IDs correctly aligned to versioned field labels | 237/272 |
| **Proposed IDs assigned to a different recognized field label** | **35/272** |
| Null scalar candidate assignments | 16 |
| Final source citations / semantic validity | 100% / 100% (historical aggregate) |

The raw confusion matrix, grouped by actual document type:

| Actual type | Proposed invoice | Proposed purchase order | Proposed unknown |
|---|---:|---:|---:|
| Delivery note (12) | 0 | 0 | 12 |
| Invoice (12) | 3 | 1 | 8 |
| Purchase order (12) | 2 | 0 | 10 |

The final independent title verifier left only three invoices correctly classified; the other classes remained unknown. The original recorded warnings include **33** unsupported title/classification warnings, **20** evidence-validation warnings and **2** detections of untrusted printed instructions. These are counts of warnings, not necessarily distinct documents.

The model's source candidate selection has a second, independent failure: **35 selections misassigned a recognized business label**. It is not sufficient to improve classification alone. The independent evidence validator rejected unsupported semantic assignments; it must not be weakened to raise apparent coverage.

## Reproduction and tests

On the pinned repository/CI Linux environment:

```bash
uv run --frozen python scripts/audit_qwen_archive.py \
  --output outputs/qwen-historical-forensic-report.json
```

The audit refuses to overwrite an output, verifies the complete immutable index, never extracts arbitrary archive members to disk, and emits aggregate metrics only (no source document values or original model response bodies). Eight regression tests exercise archive tampering, invalid member digests, unsafe paths, exact-title semantics and raw-versus-verified distinctions. The current GitHub Actions workflow runs this audit on PRs and `main`, retaining the JSON report as an artifact.

## Decision boundary and next experimental work

**The Qwen model-quality gate is still OPEN.** This diagnosis is an auditable failure analysis, not proof of remediation. A title-supported counterfactual would be a **new decision policy**, not a silently improved Qwen score; it needs its own development set, explicit scope, adverse tests and a new untouched holdout. Likewise, 237 aligned proposals do not establish document-level critical-field acceptance.

Before another acceptance decision, use development-only examples to investigate prompt/model choices and classify source-label errors, retain a fresh unseen evaluation set, execute actual bounded Qwen inference, and enforce the predeclared quality/coverage thresholds with zero false eligibility. Neither the earlier 36-document evaluation nor the independent Node 12-PDF synthetic probe qualifies real supplier distribution, and no target machine has been authorized for a production deployment. Source prereleases `v0.1.0rc1` and `v0.1.0rc2` remain immutable.
