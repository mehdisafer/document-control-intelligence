# Independent-renderer synthetic purchasing PDF safety qualification

This **post-`v0.1.0rc2` experiment** creates a genuinely different *PDF-generating implementation*, not independently sourced real supplier documents. It does **not** satisfy the full P04 independent-supplier generalization or production acceptance gate.

## Controlled inputs and boundaries

- `scripts/generate_independent_layouts.mjs` is a standalone **Node.js standard-library PDF writer**. It does not import or call the application's ReportLab corpus generator, train the statistical model, access supplier/customer data, fetch the network or use external services.
- Exactly **12 new fictional PDFs** represent four families, each with a purchase order, delivery note and invoice. Six use the **versioned known-label contract** in an independently rendered layout. Six deliberately use **unsupported aliases and geometric/no-pipe tables**, to verify safe review/abstention rather than invent extraction mappings.
- A malicious printed URL note and an untrusted instruction line are included. The generator records truth in a manifest independent from the runtime parser; every PDF has its own SHA-256.
- The experiment does not exercise OCR scans, unknown languages, real invoices, handwritten attachments, sophisticated table OCR, signed PDF authenticity or independent annotations. Its documents should never be described as sampled from suppliers.

## Reproduce on supported Linux CI

```bash
node scripts/generate_independent_layouts.mjs outputs/independent-node-corpus
uv run --frozen python scripts/qualify_independent_layouts.py \
  --manifest outputs/independent-node-corpus/manifest.json \
  --output outputs/independent-node-evaluation
```

The generator refuses to overwrite its target; the evaluator also refuses a nonempty output directory. Use a distinct destination for every run and retain both manifests and original PDFs.

The evaluator uses the real sandboxed PDF parser, original frozen model with SHA-256 `234c94149697cbeda761c22cae9c27aa0f57a8215422da906b32a6bc07148ff1`, independent evidence validator and business rules. It tests both `baseline` and `local-linear` profiles. It explicitly counts classification errors, eligible documents, wrong eligibility, parser/inference failures, source-citation validity and semantic support.

**Safety gate** (this bounded synthetic experiment only): complete 12/12 evaluations with no failures, **6/6 known-contract eligible** (so all-abstain cannot pass), **0/6 unsupported-contract eligible**, all 12 classes correct, zero false eligibility, 100% cited and semantically supported emitted evidence, and 100% critical quality among the eligible. A missing denominator is a failure, never a perfect score. Seven negative-path unit tests protect the gate logic.

Coverage and classification accuracy are **observed outputs**, not automatically promoted to PASS. The pre-existing 36-PDF policy gate is independently reported and remains a different population. No metric reported here retroactively fixes historical six-export failures or the unqualified 3/36 Qwen result.

## Evidence and decisions

GitHub Actions executes this additional step on every PR/main run and retains `independent-layout-corpus/manifest.json`, the twelve PDFs, the scored `evaluation/summary.json` and `report.json`. Observe actual CI and artefacts before marking the new safety gate passed. Even a successful run **cannot** establish real-supplier independent generalization or authorized target-host operations.

The sample is not Qwen training or a generative model evaluation. It does not authorize fallback, deployment or autonomous publication. Source prerelease `v0.1.0rc2` remains immutable at `db42dd7c`; this is subsequent code and will require a separate release candidate if adopted.

## Executed qualification — 17 November 2026, exact PR source

[GitHub Actions push run #43990896317](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43990896317) and the separate PR check run [#43990931615](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43990931615) completed all **three actual jobs successfully** on source `b92fcc9d972d4fcb58dab770de74a97b86f4d1cf`. CircleCI's source-level `build-and-test` status is separately checked before merge.

The [downloaded original artifact #14287562182](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43990896317/artifacts/14287562182) passed ZIP CRC/integrity checking: **42 retained files**, **12 PDF SHA-256 matches**, manifest digest `ab3e9904e6b0c8a8c2fe2ed5e022038c7eafe2a28c93502c0c7f4a71cd44b365`. The same manifest SHA-256 was emitted independently on PC-MEHDI by the Node writer and on the hosted Linux runner. Original PDFs were render-inspected: text, labels and alternate geometric table layout are visibly present, not placeholder objects.

| Metric | Baseline | Frozen local-linear |
|---|---:|---:|
| Parsed/evaluated PDFs | 12/12 | 12/12 |
| Correct document-type classifications | 12/12 | 12/12 |
| Known-contract cases eligible for explicit human review | 6/6 | 6/6 |
| Unsupported-label/geometric-table cases eligible | **0/6** | **0/6** |
| Incorrectly eligible documents | **0/12** | **0/12** |
| Source-citation validity | **100%** | **100%** |
| Semantic evidence validity | **100%** | **100%** |
| Parser/inference errors | 0 | 0 |
| **Defined bounded safety gate** | **Met** | **Met** |

Eligibility coverage is **6/12 (50%) by construction of the balanced fixture**; eligible critical quality is 6/6. The generic synthetic benchmark policy happens to report `policy_gate_met=true` for both profiles, but that **does not** promote a 12-PDF internally authored sample into supplier-general acceptance. The six unsupported examples abstain safely even though their document *titles* are recognized. **Classification 12/12 is not extraction accuracy 12/12 on out-of-contract labels.**

The same push CI recorded **139 Python tests, 24 JavaScript tests and a passed 36-check Chrome browser report**, in addition to the Docker/Compose and Terraform jobs. The frozen statistical model SHA remained `234c94149697cbeda761c22cae9c27aa0f57a8215422da906b32a6bc07148ff1`. This run is **post-rc2 candidate source**, not the original published rc2 tag.

**Accepted only within its measured scope:** standalone independent-*renderer* synthetic known-contract extraction and negative out-of-contract abstention. **Still open:** independent real-supplier acquisition/annotations, advanced table geometry, independent OCR, generative Qwen (historical 3/36 correct, 0 eligible), named Linux deployment target and production/operator acceptance. No change to original failed 6/7 source run.
