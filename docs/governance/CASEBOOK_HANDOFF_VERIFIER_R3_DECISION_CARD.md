# CASEBOOK Handoff Verifier — decision card

| Field | Decision |
|---|---|
| User | authenticated VOODOO One operator inspecting one known CASEBOOK task |
| Problem | an intact journal does not establish that a governed V-One grant was consumed or bound to that task |
| Expected outcome | one read-only verifier distinguishes an exact local structural match from missing or conflicting evidence |
| Risk | T2 — cross-database trust and persistence evidence |
| Original smallest safe slice (historical) | verifier + disposable synthetic contract tests + proposed ADR; no writer or runtime attachment |
| Source of truth | current V-One grant/consumption contracts, SQLite rows, complete CASEBOOK hash chain |
| Positive claim | `LOCAL_CROSS_DATABASE_STRUCTURAL_MATCH` only |
| Explicit non-claims | identity, approval, Runner effect, independent verification, provider effect, production state |
| Rollback | focused revert/delete of the six candidate paths; no data migration or runtime state |
| Protected operations excluded | commit, push, merge, release, deployment, journal write, production effect |

## Acceptance gate

- exact match passes without changing either database;
- missing or mismatched consumption fails closed;
- a validly rehashed but different CASEBOOK payload binding fails closed;
- missing append-only/immutability trigger fails closed;
- production scope fails closed;
- output cannot be interpreted as independent attestation.

## Current status

`IMPLEMENTED_IN_ISOLATED_CANDIDATE / NOT_ADOPTED / NOT_RELEASED`.

The existing CASEBOOK CASER intake candidate remains a separate upstream
contract and is not modified by this slice.

## Integration candidate boundary

The current operator-workspace candidate implements exact Passport correlation and negative binding tests, and a disabled-by-default native local/staging reader attachment and scoped HTTP GET route. It requires the explicitly configured, pinned reader, exact session/project/workspace/environment binding, fresh native permissions and validated Passport lineage. The original pure verifier remains read-only. The candidate has not changed a running instance, has no writer, resume, execution or production authority, and does not authorize enabling the opt-in. Candidate remains NOT_ADOPTED / NOT_RELEASED; exact-content owner adoption of ADR-0031 and ADR-0032, independent review and runtime acceptance remain separate prerequisites.

Technical readiness PASS covers the testable candidate, not release or activation. The readiness report exposes CASEBOOK adoption separately; release-candidate verification requires matching exact-content adoption records, including the recorded ancestor commit and document bytes, and fails closed when they are missing or inconsistent. This does not itself grant release or runtime authority.
