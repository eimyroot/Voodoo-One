# VOODOO One Vision

| Field | Value |
|---|---|
| Document status | Accepted product direction |
| Capability status | PROPOSED target state with VERIFIED current foundations |
| Owner | VOODOO product and architecture owner |
| Review cycle | At every material product or trust-boundary change |

## Purpose

VOODOO One exists to make consequential operational change understandable, authorized, controlled,
and provable.

Its product identity is:

> **Governed Operations Control Plane for Human and AI Execution**

Technical trust-plane description:

> **Provider-neutral control plane for proof-carrying operations.**

VOODOO One sits between human/AI intent and consequential operations on real systems. It accepts an
intent from a person, AI system or automation source, turns it into a precise governed operation,
evaluates current authority/policy/risk, requires the appropriate independent approval, issues only
that bounded execution authority which is justified, coordinates controlled execution, independently
verifies the real post-state, and preserves evidence about what was requested, approved, authorized,
attempted and observed.

The product is intentionally not defined by any single provider, chatbot surface, workflow engine or
automation framework. Its stable value is one governed interaction model across many systems.

## Problem

Infrastructure and software changes become dangerous when any of these questions cannot be answered:

- Who requested the change?
- What exact target and environment were affected?
- What evidence justified the change?
- Which policy version governed the decision?
- Who approved the exact payload?
- What actually ran?
- What result and post-state were observed?
- Can the evidence be independently verified?
- Can a failed or indeterminate operation be recovered safely?

VOODOO One is designed to answer those questions without making automation itself the authority.

## Product promise

The product should provide one governed path:

```text
human / AI intent
  -> normalized governed operation
  -> target + environment + current-state context
  -> policy + permission + risk evaluation
  -> exact approval requirements
  -> immutable approved content
  -> short-lived bounded execution grant
  -> isolated capability execution
  -> independent post-state verification
  -> evidence-backed outcome
```

The user-facing promise is simpler than the machinery underneath it:

```text
I want to do X
  -> VOODOO shows what X means here
  -> required people/policies decide whether it may happen
  -> VOODOO grants only the minimum authority needed
  -> the bounded operation runs
  -> VOODOO independently checks what actually happened
  -> the result remains inspectable and provable
```

`execution succeeded` must never be silently presented as `verified outcome`.

## Product North Star

VOODOO One is successful when people and AI can become more capable without receiving uncontrolled,
permanent or ambiguous privilege.

North Star:

> **Safely give humans and AI more capability without giving them uncontrolled authority.**

For every consequential operation the product should be able to answer, in a form understandable to
an operator and independently reconstructable from evidence:

- who requested it;
- what exact capability and target were involved;
- which environment and current state mattered;
- what outcome was requested;
- which policy, permission and risk facts governed the decision;
- who had to approve it and what exact content they approved;
- what bounded authority was issued and for how long;
- what runtime/capability actually attempted the operation;
- what real post-state was independently observed;
- whether the outcome is verified, failed, blocked, cancelled, interrupted or indeterminate;
- what evidence remains for review, audit and recovery.

## Target product experience: Control Room

The primary product experience is a coherent operations control room, not an unrestricted shell and
not a chat transcript pretending to be operations state.

The target Control Room should make the following views feel like projections of one lifecycle rather
than separate products:

```text
Overview
Runs / Executions
Plans / pending governed work
Capability Registry
Evidence Timeline
Policy Gates
Verifier Center
Runtime Health
Learning & Intelligence
Governance Settings
```

The first screen should answer practical questions before exposing internal implementation details:

- What is happening now?
- What is waiting for my decision?
- What is blocked or risky?
- What is running, interrupted or indeterminate?
- What failed and why?
- Which outcomes are independently verified?
- Which systems/targets are affected?
- What is the next safe action?

Approval UX must let an approver understand in seconds what changes, where, why, with what risk, what
exact authority approval permits, how long it remains valid, how the result will be verified, and how
recovery or rollback is expected to work.

Low-level objects such as grant identifiers, leases, fences, capsule digests and provider transport
metadata remain inspectable for technical/audit work, but they are not the primary user model.

Control Room projections must never become parallel authority. Capability, policy, verifier, runtime
health, learning and governance views all reflect canonical server-side state and contracts. UI state
must not manufacture approval, authorization, verification or release status.

## Capability-centered interaction model

Users should operate primarily through governed capabilities and desired outcomes rather than arbitrary
provider commands. Example target capability families include service restart/scale, deployment
inspection/rollback, configuration changes, identity lifecycle, backups/restores, repository changes,
resource lifecycle and incident diagnosis.

Each production-eligible capability must define the applicable contract for:

```text
input + target schema
required permissions
risk class
approval requirements
preconditions
bounded execution semantics
postconditions
independent verification
rollback/recovery
required evidence
```

Provider-specific behavior belongs behind the capability/module boundary. A comparable capability may
be implemented differently for Kubernetes, AWS, Azure, Linux, GitHub or another provider while the
user-facing governance lifecycle remains consistent.

