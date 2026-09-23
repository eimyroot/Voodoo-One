# V-One Product & Architecture Thesis R3 — Core Kernel + Fractal Capability Architecture

| Field | Value |
|---|---|
| Document class | Product and target-architecture thesis |
| Status | PROPOSED / REVIEW REQUIRED |
| Baseline | `review/g8-cr31-runtime-activation-binding-20260919@b9a049c71e543b3e2d98c5c81ecdef6bcbc23966` |
| Date | 2026-09-19 |
| Adoption authority | Explicit owner adoption plus required architecture/security review |
| Runtime effect | NONE |
| Release / deploy effect | NONE |
| Supersedes | Nothing until explicitly adopted |
| Builds on | `VONE_PRODUCT_ARCHITECTURE_THESIS_R2`, ADR-0012, current VOP/runtime truth |

## 0. Purpose

This thesis proposes a simpler target mental model for VOODOO One without changing the current
runtime authority chain:

> **One small trust kernel. One authority model. Fractal capability cells. Many providers.**

The proposal names two concepts that are already strongly implied by accepted/current V-One work:

1. **Core Kernel** — the small provider-neutral trust/authority semantics that every consequential
   operation must obey.
2. **Fractal Capability Architecture** — the same governed capability contract repeats at different
   product scales, while authority always narrows and canonical decision ownership remains singular.

`fractal` is a composition model. It does **not** mean recursive self-authorization, recursive runtime
execution, duplicated policy engines, autonomous child agents, or implicit authority inheritance.

This document is target architecture only. It does not activate a provider pack, enable WRITE,
change production state, alter current terminal profiles, or claim adoption merely because it exists.

## 1. Product identity

VOODOO One remains:

> **Governed Operations Control Plane for Human and AI Execution**

Technical description:

> **Provider-neutral control plane for proof-carrying operations.**

Its stable job is to turn consequential intent into a governed operation whose authority, execution
and observed result can be reconstructed and challenged.

The product should optimize for:

```text
MORE USEFUL CAPABILITY
+
LESS STANDING PRIVILEGE
+
MORE PRECISE CONTROL
+
STRONGER INDEPENDENT EVIDENCE
```

not for provider count, agent autonomy, or command throughput by themselves.

## 2. The Core Kernel

### 2.1 Definition

The Core Kernel is the smallest logical boundary that owns the semantics required to answer:

```text
What exact operation is under review?
Who may request it?
What exact authority facts apply?
What was approved?
What bounded authority may be issued?
Can downstream execution widen that authority?  NO.
What terminal profile is allowed?
What evidence is required before an outcome may be called verified?
```

The Core Kernel is a **logical trust boundary**, not a requirement to create a new microservice,
process, database or package.

Current modular-monolith packaging remains valid. Extraction is justified only by a demonstrated
trust, scaling or operational boundary.

### 2.2 Kernel-owned semantics

The kernel owns or canonically binds the semantics of:

```text
Actor / Principal
ReviewedOperation
Capability identity
Authoritative Target
Policy / Permission decision facts
Approval / ApprovalCertificate
AuthorizationSnapshot
Monotonic Authority
ExecutionGrant
GrantConsumptionWitness
Dispatch authority continuity
ExecutionCapsule binding
Capability → Terminal Profile binding
Runner authority ceiling
Verifier separation
VerificationResult semantics
Evidence lineage semantics
```

Provider SDK behavior, provider transport, cloud-specific resource models, AI reasoning and UI
presentation stay outside this semantic kernel.

### 2.3 Current canonical prefix remains unchanged

This proposal preserves the current authority/execution prefix exactly:

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

Non-negotiable current facts:

- the control plane consumes the ONE_TIME grant before Dispatch;
- the Runner never issues or consumes an ExecutionGrant;
- Dispatch, lease and epoch coordinate execution but do not create authority;
- terminal profile strength is resolved server-side from immutable capability identity;
- restart/resume reconstructs the same already-authorized execution and mints no new authority.

## 3. Kernel invariants

### K1 — Deny by default

Unknown or indeterminate protected authority state cannot become permission.

