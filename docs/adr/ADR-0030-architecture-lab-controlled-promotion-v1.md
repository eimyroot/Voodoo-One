# ADR-0030: Architecture Lab and controlled promotion pipeline v1

| Field | Value |
|---|---|
| Status | PROPOSED — exact-content owner adoption required |
| Date | 2026-10-04 |
| Decision owner | Repository owner |
| Scope | Stable auditable Production Architecture, non-authoritative Architecture Lab, controlled promotion boundary |
| Risk class | R3 architecture / governance boundary |
| Runtime effect | None |
| Production effect | None |

## ADR identity reconciliation, 2026-10-11

Status: PROPOSED ONLY. This ADR-0030 candidate is not adopted.

This candidate is additionally renumbered from the unadopted Lab ADR-0029 to avoid colliding with a separately authored, parallel, also unadopted Architecture Graph ADR-0029. Neither historical Lab ADR-0026 adoption nor the previous Lab ADR-0029 proposal grants adoption of these new ADR-0030 bytes. Current integration baseline is main@2627b7d17064608059794347a6dd46fd40a7de11.

The architecture intent was separately adopted in the historical isolated Architecture Lab lineage as ADR-0026. Original immutable content SHA-256: 6ba4a935af4610280f0520c524ddab32c130de0124917e7a226e7231e3d0fa26; candidate commit: 23d2d8e7666fcac534c182b02196107218b3b295. The original exact-content owner adoption and register remain valid historical records in their own lineage. They do not automatically adopt this newly numbered document. The canonical main G8 machine-verifier ADR-0026 remains unchanged and adopted. A new exact-content owner decision plus register-only adoption is required for ADR-0030; implementation, runtime, provider effects and deployment are not authorized.

## Context

V-One already separates intelligence from authority, execution from verification, and current evidence from target intent. The hosted-main owner-adopted R3 Core Kernel + fractal capability framing preserves Monotonic Authority and explicit governance. The R4 Control OS platform-plane direction appears in the historical isolated engineering lineage and is not asserted as adopted by hosted main. The owner operating mandate also requires stronger evidence-backed architecture to challenge the current target through the normal ADR, security, migration, verification and rollback gates rather than self-promote. `CASER/VOODOO/IDEAS` already exists as a non-authoritative incubation space.

The project also needs a permanent way to search for better architectures without destabilizing the current baseline. Treating experimental designs as current architecture would create a second source of truth. Letting an optimizer promote its own design would violate the existing authority model. Freezing architecture indefinitely would create the opposite failure: a safe system that stops learning.

## Decision proposal

Use two deliberately separated lanes and one governed bridge:

```text
CURRENT / PRODUCTION ARCHITECTURE BASELINE
        |  immutable for a given evaluation
        |  telemetry + evidence only
        v
ARCHITECTURE LAB
        |  isolated challengers; no authority
        |  preregistered hypothesis + benchmark + security review
        v
PROMOTION CANDIDATE
        |  independent evidence review
        |  exact-content owner architecture decision
        v
SEPARATELY AUTHORIZED IMPLEMENTATION
        |  normal V-One review / verification gates
        v
NEW CURRENT BASELINE
```

`Production Architecture` in this ADR means the currently accepted/adopted architectural baseline used for comparison. It does not claim that provider WRITE, release, deployment, or production effects are enabled.

## Lane 1 — current architecture baseline

The current baseline remains defined by repository truth, adopted decisions, accepted descriptive architecture, tests, CI and runtime evidence according to the existing truth hierarchy. This ADR creates no replacement architecture document and no alternate authority registry.

For each experiment the baseline must be pinned to an exact source revision. A moving or ambiguous baseline makes the comparison invalid.

## Lane 2 — Architecture Lab

The lab lives under `CASER/VOODOO/IDEAS/ARCHITECTURE_LAB/` and inherits the existing `IDEA != ADOPTED DECISION != IMPLEMENTED != VERIFIED != RELEASED` invariant.

Lab artifacts MAY contain hypotheses, prototypes, alternate harnesses, model/runtime candidates, retrieval strategies, decision-model experiments, benchmark definitions and migration sketches.

Lab artifacts MUST NOT:

- grant, approve, authorize, execute, release or deploy;
- turn a deterministic DENY into ALLOW;
- widen current V-One authority or credentials;
- silently modify current architecture, policy, runtime or capability state;
- be imported by the canonical product runtime merely because they exist in the lab;
- treat benchmark success as adoption or implementation evidence.

## Candidate identity and provenance

Every promotion-track challenger must have a machine-readable candidate manifest conforming to `architecture-lab-candidate/v1` and pin at least:

