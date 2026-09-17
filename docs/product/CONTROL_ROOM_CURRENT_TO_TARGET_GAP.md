# VOODOO One Control Room — CURRENT → TARGET Gap Map

| Field | Value |
|---|---|
| Document class | Evidence-bound product gap analysis / delivery input |
| Status | PROPOSED delivery map with current observations verified against repository source |
| Audit date | 2026-09-16 |
| Audit input HEAD | `0fc4001e6ba19d1e4dd244a72c55187e9a7937a1` |
| Current-state authority | `CURRENT_PRODUCT_STATE.md` + current repository source/tests |
| Target product authority | `VISION.md` |
| Delivery authority | `ROADMAP.md` + `TARGET_CAPABILITIES.md` |
| Production effects | BLOCKED / disabled by default |

## 1. Purpose

This document answers one bounded question:

> What already exists in the V-One Control Room, what has backend/contracts but lacks truthful product UX, and what still requires implementation to reach the accepted North Star?

It is not a capability-status replacement. Current capability truth remains in `CURRENT_PRODUCT_STATE.md` and `CURRENT_CAPABILITIES.md`.

## 2. Scope boundary

The Control Room is the V-One system-of-engagement surface for governed operations. It is not the whole VOODOO OS platform.
The broader VOODOO platform may contain or integrate model routing, voice, memory, workflow/agent planning, automation and other intelligence services. Those concerns do not become V-One authority merely because they appear in a shared visual language or future platform experience.

V-One remains responsible for the governed-operation lifecycle:

```text
intent
→ normalized governed operation
→ authority / policy / risk
→ exact approval
→ bounded execution authority
→ controlled execution
→ independent post-state verification
→ evidence-backed outcome
```

External intelligence may propose or enrich. It must not manufacture approval, authorization, execution success or verification.

## 3. Gap classes

The primary delivery classes are:

- `ALREADY_EXISTS` — current backend and current Control Room surface both exist for the stated scope.
- `BACKEND_EXISTS_UX_GAP` — relevant current contracts/data/components exist, but the Control Room is legacy, hardcoded, incomplete or not bound to canonical truth.
- `IMPLEMENTATION_REQUIRED` — required product/runtime behavior does not yet exist or is intentionally blocked behind a named gate.

`OUTSIDE_VONE_BOUNDARY` is not a fourth delivery class. It marks wider VOODOO platform concerns that must integrate through explicit contracts instead of being absorbed into V-One.

## 4. Current Control Room evidence

The current repository directly contains:

- authenticated `/console` shell in `voodoo_product/static/index.html`;
- client behavior in `voodoo_product/static/control_room.js`;
- one authenticated read-only `GET /api/v1/control-room` projection;
- server-side projection ownership in `ProductService.control_room()`;
- sections for Overview, Runs, Plans, Capability Registry, Evidence Timeline, Policy Gates, Verifier Center, Runtime Health, Learning Intelligence and Governance;
- guarded change-request / approval actions and emergency-stop control;
- system tests for console availability, CSP compatibility, projection shape and fail-closed truth.

Current product truth also confirms that the Control Room projection is `IMPLEMENTED / TARGETED VERIFIED`, while the default G8 provider runtime is still disabled and real canonical HTTP READ E2E remains unverified.

## 5. Screen-by-screen gap map

| Surface | CURRENT | TARGET | Gap class |
|---|---|---|---|
| Overview / Control Room | Trust state, run/approval counts, risk mix, receipt/audit integrity and emergency-stop state are surfaced. The orchestration strip is partly hardcoded in JS. | One truthful operational summary answering what is happening, waiting, blocked/risky, independently verified, affected and safe to do next. | `BACKEND_EXISTS_UX_GAP` |
| Runs | Legacy execution records expose status, request title, risk, environment, adapter and receipt id. | Canonical operation/execution lifecycle with authority lineage, target/capability, current epoch/lease/fence, interruption/resume state, verifier result and evidence links. | `BACKEND_EXISTS_UX_GAP` |
| Plans / Approvals | Change requests, approval counts and submit/execute actions exist. Approval inbox exposes effective threshold but not policy version/requester binding. | Governed-operation preview with exact target/content digest, policy/permission/risk facts, required approvers, expiry, verification plan and recovery expectation before approval. | `BACKEND_EXISTS_UX_GAP` |
| Capability Registry | Four current surfaces are projected from a server-side hardcoded list, including `github.read-ref/v1` disabled when canonical runtime is absent. | Registry derived from canonical capability definitions/activations with provider mapping, environments, risk, permissions, verification contract, runtime activation and eligibility. | `BACKEND_EXISTS_UX_GAP` |
| Evidence Timeline | Audit events, legacy receipts, executions and plans are merged into a small chronological projection. | Operation passport/evidence graph that correlates reviewed content, authority, dispatch/runtime lineage, observed post-state and profile-correct terminal evidence, with drill-down/export. | `BACKEND_EXISTS_UX_GAP` |
| Policy Gates | Truth invariants, production effects, emergency stop, evidence-chain integrity and canonical-runtime activation are surfaced. | Current deterministic policy/permission decision facts, revision/bundle identity, reason codes, obligations, approval requirements, freshness and denial explanation. | `BACKEND_EXISTS_UX_GAP` |
| Verifier Center | Separation rule is visible, but every receipt-derived check intentionally reports `verification_status = UNKNOWN`; canonical independent verification is not exposed. | Real `VerificationResult/v1`, verification strength, expected vs observed post-state, verifier identity/path and truthful failed/indeterminate outcomes. | `BACKEND_EXISTS_UX_GAP` |
| Runtime Health | API, database, evidence liveness, identity provider and canonical-runtime enabled/disabled state are shown. | Operational health for canonical runtime, outbox/inbox, execution epoch/lease/fence, Runner/Verifier boundaries, provider connection/configuration, recovery state and relevant SLO signals. | `BACKEND_EXISTS_UX_GAP` |
| Learning Intelligence | Simple execution success/failure and approval-queue signals exist; scoring router is explicitly `NOT_EXPOSED`. | Safe intelligence/reconciliation signals from observed outcomes and optional CyberCore/learning sources without any authorization power. | `IMPLEMENTATION_REQUIRED` beyond basic observed metrics |
| Governance & Settings | Environment, trusted hosts, CORS, identity provider, production-effects flag and approval-compatibility metadata are projected read-only. | Role/workspace governance, policy profiles, capability activation, exceptions, evidence retention, release gates and auditable administrative workflows according to separately accepted contracts. | `BACKEND_EXISTS_UX_GAP` plus `IMPLEMENTATION_REQUIRED` for still-proposed enterprise/org controls |

