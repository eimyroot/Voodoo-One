# ADR-0027 — Bounded GitHub CREATE_REF Write Activation Gate R1

- Status: PROPOSED — exact-content owner adoption required
- Date: 2026-10-07
- Scope: first current provider-WRITE activation candidate after ADR-0019 READ maturity
- Decision class: R4 security / authority / provider mutation / rollback
- Numbering note: ADR-0027 was unallocated across the active VOODOO One worktrees when this candidate was created.

## Context

ADR-0019 is effectively owner-adopted through the external authority register. On 2026-10-07 the
official G8 READ path completed two sequential successful GitHub Actions acceptances on exact hosted
main `ad66fc2a6a032a7151055a603aac0fffc5ee2f2b`. The retained two-run closure evaluates all 15
ADR-0019 READ maturity criteria as VERIFIED and therefore establishes:

```text
READ_E2E             = VERIFIED
RESTART_RESUME       = VERIFIED
NO_DUPLICATE_EFFECT  = VERIFIED
AUTHORITY_CONTINUITY = VERIFIED
INDEPENDENT_VERIFY   = VERIFIED
FAIL_CLOSED          = VERIFIED

WRITE_RUNTIME_GATE   = ELIGIBLE
```

`ELIGIBLE` is not provider-WRITE authorization.

The repository already contains historical F4b CREATE_REF and F6b DELETE_REF effect evidence and
mutation-capable transport implementations. Those historical effects are evidence only. The current
canonical A09 CREATE_REF and rollback paths intentionally stop at `WriteEffectPreflight/v1` and
`RollbackWriteEffectPreflight/v2`; no current provider mutation transport is composed into the
product runtime and there is no canonical WRITE HTTP route.

The historical `.github/workflows/f4b-live-canary-create-ref.yml` is not a current activation
surface. It is pinned to historical PR 120, branch identity, source lineage and repository
`nulleimy/V-One`. This ADR does not reactivate, repurpose or widen that workflow.

## Decision

The first current provider-WRITE activation may target exactly one bounded GitHub CREATE_REF canary
attempt and nothing broader.

The effect contract is:

```text
provider                 = github
repository               = eimyroot/Voodoo-One
environment              = staging
capability               = github.create-ref/v1
provider operation       = CREATE_REF
target kind              = git_ref
allowed namespace        = refs/heads/vone-canary/*
create semantics         = CREATE_ONLY
maximum mutations        = 1
automatic mutation retry = false
update fallback          = forbidden
force-update fallback    = forbidden
delete fallback          = forbidden
generic execute          = forbidden
production effects       = false
```

The exact ref name and exact target commit SHA must be part of the separately attributable live-effect
authorization. A wildcard namespace is only a ceiling; it is not authority to choose an arbitrary ref.

## Writer identity and credential

The live writer must use a dedicated owner-controlled GitHub App installation identity. It must not use
the workflow `github.token`, a personal PAT, the READ Runner credential or the Verifier App
credential as the provider-WRITE credential.

Required writer properties:

```text
principal class        = github-app-installation
installation owner     = eimyroot
repository scope       = exactly eimyroot/Voodoo-One
repository permissions = contents:write + mandatory metadata:read only
token lifetime         = ephemeral installation token
token issuer           = commit-SHA-pinned actions/create-github-app-token
standing token         = forbidden
ambient fallback       = forbidden
credential reuse       = forbidden outside the exact authorized attempt
```

GitHub App permissions cannot express a branch namespace or CREATE-only verb. Therefore provider-level
least privilege is exact-repository `contents:write`; namespace, verb, mutation-count and no-retry
ceilings remain mandatory runtime controls and are an explicit residual risk.

The writer App must be a different provider principal from the existing G8 Verifier App installation.
The existing Verifier App remains exact-repository READ-only with `contents:read`; widening the
Verifier App to WRITE is forbidden.

## Canonical authority path

The live effect must enter through the released canonical authority path and A09 preparation:

```text
Reviewed ChangeRequest
→ current database-backed permission/workspace authority
→ AuthorizationSnapshot
→ ExecutionGrant/v2
→ exactly-once GrantConsumptionWitness/v1
→ durable Outbox
→ DispatchEnvelope
→ durable Inbox
→ ACTIVE ExecutionEpoch + current Lease / ExecutionCapsule
→ BOUNDED_MUTATION_VERIFIED terminal profile
→ A09CreateRefPreparer
→ WriteEffectPreflight/v1
→ current-fence recheck
→ one exact CREATE_REF provider call
```

No caller-controlled terminal profile, parallel database, parallel permission authority, parallel
fence, historical pilot-seed shortcut or direct transport invocation is accepted.

## Live pre-effect gate

A live CREATE_REF attempt remains BLOCKED unless every item below is freshly true for the exact
activation SHA:

1. ADR-0019 remains effectively ADOPTED.
2. ADR-0027 exact candidate bytes are effectively ADOPTED through the external register.
3. the exact activation SHA is current protected `main`;
4. push/PR CI and the full product-readiness gate are successful on that exact SHA;
5. fresh independent review is CLEAN and blocking review threads are zero;
6. fresh G0 repository-governance verification is SUCCESS on that exact SHA;
7. repeated G8 READ maturity is VERIFIED on that exact activation SHA after the final activation code/workflow is present;
8. the dedicated Writer GitHub App is provider-observed with exactly one repository scope and only
   `contents:write` plus mandatory `metadata:read`;
9. Writer and Verifier App installation principals are distinct;
10. the exact canary ref is provider-observed ABSENT before the effect;
11. the requested ref matches the exact owner-authorized ref byte-for-byte and belongs to the
    strict `refs/heads/vone-canary/` namespace (not merely the same wildcard pattern);
