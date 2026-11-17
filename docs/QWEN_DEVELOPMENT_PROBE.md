# Real Qwen 1.3 — bounded synthetic development diagnosis

This workflow conducts **real inference**, unlike the prior read-only
36-response forensic audit. It executes a strictly pinned GGUF model and CPU
llama.cpp build on 12 **fictional** PDFs produced by the separately implemented
Node writer. These 12 PDFs have already been used for source-level safety
testing and are therefore **development examples**, not a previously untouched
holdout, independently annotated real supplier sample or production dataset.

## How it works

The source-controlled workflow is at
[.github/workflows/qwen-development.yml](../.github/workflows/qwen-development.yml).

It installs pinned Python/uv and native parser prerequisites, creates exactly
six versioned-known-label and six unsupported-contract PDFs, downloads two
reviewed public source artifacts through the existing
scripts/provision_llm.py allowlist, and verifies both cryptographic hashes.
The local runtime runs the current Qwen3-0.6B / prompt
structured-extraction-1.3 policy with 4 CPU threads, 8,192 context,
90-second request timeout, 900-second server wall limit, 4 GiB address-space
limit and loopback-only networking. The job's total timeout is 25 minutes.
No cloud inference provider is allowed.

The original run produces a manifest, 12 scored PDF records, one raw response
trace per successful model request, source hashes, server runtime measurements,
resource timeline and full machine-readable synthetic evaluation summary.
The verifier correlates all returned records and traces to original PDF hashes.
It records separately:

- Raw model classification and independently verified classification counts.
- Eligibility for *later explicit human review* in known vs unsupported layouts.
- Incorrect eligibility, missing/failed requests and proof-validity denominators.
- Full synthetic policy result, but **never** full P04 acceptance.
- Prompt and GGUF source identity, with historical data left untouched.

The additional development runtime gate requires 12 authentic raw model traces,
12 scored and hash-matched documents, no inference/parser failures, no falsely
eligible documents, no unsupported-layout eligibility and no invalid emitted
citation or semantic evidence. A missing proof denominator is **null**, never
represented as 100 percent valid evidence. A 12/12 healthy runtime with zero
eligible documents is **not** a model-quality pass.

## Observed 17 November qualification — two actual executions

