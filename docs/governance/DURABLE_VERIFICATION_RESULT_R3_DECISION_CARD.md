# Durable VerificationResult/v1 Persistence — R3 Decision Card

| Field | Decision |
|---|---|
| User | VOODOO One owner/operator |
| Problem | Canonical READ produces independent `VerificationResult/v1` only in process memory, so Operation Passport truth degrades to `NOT_PERSISTED / UNKNOWN` after the call/process ends. |
| Expected outcome | One immutable final `VerificationResult/v1` per execution is stored in the canonical SQLite database and can be revalidated by a fresh Operation Passport process without inferring verification from execution success. |
| Risk class | R3 — persistence, evidence integrity and security semantics |
| Smallest safe slice | Add one additive SQLite table/migration, one canonical durable store, runtime persistence before returning READ success, Passport read projection, and focused tests. |
| Source of truth | Current repository contracts: `VerificationResult`, canonical READ terminal, execution epoch state, dispatch outbox target binding and Operation Passport. |
| Data and permissions | Non-secret verification digests/claims only; no provider token, credential material or raw provider response is persisted. |
| Success evidence | RED→GREEN persistence/passport tests, schema migration/invariant tests, fresh-service passport projection, tamper/mismatch rejection and preservation of `UNKNOWN` when no result row exists. |
| Rollback | Revert the focused implementation before release. Migration is additive; no production migration is authorized or executed by this work block. |
| Non-scope | Provider WRITE, GitHub/live provider work, production/release/deploy, persistence of every intermediate verifier artifact, or recovery of a crash between durable Runner completion and verifier result creation. |
| Owner decision | 2026-09-19 explicit instruction to continue (`go`); GitHub work explicitly deferred. |

## Safety decision

The durable result must remain a separate independent-verification fact. A completed execution, receipt, audit-chain success or Runner completion digest must never manufacture `VERIFIED`. The store accepts only a canonical `VerificationResult/v1` and the database binds it to the same execution, epoch, target and Runner observation already represented by durable canonical state.

The public provider-effect ceiling does not change. This work persists evidence only and does not authorize or expose provider mutation.

## 7×ANO gate

```text
JEDNODUCHÁ: ANO — one immutable result table and one store owner
ÚČELNÁ: ANO — closes restart loss of final independent verification truth
AUTOMATIZOVANÁ: ANO — migration, startup schema gate and regression tests are local/CI runnable
BEZPEČNÁ: ANO — fail-closed bindings; no verification inference and no credential persistence
MĚŘITELNÁ: ANO — one-result constraint, exact digests, verdict and fresh Passport projection
VRATNÁ: ANO — additive schema/code slice; focused commit can be reverted before release
DŮKAZNĚ OVĚŘITELNÁ: ANO — migration, tamper, restart-like and runtime integration evidence
```

## Residual risk explicitly retained

Current READ ordering durably records Runner completion before independent verifier readback. This slice does not make that sequence atomic and does not claim recovery after a crash in that interval. Such an execution must remain completed with verification absent/unknown until a separately designed recovery contract exists.