### K2 — Intelligence is not authority

```text
proposal != approval
reasoning != authorization
AI text != runtime evidence
telemetry != proof
```

CyberCore and other intelligence sources may observe, correlate, explain and propose. They do not
become a parallel V-One authority system.

### K3 — Approval is not authorization

Approval binds reviewed content. Authorization derives the exact permitted authority from current
facts and policy. An approval object is not an ExecutionGrant.

### K4 — Authority is monotonic

For effective authority scopes `S`:

```text
S_grant      ⊆ S_snapshot
S_credential ⊆ S_grant
S_runner     ⊆ S_grant
S_handler    ⊆ S_grant
```

Downstream components may preserve, narrow, expire, revoke or deny authority. They may not widen it.

### K5 — Parent operations do not silently authorize children

A composed child operation receives no implicit authority merely because a parent operation was
authorized.

A child must be independently normalized, policy-evaluated and authorization-bound as required by its
capability contract.

Where a parent workflow imposes an authority ceiling, the child must satisfy both its own authority
and that ceiling:

```text
S_child_effective ⊆ S_child_authorized
S_child_effective ⊆ S_parent_ceiling
```

A richer hierarchical subset model is PROPOSED only. The current exact monotonic-authority contracts
must not be silently generalized to wildcard/resource-tree semantics.

### K6 — Execution is not verification

```text
execution.status = SUCCEEDED
```

may coexist truthfully with:

```text
verification.verdict = NOT_VERIFIED
```

Only the independent verification boundary may produce the canonical verified outcome.

### K7 — Evidence contracts are profile-specific

The lifecycle has a common authority prefix, but not every capability has the same terminal tail.

Current READ profile:

```text
READ_ONLY_VERIFIED
Runner observation
→ independent Verifier observation
→ ObservedPostState/v1
→ VerificationStrength/v1
→ VerificationResult/v1
→ STOP
```

For this current profile:

```text
ExecutionReceipt/v2 = NOT_APPLICABLE
OperationProof/v2   = NOT_APPLICABLE
OperationCell/v1    = NOT_APPLICABLE
```

Current bounded-mutation semantic tail:

```text
BOUNDED_MUTATION_VERIFIED
bounded provider mutation
→ ExecutionReceipt/v2
→ independent verifier readback
→ VerificationResult/v1
→ OperationProof/v2
→ OperationCell/v1
```

The fractal model must never collapse these tails into one universal `receipt → proof → cell` rule.

### K8 — Production is a separate effect boundary

Production capability eligibility, runtime availability and execution authorization remain separate.
No architecture document, capability registration, successful test, proof object or historical pilot
implicitly enables production effects.

## 4. Fractal Capability Architecture

### 4.1 Definition

A **Capability Cell** is a provider-neutral governed capability contract plus the provider-specific
implementation and verification pieces required to satisfy that contract.

The self-similarity is semantic:

```text
INTENT
→ EXACT OPERATION
→ CURRENT AUTHORITY CONTEXT
→ POLICY / APPROVAL OBLIGATIONS
→ BOUNDED AUTHORIZATION
→ CONTROLLED EXECUTION OR OBSERVATION
→ INDEPENDENT VERIFICATION
→ PROFILE-CORRECT EVIDENCE
```

The same questions repeat for many capabilities. The authority owners do not.

### 4.2 Capability Cell anatomy

A production-eligible capability cell should define the applicable set of:

```text
CapabilityDefinition identity + version
Input schema
Target schema / TargetBinder
ExpectedPostState
Risk class
Required permissions
Policy obligations
Approval requirements
Preconditions / PreconditionWitness requirements
Terminal profile
ExecutionCapsule requirements
Runner class / boundary
Credential contract
Provider Handler / transport binding
Timeout / cancellation / idempotency semantics
Verifier identity / credential requirements
Postconditions
VerificationStrength minimum
Recovery / rollback / reconciliation semantics
Evidence contract
Conformance tests
Lifecycle / activation state
```

A cell references kernel-owned authority semantics. It does not implement a private authorization
universe.

### 4.3 What a cell MUST NOT own

A provider/domain cell must not independently become:

- a second identity authority;
- a second workspace permission authority;
- a second approval system;
- a shadow policy decision point that can override canonical deny;
- an ExecutionGrant issuer outside the canonical kernel path;
- a caller-selected terminal-strength mechanism;
- a combined Runner+Verifier identity for a profile requiring independence;
- a generic shell escape hatch;
- a proof shortcut where execution success becomes verification.

### 4.4 Provider modules are cell implementations, not product silos

The target relationship is:

```text
VOP Capability Contract
        ↓
Capability Cell Contract
        ↓
Provider Module
        ↓
Exact Handler / Transport
        ↓
Real Provider
```

For example, the user-facing semantic capability `service.restart` could eventually have different
provider implementations, but each implementation must conform to the same V-One trust grammar and
its own exact versioned capability contract.

Provider SDK imports stay outside the authority kernel.

## 5. Fractal scales

The same narrowing questions may appear across product scopes:

```text
[Organization policy — where adopted]
        ↓
Workspace
        ↓
Environment
        ↓
Target
        ↓
Capability
        ↓
Execution attempt
```

At each scope, constraints may become stricter. A lower scope must not silently relax an upper scope.

This is a target composition principle, not a claim that every hierarchy level already has a machine-
enforced subset algebra today.

Current workspace membership, role permission, environment, capability identity, target binding,
snapshot/grant contracts and terminal-profile registry remain the actual source of authority.

## 6. Fractal composition into workflows

A workflow or future Operation Graph may compose multiple Capability Cells:

```text
Cell A
  ↓ verified/accepted dependency
Cell B
  ↓
Cell C
```

Composition changes orchestration, not authorization law.

Each consequential child node must preserve:

- its own operation identity;
- its own authoritative target;
- its own current policy/permission facts;
- its own required approvals;
- its own bounded authorization lineage;
- its own execution identity and idempotency semantics;
- its own profile-correct verification/evidence.

No `parent approved` shortcut exists.

A graph engine may schedule cells, retain dependency state and enforce parent ceilings. It must not
manufacture capability authority.

## 7. System planes

The proposed target model can be understood as five cooperating planes.

### 7.1 Intelligence / Context Plane

Examples: CyberCore, security intelligence, telemetry, inventory and human/AI planning.

Question:

> What appears to be true, relevant or worth proposing?

Authority ceiling:

```text
observe / correlate / explain / propose
```

It cannot approve, authorize or prove its own proposal.

### 7.2 Governance / Authority Plane — Core Kernel

Question:

> What exact operation is permitted, for whom, against what target, under which current facts and
> obligations?

This is the singular authority model.

### 7.3 Execution Plane

Examples: durable dispatch, isolated Runner, provider modules and exact handlers.

Question:

> How is the already-authorized bounded operation attempted without widening authority?

### 7.4 Verification Plane

Question:

> What authoritative post-state is independently observable, and does it satisfy the expected state?

Verifier identity/credential independence remains profile-dependent and explicit.

### 7.5 Evidence / Experience Plane

Examples: audit timeline, Operation Passport, Control Room, exports and portable proofs where the
registered lineage supports them.

Question:

> What can an operator or third party reconstruct from canonical evidence?

Presentation is never a parallel authority source.

## 8. Core Kernel vs Capability Cells

```text
                         ┌──────────────────────────┐
                         │  Intelligence / Context  │
                         │ observe / explain / plan │
                         └────────────┬─────────────┘
                                      │ proposals + bound facts
                                      v
                    ╔══════════════════════════════════╗
                    ║       V-ONE CORE KERNEL          ║
                    ║                                  ║
                    ║ VOP semantics                    ║
                    ║ identity / permission bindings   ║
                    ║ policy / approval obligations    ║
                    ║ AuthorizationSnapshot            ║
                    ║ monotonic authority              ║
                    ║ ExecutionGrant + consumption     ║
                    ║ terminal-profile authority       ║
                    ║ verification/evidence semantics  ║
                    ╚═════════════════╤════════════════╝
                                      │ bounded authority
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    v                 v                 v
              Capability Cell   Capability Cell   Capability Cell
                 GitHub            Kubernetes          Cloud
                    │                 │                 │
                    └────────────┬────┴────┬────────────┘
                                 v         v
                           isolated execution
                                 │
                                 v
                         independent verification
                                 │
                                 v
                         canonical evidence views
```