12. the approved target commit equals the exact authorized SHA;
13. the A09 preflight is rebuilt immediately before the effect and the current execution fence passes;
14. runtime egress is default-deny with only the bounded GitHub API path permitted;
15. sanitized evidence contains no credential bytes;
16. rollback readiness is VERIFIED as described below;
17. a separate attributable owner authorization binds the exact activation SHA, repository, canary ref,
    target commit SHA, single CREATE_REF attempt and explicit no-release/no-deploy/no-production ceiling.

The live gate output is only:

```text
CREATE_REF_LIVE_GATE = ELIGIBLE_FOR_ONE_CANARY_ATTEMPT
```

Anything less is:

```text
CREATE_REF_LIVE_GATE = BLOCKED
```

Eligibility for one attempt does not authorize a second attempt, retry, different ref or different
target SHA.

## Effect and ambiguity semantics

The transport remains one-shot. A known provider rejection is terminal for the attempt.

A network timeout, connection loss, malformed successful response or any other state where GitHub may
have received the request is `INDETERMINATE`. Automatic CREATE_REF retry is forbidden.

After ambiguity, the system must perform fresh read-only provider observation. It must not infer absence
from the transport error and must not automatically roll back. A later effect requires a new explicit
authorization after the provider state is known.

## Required post-state verification

A provider 201 response is execution evidence, not verification success.

After the effect:

```text
one CREATE_REF response
→ durable completion
→ ExecutionReceipt/v2
→ fresh read-only Runner observation
→ independent owner-controlled Verifier App readback
→ ObservedPostState/v1
→ VerificationStrength/v1 = INDEPENDENT_PROVIDER_READBACK
→ VerificationResult/v1
```

The canary attempt is accepted only if the independently observed ref exists and points to the exact
authorized target SHA and the canonical `VerificationResult/v1` verdict is `VERIFIED`.

Runner success, HTTP 201, receipt integrity, a matching digest or successful transport alone must never
promote the operation to VERIFIED.

## Rollback semantics

Rollback is required as a readiness property but DELETE_REF is not authorized by this CREATE_REF gate.

Before CREATE_REF is attempted:

- the existing A09 rollback preparation and DELETE_REF transport/verification tests must remain green;
- the exact rollback strategy is `DELETE_EXACT_CREATED_REF`;
- no automatic rollback is permitted;
- rollback requires a new, separately attributable effect authorization.

A live rollback may execute only after a fresh pre-delete READ proves that the exact canary ref still
points to the exact SHA created by this operation. Because GitHub DELETE_REF has no expected-SHA atomic
compare-and-delete, rollback remains explicitly `READ_THEN_DELETE_NON_ATOMIC`.

If the ref changed, state is ambiguous, verification is unavailable or the exact created SHA cannot be
re-established, DELETE_REF is blocked.

Successful rollback requires exactly one DELETE_REF attempt, no automatic retry and independent
read-only absence verification. Rollback success must not be inferred from DELETE transport success.

## Current readiness on 2026-10-07

Observed current state at candidate creation:

```text
ADR_0019_READ_GATE                 = VERIFIED
WRITE_RUNTIME_GATE                 = ELIGIBLE
A09_CREATE_REF_PREPARATION         = IMPLEMENTED
A09_ROLLBACK_PREPARATION           = IMPLEMENTED
HISTORICAL_F4B_F6B_EVIDENCE        = RETAINED
CURRENT_WRITER_GITHUB_APP          = NOT_PROVISIONED
CURRENT_WRITE_APP_SECRET_VARIABLES = NOT_PRESENT
CURRENT_LIVE_CREATE_REF_WORKFLOW   = NOT_CREATED
CURRENT_EXACT_SHA_G0               = REQUIRED_AT_ACTIVATION
CURRENT_EXACT_SHA_G8_RECHECK       = REQUIRED_AT_ACTIVATION
CREATE_REF_LIVE_GATE               = BLOCKED
PROVIDER_WRITE                     = NOT_AUTHORIZED / NOT_PERFORMED
RELEASE                            = NOT_AUTHORIZED / NOT_PERFORMED
DEPLOYMENT                         = NOT_AUTHORIZED / NOT_PERFORMED
PRODUCTION_EFFECTS                 = BLOCKED / NOT_PERFORMED
```

## Adoption gate

This candidate creates no provider authority until all of the following are true for its exact immutable
bytes:

```text
owner adoption decision recorded = YES
exact-head CI / verify            = SUCCESS
product/documentation truth gates = SUCCESS
fresh independent review         = CLEAN
blocking review threads           = 0
merge through protected main      = SUCCESS
external adoption record          = RECORDED
```

The exact reviewed ADR bytes remain `PROPOSED`; effective adoption must be recorded separately in
`docs/governance/AUTHORITY_AND_ADOPTION_REGISTER.md` without modifying this ADR.

Merge, CI, review or adoption of this ADR does not itself authorize a CREATE_REF effect.

## Release and deployment boundary

This ADR is staging-canary only. It does not authorize:

- production provider mutation;
- arbitrary branch creation;
- branch update or force-update;
- DELETE_REF;
- release;
- deployment;
- production effects;
- generic provider WRITE.

Production release still requires the separate release-promotion chain,
`production_release_authorized`, rollback planning and explicit deployment authorization.

## Rollback of this decision

Before live activation, rollback is a focused revert of the ADR/gate implementation and removal of any
unactivated Writer App configuration.

After Writer App provisioning but before an authorized effect, disable/uninstall the Writer App and
remove its repository configuration. No provider ref cleanup exists because no provider mutation has
occurred.

Any already-created canary ref is provider state and may be removed only through the separately
authorized rollback effect described above.
