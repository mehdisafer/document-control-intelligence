# Development and evidence workflow

Work on one coherent change at a time and preserve the purchasing contract's
source, version and decision invariants. Use only synthetic or rights-cleared
documents. Keep credentials, live databases and original client data out of commits,
logs, screenshots and issues.

Install with `uv sync --frozen --group audit`. Run Ruff and the relevant real tests,
then the complete integration suite when a shared boundary changes. The demo and
load commands are in the README. Browser, container, model and target-deployment
checks have separate prerequisites and evidence; do not substitute one for another.
Run `node --test tests/test_ui_state.mjs` with Node 24 for review-state changes.
This dependency-free DOM/fetch harness checks asynchronous state and mutation
targets; real browser execution remains a separate workflow.

Shared Pydantic contracts live in `src/dci/models.py`; emitted schemas live in
`contracts/`. Parser, extraction, rules and persistence remain separate modules.
Any new extraction value must either carry verifiable source evidence or be
explicitly identified as a human correction or a calculated check result.

Never overwrite a prior qualification directory. Retain the command, environment,
source hashes, model/parser identity, inputs and original result. Freeze model
features/prompts/thresholds before final evaluation; use a new final holdout after
quality tuning. Report abstention quality and coverage together.

A PR should state the observed problem, resulting behavior, meaningful executed
checks and remaining limitations. Assisted author review must not be represented
as an independent human approval. Documentation-only updates do not justify
repeating expensive model/charge jobs, but references and acceptance claims must
remain consistent with the actual delivered source and evidence.

## Licence

Contributions to the original project are submitted under the [Apache License,
Version 2.0](LICENSE). Preserve project attribution and the separate notices for
any third-party components. Historical execution artifacts must remain unchanged
when licensing or packaging metadata is updated.
