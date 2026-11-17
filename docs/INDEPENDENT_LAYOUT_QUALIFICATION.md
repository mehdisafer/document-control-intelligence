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

**Safety gate** (this bounded synthetic experiment only): complete 12/12 evaluations with no failures, no incorrectly eligible documents, full validity of any emitted citations/semantic evidence and **zero eligibility** for all six intentionally unsupported-contract documents. An absent denominator is reported as such; it does not assert perfect quality.

Coverage and classification accuracy are **observed outputs**, not automatically promoted to PASS. The pre-existing 36-PDF policy gate is independently reported and remains a different population. No metric reported here retroactively fixes historical six-export failures or the unqualified 3/36 Qwen result.

## Evidence and decisions

GitHub Actions executes this additional step on every PR/main run and retains `independent-layout-corpus/manifest.json`, the twelve PDFs, the scored `evaluation/summary.json` and `report.json`. Observe actual CI and artefacts before marking the new safety gate passed. Even a successful run **cannot** establish real-supplier independent generalization or authorized target-host operations.

The sample is not Qwen training or a generative model evaluation. It does not authorize fallback, deployment or autonomous publication. Source prerelease `v0.1.0rc2` remains immutable at `db42dd7c`; this is subsequent code and will require a separate release candidate if adopted.
