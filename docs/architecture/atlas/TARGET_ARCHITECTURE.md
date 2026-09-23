# Target Architecture

Status: **PROPOSED / incremental target**, constrained by verified AS-IS invariants and the R3 thesis.

## Target principles

1. Keep one canonical authority path; no parallel authorization framework.
2. Treat the Core Kernel as a logical provider-neutral trust boundary, not a mandatory new service.
3. Model provider operations as Capability Cells with explicit authority, target, execution, verification and evidence contracts.
4. Keep terminal/profile strength server-owned and capability-bound.
5. Keep Runner execution and independent verification separate.
6. Persist enough final verification truth to survive restart without manufacturing evidence.
7. Keep deployment topology simple until scaling/isolation evidence requires separation.
8. Make architecture/capability status machine-indexed but never infer semantic adoption automatically.

## Logical target planes

| Plane | Target responsibility | AS-IS foundation |
| --- | --- | --- |
| Intelligence / Context | proposals, risk/context, CyberCore/AI inputs | context-only contracts; no authority |
| Governance / Authority — Core Kernel | current facts, approval, snapshot, grant, capability/profile binding | substantially implemented canonical prefix |
| Execution | bounded capability-specific Runner/runtime | legacy adapters + G8 Runner foundation |
| Verification | independent authoritative readback | verifier identities/credential decisions + `VerificationResult/v1` |
| Evidence / Experience | durable lineage, passport, UI/operator truth | receipts/audit/passport/control-room projections |
## Capability Cell target contract

A Capability Cell is an architectural contract, distinct from the existing evidence atom `OperationCell/v1`. Each cell should declare capability identity/version, target binder, permission requirements, terminal profile, effect class, preconditions, Runner/capsule contract, credential class, verification class, evidence tail, allowed environments and activation state.

Provider-specific code implements a cell; it does not create a provider-owned authorization silo.

## Near-term target deployment

Retain the modular-monolith control-plane deployment and SQLite for bounded non-production use while the first architecture migrations land. Do not couple the R3 vocabulary adoption to PostgreSQL, Kubernetes, external brokers or service decomposition.

Production architecture is a separate target track: released enterprise identity, released production persistence, secrets, network controls, backup/restore, observability/SLOs, signed supply chain and deployment/rollback evidence.

## Target evidence model

Persist an immutable/content-bound final independent verification projection linked to the existing execution lineage. Operation Passport should be able to distinguish `NOT_EVALUATED`, `NOT_VERIFIED`, `VERIFIED`, and invalid/inconsistent durable evidence without re-running provider effects.

## Target operator truth

Control Room topology/status should derive from an evidence-backed capability/architecture projection. Planned components remain visibly planned; absent runtime activation remains absent. Decorative topology must not outrank source truth.

This target deliberately preserves the existing canonical prefix instead of replacing it.