# VOODOO Architecture Lab

Status: **NON-AUTHORITATIVE / EXPERIMENTAL**.

This directory is the bounded architecture-challenger lane inside the already non-authoritative `CASER/VOODOO/IDEAS` incubator. The governing architecture change is proposed in [`ADR-0030`](../../../../docs/adr/ADR-0030-architecture-lab-controlled-promotion-v1.md) and is not adopted merely because these files exist.

## Invariant

```text
LAB CANDIDATE
!= ADOPTED ARCHITECTURE
!= IMPLEMENTATION AUTHORITY
!= RELEASE AUTHORITY
!= DEPLOYMENT AUTHORITY
```

Nothing in this directory may approve, authorize, execute, release or deploy. Nothing here may turn a deterministic V-One `DENY` into `ALLOW` or widen current authority.

## Why this exists

Production/current architecture must remain stable enough to audit and reproduce. Architecture research must remain free to challenge it. The bridge between them must therefore be evidence and explicit governance, not filesystem proximity or optimizer confidence.

## Candidate lifecycle

```text
IDEA
→ EXPERIMENTING
→ EVALUATED
→ PROMOTION_CANDIDATE
```

At any point a candidate may become `REJECTED` or `ARCHIVED`. `PROMOTION_CANDIDATE` means "ready for an owner architecture decision", not "promoted".

## Candidate contract

Promotion-track candidates use [`candidate.schema.json`](candidate.schema.json). The schema requires:

- exact baseline source HEAD;
- preregistered hypothesis and falsification criteria;
- explicit scope/non-scope;
- all authority booleans fixed to `false`;
- isolated non-production experiment declaration;
- metrics and guardrails;
- security risk and privilege requirements;
- source/provenance and licensing status;
- rollback/containment;
- external evidence location;
- explicit `NOT_GRANTED` implementation/release/deployment authority.

[`candidate.example.json`](candidate.example.json) is a dry-run example only. It is not an active architecture decision.

## Experimental evidence contracts

The lab also carries two non-authoritative evidence contracts:

- [`evaluation.schema.json`](evaluation.schema.json) separates model intent, action serialization, adapter behavior, physical/GUI execution, post-state observation, independent verification and the agent's own claim. It defines the lab failure taxonomy and claim-evidence consistency verdicts.
- [`artifact-admission.schema.json`](artifact-admission.schema.json) records executable/model surface risk before an isolated experiment, including remote code, executable files, dependency/native surfaces, loader/pre/post-processing code, filesystem/subprocess needs, unsafe deserialization, hashes and sandbox requirements.

These contracts do **not** create new product authorities:

- `ExecutionReceipt/v2` remains the canonical execution/effect claim.
- `ObservedPostState/v1` + `VerificationResult/v1` remain the canonical independent verification evidence.
- `ExecutionCapsule/v1` remains the runtime executable identity owner.
- this lab does not create the deferred production `ExpectedPostState` owner; `expected_conditions` inside evaluation evidence are experiment assertions only.
- artifact admission reuses `candidate.security.network_required` and `candidate.provenance.sources[].license_status` rather than defining parallel network/license truth.
- vision/LLM judging may be supporting evidence only and never final authority.
- unknown improvement attribution is `INCONCLUSIVE` / `NOT_EVALUABLE`, not `PASS`.

The deterministic local gate is `scripts/architecture_lab_evidence_gate.py`. It validates the experiment examples without runtime wiring, provider effects or additional dependencies.

## Promotion path

```text
candidate manifest
→ identity / provenance check
→ isolated experiment
→ project-specific benchmark + negative cases
→ security / supply-chain review
→ contract / regression checks
→ rollback check
→ independent evidence review
→ PROMOTION_CANDIDATE
→ exact-content owner architecture decision
→ separately authorized implementation
→ independent verification
→ separate release / deploy gates if ever applicable
```

There is no direct `Architecture Lab → Production` edge.

## Evidence location

Generated evidence must live outside the product worktree:

```text
/Users/eimyna/0_EVIDENCE/Voodoo-One/ARCHITECTURE_LAB/<candidate-id>/<run-id>/
```

A lab result without attributable evidence is a hypothesis, not a promotion argument.

## Optimizer boundary

Human researchers, AI agents, CyberCore, harness designers and automated search may propose, mutate and rank lab candidates inside an approved isolated experiment. They may not:

- approve their own candidate;
- change promotion thresholds after seeing the result;
- weaken security/authority invariants to improve a benchmark;
- modify current architecture records as a side effect of an experiment;
- create production credentials or effects.

That is the difference between architecture evolution and giving the experiment keys to the building.

## Evidence-sufficiency hardening (bounded Lab contract)

The local gate enforces the JSON Schema subset actually used by the Lab contracts (required fields, types, enums, patterns, object keys, array bounds, references and conditionals) without importing production runtime or adding a dependency. This is not a general-purpose Draft 2020-12 validator.