## 6. What already exists end to end at the product surface

`ALREADY_EXISTS` today includes:

- authenticated console access and session-aware navigation;
- the complete ten-view information architecture;
- one server-owned Control Room read model;
- current run/plan/approval summaries;
- current local change-request and approval interactions;
- emergency-stop UI backed by the existing safety API;
- fail-closed visibility for disabled canonical runtime and production effects;
- evidence/audit integrity visibility;
- responsive dark Control Room shell;
- negative truth rules such as `UNKNOWN != PASS`, `MISSING != PASS` and `UNVERIFIED != PASS`.

These are real foundations, not mock-only screens. Their scope remains the current local/product projection and must not be upgraded into provider-runtime or production claims.

## 7. Backend/contracts that exist but are not yet a first-class Control Room experience

The largest product gap is not absence of trust-plane code. It is projection and interaction binding.

Current backend/contracts already include substantial foundations for:

- authoritative `AuthorizationSnapshot` creation;
- `ExecutionGrant/v2` issuance and durable one-time consumption;
- Outbox / DispatchEnvelope / Inbox admission;
- execution epoch, lease and current-fence semantics;
- `ExecutionCapsule/v1`;
- canonical capability→terminal binding;
- restart-safe reconstruction of the same ACTIVE execution;
- isolated bounded READ Runner primitives;
- independent Verifier and `VerificationResult/v1` contracts;
- profile-specific bounded-mutation receipt/proof/cell contracts;
- deterministic Policy Decision Graph foundation;
- CyberCore read-only metadata intake contract.

The Control Room does not yet expose these as one canonical operation passport. Several current screens still read legacy execution/change-request structures or hardcoded projections instead.

## 8. Implementation still required before the North Star is truthful

The following cannot be solved by visual redesign alone:

1. explicit non-production activation of the merged G8 READ runtime pack;
2. real authenticated canonical HTTP READ E2E through current DB authority;
3. process interruption while ACTIVE and restart-safe resume of the same execution;
4. evidence that no duplicate prepare/grant/consume/outbox/inbox/epoch/lease is created;
5. real independent `VerificationResult/v1` surfaced to the product;
6. canonical operation detail/passport projection joining authority, runtime and verification evidence;
7. dynamic capability-registry projection from canonical definitions/activations;
8. policy/approval projection bound to exact reviewed content and current authority facts;
9. evidence export/drill-down that preserves profile-specific semantics;
10. safe learning/intelligence projection with no path to authorization;
11. separately adopted organization/enterprise governance controls before they are shown as available;
12. controlled-pilot evidence and release gates before production language or effects.

Provider WRITE remains outside the immediate Control Room acceptance target until the adopted READ-before-WRITE evidence gate is satisfied. `ELIGIBLE` would still not mean authorized.

## 9. Wider VOODOO platform concerns — integration, not V-One ownership

The following may be important to the broader VOODOO OS/platform vision but are `OUTSIDE_VONE_BOUNDARY` unless a later accepted decision changes ownership:

- multi-model routing and model lifecycle;
- voice/STT/TTS realtime runtime;
- general semantic/episodic AI memory infrastructure;
- unrestricted agent reasoning/planning runtime;
- generic workflow/DAG engine as an authority source;
- general-purpose automation catalog;
- arbitrary tool execution;
- broad knowledge graph ownership.

V-One may receive proposals, context, observations or status from those systems through versioned contracts. It must remain the governed authority/execution/evidence boundary for operations it owns.

## 10. Recommended delivery sequence

