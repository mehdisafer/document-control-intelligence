# Acceptance matrix

This matrix separates implementation, execution and acceptance. The complete
[P04 scope issue](https://github.com/mehdisafer/document-control-intelligence/issues/1)
remains open until its unresolved criteria are handled. `0.1.0rc1` identifies a
reviewable candidate; it is not a production-readiness claim.

| Area | Implemented | Observed qualification | Remaining boundary |
|---|---|---|---|
| Unit/integration suite | Contracts, workflow, parsing/OCR, rules, model policy, recovery and complete ZIP-budget tests | 112 tests passed with no skips on source `8839be77`; the original 107-test run on `3ff93109` is retained | This local suite does not qualify deployment or browser rendering |
| Native PDF and OCR | Isolated parser, actual PDFium/Tesseract, source coordinates | Native/scanned demo and parser integrations execute | Bounded purchasing layouts; pure-native hidden-text authenticity is unqualified |
| Parser isolation | Linux seccomp, process budgets, page checkpoints | Active/encrypted/corrupt inputs, network denial, timeout and crash/recovery tests | Host/container layers have separate evidence |
| Statistical local model | Real training and safe JSON numeric inference | 30/36 eligible with 30/30 critical quality and zero false eligible on the final synthetic set | Small generator-derived sample; no supplier-general accuracy claim |
| Generative local model | Pinned Qwen/llama.cpp, typed selection, local-only router | Bounded replay: 36/36 actual requests, clean exit, 1.51 GiB peak RSS; prior failures retained | 3/36 correct classifications, 0/36 eligible; quality gate is not met |
| Deterministic rules | Financial checks, identifiers, cumulative partial matching | Unit and real workflow negative cases execute | Credit notes, returns, freight, FX and ambiguous repeated SKUs need another contract |
| Human decision | Attributed corrections, type review, role checks, revision-bound acceptance | Separate correction/acceptance actors and blocked self-approval exercised; supplemental subtotal repair publishes the seventh linear dossier | Scripted actor roles verify the workflow, not independent human approval; enterprise identity federation is outside the reference |
| Publication/export | Transactional idempotency, cross-case duplicate guard, original ZIP/JSON | Baseline: seven dossiers; unchanged local-linear demo: six; separate attributed repair: seven | The original strict seven-export assertion remains failed; consumers upsert superseding publications |
| Recovery | Leases, bounded retries, cancellation, backup/restore | Interrupted worker; seven baseline and six raw linear exports restored unchanged; separate repaired state restores all seven | Deployment-specific recovery objectives remain targets |
| Real HTTP boundary | Loopback API and separate worker, authenticated role actions and trace identifiers | 36 checks across 30 requests; three local-linear jobs; PDF/ZIP byte equality, denials, idempotency and all three request/audit/job joins | One sequential synthetic case; browser interaction and concurrent HTTP capacity are not measured |
| Worker load | Bounded queues, aging, global concurrency and batch loops | Nine PDFs per run; one/two workers at 2.08/3.92 documents/s with identical business outcomes | Small single-host Store-admission workload; no HTTP or distributed capacity claim |
| Browser | Complete operator/reader/approver/publisher interface and smoke harness | Local server starts; browser runtime is blocked by AF_UNIX restrictions; fresh browser fixture backend is exercised | CI receives no runner; real UI execution and screenshots remain unverified |
| UI state consistency | Session/selection guards, pending revision/status invalidation, captured dialog targets and disabled stale corrections | 23 JavaScript state/unit checks passed without skips on `8839be77` | Mocked DOM/fetch; rendering, PDF viewer and native focus/modal behavior remain unverified |
| Container | Pinned base, locked application, persistent volume, external secrets, quotas | CI is published and triggered | Jobs fail before runner allocation; image build and actual in-container demo remain unexecuted |
| Terraform | Docker network, retained volume and bounded containers | Local formatting and provider initialization succeed | Provider schema loading fails at its process handshake; the retained diagnostic does not identify the cause. CI receives no runner; validation and target apply remain unverified |
| Dependencies/licences | Locked graph, known-vulnerability audit, component inventory | Local audit finds zero known vulnerabilities among 32 runtime packages; inventory has no unreviewed family | Point-in-time tool result; native packages and own-project licence are separate |
| Project licence | Apache-2.0 text, attribution and package metadata | Explicitly selected by the maintainer on 2026-11-14 | Third-party components retain their separate notices |
| Public source publication | Apache-2.0 candidate, release notes, source/history and artifact review | Explicit maintainer authorization on 2026-11-14; candidate remains private at the prepublication observation | Apply/read back visibility and metadata with authenticated administration access, then verify anonymous access; overall P04 acceptance remains open |

The evidence index supplies final execution identifiers, commands, timestamps,
source hashes, original logs and CI links. A workflow definition, running service,
mock, skipped test or missing error message never counts as a passed integration.

## Remaining qualification and administration gates

1. Run browser, container and Terraform checks on an isolated environment with
   their actual prerequisites, then inspect outcomes and screenshots.
2. Explicitly accept the documented reference scope and additional linear-model
   review case, or improve model coverage using a new holdout. All original model
   results, adverse runs and the separate human-repair evidence are retained.
3. Review the actual deployment plan and exercise the service on the intended
   authorized host. Local tests and CI containers do not constitute a target rollout.
4. Configure repository description, topics and available protections through
   an authorized admin surface. The project-licence choice is resolved: Apache-2.0.
5. Complete the already-authorized public source publication: review source,
   history, issue/PR text, logs and artifacts, apply visibility through an
   authenticated administration surface and verify anonymous repository access.

Apache-2.0 was explicitly approved by the maintainer on 2026-11-14; see
[LICENSE](../LICENSE) and [NOTICE](../NOTICE). The subsequent public-source
instruction resolves the visibility decision. It does not authorize a paid
feature, public business service or target rollout, and no independent human
approval is invented. Public source-candidate publication and full operational
qualification are separate outcomes.

## Observed CI blocker

Source commit `3ff93109f3ea0d9c5f4bdfd598dd35bbd4513439` triggered
[push run 43527025131](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43527025131)
and [PR run 43527082481](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43527082481).
All three PR jobs have `runner_id: 0`, an empty runner name and `steps: []`.
They ended in failure before running the application. Dependabot's configuration
validation succeeded; it does not replace any integration gate.

The connector cannot retrieve the job-annotation endpoint, and log retrieval
returns `BlobNotFound`. The isolated cloud browser is not signed into the private
repository. The underlying account/runner rejection reason is therefore **unknown**;
no billing-limit explanation is asserted. An authorized runner/account configuration
that can allocate a runner, and access to the displayed failure annotation, are
the missing prerequisites. No billing or security setting was changed to get past it.
The original observation is in [github-actions-blocked.json](../evidence/platform/github-actions-blocked.json).

The same condition is observed on fixed source `8839be77`, including
[PR run 43601886497](https://github.com/mehdisafer/document-control-intelligence/actions/runs/43601886497):
all three jobs again have no runner or steps. The fresh
[public-source record](../evidence/publication/) separates the successful local
checks from this unresolved GitHub execution boundary.

The [local qualification](../evidence/qualification/) retains its original
`overall_requested_local_qualification_met: false`: the raw local-linear demo
did not meet its seven-export expectation. The later successful human repair and
real HTTP run have their own reports and do not overwrite that result.
