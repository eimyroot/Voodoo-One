# VOODOO — Change Decision Card: Architecture Lab + controlled promotion v1

```text
TITLE: Stable Production Architecture + isolated Architecture Lab + controlled promotion v1
DATE: 2026-10-11
OWNER: repository owner
IMPLEMENTER: AI-assisted governed implementation
REVIEWER: owner exact-content review + independent evidence review pending
RISK_CLASS: R3
MODE: DESIGN / RECONCILIATION (NO IMPLEMENTATION AUTHORITY)
```

## Záměr

```text
USER: V-One / VOODOO owner and future architecture maintainers
PROBLEM: The project needs continuous architecture experimentation without allowing experiments or optimizers to become a second source of truth or to self-promote into authority/runtime.
EXPECTED_OUTCOME: One proposed architecture boundary plus one isolated, machine-readable lab candidate contract with a fail-closed promotion path.
SMALLEST_SAFE_SLICE: Documentation/governance proposal + non-authoritative lab schema/example only; no runtime wiring.
SOURCE_OF_TRUTH: canonical hosted main@2627b7d17064608059794347a6dd46fd40a7de11; historical local Architecture Lab adoption is provenance, not authority transferred to ADR-0030.
```

## Rozsah

```text
IN_SCOPE: ADR-0030 proposal; Architecture Lab boundary under existing IDEAS incubator; candidate manifest; promotion gates; docs navigation; verification evidence; uncommitted reconciliation candidate only.
OUT_OF_SCOPE: runtime code, authority kernel, provider effects, model installation, external services, owner-adoption record, push/PR/merge/release/deploy.
AFFECTED_DATA: repository documentation and experimental lab metadata only; generated evidence outside repo.
AFFECTED_PERMISSIONS: none.
TRUST_BOUNDARIES: Architecture Lab remains proposal-only; V-One authority, Monotonic Authority, Runner/Verifier separation and READ-before-WRITE remain unchanged.
```

## Gate 7×ANO

```text
JEDNODUCHÁ: ANO — reuse existing IDEAS incubator; no new service or datastore.
ÚČELNÁ: ANO — enables permanent challenger experimentation without destabilizing the canonical baseline.
AUTOMATIZOVANÁ: ANO — candidate contract is machine-readable and verification commands are reproducible.
BEZPEČNÁ: ANO — authority flags are fail-closed; no direct lab→production path exists.
MĚŘITELNÁ: ANO — every candidate preregisters hypothesis, metrics, guardrails, success/failure and evidence.
VRATNÁ: ANO — documentation/lab-only changes can be removed without runtime or data migration.
DŮKAZNĚ OVĚŘITELNÁ: ANO — exact HEAD, schema/example validation, documentation tests and external evidence receipt are required.
```

## Verifikace a návrat

```text
TEST_PLAN: git diff --check; JSON parse + authority invariant check; targeted documentation tests; complete diff review.
SUCCESS_EVIDENCE: exact repository HEAD, executed command outputs, file digests and truthful evidence receipt under /Users/eimyna/0_EVIDENCE/Voodoo-One.
FAILURE_SIGNAL: broken docs/link/test; invalid schema/example; any authority flag true; any claim that PROPOSED equals ADOPTED/IMPLEMENTED/RELEASED.
ROLLBACK: remove/revert the bounded documentation and lab files; restore the two navigation files from Git/evidence backup.
POST_STATE_VERIFICATION: git status/diff show only approved bounded files plus pre-existing .ai/; no runtime/provider state changed.
```

## Rozhodnutí

```text
OWNER_DECISION: NEW ADR-0030 ADOPTION PENDING
DECISION_REASON: A bounded reconciliation candidate is requested. The original local ADR-0026 owner adoption does NOT transfer to ADR-0030; no commit, push, adoption, merge, deploy or provider effect is authorized.
EXPIRY_OR_REVIEW_DATE: exact-content owner review before ADR adoption or any runtime integration.
```

The unadopted Graph ADR-0029 remains outside this workstream. This proposed Architecture Lab ADR-0030 is a newly hashed identity and cannot inherit an earlier ADR adoption. Review, approval, candidate commit-A, adoption record-B and all other effects remain separate gates.
