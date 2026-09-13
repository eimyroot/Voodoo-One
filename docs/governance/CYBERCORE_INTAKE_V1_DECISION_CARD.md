# VOODOO — Change Decision Card: CyberCore Intake v1

```text
TITLE: CyberCore read-only intake contract v1
DATE: 2026-09-11
OWNER: repository owner
IMPLEMENTER: AI-assisted governed implementation
REVIEWER: owner / independent review pending PR
RISK_CLASS: R2
MODE: IMPLEMENT
```

## Záměr

```text
USER: V-One operator / product owner
PROBLEM: CyberCore proposals need a bounded machine-readable handoff into V-One without gaining authority.
EXPECTED_OUTCOME: deterministic metadata-only intake contract linked to CXP/1 and Knowledge Block evidence.
SMALLEST_SAFE_SLICE: pure contract + schema + tests + documentation, with no runtime wiring.
SOURCE_OF_TRUTH: current Voodoo-One main, product constitution, supplied CyberCore CXP/1 source material.
```

## Rozsah

```text
IN_SCOPE: CXP identity/digests, Knowledge Block reference, risk mapping, signature status, target, verification plan.
OUT_OF_SCOPE: CXP extraction, signature trust store, persistence, API, approval, execution, release, deployment.
AFFECTED_DATA: none persisted.
AFFECTED_PERMISSIONS: none.
TRUST_BOUNDARIES: CyberCore remains intelligence/proposal source; V-One remains sole authorization owner.
```

## Gate 7×ANO

```text
JEDNODUCHÁ: ANO
ÚČELNÁ: ANO
AUTOMATIZOVANÁ: ANO
BEZPEČNÁ: ANO
MĚŘITELNÁ: ANO
VRATNÁ: ANO
DŮKAZNĚ OVĚŘITELNÁ: ANO
```

## Verifikace a návrat

```text
TEST_PLAN: focused CyberCore intake tests, relevant documentation tests, ruff, compileall, full pytest, readiness gate.
SUCCESS_EVIDENCE: all executed gates reported with exact results in external evidence directory and review publication evidence.
FAILURE_SIGNAL: any contract, lint, test, documentation, readiness or publication gate failure.
ROLLBACK: revert the single feature commit; no migration or persistent state cleanup.
POST_STATE_VERIFICATION: remote review branch SHA must equal the locally verified HEAD.
```

## Rozhodnutí

```text
OWNER_DECISION: APPROVED
DECISION_REASON: explicit owner instruction on 2026-09-11 to implement into eimyroot/Voodoo-One; remote publication remains a separate governed authorization boundary.
EXPIRY_OR_REVIEW_DATE: review before merge; publication does not authorize merge/release/deploy.
```