The diagram is a target mental model. It does not claim Kubernetes/cloud cells are implemented or that
the default provider runtime is active.

## 9. Relationship to current `OperationCell/v1`

`Capability Cell` in this thesis is an architectural composition term.

`OperationCell/v1` is an existing VOP evidence atom with narrower accepted semantics for the current
bounded-mutation `OperationProof/v2` lineage.

Therefore:

```text
Capability Cell
!= OperationCell/v1
```

Do not reuse `OperationCell/v1` as the name of the architecture component. The distinction is required
to avoid semantic collision with the canonical VOP vocabulary.

## 10. Relationship to CyberCore

CyberCore may become a strong context and proposal producer:

```text
observe
→ correlate
→ explain
→ propose candidate operation
```

but the transition into effect remains:

```text
CyberCore proposal
→ VOP normalization / review
→ V-One Core Kernel
→ capability-bound execution
```

No shared memory, graph, model confidence or CyberCore database row may substitute for V-One authority.

The current contract-only read-only CyberCore intake boundary remains the safe starting point.

## 11. Product experience

The Control Room should project one kernel and many cells rather than expose vendor-specific mini-
products.

Primary user questions remain:

```text
What do I want to achieve?
What exact target/capability is involved?
What is the current state?
Why is this allowed, blocked or waiting?
What authority would be issued?
What is running or indeterminate?
What was independently verified?
What evidence remains?
What is the next safe action?
```

Provider details remain drill-down information unless required for a decision.

## 12. Market consequence

The architecture reinforces the category:

> **The control plane that safely turns intent into verified action.**

Differentiation is not `many integrations` and not `AI that can operate everything`.

The valuable composition is:

```text
one semantic language
+
one authority kernel
+
monotonic bounded authority
+
conformance-tested capability cells
+
profile-correct isolated execution
+
independent post-state verification
+
reconstructable evidence
```

The initial market wedge remains narrow. Provider breadth should follow proof that one cell can be
operated safely and repeatedly through the whole lifecycle.

## 13. Current-state mapping

This thesis intentionally maps onto the existing system instead of proposing a rewrite.

| Target concept | Current project mapping | Current truth |
|---|---|---|
| Core Kernel semantics | VOP + authority/policy/approval/snapshot/grant/profile contracts | IMPLEMENTED in substantial current scope |
| Monotonic authority | `MONOTONIC_AUTHORITY_R1` contracts and accepted architectural invariant | IMPLEMENTED contract scope; do not generalize silently |
| Durable authority continuity | grant consumption + outbox/inbox + epoch/lease/fence | IMPLEMENTED / canonical |
| READ capability cell pattern | `github.read-ref/v1` + READ terminal + independent verifier | IMPLEMENTED composition; real default-pack HTTP E2E NOT VERIFIED |
| Mutation capability cell pattern | current mutation lineage contracts | pre-effect current path; provider WRITE BLOCKED |
| Capability-cell catalog | existing capability definitions/registries | partial foundations; target conformance layer remains PROPOSED |
| Fractal workflow composition | future bounded Operation Graph | PROPOSED / later scope |
| CyberCore context plane | contract-only read-only intake | IMPLEMENTED contract-only; runtime mutation integration BLOCKED |

No row upgrades `CURRENT_PRODUCT_STATE.md`.

## 14. Adoption and delivery sequence

### R3-0 — Documentation decision

Adopt or reject the Core Kernel + Fractal Capability Architecture vocabulary.

No runtime effect.

### R3-1 — Machine-readable capability-cell contract proposal

Only after adoption, define the minimum schema required to describe one cell without duplicating
existing VOP contracts.

Gate: the schema must reference canonical primitives rather than redefine them.

### R3-2 — Conformance projection

Map existing `github.read-ref/v1` and one mutation candidate against the cell contract.

