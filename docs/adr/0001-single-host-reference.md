# ADR 0001 — Single-host state and local inference

Status: accepted for the reference profile, subject to the measured acceptance matrix.

The first deliverable needs source-linked document decisions, real OCR/model
execution, recoverable processing and an operator interface. It does not yet need
several hosts. I use SQLite WAL plus an immutable object directory to make
transactional invariants and recovery inspectable with few operational dependencies.
This choice implements an actual persistent queue; it is not a Redis/PostgreSQL
integration claim. Moving beyond one host requires explicit storage/queue contracts,
not mounting the WAL database over a network share.

I separate parser processes from API requests and preserve page checkpoints.
libseccomp provides a real Linux network boundary for parsers; Docker adds resource
and filesystem isolation. The local statistical model offers a reproducible CPU
baseline with learned classification and field assignment. The generative Qwen
profile is separately evaluated and can remain unqualified without being hidden
behind another extraction profile.

Terraform manages only Docker resources actually supported by the pinned provider:
network, persistent volume and bounded containers. Compose is an alternative
deployment owner. Neither is applied to external infrastructure during development.
Container/CI execution status is recorded separately from source implementation.
