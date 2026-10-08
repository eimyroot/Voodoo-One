# GitHub CREATE_REF Write Activation — R1 Decision Card

| Field | Decision |
|---|---|
| User | VOODOO One owner/operator |
| Problem | ADR-0019 READ maturity is now VERIFIED, but current provider WRITE still has no adopted effect-specific activation authority |
| Expected outcome | define one staging-only, one-shot GitHub CREATE_REF canary gate without activating provider mutation |
| Risk class | R4 — external provider mutation, credential scope, rollback and independent post-state verification |
| Smallest safe slice | exact-content ADR/gate + truth reconciliation + regression tests; no Writer App provisioning and no live WRITE workflow/effect |
| Source of truth | current repository, ADR-0019 adoption record, G8 two-run closure, historical F4b/F6b evidence, current A09 pre-effect implementation and exact-head CI |
| Effect ceiling | one `CREATE_REF` in `eimyroot/Voodoo-One`, staging, exact `refs/heads/vone-canary/*` ref, exact authorized SHA, create-only, no retry/update/delete fallback |
| Writer credential target | dedicated owner-controlled GitHub App installation, exact one-repository scope, `contents:write` plus mandatory `metadata:read`, ephemeral installation token |
| Verifier | existing owner-controlled G8 Verifier App remains distinct and READ-only; widening it to WRITE is forbidden |
| Post-state | exact ref + exact target SHA independently read back and persisted as canonical `VerificationResult/v1 = VERIFIED` |
| Rollback | separate authorization only; fresh exact-SHA pre-delete READ, one DELETE_REF, no retry, independent absence verification |
| Non-scope | Writer App provisioning, secret creation, live workflow, CREATE_REF, DELETE_REF, release, deployment, production effects |
| Current decision | DESIGN / CANDIDATE ONLY; live effect remains BLOCKED |

## Current prerequisite transition

The 2026-10-07 G8 closure establishes:

    READ_E2E             = VERIFIED
    RESTART_RESUME       = VERIFIED
    NO_DUPLICATE_EFFECT  = VERIFIED
    AUTHORITY_CONTINUITY = VERIFIED
    INDEPENDENT_VERIFY   = VERIFIED
    FAIL_CLOSED          = VERIFIED

    WRITE_RUNTIME_GATE   = ELIGIBLE

That transition permits effect-specific design. It does not authorize provider mutation.

## Identity topology

    Writer:
      dedicated GitHub App installation
      exact repository eimyroot/Voodoo-One
      contents:write + metadata:read only
      ephemeral token
      one authorized CREATE_REF attempt

    Verifier:
      voodoo-one-g8-verifier App installation
      exact repository eimyroot/Voodoo-One
      contents:read + metadata:read
      independent provider readback

    Writer principal != Verifier principal
    Writer credential != Verifier credential

The Verifier App must not be widened to satisfy Writer needs.

## Live effect gate

A future live effect requires all of:

    ADR-0027_EFFECTIVE_STATUS          = ADOPTED
    EXACT_ACTIVATION_MAIN_SHA          = PINNED
    EXACT_HEAD_CI                      = SUCCESS
    INDEPENDENT_REVIEW                 = CLEAN
    BLOCKING_REVIEW_THREADS            = 0
    G0_ON_EXACT_ACTIVATION_SHA         = VERIFIED
    TWO_RUN_G8_ON_EXACT_ACTIVATION_SHA = VERIFIED
    WRITER_APP_EXACT_REPO_SCOPE        = VERIFIED
    WRITER_APP_PERMISSION_CEILING      = VERIFIED
    WRITER_VERIFIER_PRINCIPALS         = DISTINCT
    CANARY_REF_PRE_STATE               = ABSENT
    CANARY_REF_NAMESPACE               = STRICT_PREFIX
    EXACT_AUTHORIZED_REF               = MATCH_REQUESTED_REF
    A09_CURRENT_FENCE_PREFLIGHT        = PASS
    DEFAULT_DENY_EGRESS                = PASS
    ROLLBACK_READINESS                 = VERIFIED
    EXACT_EFFECT_AUTHORIZATION         = RECORDED

Only then:

    CREATE_REF_LIVE_GATE = ELIGIBLE_FOR_ONE_CANARY_ATTEMPT

Anything else:

    CREATE_REF_LIVE_GATE = BLOCKED

## Failure semantics

Known rejection stops the attempt. Ambiguous network/provider outcome is INDETERMINATE and is never
automatically retried. Independent readback is required before any later effect decision.

HTTP 201 is not verification. Success requires canonical independent provider readback and
`VerificationResult/v1 = VERIFIED`.

## Rollback

CREATE_REF authority never implies DELETE_REF authority.

Rollback requires a new owner-attributable authorization, fresh pre-delete observation of the exact
created SHA, one DELETE_REF attempt, no retry and independent absence verification. The temporal model
remains `READ_THEN_DELETE_NON_ATOMIC`.

## 7×ANO candidate gate

    JEDNODUCHÁ: ANO — one named effect, one repo, one namespace, one mutation
    ÚČELNÁ: ANO — converts READ maturity into a bounded next-stage gate without broad WRITE enablement
    AUTOMATIZOVANÁ: ANO — final live gate is intended to be machine-enforced and evidence-sealed
    BEZPEČNÁ: ANO — exact authority chain, dedicated App, one-shot transport, no retry, independent verify
    MĚŘITELNÁ: ANO — SHA, ref, principal, permissions, mutation count and verification result are observable
    VRATNÁ: ANO — source/config can be reverted pre-effect; provider rollback is separately governed
    DŮKAZNĚ OVĚŘITELNÁ: ANO — exact-head CI + G0 + repeated G8 + sanitized live effect evidence

Current truth:

    CREATE_REF_GATE_DESIGN = PROPOSED
    WRITER_APP = NOT_PROVISIONED
    LIVE_WRITE_WORKFLOW = NOT_CREATED
    PROVIDER_WRITE = NOT_AUTHORIZED / NOT_PERFORMED
    RELEASE = NOT_AUTHORIZED / NOT_PERFORMED
    DEPLOYMENT = NOT_AUTHORIZED / NOT_PERFORMED
    PRODUCTION_EFFECTS = BLOCKED / NOT_PERFORMED