[PR #26](https://github.com/mehdisafer/document-control-intelligence/pull/26)
preview [GitHub Actions #44168516337](https://github.com/mehdisafer/document-control-intelligence/actions/runs/44168516337)
ran actual pinned Qwen inference from merge-preview commit `b2e7bcf`.
The preview, PR head `c87c097` and merged main `4b9f8b3` have the
identical tracked Git tree `b16507ba5016dd5e9553d0fd8bd4272b7f4b269d`.
Independently, [main workflow #44169464563](https://github.com/mehdisafer/document-control-intelligence/actions/runs/44169464563)
completed actual inference on that final merged source.

| Original observation | PR preview | Merged main |
|---|---:|---:|
| Real scored model responses/traces | 12/12 | 12/12 |
| Correct document classes | 7/12 | 7/12 |
| Eligible for later explicit human review | 4/12 | 4/12 |
| Eligible critical quality | 4/4 | 4/4 |
| Unsupported layouts falsely eligible | 0/6 | 0/6 |
| Parser/inference failures | 0 | 0 |
| Local runtime/safety gate | **PASS** | **PASS** |
| Independent synthetic development quality gate | **FAIL** | **FAIL** |
| Server full process wall time | 66.24 s | 69.17 s |
| Maximum observed server RSS | approx. 1,748 MiB | approx. 1,748 MiB |

Downloaded and independently ZIP-CRC-checked original artifacts:
[PR #14367385832](https://github.com/mehdisafer/document-control-intelligence/actions/runs/44168516337/artifacts/14367385832)
has **43 members**, SHA-256
`94ab771e7277cef5a6575f3355bbbd4eb81486635b398157dcb9b2131338f380`;
[main #14366358107](https://github.com/mehdisafer/document-control-intelligence/actions/runs/44169464563/artifacts/14366358107)
has **43 members**, SHA-256
`dfda3b1c40b9a89ae612ddb880da0499ecfc0094e8c44b3186f810310664dca3`.
Each archive retains twelve synthetic PDFs, twelve model raw-response traces,
twelve scored document outputs and source/runtime/resource receipts.

The original `qwen-dev-report.json` confirms **4/6** known-contract PDFs
eligible, **0/6** unsupported PDFs eligible and zero false eligibility.
All four purchase orders were assigned `unknown` (including two known
contracts). Both citation and semantic evidence-validity indicators
are 100% on their applicable measured denominators; they do not rescue
wrong document classes or missing eligible coverage.

The predeclared **50% synthetic eligible-coverage criterion is unmet**
at **4/12 = 33.3%**. There is no untouched supplier benchmark or
operator acceptance. The historical Qwen 3/36 result uses a different
cohort and must not be advertised as controlled before/after improvement.
[Exact merged-main full CI #44169464538](https://github.com/mehdisafer/document-control-intelligence/actions/runs/44169464538)
passed 171 Python, 24 JavaScript and 36 real Chrome checks, plus the
other two required jobs. CircleCI build-and-test succeeded on the same SHA.
No release tag, production service or model-quality gate was changed.

## Rejected real Qwen prompt 1.4 experiment

[PR #27](https://github.com/mehdisafer/document-control-intelligence/pull/27) changed only the model instruction for selecting the class from unique title signals. Its [actual 1.4 Qwen workflow](https://github.com/mehdisafer/document-control-intelligence/actions/runs/44170413325) completed with **12/12 real model traces**, zero inference errors, 0 false eligible and valid emitted citations. Yet on the **same PDF hashes as 1.3**, the model made **the exact same twelve class proposals**, scored **7/12 classifications, 4/12 eligible** (33.33% coverage: **FAIL** vs 50%), and both in-contract purchase orders remained `unknown`. Raw field selections for those two documents regressed from **eight candidate IDs per document in 1.3** to **eight nulls per document in 1.4**. Both original ZIP artifacts were hash- and CRC-checked. The experiment was **closed without merge**, leaving 1.3 as the current development protocol. This is development evidence only; see the [complete paired negative report](QWEN_PROMPT_14_EXPERIMENT.md).


## Reproducible original-artifact paired comparison — issue #30

The read-only [paired ZIP comparator](../scripts/compare_qwen_archives.py)
reconciles the **original downloaded GitHub Actions artifacts**, not CI badges.
It refuses unknown/duplicate/traversal ZIP entries, inflated ZIP members,
corrupted CRCs, changed PDF bytes, mismatched dataset manifests, missing
or duplicated scored cases, missing/altered raw model traces, swapped GGUF
hashes, incompatible prompts within one run, and field/aggregate totals
inconsistent with the manifest truth and recorded extraction. It reports
classification, review eligibility, required/critical abstentions, field
correctness, and raw per-field ID proposals **by original PDF SHA-256**.

For the two archived, distinct executions of the **same previously seen**
12-PDF development corpus, download GitHub's original ZIP files first:

- [Qwen 1.3 main original, artifact #14366358107](https://github.com/mehdisafer/document-control-intelligence/actions/runs/44169464563/artifacts/14366358107):
  ZIP SHA-256 `dfda3b1c40b9a89ae612ddb880da0499ecfc0094e8c44b3186f810310664dca3`
- [Rejected Qwen 1.4 original, artifact #14366438718](https://github.com/mehdisafer/document-control-intelligence/actions/runs/44170413325/artifacts/14366438718):
  ZIP SHA-256 `f1f5877785a773da5b034b4e9d1e9130c68703b5568f9af20931775a20038cd0`

The source-only command below **does not download artifacts or invoke a model**.
Use fresh local paths; never commit unredacted raw model requests or private
credentials:

```bash
python scripts/compare_qwen_archives.py \
  --baseline /private/archives/qwen-1.3-original.zip \
  --candidate /private/archives/qwen-1.4-original.zip \
  --baseline-sha256 dfda3b1c40b9a89ae612ddb880da0499ecfc0094e8c44b3186f810310664dca3 \
  --candidate-sha256 f1f5877785a773da5b034b4e9d1e9130c68703b5568f9af20931775a20038cd0 \
  --output evidence-local/qwen-1.3-vs-1.4-paired.json \
  --require-nonregression
```

The expected **exit code is 1** because nonregression is **FAILED**:
the original per-document evidence recomputes **90/156 -> 74/156**
correct fields and **60/120 -> 74/120** critical abstentions, despite the
unchanged **7/12** correct document classes and **4/12** eligible records.
Both purchase orders in the known-contract subset lost eight raw scalar-ID
proposals apiece; the system's independent verifier still prevented false
eligibility. A failed nonregression **still writes** a private, write-once
JSON comparison receipt with both original ZIP SHA-256s and per-case deltas.
Without `--require-nonregression`, the tool returns success for a
**valid provenance/measurement comparison**, NOT a passing model score.

The local code and tests must independently pass the exact PR-head and
postmerge CI before treating this as integrated. The original Qwen 1.2
36-document corpus is **not paired** against this reused 12-document corpus.
This comparison does not independently re-run OCR or supplier review, does
not establish prompt-change causality, and cannot close P04 model quality,
untouched supplier holdout or target-host operations.

## Execute and interpret

The GitHub workflow can run when its source changes, through an authorized
same-repository PR, when its contents change on main, or through a manual
workflow dispatch. It has read-only repository permissions and never uploads
the downloaded model weights or runtime binary. Artifacts contain only
fictional synthetic documents, raw model responses and derived receipts;
they are retained for 14 days.

Do not compare classification accuracy on this 12-PDF development sample
directly with the **historical 3/36 correct, 0/36 eligible** Qwen result on the
different original dataset. Also do not move v0.1.0rc1/v0.1.0rc2 release tags.
No real supplier-general performance, unseen supplier layouts, independently
reviewed business decisions or target-host deployment is proven by this run.

A later **fresh unused**, independently sourced and annotated supplier
holdout with a precommitted gate and no tuning on final data is necessary
before closing the P04 generative-model quality criterion.
