# Critical Flows

## F1 — Local login/session

Client submits credentials to `/api/v1/auth/login`. The local identity path applies rate-limit controls, verifies credentials, issues a signed bounded-TTL token and records an active-session reference. Every bearer authentication revalidates the active session and current user/role.

Failure behavior: invalid credentials/rate limits fail authentication; revoked/expired sessions fail bearer authentication. There is no refresh-token/OIDC recovery path in the released implementation.

## F2 — Reviewed change -> legacy bounded execution

A requester creates/submits a change request. An authorized reviewer records a decision bound to reviewed content. An operator with `execution.run` calls the legacy execute route. `ExecutionService` checks idempotency, emergency stop, request approval, workspace/environment equality and production-effects gating, then creates a fenced running execution.

The selected allowlisted adapter runs outside the transaction. Completion transaction marks execution/request state and appends receipt + audit evidence. Adapter error yields `FAILED`; it is recorded rather than silently retried.

Recovery is separate: a security reviewer may recover only a `RUNNING` execution whose lease expired, and only while emergency stop is active. Recovery records `INTERRUPTED / INDETERMINATE`; it does not pretend an unknown effect was rolled back.
## F3 — Canonical GitHub READ

The canonical route requires outer `execution.run`, a bounded idempotency key and an explicitly active canonical runtime. The pipeline creates/revalidates current authority, selects the immutable READ terminal profile, persists Snapshot/Grant/consumption/dispatch/lease lineage, then the READ terminal activates a bounded Runner.

Runner reads GitHub with its credential, durable completion is recorded, then a separate Verifier identity and credential decision perform independent GitHub readback. Only this path produces `VerificationResult/v1`.

Failure behavior is fail-closed at every missing/mismatched binding. There is no automatic mutation rollback because the operation is READ-only. Current live G8 workflow additionally tests process interruption followed by resume of the same active execution with unchanged lineage.

## F4 — Canonical restart/resume

Resume starts from an existing execution ID and current actor authority. It reconstructs retained Snapshot/Grant/consumption/outbox/inbox/lease truth and rechecks database ownership, permission authority, profile registry, envelope revision and current fence. It must not create a second grant, consumption, dispatch admission or lease.

## F5 — Provider WRITE

Current reusable canonical mutation methods produce CREATE_REF/DELETE_REF preflight artifacts only. No canonical WRITE HTTP route or current provider mutation transport is active. Therefore AS-IS rollback for canonical provider WRITE is **BLOCKED**, not an imaginary happy-path arrow.

Sequence sources: [G8 READ](diagrams/as-is-g8-read-sequence.mmd), [legacy reviewed execution](diagrams/as-is-legacy-execution-sequence.mmd), [execution recovery](diagrams/as-is-recovery-sequence.mmd).