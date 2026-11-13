# Document Control Intelligence

Evidence-linked document control for a fictional industrial purchasing team.

## Product goal

Receive purchase orders, delivery notes and invoices, extract fields with verifiable
source references, reconcile the documents, and give an operator an explicit review
and publication workflow. All demonstration documents and suppliers are synthetic.

## Current state

The repository was empty when implementation started. This commit records the
scope; it does not claim an implemented or validated system.

## Acceptance priorities

1. Parse real native PDFs and scanned pages, preserving page and text/box references.
2. Compare a deterministic baseline with an actually executed local model.
3. Abstain when a critical value or its evidence cannot be verified.
4. Reconcile orders, deliveries and invoices, including legitimate partials.
5. Audit human corrections and enforce explicit review and publication roles.
6. Exercise duplicates, version changes, corruption, cancellation, parser/model
   failures, budget limits, bounded queues and recovery.
7. Generate an export from the live workflow and retain reproducible execution evidence.
8. Provide locked dependencies, containers, operations and restore procedures, CI,
   evaluation splits and clearly stated limitations.

The full acceptance matrix and implementation evidence will accompany the product
change. The repository remains private. A project license has not been selected;
no open-source license is implied. Third-party components retain their own terms.
