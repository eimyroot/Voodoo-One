# Architecture Roadmap

Status is evidence-scoped and applies to the stated scope only.

## VERIFIED

- Canonical repository/bootstrap/governance hash and current source inventory.
- AS-IS API, migration, dependency/import and deployment-file inventory.
- Ruff + Python compile checks on the audited tree.
- 68 architecture-critical tests: migrations, composition, G8 activation/workflow contract, passport, documentation.
- Additional 112 current product-boundary tests: auth/session, permissions/workspaces, change requests, legacy execution/idempotency/recovery, receipts, HTTP security and operational safety.
- No internal Python import cycles in the scanned top-level `voodoo_product` graph.
- G-05 startup schema invariants for all durable canonical tables/indexes/triggers introduced in migrations `0010-0013`; 35 negative object-loss tests plus broader migration/runtime gates pass.
- One exact-main G8 READ acceptance is `VERIFIED_ALT_EXTERNAL_LINUX`; official GitHub Actions parity remains externally blocked.
- G-02 durable `VerificationResult/v1` persistence + restart-safe Passport projection is locally verified and fresh live READ verified under schema v15 on runtime source `f417d780...`.
- R3 Core Kernel + Fractal Capability Architecture exact bytes are effectively ADOPTED through the authority register; runtime realization remains separately gated.
- Control Room AS-IS architecture projection, read-only Operation Passport drill-down, durable Verifier Center projection and bounded canonical/legacy Evidence Timeline convergence are implemented and targeted-verified on the current PRIMARY.

## IMPLEMENTED BUT NOT VERIFIED

- Repeated/full ADR-0019 READ-before-WRITE closure beyond the retained historical exact-main run plus the fresh schema-v15 live READ run.
- Release-candidate workflow execution on the current source line.

## IN PROGRESS

- Core Kernel / Capability Cell runtime realization planning after target-governance adoption.
- Living Architecture Atlas iterative maintenance and evidence-manifest expansion.
## NEXT

1. Prepare the governed review-publication strategy from reconciled PRIMARY `081adce...`; stale PR #166 is superseded for new development/review composition and must not be merged as-is.
2. Build repeated/full ADR-0019 acceptance evidence; restore official GitHub Actions parity when account eligibility returns.
3. ✅ Durable independent verification projection under ADR-0022 + migration `0015`; local restart/passport/conflict/binding gates PASS.
4. Continue behavior-preserving G8 assembly extraction after topology/builder-pin characterization and duplicate-class cleanup.
5. ✅ Control Room architecture truth + read-only Operation Passport drill-down.

## BLOCKED

- Official GitHub Actions G8 parity is externally BLOCKED: GitHub returns HTTP 422 `Actions has been disabled for this user` before creating a run, despite repository Actions enabled and the workflow active. Product READ acceptance is separately `VERIFIED_ALT_EXTERNAL_LINUX` on exact `main@2f9ab7f...`.
- Canonical provider WRITE activation until READ-before-WRITE and effect-specific gates pass.
- OIDC until a released provider implementation and security/operations evidence exist.
- PostgreSQL/HA until a released adapter and concurrency/migration/backup/recovery gates pass.
- Production effects/release/deployment until production architecture, observability, secrets and rollback controls are evidenced.
- CyberCore mutation/runtime authority; CyberCore must remain context/intelligence until separately governed integration exists.

## LATER

- External broker or service decomposition, only if measured scaling/isolation demands it.
- Persistent multi-environment IaC, richer ProofGraph anchoring, signed multi-platform distribution.
- AI Change Copilot/outcome-learning loop and broader capability graph composition.
- SandCloud/Kubernetes/cloud Capability Cells only after concrete provider contracts exist.