An agent's reported verified post-state must agree with the separate post-state verification record. A vision/LLM supporting-only method cannot assert a verified match/mismatch; it can contribute supporting evidence to an inconclusive assessment. A PASS quality-attribution declaration requires all five quality dimensions to carry evidence references, a consistent agent claim, and matching observed post-state.

The v1 `metrics` block is a set of per-record normalized indicators (`0`, `1`, or `null` where the record cannot support the measurement). The local gate derives every metric that is deterministically recoverable from the same execution/claim/post-state evidence and rejects contradictory declared values. Cohort-level rates must be aggregated from validated records rather than manually overriding per-record evidence.

Execution traces are ordered contracts, not bags of labels: the gate requires the canonical six-stage order and rejects failure classes assigned to an incompatible stage. Every stage must carry at least one evidence reference. Evidence suppression is derived from the difference between evaluator-visible evidence (execution evidence plus any bound verified post-state reference) and the subset the agent disclosed; the agent cannot self-certify that it disclosed everything. Model/harness failure attribution is counted only from trace entries that carry an explicit failure class. A stage with no classified failure must keep failure_origin=NONE. MODEL_INTENT, serialization, adapter and physical execution cannot be PASS while carrying a failure class; post-state observation and verification may themselves pass while correctly diagnosing a failure in the executed reality.

Artifact Admission records filesystem/subprocess/sandbox needs, but canonical runtime permission identity remains owned by `ExecutionCapsule/v1`; the Lab record references that owner rather than inventing a second permission model.

Pressure/reward/conflict/missing-evidence/partial-success fields are adversarial scenario context only. They may select or label evaluation cases, but they are never evidence of model intent; claim/evidence verdicts remain functions of observable claim, execution evidence and verified post-state.

For remote executable/model code, REVIEWED requires remote_code_review_receipt tied to exact source revision, code revision and SHA-256 code hash; a missing or mismatched receipt blocks admission. Such a receipt is still a declaration: this local gate cannot authenticate the reviewer's identity, verify external evidence bytes, or establish the trustworthiness of reviewed code by itself. Independent evidence authentication and canonical project governance remain separate promotion requirements.

Promotion PASS is additionally fail-closed on evidence suppression and on any known REGRESSED quality dimension. For a verified post-state after a passed PHYSICAL_GUI_EXECUTION stage, the Lab record must bind both pre-state evidence and an execution-receipt reference; this does not make bounded-mutation ExecutionReceipt/v2 universal for READ-only product profiles.

Artifact Admission treats executable/runtime behavior as elevated evidence surface: executable code, model loaders, pre/post-processing, native extensions, subprocess use, unsafe deserialization, or filesystem writes cannot remain BASELINE risk. Remote or executable code must bind a dependency-manifest reference and SHA-256 before isolated admission. These checks remain admission evidence only and do not replace ExecutionCapsule/v1 permissions.

These checks affect only isolated Lab evidence validation. They do not grant implementation, authority, release, provider-write or deployment capabilities.


An isolated admission is a metadata review only; local executable code remains **BLOCKED** by the v1 gate until an independently reviewed local-code admission contract exists. Submitted records must bind to a common candidate/source identity. Missing, ill-typed or non-finite fields and unreadable or invalid JSON fail closed with structured errors. These checks do not authenticate claimed source bytes or sandbox execution and never grant V-One authority.

## Reconciliation notice

The hosted-main Architecture Lab ADR-0030 is only a PROPOSED reconciliation candidate. The historical locally adopted Lab ADR-0026 retains its original SHA-256 and adoption record in its source lineage; the separately adopted G8 ADR-0026 on canonical main is untouched. See docs/governance/ARCHITECTURE_LAB_ADR_ID_RECONCILIATION_CANDIDATE.md.


## F1-F3 remediation candidate (not adopted)

The deterministic evidence gate now requires three records: --candidate, --evaluation, and --artifact-admission. The candidate manifest is required so the gate can bind candidate_id across records, pin evaluation source_head to candidate.source_head, and require the artifact source reference and revision to exist in candidate provenance. A declared model/code source SHA-256 must match the corresponding admitted artifact digest; admissions with unpinned model/code source digests fail closed.

The gate rejects admission when admission_risk is REJECTED, or when admission_verdict is ADMIT_FOR_ISOLATED_EVAL but sandbox_requirements are empty. This covers local executable surfaces as well as remote code.

Example invocation:

    python3 scripts/architecture_lab_evidence_gate.py --candidate CASER/VOODOO/IDEAS/ARCHITECTURE_LAB/candidate.example.json --evaluation CASER/VOODOO/IDEAS/ARCHITECTURE_LAB/evaluation.example.json --artifact-admission CASER/VOODOO/IDEAS/ARCHITECTURE_LAB/artifact-admission.example.json

The gate validates claimed evidence shape and cross-record attribution, not reviewer authenticity, external artifact bytes, actual sandbox isolation, or any V-One execution/promotion permission. Example values and placeholder hashes remain illustrative.
