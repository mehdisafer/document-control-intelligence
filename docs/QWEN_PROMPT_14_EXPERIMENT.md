# Qwen 1.4 — negative real-inference development experiment

## Source identity and decision — 17 November 2026

**REJECTED: PR #27 is closed without merge.** The attempted prompt-only revision `structured-extraction-1.4` is commit `5bdc2c7b9b33c82eccc16661dca275aa03487d7f`; the GitHub pull-request runner recorded execution source `b56a7dfc65b1af85a4879708a332a7c69d6d9fcd` (test merge SHA). The supported `main` branch remains **Qwen prompt 1.3**, and the published `v0.1.0rc2` tag remains immutable at `db42dd7c7668d70deb8cf5ea6512abcd94a36510`.

[Qwen 1.4 real run #44170413325](https://github.com/mehdisafer/document-control-intelligence/actions/runs/44170413325), [full app CI #44170413411](https://github.com/mehdisafer/document-control-intelligence/actions/runs/44170413411) and CircleCI all succeeded technically. They are **not** model quality passes.

The original [1.4 artifact #14366438718](https://github.com/mehdisafer/document-control-intelligence/actions/runs/44170413325/artifacts/14366438718) was downloaded; all **43 ZIP members passed CRC**, ZIP SHA-256 `f1f5877785a773da5b034b4e9d1e9130c68703b5568f9af20931775a20038cd0`. It includes 12 real Qwen response traces, synthetic PDFs, scored outputs and runtime receipts. The comparison uses the independently downloaded [1.3 main artifact #14366358107](https://github.com/mehdisafer/document-control-intelligence/actions/runs/44169464563/artifacts/14366358107), SHA-256 `dfda3b1c40b9a89ae612ddb880da0499ecfc0094e8c44b3186f810310664dca3`. **All 12 PDF input SHA-256 values are identical** across the two runs, with manifest SHA-256 `ab3e9904e6b0c8a8c2fe2ed5e022038c7eafe2a28c93502c0c7f4a71cd44b365`.

## Paired observations on the exact same synthetic development inputs

| Metric | Qwen 1.3 — active source | Qwen 1.4 — rejected |
|---|---:|---:|
| Real model responses | 12/12 | 12/12 |
| Correct document classifications | **7/12** | **7/12** |
| Eligible for later human review | **4/12** | **4/12** |
| Critical accuracy among eligible | 4/4 | 4/4 |
| Unsupported-contract documents eligible | 0/6 | 0/6 |
| False eligibility / inference errors | 0 / 0 | 0 / 0 |
| Supported citation / semantic evidence validity | 100% / 100% | 100% / 100% |
| Runtime and semantic safety gate | **Met** | **Met** |
| **Predeclared 50% eligible-coverage gate** | **FAILED (33.3%)** | **FAILED (33.3%)** |
| In-contract purchase orders classified `unknown` | 2/2 | 2/2 |
| Scalar source-ID proposals on **each** of those two purchase orders | **8/8** | **0/8 (all null)** |

The **12 raw proposed document classes** and **12 final verified classes** were **exactly identical** between protocols. Ten documents had unchanged field candidate mappings. The two in-contract purchase orders **lost all 16 scalar source-ID selections combined**, while retaining the wrong/unknown classification. The 1.4 prompt therefore caused a *raw field-proposal coverage regression* and **no classification or eligibility improvement**. The source verifier still prevented inappropriate acceptance.

The 1.4 source edit only emphasized using one unambiguous title signal in model instructions. It did not modify model weights, provider, independent verifier, candidate schema, payments, publication authority or release tags. Its failure on these development inputs does not prove that every possible prompt or larger model will fail.

## Reproducible paired archive check (without Qwen inference)

The read-only [paired original-artifact comparator](../scripts/compare_qwen_dev_archives.py)
re-derives per-PDF classification, field correctness, critical abstention and
safety counts from the **original** workflow artifact ZIPs. It rejects
unmatched PDF hashes, forged/missing raw Qwen responses, duplicate or unsafe ZIP
members and inconsistent summary counters. The comparator also **recomputes**
source-citation validity and unsupported-layout eligibility; a green runtime
flag in the report cannot override contradictory scored source evidence. Its synthetic
[negative-test suite](../tests/test_compare_qwen_dev_archives.py) runs in both
GitHub Actions full unittest discovery and CircleCI's focused suite.

Download the two artifact ZIPs from the dated links above to a **local isolated
analysis directory** (do not commit original PDFs, Qwen traces or model weights):

```bash
python scripts/compare_qwen_dev_archives.py \
  --baseline /path/to/qwen-1.3-main.zip \
  --candidate /path/to/qwen-1.4-pr27.zip \
  --output /fresh/path/qwen-paired-result.json \
  --require-nonregression
```

The bounded CLI retains its JSON result using exclusive file creation and returns
**exit status 3** for the observed Qwen 1.4 regression, rather than a misleading
green model-quality signal. Success without `--require-nonregression` means
only that the archived evidence was structurally comparable. Even passing
nonregression cannot establish fresh supplier performance, a production-ready
model or causality from one paired execution. The original run artifacts remain
source-bound and are not uploaded into this repository.

## Acceptance and next work

- Keep **PR #27 closed, not merged**; do not backport 1.4 to `main`.
- Retain this negative result alongside the already failed historical Qwen 1.2 benchmark (**3/36 correct classes, 0 eligible**) and the separate Qwen 1.3 development failure (**7/12 correct, 4/12 eligible; 33.3% coverage**). Different cohorts cannot be compared as a controlled accuracy uplift.
- Before another prompt/model experiment, predeclare a **new development strategy and split**; assess model capacity, structured-output behavior and original evidence quality instead of tuning against previously inspected final results.
- The 12 examples here were already used for source-safety/development and **are not independently acquired, annotated real supplier PDFs or an untouched holdout**. No supplier generalization, production deployment or independent human approval is established.
- GitHub `main` ruleset and four malformed links in the existing rc2 release body remain separate owner-side administration gates.

The narrow bounded safety/runtime evidence is valid; **Qwen generative quality remains an OPEN, failed acceptance gate**.
