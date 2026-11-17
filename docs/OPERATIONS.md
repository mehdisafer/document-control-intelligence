# Operations, incident response and restoration

## Target and service objectives

Target: one Linux host, local SSD, at least 4 CPU cores and 8 GiB RAM for a small
team; the optional LLM needs a measured memory allocation in addition to workers.
Only the review API is bound to host loopback. Place a separately reviewed TLS and
identity layer in front of it before multi-user network access. The application
reference is not a public service deployment.

Proposed SLOs are operating targets, not availability measurements: queue age below
five minutes under the agreed small-document workload; zero duplicate publications;
zero accepted unverified critical fields; restoration of a tested snapshot within
30 minutes after provisioning dependencies/secrets. The local benchmark reports
observed latency/throughput separately. It is not a capacity or uptime guarantee.

`/healthz` reports process liveness only. Authenticated `/api/ready` checks storage
and reports queue state; it does not claim worker/model readiness. `/metrics`
exposes bounded queue status, oldest queued age, completed processing count/time
and publication count. Scrape with a reader token from external secret storage.
`infra/alerts.yaml` supplies actionable examples; no monitoring server is silently
installed. API logs contain request IDs/status/timing; worker logs link job,
document, case, attempt, stage outcome and error code without document text/tokens.
The upload response's `X-Request-ID` is retained in the immutable `document.ingested`
event alongside the job/document/case identifiers, joining API and worker evidence.

## Startup and shutdown

Run `dci init --home .data` once, then use `.data/config.json` for both API and
workers. Retain the separate actor credentials securely. Start one API and the
configured number of workers. Matching runtime/config/model digests are required
to process queued jobs. A changed policy does not silently reinterpret old work;
use the attributed manual retry flow after reviewing the change.

SIGTERM stops new claims and lets the current bounded stage finish. The reference
grace period is 240 seconds for workers. If a process dies, its lease expires and
the queue reclaims the job within the attempt allowance. Cancellation revokes
commit rights immediately; an already-running parser may consume its remaining
bounded stage time before exit. No cancelled result can become a publication.

## Runbooks

| Symptom | Inspect | Action |
|---|---|---|
| Queue full / HTTP429 | Queue depth/age and running worker count | Let admitted work drain; fix worker failure; add workers only within measured host capacity and configured cap. |
| `MODEL_UNAVAILABLE` / `MODEL_TIMEOUT` | Worker attempt count, local server logs, exact model/runtime digests | Restore the approved local runtime; allow bounded retries or use a reasoned manual retry. Never set an API fallback. |
| `MODEL_BUDGET` / `page_budget` / `size_budget` | Document size/pages and explicit configured limits | Request a smaller/supported document or review a versioned budget change; do not loop retry unchanged input. |
| `PROCESSING_POLICY_CHANGED` | Queued digest versus current parser/model/config and, for Qwen, **effective prompt text/version and executable LLM/extraction source identities** | Restore the matching policy or explicitly reprocess with a recorded reason; a queued local-LLM document must not silently cross a prompt/schema revision. |
| Parser crash or timeout | Stage/checkpoint identity, error code, resource availability | Keep input and evidence; investigate in the isolated parser. Do not infer OOM from SIGKILL alone. |
| Contradictory amounts/quantities | Source spans, arithmetic findings, cumulative reconciliation | Obtain a corrected source version or make an attributed human correction with justification. |
| Missing evidence / classification unknown | Original, abstention reason and original model proposal | Keep absent values in review. An operator can explicitly review a document type with a reason; retain the proposal and use a different approver. Type review never supplies missing field evidence. |
| `BLOB_INTEGRITY` / `EVIDENCE_CHANGED` | Original digest, backup manifest, append-only event history | Stop publication for the affected case; preserve evidence; restore a verified snapshot to a new location. |
| Stale revision / self-approval denied | Current revisions and correction authors | Refresh the source set or have another approver perform explicit acceptance. |

## Backup

```bash
uv run dci backup --config .data/config.json --output backups/snapshot-001
```

The command refuses an existing destination and a destination nested in live data.
SQLite's backup API captures a consistent database. The tool then copies exactly
the immutable blobs referenced by that snapshot and verifies each digest.
The manifest includes database/object hashes. Secrets and model artifacts are
excluded and require a separate secure provisioning plan. Protect backup access
the same way as original documents. A checksum is an integrity comparison, not an
authenticity signature or a substitute for trusted backup storage.

## Restore exercise

```bash
uv run dci restore --snapshot backups/snapshot-001 --output restored/snapshot-001
```

Restore validates the schema, SQLite integrity, exact set of database-referenced
objects and their hashes before creating the new destination. It never overwrites
live data. Interrupted leases are requeued with their attempt count retained and
an audit event; exhausted budgets remain blocked. Provision the same configuration,
actor identities and model artifacts, verify original hashes, and compare published
exports before redirecting the API/workers. Keep the earlier directory for rollback.

The default baseline demo executes this procedure and compares all seven published dossier exports
after restoration. `tests/test_operations.py` exercises corruption, missing files,
existing-destination refusal, interrupted work and concurrent snapshots.

## Migration and rollback

The package applies ordered SQL migrations under a write transaction. Schema1 is
the first release; a newer unsupported schema fails closed. Before any future
upgrade: stop admission, drain or checkpoint work, create/verify a snapshot, record
application/model/config identities, and migrate a restored copy. Re-run the
smoke workflow before switching paths. Schema downgrade is not implemented; restore
the prior snapshot with its prior package/model and replay reviewed new inputs if
an upgrade must be rolled back. Never copy only a live WAL `.db` file.

## Retention and storage

All originals, prior document versions, audit events and published snapshots are
retained in this release. `retention_days` is a review-policy parameter (default90),
not automatic disposal. Automatic deletion is deliberately unimplemented until an
operator retention/legal-hold policy is approved. Per-case retained-byte,
document-count and version caps prevent unbounded single-case admission. Track
total disk capacity at the host level; define an archival schedule before real
deployment. Never delete WAL/SHM files or immutable objects while the service runs.
