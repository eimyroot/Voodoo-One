# Incremental Migration Plan

No step below is a big-bang redesign. Each phase has an evidence gate before the next widens scope.

## M0 — Freeze AS-IS and architecture truth

**Why:** refactoring against disputed architecture would destroy the baseline needed to prove semantic preservation.

**Change:** adopt this Atlas, add a machine-readable architecture manifest and objective drift checks.

**Files/components:** `docs/architecture/atlas/*`, future validation script, `tests/system/test_project_documentation.py`, CI.

**Risk:** brittle manifest paths or false confidence from automation.

**Verify:** manifest schema tests; current paths/routes/migrations/workflows resolve; intentionally removed fixture fails the drift checker.

## M1 — Complete repeated G8 evidence gate

**Status:** One exact-main acceptance is VERIFIED via the owner-authorized alternative external Linux run; repeated/full ADR-0019 evidence remains OPEN. Official GitHub Actions dispatch remains externally BLOCKED.

**Why:** authenticated HTTP READ, ACTIVE interruption/resume and independent readback are live-evidenced once, but one run is not repeated READ-before-WRITE proof.

**Change:** repeat the canonical acceptance semantics through an authorized path, retain sanitized evidence and close only directly demonstrated ADR-0019 gates.
**Files/components:** acceptance workflow/driver and evidence/status docs unless a repeated run exposes a confirmed product defect.

**Risk:** provider credentials/network isolation or failure injection may expose configuration/runtime defects.

**Verify:** exact-main source binding, distinct Runner/Verifier principals, authenticated HTTP READ, process interruption/resume, unchanged authority lineage, independent readback, repeated-run evidence and fail-closed injections.

## M2 — Complete durable verification truth

**Status:** IMPLEMENTED / LOCALLY VERIFIED; schema-v15 persistence post-dates the retained live-provider acceptance and therefore has not itself been exercised by that live run.

**Why:** process-local `VerificationResult/v1` previously could not survive into a restart-safe passport.

**Change:** define ADR/contract, add immutable persistence + statements/service projection, bind it to execution/passport lineage.

**Files/components:** verification model/store, `operation_passport.py`, `statements.py`, new SQLite migration, database/read-model tests.

**Risk:** schema compatibility, accidental inference of verification, duplicate/contradictory verifier records.

**Verify:** upgrade/rollback fixtures, one-result lineage constraints, restart passport test, tamper/mismatch negatives, no execution success -> verification promotion.

## M3 — Strengthen schema invariants

**Status:** IMPLEMENTED / VERIFIED LOCALLY under G-05.

**Why:** startup validation previously omitted later canonical durable tables/indexes/triggers.

**Change:** characterize current behavior with drop-table tests, then extend required schema/index/trigger invariants as justified.
**Files/components:** `db.py`, `tests/system/test_database_migrations.py`, possibly migration documentation only.

**Risk:** rejecting valid upgraded legacy databases if invariants are specified incorrectly.

**Verify:** current/upgrade fixtures pass; dropping each newly required object fails closed; migration checksum/history behavior unchanged.

## M4 — Refactor G8 assembly after characterization

**Status:** IN PROGRESS. Duplicate role-bound definitions are removed; pure immutable credential pin/pair guards are in `g8_credential_pins.py` and immutable assembly provenance guards are in `g8_assembly_guards.py`. Provider-effect execution, import-time implementation checks and public-builder pin boundaries remain unchanged.

**Why:** repeated hardening layers in `g8_read_runtime.py` make security review and maintenance expensive.

**Change:** split assembly/binding roles into explicit internal modules without changing public contracts, digests or authority semantics.

**Files/components:** `g8_read_runtime.py` and new focused internal G8 modules; activation/composition tests.

**Risk:** subtle ordering, identity, capsule or verifier-binding regression.

**Verify:** characterization tests first, exact moved-definition AST parity, existing G8/adversarial tests and broad cross-surface regressions; repeat live G8 acceptance before claiming full external-runtime equivalence for later material assembly moves.

## M5 — Make Control Room architecture truthful

**Status:** IMPLEMENTED / VERIFIED LOCALLY; backend AS-IS flow projection replaces pseudo-topology, and Runs now exposes a read-only Operation Passport drill-down.

**Why:** historical topology included labels with no AS-IS backend component.

**Change:** expose capability/runtime/status metadata from backend and render it instead of a hard-coded aspirational sequence.

**Files/components:** control-room projection in `service.py`, `static/control_room.js`, API/UI tests.

**Risk:** UI churn and accidental exposure of internal/security-sensitive data.

**Verify:** every rendered node maps to known capability/component/status; blocked/planned/runtime-off states are distinguishable.
## M6 — Production platform gates, separately

**Why:** product packaging is not production architecture.

**Change:** only after earlier trust-plane gates, design/release production persistence, enterprise identity, secrets, ingress/network boundaries, backup/restore, observability/SLOs, supply-chain signing and deploy/rollback automation.

**Files/components:** new adapters/IaC/runbooks/workflows plus existing config/composition boundaries; scope must be split into separate ADR-backed increments.

**Risk:** largest operational/security scope; dangerous if coupled to provider WRITE activation.

**Verify:** staged rehearsals, concurrency/failover tests, backup/restore and rollback drills, alert/SLO tests, exact artifact/source attestation. Production effects remain disabled until these gates are evidenced.

## Provider WRITE gate

Provider WRITE does not become `NEXT` from the single exact-scope M1 acceptance. Repeated/full ADR-0019 evidence remains incomplete. Each effect also requires its own current authority, precondition, credential, execution, verification, rollback, security, release and deployment decision.