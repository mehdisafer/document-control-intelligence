# Execution evidence

This directory contains selected original qualification artifacts and a publication
map to the delivered source. The complete application generates its own evidence:
the demo parses actual PDFs, runs the selected local model, records human decisions,
exports dossiers and compares them after a real restore.

Evidence is divided by execution. Adverse model runs, local environment blockers
and original denominators are retained. A runtime failure is not converted into a
successful abstention. No screenshots are created when the browser cannot run.

Raw credentials, authentication configurations, live databases and personal/client
documents are excluded. Published document examples are synthetic. Historical
reports with `git_commit: null` retain that value and their original source hashes;
a subsequent mapping identifies the commit with those bytes without pretending
that the commit existed at execution time.

See [evaluation](../docs/EVALUATION.md) for metric definitions and limitations,
[acceptance](../docs/ACCEPTANCE.md) for separate implementation/execution gates,
and the PR for the final source and actual CI links. A hash establishes content
agreement, not an independent audit or certification.
