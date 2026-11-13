# Evaluation protocol and observed limits

## What the comparison establishes

The reference runs actual PDF parsing, OCR and local inference. The final corpus
contains 36 synthetic documents, not an independent supplier sample. The trained
linear classifier meets the declared quality/coverage gate on this set. The
baseline does not meet its coverage target. The generative Qwen profile remains
experimental: real model execution does not by itself qualify its decisions.

The original execution reports are retained in `evidence/`. Failed model requests
remain in their denominators. Successful requests, infrastructure errors and
document-level abstention are reported separately.

## Dataset and separation

`dci corpus --seed 42 --per-split 12` creates 144 PDFs: 72 training, 36 tuning and
36 final. Each family contains a purchase order, delivery note and invoice. Family
IDs and layout IDs are disjoint between splits. Training uses `classic_en` and
`stacked_fr`, tuning uses `banded_en` and `compact_fr`, and the final set uses
`sidebar_en` and `ledger_fr`.

The generator varies coordinates, language, number formatting, line count and
scan degradation. Final examples include multipage tables, missing/conflicting
values and document-borne malicious instructions. The separate application demo
adds corrected versions, duplicate submission and interdocument contradictions.
Truth manifests are available to training/evaluation only; the application never
reads expected values.

This separation prevents reusing a document family or layout ID across splits.
It does **not** make synthetic examples independent of the generator: domain
labels and explicit pipe-delimited table conventions are shared. The result is a
qualification of this bounded purchasing contract. Arbitrary supplier layouts,
new table geometry and independent OCR acquisition need a new corpus.

## Frozen recipe and declared gates

The baseline and statistical classifier use the same independent source verifier,
normalization and financial rules. The linear artifact is genuine scikit-learn
TF-IDF/logistic training, serialized as safe numeric JSON. Training uses only
the training split. Heading features and prompt design were adjusted on tuning
data before the final source freeze.

The final policy was recorded before execution:

- Every emitted citation and supported normalization must validate.
- No document may be eligible with an incorrect critical value.
- Quality among eligible documents must be 100% on this small qualification set.
- Eligible coverage must be at least 50%, so abstaining on everything cannot pass.

These are reference acceptance thresholds, not a statistical guarantee of safety.
Eligibility is not an approval: an authenticated approver must still accept the
current version, and a publisher must explicitly publish it.

The trained artifact has SHA-256
`234c94149697cbeda761c22cae9c27aa0f57a8215422da906b32a6bc07148ff1`.
The generative recipe uses Qwen3-0.6B Q4_K_M, llama.cpp `b12359`, prompt
`structured-extraction-1.2`, fixed seed, context 8192 and four CPU threads.
Exact artifact hashes, parser/OCR identity and source hashes accompany results.

## Final baseline and trained-model results

| Metric | Baseline | Local linear |
|---|---:|---:|
| Correct document class | 20/36 (55.56%) | 34/36 (94.44%) |
| Macro precision over known classes | 100% | 100% |
| Macro recall over known classes | 55.56% | 94.44% |
| Eligible documents / coverage | 16/36 (44.44%) | 30/36 (83.33%) |
| Critical quality among eligible | 16/16 (100%) | 30/30 (100%) |
| False eligible documents | 0 | 0 |
| Review or rejection rate | 55.56% | 16.67% |
| Valid emitted source citations | 2,448/2,448 | 2,448/2,448 |
| Semantically supported emitted values | 1,349/1,349 | 1,349/1,349 |
| Correct normalized present fields | 1,349/1,364 (98.90%) | 1,349/1,364 (98.90%) |
| Correct fields including required abstentions | 1,353/1,368 (98.90%) | 1,353/1,368 (98.90%) |
| Required missing/ambiguous abstentions | 4/4 | 4/4 |
| Critical fields abstained | 19/1,080 | 19/1,080 |
| Unexpected line candidates | 3, held for review | 3, held for review |
| Median document latency | 0.321 s | 0.327 s |
| p95 document latency | 1.236 s | 1.245 s |
| Declared synthetic gate | Not met: coverage | Met on this set |

