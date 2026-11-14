# Qualification of the published source

These executions use implementation commit
`3ff93109f3ea0d9c5f4bdfd598dd35bbd4513439`. The command ledger, original logs,
before/after source hashes and input digests are retained. Later documentation
and evidence packaging do not alter the executed application. See the
[publication map](../publication-map.json) for the byte comparison.

The later Apache-2.0 change updates package metadata and Docker's licence-file
inputs. These original reports are not executions of that later commit. The HTTP
harness checks `pyproject.toml` as part of its frozen source; its reproduction
therefore uses a detached checkout below, preserving the original guard.

## Observed results

| Execution | Observed result | Original evidence |
|---|---|---|
| Unit/integration suite | 107 tests in 29.452 s, no skips | [Log](unittest.log), [summary](qualification-summary.json) |
| Baseline demo | Nine cases, 28 completed jobs, seven published dossiers; all seven payloads equal after restore; strict verifier succeeds | [Result](demo-baseline/result.json), [verifier](verify-demo-baseline.log) |
| Frozen local-linear demo | Nine cases, 28 completed jobs, six published dossiers; all six payloads equal after restore; unchanged seven-export verifier fails | [Result](demo-local-linear/result.json), [failed verifier](verify-demo-local-linear.log) |
| Supplemental human repair | Explicit subtotal correction, self-approval denied, separate approver accepts, publisher publishes idempotently; seven exports equal after another restore | [Report](manual-recovery-report.json), [command](manual-recovery-command.json) |
| Frozen evaluation regression | All 72 baseline/local-linear semantic outputs match the original; only timing fields excluded | [Comparison](regression-comparison.json), [summary](evaluation-regression/summary.json), [raw results](regression-raw-results.tar.gz) |
| Worker load | Same nine PDFs per run, one/two workers, 2.083445/3.919187 documents/s; identical business outcomes, no false eligibility or duplicate publication | [Raw report](benchmark-1-2.json), [log](benchmark.log) |
| Real HTTP/separate worker | 36 checks across 30 requests, three local-linear jobs, role denials, original bytes, evidence, idempotency and three request/audit/job joins | [Report](http/run-3ff93109/report.json), [server log](http/run-3ff93109/server.log), [worker log](http/run-3ff93109/worker.log) |

The original [predeclared plan](predeclared-plan.json) required seven exported
dossiers for both automatic demos. Therefore
`overall_requested_local_qualification_met` remains **false** in the original
aggregate. The later successful recovery and HTTP exercise are distinct records.
No failed assertion, command exit code or original model result is replaced.

## Why the linear demo needs one more review

The frozen field-label model treats an unrelated URL in the malicious-instruction
footer as a second subtotal candidate. The source verifier abstains on those
conflicting candidates; the injection case remains in review. No printed
instruction changes a policy, invokes a tool or sends content externally.

The supplemental exercise restores that state and corrects the subtotal through
the existing review API. It records the exact source quotation
`Subtotal: 1,255.00`, normalized value `1255`, the original abstention and both
citations, actor, justification, source version 1 and incremented revision.
Even an actor holding both operator and approver roles receives
`403 SELF_APPROVAL`. A different actor accepts the corrected revision before
publication. The original classification proposal and confidence remain intact.

This is a scripted execution of attributed human-decision roles. It verifies
the workflow; it is not an independent person's review or a new model-quality
result. The repair makes zero parser/model calls. Its temporary authentication
and live databases were removed after verifying the restored exports.

## Network and resource scope

The HTTP harness starts a real Uvicorn child process, sends HTTP/1.1 through
`http.client` to loopback TCP and launches a distinct worker process. It checks
the frozen source/model before and after execution. The observed wall time is
2.110694 s, including 1.218856 s for the worker. Original PDFs and the
[control dossier ZIP](http/run-3ff93109/control-dossier.zip) are retained.
The intentional SIGTERM is accompanied by completed application-shutdown logs.
This sequential case does not validate browser interaction, HTTP concurrency,
container isolation or a remote deployment.

The worker benchmark admits work through the Store API. Each run uses nine PDFs,
15 pages and three OCR pages. Two cases publish and one remains in review under
both worker counts. The host exposes nine AMD EPYC 9V74 CPUs, about 9.73 GiB host
RAM and no GPU. Cgroup measurements are unavailable; RSS observations are
per-process, partially sampled and can double-count shared pages. Stage timings
are measured, but exclusive stage memory is not. See [evaluation](../../docs/EVALUATION.md)
for the table and interpretation. This small workload is not a capacity promise.

## Reproduce without overwriting evidence

Install the locked dependencies and native prerequisites from the root README.
Run from the repository root, using output paths that do not exist yet:

```bash
uv run --frozen python -m unittest discover -s tests -v
uv run --frozen dci demo --output outputs/reproduction-baseline
uv run --frozen python scripts/verify_demo.py outputs/reproduction-baseline/result.json
uv run --frozen dci demo --profile local-linear \
  --model-path evidence/evaluation/local-linear-model.json \
  --output outputs/reproduction-linear
uv run --frozen python scripts/benchmark.py --cases 3 --workers 1 2 \
  --batch-size 2 --output outputs/reproduction-load.json
```

Replay the original HTTP qualification from the repository root, using the
executed source and the retained harness/model from the licensed checkout:

```bash
mkdir -p outputs
git worktree add --detach outputs/http-source-3ff93109 3ff93109f3ea0d9c5f4bdfd598dd35bbd4513439
env -u UV_PROJECT_ENVIRONMENT -u PYTHONPATH \
  uv run --frozen --project outputs/http-source-3ff93109 --python 3.12.14 python \
  "$PWD/evidence/qualification/http/qualify_http.py" \
  --repo "$PWD/outputs/http-source-3ff93109" \
  --model "$PWD/evidence/evaluation/local-linear-model.json" \
  --output "$PWD/outputs/reproduction-http"
```

A normal full Git clone must contain the original commit. Both worktree and
output paths must be new; choose different names for another replay. The new run
records its own source identity and does not overwrite the published proof.

Running the strict demo verifier against the raw linear result is expected to
reproduce the retained six-versus-seven assertion. Use the UI or review API and
a distinct approver for an explicit correction; do not relax the verifier or
model thresholds to hide that result. For final-model replay, including original
PDF bytes and the earlier rule snapshot, follow [evaluation reproduction](../evaluation/README.md).

`run_qualification.py`, `compare_and_summarize.py` and `manual_recovery.py` are
the original execution harnesses. They contain the original commit guard and
temporary path conventions. They are retained for provenance; they must not be
run in this committed evidence directory. A new manual-recovery exercise needs
a newly generated demo backup and its own output paths. The HTTP harness accepts
explicit `--repo`, `--model` and `--output` arguments and refuses an existing
output directory.

## Artifact integrity

[index.json](index.json) records 46 original copied artifacts and all 111 members
of the regression archive. The supplemental HTTP run has its own
[16-artifact manifest](http/run-3ff93109/artifacts.json). Source hashes, timestamps
and working-tree metadata remain as recorded. Native PDF exports are synthetic.
Credentials, runtime authentication configurations, live databases and large
runtime/model binaries are not included.
