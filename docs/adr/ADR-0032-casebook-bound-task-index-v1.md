# ADR-0032: CASEBOOK authorized bound task index

Status: PROPOSED — isolated implementation candidate; exact owner adoption and independent review pending.
Date: 2026-11-25
Scope: local/test CASEBOOK read-only discoverability, R2 presentation / R3 authorization review.

## Decision

Reuse the explicitly attached CasebookTaskGateway. GET /api/v1/casebook/tasks returns at most 50 authorized, server-bound session IDs and project/workspace/environment metadata, plus has_more and NOT_CHECKED_BY_INDEX. Re-evaluate each binding against the native principal and current database permission authority. Filter denied scopes without disclosing their count. No journal reader call, filesystem discovery, new grant, persistence, credential, production activation or execution. Existing exact-session detail continues to perform all current authorization and integrity checks. The console uses no-store and discards stale responses on token change or index refresh. An unconfigured attachment or authority failure is unavailable, not an empty verified journal.

## Threats and acceptance

Cross-workspace disclosure: deny-by-default and exact permission decision binding. Revocation: native session authentication and fresh DB checks. Untrusted rendering: escape labels and IDs, validate schema; detail read still authorizes independently. Availability: bounded returned rows, scan limited to explicit configuration (currently one scope in native composition). No verification claims from metadata. Test unauthenticated, revoked, unauthorized scope, unconfigured gateway, and no journal reads during discovery. No automatic retries, no execution authority.

## Exclusions and rollback

No automatic discovery of unbound tasks, no session-to-Passport inference, no resume execution from notes. A durable binding and a separately reviewed native resume operation are required for these. No changes to permission policy or existing pinned CASEBOOK source. Roll back exact candidate source changes without modifying journals. Local candidate only; production/release and independent review remain separate.