Unknown classifications count against recall. Precision of 100% therefore does
not imply that every document was classified. The local model's measured gain
comes from classification: field accuracy is unchanged in this comparison.
The two invoice classification abstentions and the source-quality abstentions
remain visible; none is silently converted into acceptance.

Parsing is performed once per document and reused across profiles. The latency
reported for each profile adds its extraction time to that observed parse time;
it is not an independent cold parsing run for every profile. Stage-level timings
are available in the raw reports. These values depend on this shared CPU host.

## Generative profile and adverse executions

The first final run obtained 12 real model responses, followed by 24
`MODEL_UNAVAILABLE` results after the model server exited with SIGKILL (-9).
The unchanged-runtime repeat obtained 19 responses and 17 unavailable results.
Successful responses still abstained on document classification, so no document
became eligible. No external inference fallback occurred.

The second run measured a peak server RSS of 3,635,604 KiB, increasing over the
request sequence. Host available memory changed substantially around the exit.
The environment did not expose an OOM-kill counter or an attribution of the
signal. The evidence supports memory growth and SIGKILL; it does not establish
the killer or certify an OOM diagnosis.

A separately identified operational replay, `local-llm-bounded-1.0`, retains
weights, prompt, seed, context and thread count. It disables prompt/idle cache
retention and context checkpoints and reduces batch sizes:

```text
--cache-ram 0 --no-cache-prompt --ctx-checkpoints 0
--batch-size 512 --ubatch-size 128
```

The harness also applies a 4096 MiB address-space limit, a 1800-second CPU budget,
a 900-second server wall budget and a 90-second individual request budget. Resource
telemetry and request failures remain part of its report. The replay completed
all 36 real model requests with zero infrastructure failures and a clean server
exit. Peak server RSS was 1,587,868 KiB (about 1.51 GiB), harness wall time 412.29 s
and server CPU time 1,294.76 s. Actual usage was 37,808 prompt and 4,700 completion
tokens. Observed document latency was 6.03 s median and 41.74 s p95 on the shared
host. The resource correction is supported by this bounded run, not by a soak test.

Quality still fails the declared gate: 3/36 classifications are correct,
1,290/1,364 present fields are correct (94.57%), and 2,412/2,412 emitted citations
validate. All four required abstentions are respected. No document is eligible;
review rate is 100%. Quality among eligible documents is undefined (`null`), not
100%. Operational success therefore does not make this generative profile an
accepted classifier. No final-set quality tuning occurred during this replay.

Repeatability is measured on overlapping successful responses from the two
original identical-runtime attempts: 12 documents, two responses each, zero
semantic changes. This small successful subset excludes 24 and 17 infrastructure
failures respectively. It does not establish full-run repeatability or robustness.

Further quality development requires a new final holdout. The current final set
must not become another tuning set while retaining the same validation claim.

## Environment, load and cost

The observed host exposes 9 CPUs, AMD EPYC 9V74 and approximately 9.73 GiB host
RAM, without a GPU. Cgroup memory limits are not readable. Shared-host contention
can change latency and available memory during a run. RSS, address-space limits,
host memory and CPU time are distinct measurements.

The load harness processes actual PDFs through spawned workers and compares
business outcomes across worker counts. It measures queue admission through the
Store API, not HTTP throughput. Its source hashes, workload, page/OCR counts,
stage timings, retries, publications and observed resources are retained.
The original load attempt could not enumerate child PIDs: its child-RSS zeros
mean **unmeasured**. The revised instrumentation uses known worker PIDs and
per-process resource accounting; the original artifact is not rewritten.

External inference/API fees are zero for these local runs. Host rental,
electricity, development time and deployment cost are not metered. No throughput
or cost extrapolation to a distributed installation is made.

## Provenance and evidence interpretation

Early runs preceded the source commit. They retain exact source hashes and
`git_commit: null` where applicable. A later publication map identifies the
commit containing those bytes; it does not backdate the execution or rewrite the
original metadata. A hash establishes content agreement, not an independent
audit, document authenticity or production certification.
