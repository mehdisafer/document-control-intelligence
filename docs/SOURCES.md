# Upstream sources and component decisions

Verification date: 2026-11-13. The versions below are deliberate reproducibility
pins, not a claim that every component is the newest release. Execution evidence
records the installed versions separately. An upstream metadata check does not
certify the dependencies or replace vulnerability scanning.

## Python and document processing

| Component | Inspected version | Python requirement | Published licence | Primary source |
|---|---|---|---|---|
| FastAPI | 0.141.1 | >=3.10 | MIT | [Versioned release](https://pypi.org/project/fastapi/0.141.1/) |
| Pydantic | 2.13.4 | >=3.9 | MIT | [Versioned release](https://pypi.org/project/pydantic/2.13.4/) |
| pypdf | 6.21.4 | >=3.9 | BSD-3-Clause | [Versioned release](https://pypi.org/project/pypdf/6.21.4/) |
| pdfplumber | 0.11.9 | >=3.8 | MIT | [Versioned release](https://pypi.org/project/pdfplumber/0.11.9/) |
| pypdfium2 | 5.13.0 | >=3.6 | Apache-2.0 / BSD-3-Clause; bundled dependencies | [Versioned release](https://pypi.org/project/pypdfium2/5.13.0/) |
| ReportLab | 4.4.9 | >=3.9, <4 | BSD | [Versioned release](https://pypi.org/project/reportlab/4.4.9/) |
| Pillow | 13.0.0 | >=3.11 | MIT-CMU | [Versioned release](https://pypi.org/project/pillow/13.0.0/) |
| scikit-learn | 1.8.0 | >=3.11 | BSD-3-Clause | [Versioned release](https://pypi.org/project/scikit-learn/1.8.0/) |
| Tesseract | Runtime records executable version | Native executable | Apache-2.0 | [Upstream licence](https://github.com/tesseract-ocr/tesseract/blob/main/LICENSE) |

FastAPI 0.141.1 declares Pydantic >=2.9.0, Starlette >=0.46.0 and multipart
>=0.0.18 for the relevant optional functionality. The complete resolver lock is
the installation authority. See the [versioned project metadata](https://raw.githubusercontent.com/fastapi/fastapi/0.141.1/pyproject.toml).

### APIs used

- [pdfplumber](https://github.com/jsvine/pdfplumber) documents `extract_words()`
  and its text/bounding-box records. Source quotations keep the canonical text
  intact; normalization is recorded separately.
- [pypdfium2 API](https://pypdfium2.readthedocs.io/en/stable/python_api.html)
  documents `PdfPage.render(scale=...)` and bitmap conversion. PDFium is not
  thread-safe across documents. This application performs parsing/rendering in
  separate bounded processes, not simultaneous PDFium threads.
- [Tesseract command-line usage](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html)
  documents TSV words, boxes and confidence; `--oem 1` selects neural LSTM OCR.
  OCR pixel positions are mapped back to page points using the recorded scale.
- [pypdf text extraction](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)
  explains the difference between native text and image-only pages. OCR is a
  separate stage, not a hidden PDF text-extraction capability.

The [pypdfium2 licensing section](https://github.com/pypdfium2-team/pypdfium2#licensing)
requires retention of PDFium and bundled dependency licences when distributing
binaries. The wheel/container includes upstream licence files. Documentation and
examples have separate CC-BY-4.0 terms. An SBOM or package licence string alone
does not replace those notices. PyMuPDF is not a project dependency.

## Real local models

### Statistical profile

`local-linear` is a trained statistical model, not an LLM. Two fitted heads use
explicit character/word counts, TF-IDF and logistic regression: one for document
class and one for scalar label assignment. Actual parsed training documents
supply the fitting examples. Deterministic table parsing and source validation
remain separate. The JSON artifact contains only bounded vocabulary, classes,
numeric weights and provenance; there are no pickles or serialized callables.

Relevant primary references:

- [TF-IDF transformer, scikit-learn 1.8](https://scikit-learn.org/1.8/modules/generated/sklearn.feature_extraction.text.TfidfTransformer.html).
- [Logistic regression, scikit-learn 1.8](https://scikit-learn.org/1.8/modules/generated/sklearn.linear_model.LogisticRegression.html).
- [Model persistence and its security limits](https://sklearn.org/1.8/model_persistence.html).

The safe runtime calculation is checked against the fitted estimator's class
and probability outputs before saving. Training-fit metrics are not held-out
quality metrics; the application evaluates final layouts separately.

### Local LLM profile

The `local-llm` profile uses the original publisher's Qwen3-0.6B GGUF, with
llama.cpp running on CPU. OpenAI-compatible HTTP describes the wire protocol;
it does not mean that any external OpenAI service receives documents.

| Item | Pinned identity |
|---|---|
| Model | `Qwen/Qwen3-0.6B-GGUF`, `Q4_K_M` |
| Model revision | `1208e45d782fe18602c5eaf10e5758d5b0f24c03` |
| Model licence | Apache-2.0 |
| Model file | `Qwen3-0.6B-Q4_K_M.gguf`, approximately 397 MB |
| Model SHA-256 | `b0638f08417a2d3c8652760462eb5407c6e30173cf9608ad0820757a281eea0e` |
| Runtime | llama.cpp v1.0.0, binary build `b12359` |
| Runtime source commit | `b1b770d90d94cad9e9ea5b993bdbc383a522fb28` |
| Runtime licence | MIT |
| CPU binary archive | `llama-b12359-bin-ubuntu-x64.tar.gz`, 23,311,084 bytes |
| Archive SHA-256 | `0bc1f091e8916102b6d8f2cf944233a620e90a0f856c72d0ce41150c65c2e72e` |

Primary sources:

- [Pinned publisher model file, licence and digest](https://huggingface.co/Qwen/Qwen3-0.6B-GGUF/blob/1208e45d782fe18602c5eaf10e5758d5b0f24c03/Qwen3-0.6B-Q4_K_M.gguf).
- [Pinned publisher model card](https://huggingface.co/Qwen/Qwen3-0.6B-GGUF/blob/1208e45d782fe18602c5eaf10e5758d5b0f24c03/README.md).
- [Official runtime release metadata and asset digests](https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/b12359).
- [Versioned server API and flags](https://raw.githubusercontent.com/ggml-org/llama.cpp/v1.0.0/tools/server/README.md).
- [Versioned runtime licence](https://raw.githubusercontent.com/ggml-org/llama.cpp/v1.0.0/LICENSE).

The inspected server supports schema-constrained `/v1/chat/completions` and
`--reasoning off`. This profile pins those APIs, disables the web UI, uses one
inference slot and binds to `127.0.0.1`. No model tools are supplied. The client
uses a fixed loopback host and validates the configured model digest, model alias,
provider, export policy and request budgets. No proxy, arbitrary URL, redirect or
cloud fallback is accepted. A missing runtime or exhausted budget produces
abstention/review. Model confidence is not accepted as source evidence.

Downloading the runtime/model requires network access to their distribution
hosts at provisioning time. Runtime document processing uses the provisioned
local files. No claim of model accuracy, latency or successful execution is made
from upstream descriptions; see the repository's original run evidence.

## Project and synthetic-data rights

The corpus generator creates fictional procurement documents and ground truth.
No employer/client data or documents are inputs. No code or datasets are imported
from another portfolio repository. The maintainer explicitly selected
[Apache-2.0](../LICENSE) for the original project on 2026-11-14.
[NOTICE](../NOTICE) records project attribution. Third-party component licences
and notices remain separate and are not replaced by the project's licence.

The licence text comes from the [official Apache License 2.0 text](https://www.apache.org/licenses/LICENSE-2.0.txt).
Application guidance was checked against the [Apache licensing FAQ](https://www.apache.org/foundation/license-faq.html#Apply-My-Software).
