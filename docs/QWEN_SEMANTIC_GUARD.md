# Qwen semantic candidate guard — post-rc2, experimental

This change strengthens the source contract before any Qwen response can be
considered for extraction. The historical Qwen benchmark remains failed:
3/36 correct classes and 0/36 eligible. The 36 immutable old model responses
and their 406 original evidence files must never be re-labelled as passing.

## Rationale

The actual raw-trace audit found 35/272 selected candidate IDs assigned to a
different, independently recognized business field label. The legacy schema
permitted any candidate ID in every field; the independent verifier correctly
rejected the semantic mismatches later. The new source-level contract excludes
these invalid pairings already in the model's schema and rechecks the mapping
when a structured response returns, regardless of server grammar enforcement.

Each field now advertises only candidate IDs whose printed label matches
its versioned source-label contract, plus null for abstention. Real repeated
known labels stay in the pool and are still treated as potential contradictions
by the unchanged independent evidence validator. Unsupported URL/footer labels
are never authorized as value evidence. The existing row-ID and request-size
budgets remain in effect.

The local request also includes a bounded list of exact title quotations from
the parsed PDF (not a forced class and never a trusted document instruction).
This addresses a diagnostic blind spot where the former model request sent only
the first three text lines per page, while the independent title verifier
considered the entire parsed source. Exact titles and printed values remain
untrusted observations. Nothing here authorizes an unrecognised supplier layout.

## Scope and proof

- Prompt identity increments to structured-extraction-1.3. The frozen GGUF,
  runtime and original evidence remain unchanged.
- Eight deterministic unit tests exercise valid recognized labels, unknown
  malicious labels, semantically wrong known labels, duplicate IDs/rows,
  conflicting real subtotals, null abstention and bounded exact title signals.
- The current project CI tests parsing, browser, container and Terraform. These
  tests do not invoke the Qwen model and cannot prove a new model score.
- This changes development source after the immutable v0.1.0rc2 tag. A new
  Qwen run on a development set and a fresh unused holdout is required before
  any quality gate is closed. The prior final 36-PDF split cannot be used as
  a tuning set without contaminating acceptance.

This is a **candidate semantic/structural hardening**, not supplier-general
extraction accuracy, operational deployment or Qwen model acceptance.

## Executed source qualification — 17 November 2026

The experimental hardening is now **merged** through [PR #24](https://github.com/mehdisafer/document-control-intelligence/pull/24)
at development `main` SHA `b78104439c6614fbb8d3f2ab97e0899e4db047f6`.
[GitHub Actions #44165434992](https://github.com/mehdisafer/document-control-intelligence/actions/runs/44165434992) completed all three actual hosted
jobs successfully; CircleCI `build-and-test` succeeded at the same SHA.
The [original 43-file main artifact](https://github.com/mehdisafer/document-control-intelligence/actions/runs/44165434992/artifacts/14364034272) was downloaded and checked:
ZIP CRC passed, SHA-256
`f3f0814c65781c7d8193bc46ba09b0e492b232bd4510cf7953d2977f57f92520`.
The actual logs showed **162/162 Python**, **24/24 JavaScript**, **36/36 Chrome**
checks; the previous code-head test failure (legacy global candidate-ID test)
remains historical evidence and was corrected before the final PR-head rerun.

**Accepted only:** implementation and source-integrity tests of the
field-specific Qwen response schema and independent semantic validation.
**Not measured:** new Qwen 1.3 live responses, model accuracy, document
eligibility coverage, new/fresh holdout performance or CPU inference cost.
The original Qwen 3/36 correct, 0/36 eligible remains the latest *real*
generative model measurement and **fails the quality gate**. See the
[current consolidated post-release acceptance status](POST_RC2_QUALIFICATION.md).

## Subsequent real model experiment — 17 November 2026

The later [PR #26](https://github.com/mehdisafer/document-control-intelligence/pull/26)
ran the pinned Qwen GGUF with prompt 1.3 on the twelve **previously seen**
Node-generated synthetic development PDFs. Actual results were **7/12 class
correct, 4/12 eligible, 0 false eligible, 100% citation/semantic validity**,
with zero inference failures. The declared 50% development coverage threshold
was **not met** (4/12 = 33.33%). Both in-contract purchase orders were
classified unknown despite explicit titles, so the protocol 1.4 *experimental*
prompt now instructs the model to select the one unambiguous recognized
document title class, or unknown if none/conflicting. New real inference
qualification is required; no historical result changes.

The earlier paragraph describing Qwen 1.3 as unmeasured refers only to the
original source-hardening PR #24, **before** PR #26 ran inference.
