# Reproducible installation and deployment reference

## Local Linux execution

Prerequisites: Python3.12, uv0.13.6, Tesseract with English LSTM trained data and
libseccomp2. On Debian/Ubuntu, provision native packages with the system package
manager, then `uv sync --frozen --group audit`. Python dependencies and hashes are
in `uv.lock` and `requirements.lock`; installed native/OCR versions and trained-data
digest are captured in each execution. Native Windows parsing is not supported;
use the Linux container or an explicitly provisioned WSL2 environment.

```bash
uv run dci init --home .data
uv run dci serve --config .data/config.json
# Another terminal, same environment:
uv run dci worker --config .data/config.json
```

Open `http://127.0.0.1:8000`. Tokens are in the private credential file written by
`init`, not the console. For the seeded UI, use the runtime configuration produced
by `dci demo` instead. Do not expose a development listener beyond loopback.

## Authenticated original-page preview

The review page displays a bounded **PNG raster** rather than delegating untrusted
PDF files to a browser's native PDF plugin. A logged-in operator/reader may request
`GET /api/documents/{document_id}/preview/{page_number}` only after the original
has passed parser inspection. The original-download endpoint remains unchanged.

The API verifies the stored PDF SHA-256 and delegates each request to a separate
short-lived Linux PDFium child. That process applies the same Linux seccomp
network-denial policy as document parsing **before** importing the PDF engine.
It rejects scripts, active/embedded content and encrypted documents; it enforces
the source byte/page budget, a preview wall-clock budget of at most **12 seconds**,
a 768 MiB address-space cap (or lower configured parser limit), **2.5 million
rendered pixels** and **5 MiB per PNG**. The API admits at most two concurrent
preview workers per process and returns `429 PREVIEW_BUSY` instead of creating
unbounded parser work. HTTP responses have `Cache-Control: no-store` and
require the same bearer authentication used by the rest of the review UI.

The browser requests each page separately, revokes superseded object URLs, and
rejects late results following actor or document changes. Page navigation
uses the original page number; all extracted citations still refer to the
unmodified PDF source. If rasterization fails, the UI shows an explicit error and
offers the original download. No cloud rendering or remote model API is used.

[Real hosted visual qualification](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43770874796)
executed genuine desktop/mobile Chrome checks and retained screenshots proving
a **953 × 1348** pixel page was decoded and displayed. These bounds are for a
single-host reference, not a measured production throughput or SLA.

## Trained local model

```bash
uv run dci corpus --output outputs/corpus --seed 42 --per-split 12
uv run dci train --manifest outputs/corpus/manifest.json --output .data/models/local-linear.json
uv run dci demo --profile local-linear --model-path .data/models/local-linear.json --output outputs/demo-linear
```

Training opens only train documents. Keep the model, manifest, recipe and source
version together. Change `profile` and `model_path` in a new validated configuration
to make this profile the worker default. Existing queued policy changes require
explicit retry. The statistical model is not presented as an LLM.

## Optional local LLM

The profile is experimental; see the measured evaluation before choosing it.
Provisioning downloads public model/runtime artifacts only and verifies pinned
SHA-256 values. It does not upload documents or run cloud inference.

```bash
uv run python scripts/provision_llm.py --output .runtime
uv run python scripts/run_llm_evaluation.py \
  --server .runtime/llama/bin/llama-b12359/llama-server \
  --model .runtime/models/Qwen3-0.6B-Q4_K_M.gguf \
  --manifest outputs/corpus/manifest.json \
  --linear-model .data/models/local-linear.json \
  --output outputs/final-evaluation
```

The harness verifies the actual binary/build and model, starts a loopback server,
performs real requests and terminates the process. Runtime launch and inference
must share a network namespace. A separate long-running worker uses a `LlamaConfig`
file with absolute `model_path`, `runtime_binary`, port, budgets and optional trace
directory. Raw traces contain documents; retain them only in the permitted local
environment. No external provider profile is enabled.

## Container reference

`Dockerfile` pins the Python base image by manifest digest and uses the same lock.
Native Debian packages are recorded at build/execution; their package mirror is
not an immutable OS snapshot, so the final image digest is the deployable identity.
Retain the image digest and notices alongside results. The release acceptance
matrix distinguishes source definitions, build checks and actual container runs.

```bash
uv run python scripts/prepare_container.py --output .runtime/container-config --profile baseline
mkdir -p .runtime/container-models
export DCI_CONFIG_DIR="$PWD/.runtime/container-config"
export DCI_MODELS_DIR="$PWD/.runtime/container-models"
docker compose build
docker compose config
docker compose up -d --scale worker=2
```

The plaintext credential file is placed beside, outside, the mounted configuration
directory. Only hashed token configuration enters the containers. Data uses a named
volume; image files are read-only; temporary storage, memory, processes and CPU
are bounded. Workers have no network. The API's internal network publishes only
`127.0.0.1:8000`. Docker-level transport/quotas require actual daemon verification;
do not infer a deployment from YAML validation.

For `local-linear`, copy the verified safe JSON model to the model directory as
`local-linear.json` and prepare the corresponding profile. For `local-llm`, use the
provisioned GGUF and pinned runtime directory, prepare the LLM config, set
`DCI_LLAMA_DIR`, and add `-f compose.yaml -f compose.llm.yaml`. The worker shares
the model container's networkless namespace; the model listens only on that
namespace's loopback. Size the model container using measured peak memory. This
profile's quality/resource gates remain separate from the baseline container run.
The LLM configuration admits one active worker to match the one-slot model server;
run this override with `--scale worker=1`. The baseline/local-linear reference
admits two. Raising container replicas does not bypass the transactional job cap.

The optional override uses the `local-llm-bounded-1.0` resource profile: context
8192, four threads, one slot, no retained prompt cache/context checkpoints,
logical batch 512 and microbatch 128. Its container RSS limit is 2048 MiB. The
evaluation harness additionally bounds address space and CPU/wall time; those
limits are not interchangeable with a Docker resident-memory quota. Original
unbounded-cache executions and their failures remain in the evaluation evidence.

Stop with `docker compose down`, without `--volumes`. Back up and exercise restore
before upgrading. Application liveness does not prove worker/model readiness.

## Terraform alternative

`infra/terraform` manages the actual single-host Docker network, retained volume
and containers using `kreuzwerker/docker`4.7.0. It does not create cloud resources.
Use either Terraform or Compose for a deployment; do not give both ownership of
the same resources. The optional LLM namespace topology is currently defined in
Compose; Terraform targets baseline/local-linear CPU workers.

```bash
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform fmt -check
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform plan \
  -var="image_id=$(docker image inspect dci:0.1.0rc1 --format '{{.Id}}')" \
  -var="config_directory=$DCI_CONFIG_DIR" \
  -var="models_directory=$DCI_MODELS_DIR"
```

Inspect the concrete plan before applying it on an authorized host. The data volume
has `prevent_destroy`; credentials are file mounts and are not Terraform variables
or state content. Schema validation does not establish that Docker is reachable,
and a plan is not an executed deployment.
