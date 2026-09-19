# ADR-0021: Core Kernel + Fractal Capability Architecture

| Field | Value |
|---|---|
| Status | PROPOSED / REVIEW REQUIRED |
| Date | 2026-09-19 |
| Decision owner | Repository owner |
| Scope | Product/architecture framing and future capability composition |
| Baseline | `review/g8-cr31-runtime-activation-binding-20260919@b9a049c71e543b3e2d98c5c81ecdef6bcbc23966` |
| Risk class | R2 architecture / trust-model semantics; documentation-only effect in this change |
| Reversibility | REV-1: remove proposal docs/links; no runtime/state migration |
| Runtime effect | NONE |
| Production effect | NONE |

## Context

V-One already has a strong provider-neutral trust model, canonical VOP language, monotonic-authority
invariant, capability-bound terminal profiles, durable control-plane grant consumption, isolated
Runner boundaries and independent verification semantics.

The existing architecture is technically precise but is harder to explain as one scalable product
model. Product discussions also risk drifting toward two bad interpretations:

1. a large platform composed of vendor-specific mini-products; or
2. a generic recursive agent/workflow system where each module recreates governance and authority.

Neither matches the current V-One direction.

The repository already states:

```text
ONE SYSTEM = ONE SEMANTIC LANGUAGE
```

and:

```text
child authority ⊆ parent authority
```

while `VONE_PRODUCT_ARCHITECTURE_THESIS_R2` describes a small immutable trust kernel and a
conformance-tested module ecosystem.

The missing piece is an explicit composition model that explains how the same governed operation
contract can repeat across capabilities and scopes without duplicating authority.

## Proposed decision

Adopt, after required review, the following target architecture framing:

> **VOODOO One is one small provider-neutral Core Kernel surrounded by fractal Capability Cells that
> repeat the same governed-operation contract while authority only narrows downstream.**

`fractal` means semantic self-similarity of capability contracts. It does not mean recursive runtime
execution or self-authorization.

The detailed proposal is:

[`../architecture/VONE_PRODUCT_ARCHITECTURE_THESIS_R3.md`](../architecture/VONE_PRODUCT_ARCHITECTURE_THESIS_R3.md)

## Core Kernel boundary

The logical Core Kernel owns canonical semantics for:

- VOP operation identity;
- current permission/policy/approval bindings;
- AuthorizationSnapshot;
- monotonic authority;
- ExecutionGrant and control-plane consumption semantics;
- capability→terminal-profile authority;
- Runner authority ceiling;
- independent-verification semantics;
- profile-correct evidence lineage.

The Core Kernel is not automatically a new service, process, database or package.

## Capability Cell boundary

A Capability Cell is a governed capability contract and its conforming provider implementation.

It may contain provider-specific target binding, execution, verification, recovery and evidence
requirements, but it may not become a parallel owner of canonical identity, policy, approval or grant
issuance.

`Capability Cell` is an architectural term and is explicitly distinct from canonical
`OperationCell/v1` evidence semantics.

## Fractal authority rule

The common lifecycle may repeat across composed scopes/capabilities, but authority does not recursively
copy itself.

A child operation must be independently authorized as required by its capability contract.

Where composition supplies a parent ceiling:

```text
S_child_effective ⊆ S_child_authorized
S_child_effective ⊆ S_parent_ceiling
```

No current contract is generalized to wildcard or hierarchy semantics by this ADR. A future richer
subset algebra requires a separately versioned schema and conformance tests.

## Current runtime remains authoritative

This proposal does not alter the current canonical prefix:

```text
ReviewedOperation
→ Approval / ApprovalCertificate
→ AuthorizationSnapshot
→ ExecutionGrant/v2
→ GrantConsumptionWitness/v1          [CONTROL PLANE ONLY]
→ DispatchOutboxEntry/v1
→ DispatchEnvelope/v1
→ DispatchInboxAdmission/v1
→ ExecutionEpoch + ExecutionLease/v1
→ ExecutionCapsule/v1
→ capability-bound terminal profile
```

It also preserves current profile-specific terminals:

```text
READ_ONLY_VERIFIED          → VerificationResult/v1 → STOP
BOUNDED_MUTATION_VERIFIED   → Receipt/v2 → VerificationResult/v1 → Proof/v2 → Cell/v1
```

## Security consequences

Positive:

- makes one authority owner per decision explicit;
- makes provider modules easier to constrain and conformance-test;
- reinforces monotonic authority;
- reduces risk of vendor-specific policy/approval forks;
- prevents `fractal` from becoming a euphemism for recursive autonomous authority;
- gives future Operation Graph work a clear no-implicit-inheritance rule.

Risks:

- the word `fractal` can be misread as runtime recursion;
- `Capability Cell` can be confused with `OperationCell/v1`;
- hierarchical scope language can accidentally overstate currently implemented subset semantics;
- an oversized "kernel" can become a central monolith if provider/runtime responsibilities leak in.

Required mitigations are explicit terminology, current-vs-target labels, machine-enforced VOP identity
and no provider SDK imports in the authority kernel.

## Alternatives considered

### A. Keep R2 language only

Valid, but it leaves the product composition model implicit and makes provider/module expansion harder
to explain consistently.

### B. Provider-oriented modules as primary architecture

Rejected. It encourages AWS/GitHub/Kubernetes product silos and duplicated governance behavior.

### C. Recursive autonomous agent graph

Rejected. It weakens the singular V-One authority model and creates implicit delegation risk.

### D. Microservices-first trust kernel

Rejected. Current modular-monolith boundaries are adequate and a process split is not justified by
this terminology decision.

## Adoption gate

Before this ADR may become ACCEPTED, review must confirm:

1. consistency with `PROJECT_CONSTITUTION.md` and `SECURITY.md`;
2. consistency with current `ARCHITECTURE.md` and `CURRENT_PRODUCT_STATE.md`;
3. no conflict with canonical VOP vocabulary or terminal profiles;
4. no weakening of control-plane grant consumption;
5. no Runner/Verifier authority collapse;
6. no current capability/runtime/release status upgrade;
7. exact distinction between `Capability Cell` and `OperationCell/v1`;
8. architecture/security owner acceptance of the R3 thesis exact content.

## Verification for this documentation-only slice

Required repository checks:

```text
git diff --check
.venv/bin/python -m pytest -q tests/system/test_project_documentation.py tests/system/test_vop_canonical_vocabulary.py
```

Review must also inspect all modified paths and confirm no source/runtime/configuration file changed.

## Rollback

Before adoption, rollback is:

1. remove this ADR;
2. remove `VONE_PRODUCT_ARCHITECTURE_THESIS_R3.md`;
3. remove documentation-index/current-architecture proposal links.

No database, API, runtime, release, provider or production rollback exists because this slice has no
runtime effect.

## Non-goals

This ADR does not authorize or implement:

- a new runtime service;
- a `CapabilityCell` Python class or schema;
- a new policy engine;
- a new database;
- provider WRITE;
- production effects;
- Operation Graph runtime;
- recursive agent execution;
- CyberCore mutation authority;
- release or deployment;
- merge or adoption by documentation presence alone.
