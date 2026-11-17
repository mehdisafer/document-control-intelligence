# Reproduce the original Qwen 1.3 vs 1.4 ZIP comparison on hosted CI

This is a **source-bound forensic regression test**, not new Qwen inference
or a real-supplier benchmark. The [dedicated GitHub Actions workflow](../.github/workflows/qwen-original-artifact-replay.yml)
downloads the **two original artifact ZIPs** from this same repository through
a read-only `GITHUB_TOKEN`, then invokes the **exact checked-out**
`scripts/compare_qwen_dev_archives.py` comparator.

Inputs have precommitted SHA-256 digests:

| Original workflow artifact | SHA-256 |
|---|---|
| [Qwen 1.3 #14366358107](https://github.com/mehdisafer/document-control-intelligence/actions/runs/44169464563/artifacts/14366358107) | `dfda3b1c40b9a89ae612ddb880da0499ecfc0094e8c44b3186f810310664dca3` |
| [Rejected Qwen 1.4 #14366438718](https://github.com/mehdisafer/document-control-intelligence/actions/runs/44170413325/artifacts/14366438718) | `f1f5877785a773da5b034b4e9d1e9130c68703b5568f9af20931775a20038cd0` |

The comparator checks ZIP CRC/paths, all 12 identical synthetic document
SHA-256s, manifest SHA, original scored fields against expected truth and
actual extraction, raw model JSON responses against decoded proposals,
prompt SHA uniformity, citations/critical fields, and source identity.

The expected evidence is **not a quality improvement**:
Qwen 1.3 vs 1.4 both classify 7/12 correctly and make 4/12 eligible
(below the 50% threshold); actual correct fields decline **90/156 to
74/156** and critical abstentions rise **60/120 to 74/120**.
A correct source comparator must refuse the new candidate under
`--require-nonregression` with **exit code 3**, while retaining the
source-linked aggregate JSON. A **green workflow** means the expected
negative model result was detected and provenance checked, **not** that the
generative Qwen model passed quality acceptance.

The workflow uploads only the aggregate comparison, source commit and ZIP
checksum receipts; it does **not** upload the raw original response ZIPs,
model/runtime binaries, or user/client data. It is intentionally
triggered only by its own source change, selected comparable code changes
or manual dispatch, **not** a recurring background model evaluation.

**Artifact expiration:** the original workflow ZIPs have finite retention
(14 days). After their expiration this replay will **fail visibly**, not
claim a PASS with substituted/rewritten evidence. This standalone qualification
should not be made a permanent required merge check without archiving the
original immutable inputs in an independently verified, authorized location.

The published rc1/rc2 tags, historical 3/36 Qwen failure, separate supplier
generalization, production-host approval and operator requirements are unchanged.

## Executed hosted replay — 17 November 2026

[PR #36 original-pair workflow #44187251064](https://github.com/mehdisafer/document-control-intelligence/actions/runs/44187251064) completed **successfully**, including original ZIP download, both SHA-256 checks, execution of the **actual checked-out comparator**, every evidence assertion, and verification of the expected nonregression **exit code 3**. The checkout source recorded in the run artifact is GitHub's PR merge-test commit `6834e38eda92f69166a951a231f6bbc7ac328e3b`, derived from candidate branch commit `125c808bfc18718860b9495d1f70d18854c66a0c` and the referenced main base. The comparator executable code is unchanged from the already qualified `main`.

[Original generated aggregate artifact #14373569905](https://github.com/mehdisafer/document-control-intelligence/actions/runs/44187251064/artifacts/14373569905), downloaded and independently inspected: **five ZIP members**, all CRC-valid, ZIP SHA-256 `03b55cacf7cf14bbc19973057a7280d66eeb7d3725c38ad1ae2e388aa876e105`. The two comparator-output JSON files are identical byte-for-byte, and `verdict.txt` explicitly records **exit code 3 expected and observed**. Original archive digests, manifest SHA, all 12 source document hashes, Qwen prompt identities and exact negative field/abstention metrics are source-bound in the JSON.

The narrow **hosted original-byte replay gate is met on this PR source**. Application CI and eventual merged-main verification must be checked separately before treating the new workflow as fully integrated. This remains a forensic/CI reproducibility result, **not** a model quality or production acceptance.

