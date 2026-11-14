# Evaluation evidence

This directory preserves the original execution results and a derived comparison.
The benchmark uses 36 final PDFs from layouts and document families excluded from
training. The local linear model was fitted on 72 actual parsed training PDFs and
576 field examples. Model weights, extraction prompts and thresholds were frozen
before final evaluation; the later LLM change addressed runtime resources.

The [development tuning records](development-tuning/provenance.json) are preserved
separately. That earlier model used 36 training PDFs and format `1.0`; its heading
feature adjustment changed tuning classification coverage from 9/18 to 18/18 with
unchanged thresholds. It is not relabeled as the final model and does not substitute
for final evaluation of the distinct 72-document-trained `1.1` artifact.

## Measured results

| Profile | Classification accuracy | Normalized field accuracy | Eligible documents | Quality among eligible documents |
| --- | ---: | ---: | ---: | ---: |
| Deterministic baseline | 55.56% | 98.90% | 16 / 36 | 100% |
| Local linear model | 94.44% | 98.90% | 30 / 36 | 100% |
| Local Qwen GGUF, bounded runtime | 8.33% | 94.59% | 0 / 36 | Undefined: no eligible documents |

Eligibility is a candidate state before mandatory human approval. It is not an
automatic publication rate or a measured reduction in operator time. The field
accuracy column includes correct required abstentions. All three profiles emitted
valid source citations and no falsely eligible document in this synthetic sample.
Zero false eligibility with zero eligible output does not establish quality on
accepted documents. See the [derived comparison](summary.json) for denominators,
review rates, critical-document accuracy and the predeclared gate.

The local linear profile meets this synthetic benchmark gate. Qwen was actually
executed on every final input, but it does not meet the quality or coverage target.
It remains an experimental profile. These results do not validate real suppliers,
forensic document authenticity or production capacity.

## Retained runtime failures

Both original default-cache attempts are retained. The first returned 12 complete
responses and then 24 unavailable results; the second returned 19 complete
responses and then 17 unavailable results. Both servers exited with SIGKILL. The
second attempt captured rising RSS, but kernel/cgroup cause evidence was not
available. Neither failure is described as a proved OOM or a controlled stop.

The bounded operational profile disabled prompt cache and context checkpoints,
reduced batching, and applied a 4,096 MiB address-space limit with CPU/wall budgets.
It completed 36 responses and shut down with exit status 0. Its measured peak RSS
was 1,587,868 KiB; address space and resident memory are distinct quantities. Model,
prompt, seed, context size and inference threads were unchanged. Latency was
observed in a shared execution environment, including substantial scheduling
variation. The [bounded harness record](attempt-03-bounded-cache/harness.json)
contains the exact flags, limits, hardware-linked measurements and source hash.

The [repeatability view](repeatability-two-original-attempts.json) compares two
successful responses for each of 12 overlapping inputs under the original,
identical profile. It observed no semantic changes. This small, success-conditioned
sample does not erase the recorded runtime failures.

## Original files and provenance

Each attempt directory contains byte-for-byte copies of its original summary,
harness record, pre-run policy and server log. Source and usage views are explicitly
identified as derived where appropriate. The [index](index.json) maps original
paths to copied files or archive members, with sizes and SHA-256 values.

The [raw archive](raw-executions.tar.gz) contains every per-document result, parsed
page payload and raw model response from all three attempts, the 36 original final
PDFs, and matching source snapshots. Every archived member was reopened and checked
against its original bytes. Parser checkpoints and runtime/model binaries are
excluded. The GGUF download remains separately pinned by digest and upstream license.

Original `git_commit` and working-tree state values have been retained. A missing
commit was not invented. The source snapshots establish the code used by the
original evaluation. Later changes to audited human classification in the review
workflow are not presented as that original benchmark source. Hashes establish
content correspondence, not certification.

## Reproduction

Use the Linux runtime and pinned dependencies described in the main README. To
replay the original CPU profiles using the captured core implementation and model:

```bash
PYTHONPATH=evidence/evaluation/source-snapshot/src uv run --frozen python - <<'PY'
from pathlib import Path
from dci.corpus import generate_corpus
from dci.evaluation import evaluate_manifest

generate_corpus(Path("outputs/proof-corpus"), seed=42, per_split=12)
evaluate_manifest(
    Path("outputs/proof-corpus/manifest.json"), Path("outputs/proof-cpu"),
    profiles=("baseline", "local-linear"),
    model_path=Path("evidence/evaluation/local-linear-model.json"),
)
PY
```

For the local LLM, provision the pinned assets using `scripts/provision_llm.py`
and the main README, then run the captured bounded launcher with the same manifest:

```bash
PYTHONPATH=evidence/evaluation/source-snapshot/src uv run --frozen python \
  evidence/evaluation/source-snapshot/scripts/run_llm_evaluation.py \
  --server .runtime/llama/bin/llama-b12359/llama-server \
  --model .runtime/models/Qwen3-0.6B-Q4_K_M.gguf \
  --manifest outputs/proof-corpus/manifest.json --profiles local-llm \
  --output outputs/proof-llm --threads 4 --timeout-seconds 90
```

Choose new output directories for each run; existing evidence is not overwritten.
The archive also retains the evidence-packaging script. No cloud inference service
or paid inference API was invoked. CPU/RAM and reported token use were measured; local compute was
not assigned an invented monetary cost.
