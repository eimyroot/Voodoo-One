# Operator Workspace Information Architecture

Status: `OWNER_DECIDED / IMPLEMENTATION_IN_PROGRESS`
Decision date: 2026-11-25
Runtime effect of this document: `NONE`

## Product rule

The primary navigation is organized around operator work, not internal architecture. Every primary
destination must help an authorized user decide, perform, observe or prove something. A surface that
only explains architecture belongs in contextual detail or administration.

## Target primary navigation

| Destination | Operator question | Required product outcome |
|---|---|---|
| Overview | What needs my attention? | Current actionable priority without inventing health or verification. |
| Requests | What should happen and who must decide? | Create, review and decide an exact governed request. |
| Runs | What is executing or waiting? | Observe state and open the corresponding request and Passport. |
| Verification & evidence | What actually happened and what proves it? | Correlate a run, independent verdict and durable evidence. |
| Task journal | What is the durable task state and next step? | Read the bound CASEBOOK session without claiming execution. |
| System | Is the runtime available and safely controllable? | Distinguish health, configuration and emergency-stop state. |
| Settings | Which environment and safety boundaries are active? | Read current environment, identity and effect restrictions. |

## Contextual surfaces

Capability Registry, Authority & Safety, Policy Gates, Evidence Chain, Task Lifecycle, Project
Overlays, Ecosystem Map, Learning Intelligence and Project Control Map remain available only where
their data supports a primary task or in advanced administration. Availability is not authority;
reference models are not runtime evidence.

Agents and Skills do not become active primary destinations until the runtime exposes an authorized
roster or catalog with useful operator actions.

## Delivery order

1. Requests: exact intent, capability, target, effect, verification and approval.
2. Runs: request-to-execution navigation and trustworthy queue states.
3. Verification & evidence: one operation, one correlated evidence view.
4. Task journal: bound session entry and recorded next step.
5. System and Settings: explicit state, freshness and safe controls.
6. Overview: compose only the verified outputs of the completed destinations.

## Current first slice

The Requests destination absorbs capability context, requires a review of the exact effect before
creation, and blocks approval actions when the underlying request or capability cannot be resolved.
It does not change server authorization, approval semantics, execution or production effects.
