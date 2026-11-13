# Acceptance matrix

This matrix separates implementation, execution and acceptance. The complete
[P04 scope issue](https://github.com/mehdisafer/document-control-intelligence/issues/1)
remains open until its unresolved criteria are handled. `0.1.0rc1` identifies a
reviewable candidate; it is not a production-readiness claim.

| Area | Implemented | Observed qualification | Remaining boundary |
|---|---|---|---|
| Native PDF and OCR | Isolated parser, actual PDFium/Tesseract, source coordinates | Native/scanned demo and parser integrations execute | Bounded purchasing layouts; pure-native hidden-text authenticity is unqualified |
| Parser isolation | Linux seccomp, process budgets, page checkpoints | Active/encrypted/corrupt inputs, network denial, timeout and crash/recovery tests | Host/container layers have separate evidence |
| Statistical local model | Real training and safe JSON numeric inference | 30/36 eligible with 30/30 critical quality and zero false eligible on the final synthetic set | Small generator-derived sample; no supplier-general accuracy claim |
| Generative local model | Pinned Qwen/llama.cpp, typed selection, local-only router | Bounded replay: 36/36 actual requests, clean exit, 1.51 GiB peak RSS; prior failures retained | 3/36 correct classifications, 0/36 eligible; quality gate is not met |
| Deterministic rules | Financial checks, identifiers, cumulative partial matching | Unit and real workflow negative cases execute | Credit notes, returns, freight, FX and ambiguous repeated SKUs need another contract |
| Human decision | Attributed corrections, role checks, revision-bound acceptance | Separate correction/acceptance actors and blocked invalid publication exercised | Enterprise identity federation is outside the reference |
| Publication/export | Transactional idempotency, cross-case duplicate guard, original ZIP/JSON | Seven actual demo dossiers exported | Consumers must upsert superseding case publications |
| Recovery | Leases, bounded retries, cancellation, backup/restore | Interrupted worker and seven restored published exports checked | Deployment-specific recovery objectives remain targets |
| Worker load | Bounded queues, aging, global concurrency and batch loops | One/two-worker actual-PDF workload with outcome comparison | Small single-host execution; no distributed capacity claim |
| Browser | Complete operator/reader/approver/publisher interface and smoke harness | Local server starts; browser runtime is blocked by AF_UNIX restrictions | Real browser execution and screenshots require a capable isolated runner |
| Container | Pinned base, locked application, persistent volume, external secrets, quotas | Docker job is defined in CI | Image build and actual in-container demo are separate pending checks until a run succeeds |
| Terraform | Docker network, retained volume and bounded containers | Local formatting and provider initialization succeed | Local provider IPC is blocked by AF_UNIX; remote schema validation and target apply are separate |
| Dependencies/licences | Locked graph, known-vulnerability audit, component inventory | Local audit finds zero known vulnerabilities among 32 runtime packages; inventory has no unreviewed family | Point-in-time tool result; native packages and own-project licence are separate |
| Public release | Release notes and repository settings prepared | Private repository and author-side review only | Explicit licence/visibility decisions and administration access remain required |

The evidence index supplies final execution identifiers, commands, timestamps,
source hashes, original logs and CI links. A workflow definition, running service,
mock, skipped test or missing error message never counts as a passed integration.

## Remaining release gates

1. Run browser, container and Terraform checks on an isolated environment with
   their actual prerequisites, then inspect outcomes and screenshots.
2. Retain all final model/runtime results and explicitly accept the reference
   scope or improve generative classification using a new holdout.
3. Review the actual deployment plan and exercise the service on the intended
   authorized host. Local tests and CI containers do not constitute a target rollout.
4. Obtain the maintainer's explicit project-licence choice; configure repository
   description, topics and available protections through an authorized admin surface.
5. Before any separately authorized public visibility change, review source,
   history, issue/PR text, logs and artifacts, then verify anonymous repository access.

No paid feature, public service, visibility change, licence selection or
independent human approval is inferred from this implementation work.
