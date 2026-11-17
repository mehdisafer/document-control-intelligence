# Qwen 1.3 / 1.4 — bounded synthetic development diagnosis

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
The local runtime uses the current source prompt protocol
(1.3 for the first completed run; 1.4 for the subsequent title-decision
experiment) with 4 CPU threads, 8,192 context,
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

## Executed protocol 1.3 baseline — 17 November 2026

[PR #26 real model run](https://github.com/mehdisafer/document-control-intelligence/actions/runs/44168516337)
and [exact merged-main repeat](https://github.com/mehdisafer/document-control-intelligence/actions/runs/44169464563)
produced **12/12 real Qwen inference traces**, zero errors, **7/12 correct
document classifications**, **4/12 explicitly human-review-eligible documents**,
**4/4 eligible critical quality**, **0/6 unsupported-layout eligible**, zero
false eligibility and 100% source citation/semantic validity on these
previously seen synthetic development inputs. The **50% eligible-coverage
policy failed** because 4/12 (33.33%) is below 6/12. The report
[for the merged source](https://github.com/mehdisafer/document-control-intelligence/actions/runs/44169464563)
is retained in its original artifact; model/runtime identities were pinned.
This historical development outcome must never be converted into a PASS.

All **two in-contract purchase orders** were classified `unknown` despite
printed exact title support. Their fields were otherwise source-supported;
class abstention blocked review eligibility. Protocol 1.4 narrows the
instruction for the model's **kind** decision only. It does not force an
unrecognized layout into eligibility, override the independent title verifier,
change model weights or relax published business/source restrictions.

**Protocol 1.4 outcome is UNMEASURED until its own real CI finishes.** Both
samples are development data, so even a policy success cannot close the
independent real-supplier/fresh-holdout quality gate.
