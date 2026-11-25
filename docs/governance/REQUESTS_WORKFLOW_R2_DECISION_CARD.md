# Requests Workflow R2 Decision Card

NÁZEV: Operator-first Requests workflow
UŽIVATEL: authorized VOODOO One operator and approver
PROBLÉM: request creation and approval exist, but capability effect, exact target and required
verification are not presented as one decision context; Capability Registry is a separate primary
navigation destination.
OČEKÁVANÝ OUTCOME: an operator reviews the exact request impact before creation and an approver sees
the bound target, effect and verification requirement before deciding.
RISK CLASS: `R2` — operator UI workflow; server policy and public API remain unchanged.
NEJMENŠÍ BEZPEČNÝ SLICE: consolidate capability context into Requests, add a client-side impact review,
and fail closed when exact approval context cannot be resolved.
ZDROJ PRAVDY: authorized `/control-room`, `/change-requests` and `/approvals` API responses; server
authorization remains authoritative.
DOTČENÁ DATA A OPRÁVNĚNÍ: read-only projections plus existing create/submit/decision actions; no new
permission, persistence owner or production effect.
DŮKAZ ÚSPĚCHU: behavior tests prove that creation requires a current impact review, changed input
invalidates the review, exact context is escaped and missing context removes decision actions.
ROLLBACK: revert the scoped HTML, JavaScript, CSS, tests and documentation patch. No data migration.
MIMO ROZSAH: backend policy changes, new adapters, execution changes, merge, deploy and production.
OWNER DECISION: approved by the project owner in the active conversation on 2026-11-25.

## 7×ANO

JEDNODUCHÁ: ANO — one bounded operator workflow.
ÚČELNÁ: ANO — removes a confirmed decision-context gap.
AUTOMATIZOVANÁ: ANO — browser contract tests cover the workflow.
BEZPEČNÁ: ANO — no new authority; missing context fails closed.
MĚŘITELNÁ: ANO — creation and decision-action gates are testable.
VRATNÁ: ANO — source-only patch without migration.
DŮKAZNĚ OVĚŘITELNÁ: ANO — exact diff and test results remain reviewable.

## R2 follow-through: Runs and Passport (2026-11-25)

Owner decision: continue the same vertical delivery in the existing isolated review branch,
including a local checkpoint commit and readiness checks. This extends presentation only:
reuse already validated canonical Passport rows from the existing Control Room composition,
merge by execution ID, retain canonical runtime status and display independent verification
separately. Missing verification stays UNKNOWN; COMPLETED is not SUCCEEDED.
Title/risk enrichment requires matching request workspace and environment. No additional
endpoint, persistence owner, permission, provider effect or execution action is introduced.

Acceptance: canonical and legacy rows remain visible, IDs are deduplicated, active/completed
counts use the bounded supplied projection, unbound metadata stays UNKNOWN, and the selected
Passport cannot be replaced by a stale or mismatched response. Rollback: revert the scoped
projection/UI/test changes or restore the exact pre-change backups outside the repository.
Existing audit/refactor checkout remains paused and untouched; reconcile this read-only
projection into that workstream only after the reviewed integration baseline advances.
Independent review and exact-commit readiness are separate acceptance gates.
No merge, push, deployment or production authorization is implied.
