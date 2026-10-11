# VOODOO One — Quarterly Architecture Review, 2026 Q4

| Field | Value |
| --- | --- |
| Review basis | `PROJECT_CONSTITUTION.md`: quarterly and after material incidents |
| Review date | 2026-10-10 |
| Review status | IMPLEMENTATION CANDIDATE; integration and independent final acceptance pending |
| Baseline | `main@3e242bf6e8a7ff5e1e6c416d69314651ddd41e8b` |
| Isolated branch | `refactor/control-room-approval-index-20261010` |
| Effects | No provider WRITE, release, deployment, or production authorization |

## 1. Scope and evidence hierarchy

This review is a code-grounded engineering checkpoint, not a claim that the whole quarterly
architecture process or production acceptance is complete. Current executable source, Git
identity, migrations, integration tests and observed runtime outrank dated architecture
theses. The project Architecture Atlas provides the AS-IS map and drift checker; proposed
R3 target structures and experimental VOODOO-SOURCES graphs are not silently treated as
implemented architecture.

Canonical sources examined: `AGENTS.md`, `PROJECT_CONSTITUTION.md`,
`CURRENT_PRODUCT_STATE.md`, `ARCHITECTURE.md`, `docs/architecture/atlas/`,
`docs/governance/OWNER_OPERATING_MANDATE.md`, code, tests and the governed
skill-runtime architecture retrieval. The original quarterly rule states an inspection
cadence, not permission to activate effects.

## 2. Actual architecture and important data flows

VOODOO One is a Python 3.12 / FastAPI modular monolith. `main.py` and
`composition.py` configure one `ProductService` and shared SQLite database.
The HTTP boundary performs identity and permission checks, while service and
persistence owners implement two distinct flows:

1. Existing change-request path: reviewed request, approval and emergency-stop
   gates, bounded legacy adapter execution, receipt/audit evidence and controlled
   recovery after indeterminate execution.
2. Canonical READ path: reviewed intent, database-authoritative
   `AuthorizationSnapshot`, one-time `ExecutionGrant` consumption, durable
   dispatch/inbox/epoch/lease, bounded Runner READ, independent Verifier readback,
   durable verification, restart/resume and `OperationPassport`.

Control Room reads existing service/evidence projections. It is **not** the owner
of approval authority, immutable evidence, verifier verdicts, provider credentials,
or provider effects. The canonical G8 READ runtime is explicitly activated and
normally fail-closed. SQLite and in-process coordination are the implemented
baseline; multi-node persistence and external Runner isolation are target work,
not current production guarantees.

## 3. Findings and disposition

| Priority | Evidence-backed observation | Disposition |
| --- | --- | --- |
| P1 | `service.py` combines orchestration facade with pure read-only dashboard projections | EXTRACT pure projection owner behind compatibility methods; preserve exact API |
| P1 | Plan summary repeatedly scanned pending approvals for each displayed plan | IMPLEMENTED first-match indexed lookup in original local commit `c0b41b28e18c9b2e434ccea249a52f1c97d1c66c`, reapplied on current main as `d5fd172` |
| P1 | G8 READ runtime is a large compatibility-heavy trust component | DEFER broad extraction; require alias/identity, immutable credential, negative and live READ gates |
| P1 | Numerous repeated digest/field/timestamp validators have byte-identical bodies | DEFER mechanical de-duplication; equality of code does not establish equality of contract and error semantics |
| P2 | Control Room coordinates several sequential read sources and checks | MEASURE query timing and consistency before transactional redesign or caching; no current defect proof |
| P2 | SQLite and single-process orchestration have a multi-instance scaling ceiling | Separate ADR and operational load tests required; no opportunistic database replacement |
| P2 | AS-IS documentation and old snapshots may lag current main | Retain living Atlas/drift verification; mark dated evidence as historical |
| P2 | Production SLO metrics and incident alerting lack current acceptance | Separate observability slice; no false assumption of deployed alert coverage |

## 4. Executed behavior-preserving refactoring

The current isolated slice extracts the three **pure**, already-authorized Control
Room projections to `voodoo_product/control_room_projections.py`:

- `summarize_runs`
- `summarize_plans`
- `summarize_learning_intelligence`

The corresponding `ProductService` methods keep their names, arguments and output
contracts as thin compatibility wrappers. The existing `CONTROL_ROOM_LIMIT` is
supplied explicitly to helpers; no new global configuration or authoritative
state is introduced.

Characterization tests capture unchanged behavior for: ordered plan rows,
first matching duplicate approval, missing approval default, pending-approval
count, bounded displayed executions vs full supplied counters, missing receipt,
unknown observation states and Python round-to-even success rate. The module
does not query a database, authorize execution, call an external provider, or
infer verification from runtime completion.

Expected benefit: shrink orchestration facade, isolate read-only presentation
logic, reduce coupling for future Control Room performance instrumentation,
without changing transport, schemas or trust semantics.

## 5. Verification and integration gates

Require exact branch/HEAD, `git diff --check`, Ruff, compile, focused and
full system regressions, Atlas manifest check, independent review of the
scoped diff, then separate governed branch publication and CI if authorized.
Snapshot the observable Control Room response shape before any further extraction.
Provider READ/WRITE, authorization, persisted identities and verification owners
are explicitly out of scope.

The first plan-index slice passed 59 focused/system regression tests, Ruff,
compile and Atlas checks on original local `c0b41b2` (carried forward on PR #184 main as `d5fd172`). This quarterly follow-up adds
read-only extraction characterization tests and reruns those checks. Record
final full-suite results in separate evidence rather than retroactively
upgrading an incomplete run.

**Rollback:** revert only the isolated refactor commits; do not rewrite
the original ADR, migration history, or main. No production effects are part
of this review.

## 6. Quarterly follow-up queue

1. Finish and independently verify the full test suite on the exact candidate.
2. Review `ProductService.control_room` queries and measure query count, timing,
   boundedness and mixed-snapshot implications before optimizing persistence.
3. Classify each duplicate validator by contract revision and failure semantics;
   consolidate only independently characterized equivalences.
4. Define targeted internal modules for remaining large presentation/assembly
   components; do not break the G8 runtime compatibility aliases.
5. Reconcile Atlas against canonical main when the isolated refactor is accepted.

No automatic promotion or effect authorization results from this document.

## 7. 2026-10-10 exact-main reconciliation

During Q4 regression execution, protected GitHub main advanced independently through
PR #184 to `3e242bf6e8a7ff5e1e6c416d69314651ddd41e8b`. The seven changed
files concern hashed requirements lockfiles, lockfile drift enforcement and CI;
they do not overlap the five Control Room refactor files.

The original review plan tied to `428f201f0726092ce2744b631eb500e04bdcbad7`
and the older main is retained for evidence, but **superseded for integration**.
The two exact local commits were cherry-picked without rewriting their history
into a new clean worktree on the current protected main:

- `d5fd172` replays the approved plan-index optimization
- `6666aa4` replays the isolated pure-projection extraction and Q4 review document

A third documentation-only commit updates the integration baseline references.
The current candidate requires fresh exact-HEAD tests and a **new** canonical
publication plan with its own plan-bound approval. No push, merge, deployment,
release or production effects have been authorized by this reconciliation.
