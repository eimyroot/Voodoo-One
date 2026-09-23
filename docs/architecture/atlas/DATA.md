# Data Architecture

## Primary store

The released product persistence path is one SQLite database owned by `ProductService`. Canonical authority/runtime components are required to share that exact database instance.

## Main entity groups

| Group | Durable entities / tables | Ownership / mutation boundary |
| --- | --- | --- |
| Identity | `users`, `active_sessions`, `auth_rate_limits`, `external_identity_bindings` | identity/session/account services |
| Workspace | `workspaces`, `workspace_memberships` | workspace service; membership is explicit, not inferred |
| Review/governance | `change_requests`, `approvals` | change-request/approval services with immutable review binding |
| Legacy execution | `executions` | execution service + recovery fencing |
| Evidence | `receipts`, `audit_events` | receipt/audit ledgers; hash chained |
| Runtime control | `runtime_flags` | operational safety, including emergency-stop state |
| Canonical authorization | `authorization_snapshots`, `execution_grants_v2`, `grant_consumptions_v1` | canonical snapshot/grant services |
| Canonical dispatch | `dispatch_outbox_v1`, `dispatch_inbox_v1` | durable dispatch services/coordinator |
| Canonical fencing | `execution_leases_v1`, `execution_epoch_state_v1` | durable coordinator/current fence |
| Canonical verification | `verification_results_v1` | immutable final `VerificationResult/v1`; exact execution/epoch/target/completion binding |
| Migration history | `schema_migrations` | database initializer; checksummed migration history |

`receipts_v3` and `receipt_sequence_migration_guard` are migration-time structures in `0003`; `receipts_v3` is renamed to the canonical `receipts` table.
## Key data flows

Canonical READ preparation mutates durable authority state in this order: reviewed request/approval truth -> AuthorizationSnapshot -> ExecutionGrant/v2 -> one-time grant consumption + Outbox -> Inbox admission -> execution epoch/lease. The READ terminal then performs provider observation and durable completion before independent verification.

Legacy execution writes `executions`, updates the linked `change_requests` status, then appends receipt and audit evidence. Recovery may mark an expired running execution as interrupted/indeterminate, but only while emergency stop is active.

## Durable verification result

Schema v15 adds `verification_results_v1`. Canonical READ runtime persists the exact terminal-produced `VerificationResult/v1` only after durable completion. SQLite rejects premature/mismatched inserts, the store rejects conflicting second results, and Operation Passport revalidates canonical JSON plus execution/epoch/target/completion lineage after restart. Absence remains `NOT_PERSISTED / UNKNOWN`.

## Startup schema invariants

`db.py` now explicitly requires the durable canonical tables, indexes and binding/immutability triggers introduced by migrations `0010-0013`, in addition to the older core schema invariants. Post-migration manual loss of those objects therefore fails closed on initialization instead of relying only on migration history/checksums. The change is covered by 35 parameterized negative object-loss tests.

Primary diagram: [as-is-data.mmd](diagrams/as-is-data.mmd).