## Market position and initial wedge

The target category is **governed operations**, not generic AI automation. The initial buyer/user
hypothesis focuses on Platform Engineering, DevOps/SRE, Security/Infrastructure teams and organizations
introducing AI into operational workflows while retaining explicit authority boundaries.

The strongest initial wedge is a deliberately narrow subset of AI-assisted governed operations over
engineering systems, beginning with read/inspect/diagnose paths and only later adding reversible
mutations after the required execution and verification gates are evidenced.

GitHub, Kubernetes and cloud infrastructure are plausible early domains, but provider count is not the
product metric. The product wins when the same trust and interaction model remains understandable and
verifiable across providers.

Market fit, exact ICP boundaries, pricing and willingness to pay remain hypotheses until validated by
real design partners/pilots. Competitor presence or internal enthusiasm is not product-market-fit
evidence.

## Long-term system model

```text
CyberCore or another intelligence source
  observations -> evidence -> knowledge -> proposal
                         |
                         | versioned references
                         v
VOODOO One
  identity -> policy -> approvals -> execution grant -> evidence
                         |
                         | short-lived capability grant
                         v
Isolated Runner
  preflight -> apply -> postflight -> signed receipt
                         |
                         v
ProofGraph
  source -> decision -> build -> execution -> receipt -> checkpoint
```

The intended division of responsibility is:

- **CyberCore or another intelligence source:** system of understanding;
- **VOODOO One:** system of authorization and governed lifecycle;
- **isolated runner:** system of action;
- **ProofGraph:** system of evidence.

## Principles

1. Humans remain authoritative at material mutation boundaries.
2. AI may propose, explain, correlate, draft, and review; it may not silently approve itself.
3. Approval must bind to exact content, target, environment, policy, and validity period.
4. Execution must use capabilities, not arbitrary user-provided shell commands.
5. Production effects remain disabled until separately released with evidence.
6. Evidence must distinguish integrity, provenance, authorization, execution, and observed outcome.
7. Failure, uncertainty, and indeterminate outcomes must remain visible.
8. Current capability claims must never be inferred from roadmap or vision documents.
9. Small, reversible vertical slices are preferred over broad rewrites.
10. CyberCore integration, if adopted, begins read-only and without a shared database.

## Intended users

Primary operational users and buyers are expected to include:

- Platform Engineering teams managing many systems and internal platforms;
- DevOps and SRE teams performing deployments, incident response and operational change;
- Security / Infrastructure teams governing privileged operations and evidence;
- administrators, operators, approvers and auditors;
- developers proposing governed changes;
- AI-assisted systems that submit proposals, analyses or plans but do not own authorization.

The simple human runtime role model remains `ADMIN`, `OPERATOR`, `APPROVER`, `AUDITOR`; machine identities
such as `AGENT`, `RUNNER` and verifier identities are separate security principals, not extra human UI
roles.

## Success outcomes

VOODOO One is successful when:

- materially risky changes cannot bypass policy and independent approval;
- approval becomes invalid when its governed inputs drift;
- execution is isolated from the control-plane identity;
- every execution has a structured, bounded, and verifiable result;
- evidence can be independently checked without trusting the running application;
- operators can understand why an action is allowed, blocked, failed, or indeterminate;
- recovery and rollback procedures are explicit before mutation;
- production activation is a governed release decision, not a configuration accident.

## Non-goals

VOODOO One is not intended to become:

- a generic autonomous shell agent;
- a duplicate infrastructure inventory or knowledge platform;
- a second implementation of CyberCore;
- an unbounded provider-specific automation monolith;
- a replacement for Terraform, Ansible, monitoring, or provider APIs;
- a system that treats AI confidence as authorization;
- an unrestricted production platform before runner isolation, signed evidence, and release gates exist.

## Current versus target boundary

This document is the canonical long-term product-direction projection. Target UX, provider breadth,
capability breadth, commercial positioning and market hypotheses described here do **not** prove current
implementation, runtime activation, release, deployment or product-market fit.

Current product truth remains in `CURRENT_PRODUCT_STATE.md` and
`docs/product/CURRENT_CAPABILITIES.md`; ordered delivery and safety gates remain in `ROADMAP.md` and
`docs/product/TARGET_CAPABILITIES.md`. The evidence-bound Control Room bridge between those two states is
[`docs/product/CONTROL_ROOM_CURRENT_TO_TARGET_GAP.md`](docs/product/CONTROL_ROOM_CURRENT_TO_TARGET_GAP.md).
Accepted architecture/ADR trust invariants remain in force unless explicitly superseded. Product
simplicity at the UI layer must never weaken those trust boundaries.

## Current reality

The current repository provides a tested development control-plane baseline, local adapters with
production effects disabled, and a local checkpoint ProofGraph verifier. It is not an unrestricted
production release.

The authoritative current-state inventory is
[`docs/product/CURRENT_CAPABILITIES.md`](docs/product/CURRENT_CAPABILITIES.md). The delivery sequence
is maintained in [`ROADMAP.md`](ROADMAP.md).
