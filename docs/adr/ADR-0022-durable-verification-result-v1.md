# ADR-0022 — Durable VerificationResult/v1 projection

Status: `PROPOSED`
Implementation state: `IMPLEMENTED_LOCALLY / R3 REVIEW PENDING`
Risk class: `R3`
Date: `2026-09-19`
Decision card: `docs/governance/DURABLE_VERIFICATION_RESULT_R3_DECISION_CARD.md`

## Context

The canonical `READ_ONLY_VERIFIED` terminal already produces a cryptographically self-validating `VerificationResult/v1` from an independent Verifier readback. The result is returned to the caller, but the current SQLite schema does not store it.

Operation Passport therefore correctly reports `verification.status = NOT_PERSISTED` and `verification.verdict = UNKNOWN`, even after a process-local READ returned a final verifier verdict. Execution completion, receipt integrity and audit integrity are deliberately insufficient to infer independent verification.

The shared durable prefix already contains enough binding material to validate a final result without creating a second authority graph: authorization snapshot, dispatch target, current execution epoch and the Runner observation digest recorded as durable completion.

## Decision

Persist exactly one immutable canonical `VerificationResult/v1` per execution in the released SQLite persistence boundary. Preserve the existing `VerificationResult` contract as the semantic owner; persistence stores and revalidates that exact contract rather than defining a competing verification model.

The product runtime persists the terminal-produced final result before returning READ success to its caller. The READ terminal remains responsible only for producing independently verified evidence and remains free of database ownership.

## Durable binding

The new persistence row duplicates only claims needed for indexed lookup and fail-closed binding while retaining canonical `result_json` as the full contract. At insert time the database must require:

```text
result.execution_id = authorization / dispatch execution
result.target_digest = dispatch target digest
result.execution_epoch = current durable execution epoch
execution epoch status = COMPLETED
result.runner_observation_digest = durable completion_digest
```

The row is immutable after insertion. A second exact store attempt is idempotent; a different result for the same execution is a conflict and must fail closed.

Operation Passport LEFT JOINs this result into the existing durable lineage. When no row exists, the existing `NOT_PERSISTED / UNKNOWN` projection remains unchanged. When a row exists, Passport decodes `VerificationResult.from_dict`, requires canonical JSON, validates duplicated columns and the durable execution/target/epoch/completion bindings, then exposes the stored verdict and digest.

## Ownership

- `verification_result.py` remains semantic owner of `VerificationResult/v1`.
- one new durable store owns persistence mechanics over the existing `ProductDatabaseAdapter`;
- `CanonicalOperationRuntime` is the orchestration seam that persists terminal output before returning success;
- `OperationPassportService` remains a read-only projection and creates no verification authority;
- ProductComposition requires the runtime store to share the exact ProductService database.

## Invariants

1. Execution success, completion, receipt existence or chain integrity never imply independent `VERIFIED`.
2. Only a canonical `VerificationResult/v1` produced after independent verifier readback can be persisted.
3. At most one final result exists for an execution.
4. Persisted result target, execution epoch and Runner observation must match durable canonical state.
5. Persisted verification is immutable.
6. Missing verification remains explicit `UNKNOWN`; absence is never treated as failure or success by inference.
7. Provider WRITE and production effects remain blocked and unchanged.
8. No raw Runner/Verifier credential, token or provider response is stored.

## Residual crash window

The current terminal records durable Runner completion before independent verifier readback. A process crash in that interval can therefore leave `execution_epoch_state_v1.status = COMPLETED` with no durable verification result. This ADR does not silently change resume semantics or synthesize a verifier result after restart.

A future recovery design may address that window, but it requires its own authority, credential and idempotency analysis. Until then Passport truth for that state remains `NOT_PERSISTED / UNKNOWN`.

## Schema evolution

Add SQLite migration `0015_durable_verification_results.sql`. The migration is additive and introduces no destructive rewrite of existing durable state. Startup schema validation must require the new table and its security triggers after migration 0015.

## Verification gates

- migration upgrades an existing v14 database to v15 without changing prior rows;
- dropping the required result table or immutable/binding triggers makes startup validation fail closed;
- store round-trips exact canonical `VerificationResult/v1` and rejects contradictory duplicates;
- database binding rejects wrong execution epoch, target or Runner completion digest;
- Passport preserves `NOT_PERSISTED / UNKNOWN` when no row exists;
- Passport rejects non-canonical, corrupted or lineage-mismatched persisted rows;
- a fresh `OperationPassportService` over the same SQLite database reconstructs the persisted result after a completed local READ;
- existing Runner/Verifier separation and G8 adversarial tests remain green.

## Rollback

Before release or production migration, rollback is the focused Git revert. No production migration is authorized by this ADR. If migration 0015 is ever released and data exists, schema rollback becomes a separately governed data operation; older application code can ignore the additive table but must not delete verification evidence without an explicit retention/migration decision.

## Non-scope

- persistence of every intermediate `VerifierIdentity`, boundary, credential decision, observation, `ObservedPostState` or `VerificationStrength` object as separate rows;
- provider WRITE or mutation authorization;
- production deployment or release;
- live GitHub acceptance;
- crash recovery between Runner completion and verifier readback;
- changes to `OperationProof/v2` or `OperationCell/v1` semantics.