- candidate id and lifecycle state;
- exact current baseline revision;
- hypothesis, baseline, success and failure criteria defined before evaluation;
- in-scope and out-of-scope boundaries;
- authority flags fixed to false;
- isolated experiment environment;
- metrics and guardrails;
- security risk class and required privileges;
- source/provenance identity, revision and licensing status where applicable;
- rollback/containment strategy;
- external evidence root;
- explicit statement that implementation, release and deployment authority are not granted.

## Promotion states

```text
IDEA
→ EXPERIMENTING
→ EVALUATED
→ PROMOTION_CANDIDATE
```

At any point a candidate may become `REJECTED` or `ARCHIVED`. `PROMOTION_CANDIDATE` means only that evidence is sufficient for an owner architecture decision. It does not mean adopted, implemented, released or deployed.

## Promotion gates

A candidate may reach `PROMOTION_CANDIDATE` only when all applicable gates are current and attributable:

1. **Baseline identity** — exact repository/current architecture revision is pinned.
2. **Candidate identity** — exact candidate source/artifact revision and provenance are known.
3. **Preregistered hypothesis** — metrics, success, failure and kill criteria existed before results were observed.
4. **Isolation** — experiment is non-production and cannot mutate canonical authority or protected runtime state.
5. **Security / supply chain** — required permissions, executable surface, dependencies, license and provenance are reviewed to the risk class.
6. **Objective evaluation** — representative project-specific benchmarks and negative cases are executed or explicitly marked not applicable with rationale.
7. **Contract and regression safety** — applicable VOP, policy, schema, security and regression invariants remain satisfied.
8. **Rollback / containment** — the candidate can be removed or safely contained without depending on undocumented memory.
9. **Evidence sufficiency** — an independent verifier accepts the evidence scope; missing evidence never counts as pass.
10. **No authority widening** — the challenger cannot weaken Monotonic Authority, approval separation, Runner/Verifier separation or READ-before-WRITE boundaries.

The gate result is fail-closed. `UNKNOWN`, `INDETERMINATE`, stale evidence, source drift or changed success thresholds blocks promotion.

## Adoption and implementation boundary

Promotion from the lab is never automatic. After `PROMOTION_CANDIDATE`:

1. the repository owner reviews the exact candidate and evidence;
2. a material architecture/trust-boundary decision is adopted through the existing ADR/adoption mechanism;
3. implementation receives a separate scoped authorization;
4. implementation is verified through normal tests, evidence and review gates;
5. release, deployment, provider mutation and production effects remain separate authorization boundaries.

An AI, CyberCore, harness optimizer, decision model, benchmark runner or Architecture Lab component may propose or rank candidates. None may approve or activate its own candidate.

## Measurement rule

The lab does not create one universal numeric architecture score. Each experiment defines metrics appropriate to the claimed improvement and guardrails that must not regress. Project-native 7Q, risk, security and evidence gates remain the governance filter; benchmark numbers are evidence, not authority.

This avoids false precision such as treating `96.5 > 95.8` as a scientific architecture verdict when the underlying weights are heuristic.

## Evidence

Generated benchmark output, traces, manifests, receipts and comparison reports belong under:

```text
/Users/eimyna/0_EVIDENCE/Voodoo-One/ARCHITECTURE_LAB/<candidate-id>/<run-id>/
```

They do not belong in the product worktree. Evidence must identify baseline revision, candidate revision, commands/methods, environment, passed/failed/not-run checks, digests, residual unknowns and a truthful conclusion.

## First pilot after adoption

Run one read-only dry-run using the lab candidate manifest and the current architecture baseline. The pilot proves the promotion process itself: pinned identities, preregistered gates, fail-closed unknowns, external evidence, independent review and no authority widening. It does not promote a runtime component.

## Non-goals

This proposal does not:

- activate a self-modifying production architecture;
- create a new authority, policy engine or approval path;
- change provider READ/WRITE eligibility;
- change current VOP semantics;
- install a model, framework, service, database or workflow engine;
- authorize commit, push, merge, release, deployment or production effect.

## Verification

For this documentation-only slice:

- validate Markdown links and repository documentation tests;
- parse the candidate schema and example as JSON;
- verify the example's authority flags are all false and promotion authorities remain `NOT_GRANTED`;
- run `git diff --check` and review the complete diff;
- preserve an external evidence receipt with exact HEAD and executed checks.

## Rollback

Before adoption or runtime integration, rollback is a normal repository revert/removal of the new ADR, decision card, lab contract/schema/example and documentation links. No database migration, persisted runtime state, provider resource or production cleanup is required.