Gate: no runtime authority change; gaps remain explicit.

### R3-3 — Registry / tooling

Only if the projection proves useful, add conformance checks that reject incomplete or semantically
ambiguous cells.

### R3-4 — Bounded graph composition

Only after cell conformance and the existing READ-before-WRITE gates, design a future Operation Graph.

Gate: no implicit parent→child authority inheritance and no automatic scope widening.

## 15. Rejected interpretations

The following are explicitly rejected:

```text
"Fractal" means each module owns its own policy engine              → REJECT
"Fractal" means child operations inherit parent authority          → REJECT
"Kernel" means a new microservice must be created                  → REJECT
"Kernel" means moving provider SDKs into a central package         → REJECT
All terminal profiles must emit Receipt/Proof/OperationCell         → REJECT
Knowledge graph or memory becomes execution authority               → REJECT
Runner may re-consume grants because every cell is self-contained   → REJECT
A cell may choose a stronger terminal profile                       → REJECT
Recursive autonomous agents are the fractal architecture            → REJECT
Provider count is the primary product success metric                → REJECT
```

## 16. Verification requirements before adoption

Architecture review must verify at least:

1. no conflict with the current canonical authority/execution prefix;
2. no new parallel authority owner;
3. no weakening of grant-consumption or Runner boundaries;
4. no universalization of mutation-only evidence contracts;
5. explicit distinction between `Capability Cell` and `OperationCell/v1`;
6. exact monotonic-authority language remains narrower than any future hierarchy algebra;
7. CyberCore remains intelligence/context only;
8. current product/runtime/release status is not upgraded;
9. rollback is documentation-only;
10. terminology can be represented without breaking VOP canonical vocabulary.

## 17. Source synthesis and conflict resolution

Project truth outranks supporting and experimental source material.

Resolved concepts:

- **approval:** current exact-content approval and canonical authorization separation wins over generic
  workflow diagrams that show one undifferentiated approval gate;
- **capability:** current immutable capability identity and server-selected terminal profile win over
  generic module/plugin concepts;
- **evidence:** current profile-specific tails win over experimental `receipt/proof` universal tails;
- **governance:** repository constitutions and current runtime invariants win over VOODOO OS supporting
  governance diagrams;
- **intent:** experimental intent/planning flows are accepted only as upstream proposal/context shapes;
- **knowledge/memory:** supporting knowledge graphs may inform context but receive no authority role;
- **runtime:** current ProductComposition, control-plane grant consumption, durable dispatch and
  restart-safe resume are preserved exactly;
- **security:** monotonic authority, separation of duties and fail-closed behavior are mandatory;
- **telemetry:** telemetry may support observability and verification inputs, but does not itself become
  authorization or proof.

No retrieved VOODOO-SOURCES artifact contained an established `fractal architecture` contract. The
fractal concept in R3 is therefore a new synthesis over current project invariants, not imported
canonical truth.

## 18. Final thesis

```text
V-ONE
=
ONE CANONICAL OPERATION LANGUAGE
+
ONE SMALL TRUST / AUTHORITY KERNEL
+
MONOTONIC AUTHORITY
+
FRACTAL CAPABILITY-CELL CONTRACTS
+
PROVIDER MODULES OUTSIDE THE KERNEL
+
PROFILE-CORRECT ISOLATED EXECUTION
+
INDEPENDENT POST-STATE VERIFICATION
+
RECONSTRUCTABLE EVIDENCE
```

Short form:

> **One kernel. One trust model. Many capability cells. Any provider that can conform.**

Operational invariant:

```text
INTELLIGENCE MAY PROPOSE.
THE KERNEL MAY AUTHORIZE.
DOWNSTREAM AUTHORITY MAY ONLY NARROW.
CELLS MAY IMPLEMENT CAPABILITIES.
RUNNERS MAY EXECUTE ONLY BOUNDED AUTHORITY.
ONLY INDEPENDENT VERIFICATION MAY ESTABLISH THE VERIFIED OUTCOME.
```

The target is not a giant platform made of vendor-specific control panels. It is one small governed
trust model repeated coherently across capability boundaries without duplicating authority.
