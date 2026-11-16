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
are available in the raw reports. The table retains the original
`attempt-01-default-cache` execution times. The later source-commit regression
has different timings and identical semantics; it does not overwrite that
historical measurement. These values depend on this shared CPU host.

## Application qualification on the published source

Source commit `3ff93109f3ea0d9c5f4bdfd598dd35bbd4513439` passed 107 unit/integration
tests with no skips. A new execution of both final baseline/local-linear profiles
reproduced all 72 semantic document outputs: classification probabilities, field
values and status, citations, rows, findings, calculations and aggregate quality.
Only `timings` and `elapsed_seconds` are excluded from the comparison. The model,
input manifest and application source remained unchanged. Original commands,
before/after hashes and reports are in [qualification](../evidence/qualification/).

The frozen local-linear application demo has a separate observed limit: an
unrelated URL in the malicious-instruction footer is classified as another
subtotal label. Source/normalization checks abstain on the conflicting candidates.
The actual injection case remains in review; six dossiers publish and all six
exports survive restoration. The baseline publishes seven. The unchanged strict
demo verifier expected seven and failed on the local-linear injection case; its
original report is retained. This is additional conservative review, not a false
acceptance or evidence of external instruction execution. No final model was
retuned or value silently repaired in response to this result.

A separate recovery exercise restored the unchanged local-linear state and used
the review API to correct `subtotal` from its source quotation
`Subtotal: 1,255.00` to normalized `1255.00`. The audit retains the old abstention,
both candidate citations, the correction actor, reason, source version and new
revision. Self-approval returns `403 SELF_APPROVAL`; a distinct approver accepts
and a publisher explicitly publishes. The repaired state contains seven
publications, and all seven exported payloads compare equal after another restore.
No parser or model request was made during this repair. These scripted actor
actions qualify the review workflow, not improved model accuracy or independent
human approval. The original failed assertion and aggregate result remain intact.

A second supplemental run exercised real HTTP/1.1 over loopback TCP with a Uvicorn
process and a separate worker. Its 36 checks across 30 requests verified a fresh
three-document local-linear case, exact normalized fields and source spans,
unauthorized action denials, unchanged original/ZIP bytes, idempotent publication
and all three upload-request/audit/job joins. Wall time was 2.110694 s, including
1.218856 s for the separate worker. This sequential case establishes the network
and process boundary; it is not a concurrent HTTP benchmark or a browser test.

## Source-label contract guard — subsequent fixed-model regression

The original local-linear six-export failure above remains **unchanged**.
Its unnecessary abstention was caused by a high-confidence learned proposal
from an unrelated printed URL label being added to the critical subtotal
candidate set. The independent `validate_evidence` verifier already rejected
unknown labels, so this unsupported proposal could only mask an otherwise
valid source value; it could not provide an accepted citation.

[PR #19](https://github.com/mehdisafer/document-control-intelligence/pull/19)
introduces a conservative proposal gate: for the statistical profile, a
candidate is selected only if the model's key agrees with the **versioned
independent `LABEL_TO_KEY` semantic contract**. Out-of-contract model
proposals remain visible in warnings. Two recognized but conflicting
subtotals still require review, and neither the source-verifier, the
model's weights, its thresholds nor the original evidence has changed.

On [GitHub Actions push run 43977956360](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43977956360)
at source `ac8745920ade9f023ebe9b9a692a9cd8811d48ba`, the **unchanged**
strict nine-scenario demonstration passed and produced **7/7 eligible
dossiers and 7/7 published/restored exports**. The acceptance and publication
requests were explicit, role-separated **scripted test actions**; this is not
an independent human approval or autonomous payment authorization.
The contradictory overbilling and incomplete-invoice scenarios remained
ineligible. Four additional adversarial/source-contract tests passed.
The original six-export report and its failed assertion were not altered.

An independent *execution* then replayed the existing **same-generator,
seed-42, 36-document synthetic final split** with the fixed
`local-linear-model.json` artifact (SHA-256
`234c94149697cbeda761c22cae9c27aa0f57a8215422da906b32a6bc07148ff1`).
The new source-qualified metrics were:

| Frozen 36-PDF replay metric | Observed result |
|---|---:|
| Correct classification | 34/36 (94.44%) |
| Eligible for explicit acceptance | 30/36 (83.33%) |
| Critical quality among eligible | 30/30 (100%) |
| False eligible | 0 |
| Source citation validity | 100% |
| Independent semantic evidence validity | 100% |
| Predeclared synthetic policy gate | Met |
| Execution failures | 0 |

The exact original [GitHub Actions evidence artifact](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43977956360/artifacts/14282505849)
contains `linear-final-replay/summary.json`, the policy-before-run,
the separate local-linear demo, unit/JS/browser logs and real screenshots.
The output's source commit, model digest and manifest SHA-256 are checked
independently from the historical records. The previous final results
were **not overwritten**. This replay is a source regression on the
**existing** generator and split, not a new independent supplier distribution,
post-training calibration or a new large-language-model evaluation.

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

The final load execution used the same nine PDFs, 15 pages and three OCR pages
for each worker count, with the baseline profile and a batch size of two:

| Observed metric | One worker | Two workers |
|---|---:|---:|
| Processing wall time, including spawn | 4.319768 s | 2.296395 s |
| Throughput | 2.083445 documents/s | 3.919187 documents/s |
| Processing p95 | 1.243155 s | 1.195962 s |
| End-to-end p95 | 4.147932 s | 2.244896 s |
| Completed jobs | 9/9 | 9/9 |
| Eligible documents | 8/9 | 8/9 |
| Published cases | 2/3 | 2/3 |
| False eligible results / duplicate publications / worker errors | 0 / 0 / 0 | 0 / 0 / 0 |

Both runs have identical business signatures: two matched cases and one review
case. The largest worker-reported peak RSS was 80,441,344 bytes; the largest
reaped parser-child peak was 73,412,608 bytes. These are separate per-process
observations, not a total RAM estimate. Process-tree enumeration is incomplete,
sampled RSS can double-count shared pages, and cgroup metrics are unavailable.
Stage timings are recorded; exclusive memory per parsing/OCR/model stage is not.
This short workload supports the observed invariant comparison, not a capacity
commitment or long-running reliability claim.

External inference/API fees are zero for these local runs. Host rental,
electricity, development time and deployment cost are not metered. No throughput
or cost extrapolation to a distributed installation is made.

## Provenance and evidence interpretation

Early runs preceded the source commit. They retain exact source hashes and
`git_commit: null` where applicable. A later publication map identifies the
commit containing those bytes; it does not backdate the execution or rewrite the
original metadata. A hash establishes content agreement, not an independent
audit, document authenticity or production certification.