### CR-0 — Truth convergence

Status: `IMPLEMENTED` by this reconciliation when the current documentation and gap map pass local static verification.

- current G0 remains `UNKNOWN` after repository rename;
- current G8 pack remains implemented but default inactive;
- current Control Room projection claims only what its API actually exposes;
- vision/target material cannot upgrade current capability status.

### CR-1 — Canonical operation read model

Status: `IMPLEMENTED / TARGETED VERIFIED`.

The product now exposes one read-only `vone.operation-passport/v1` query projection over the existing
canonical durable objects through `GET /api/v1/operations/{execution_id}/passport`. It uses the same
ProductService database, validates canonical stored JSON and cross-row lineage, creates no authority,
performs no provider effect and introduces no second persistence owner.

Current verification truth remains deliberately incomplete: READ `VerificationResult/v1` is not yet
durably stored, so the passport reports `UNKNOWN / NOT_PERSISTED` instead of promoting execution or
evidence integrity to independent verification.

### CR-2 — G8 live READ acceptance

Target: prove the backend path that the product experience is meant to represent.

- activate the merged READ-only runtime only through explicit non-production configuration;
- run authenticated canonical HTTP READ E2E;
- inject restart while ACTIVE;
- prove durable same-execution resume and no duplicate authority/dispatch state;
- expose the independent verifier result without converting execution success into verification.

This slice is constrained by `G8_READ_RUNTIME_GATE.md` and ADR-0019.

### CR-3 — Operation Passport UX

Target: one drill-down from intent to independently observed outcome.

The first useful detail view should show:

```text
request / actor
reviewed content + target
permission / policy / approval facts
authorization snapshot + bounded grant
dispatch / epoch / lease / capsule state
execution status
expected vs observed post-state
verification verdict / strength
evidence references
recovery / next safe action
```

Low-level identifiers remain inspectable, but the primary UX explains their operational meaning.

### CR-4 — Registry, Policy and Verifier convergence

Replace hardcoded or receipt-derived projections only after a canonical read model exists:

- registry from canonical capability definitions/activations;
- policy view from current deterministic authority/policy facts;
- verifier view from actual `VerificationResult/v1` evidence;
- evidence timeline from correlated canonical lifecycle facts.

No screen may become a new source of authority.

### CR-5 — Product experience refinement

Only after semantic/data convergence:

- adopt the accepted VOODOO visual language without changing trust semantics;
- add filters, search, drill-down, correlation and operator-focused next actions;
- improve role-aware information density and approval comprehension;
- validate responsive behavior, accessibility and failure/empty states;
- retain visible distinction between `EXECUTED`, `VERIFIED`, `BLOCKED`, `UNKNOWN` and `INDETERMINATE`.

### CR-6 — Wider platform integrations

After the V-One operation cell and controlled pilot are stable, integrate optional VOODOO platform intelligence through explicit read/proposal contracts. Models, voice, memory, learning and orchestration may enrich the experience, but cannot bypass V-One authority.

## 11. Product acceptance test for the Control Room North Star

The Control Room is not North-Star complete because all ten menu items render. It approaches the target only when an operator can take one real governed operation and answer, from the product without inventing missing facts:

```text
what is requested?
what target/environment will be touched?
what authority and policy apply?
what exact content was approved?
what bounded authority was issued?
what is executing or waiting?
what happened after restart/recovery?
what did an independent verifier observe?
is the outcome verified, failed, blocked or indeterminate?
where is the evidence and what is the next safe action?
```

If any required fact is unavailable, the product must show that absence rather than infer success.

## 12. Immediate decision

The next product-development bottleneck is not another dashboard section and not a broader provider catalog.

It is:

```text
CANONICAL OPERATION PASSPORT READ MODEL = IMPLEMENTED
→ EXPLICIT NON-PRODUCTION G8 ACTIVATION
→ REAL AUTHENTICATED HTTP READ
→ ACTIVE RESTART / SAME-EXECUTION RESUME
→ DURABLE / EXPOSED INDEPENDENT VerificationResult/v1
→ ENRICH OPERATION PASSPORT WITH OBSERVED OUTCOME
→ CONTROL ROOM DRILL-DOWN
```

That sequence converts the existing Control Room from a truthful control-plane dashboard into the first evidence-backed operational product slice of the North Star without widening authority.

## 13. Non-goals of this gap map

This document does not authorize:

- provider WRITE;
- production effects;
- release or deployment;
- adoption of a new workflow engine, model runtime, memory system or voice stack;
- generic shell execution;
- rewriting immutable ADR/history;
- treating visual concepts as implementation evidence;
- treating the broader VOODOO OS platform concept as current V-One capability.

## 14. Verification boundary

This map is based on current repository source, current Control Room UI/API/tests and current reconciled documentation. The reconciliation worktree was validated on 2026-09-16 in the hash-locked Python 3.12 development environment with full `ruff check .`, full `pytest -q` and `scripts/product_readiness_gate.py` passing. That source/worktree evidence does not prove fresh G0, provider-runtime activation, real G8 HTTP READ E2E, release or deployment.
