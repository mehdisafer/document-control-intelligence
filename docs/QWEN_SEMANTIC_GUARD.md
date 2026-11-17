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
