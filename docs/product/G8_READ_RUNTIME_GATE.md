# G8 — Explicit READ-Only Provider Runtime Gate

Current source state: **G8 READ runtime pack IMPLEMENTED / MERGED; explicit non-production activation path IMPLEMENTED; owner-authorized alternative external Linux READ acceptance VERIFIED for `main@2f9ab7fdfe8793a9b2c977bc620c0f10921f4e3f`; default remains OFF and official GitHub Actions parity remains pending due account-level Actions policy.**

## Purpose

G8 productizes the first default provider runtime pack without widening provider-effect authority. The first pack is READ-only and exists to prove the canonical HTTP → trust-plane → restart-safe Runner → independent Verifier → `VerificationResult/v1` lifecycle as one real operational path.

## Preconditions

```text
G0_GITHUB_GOVERNANCE = PASS
G7_CANONICAL_API = MERGED
G7_DURABLE_RESUME = MERGED
G7_RUNTIME_RESUME_WIRING = MERGED
PRODUCTION_WRITE_EFFECTS = DISABLED
```

## Required runtime bindings

The G8 runtime pack must share the exact canonical objects used by ProductComposition:

- ProductService database;
- DatabasePermissionAuthority;
- terminal-profile registry;
- envelope revision;
- DurableCurrentExecutionFence;
- canonical READ terminal contracts.

Any parallel database, permission authority, profile registry, fence, execution coordinator, or legacy fallback is rejected.

## Identity and credential separation

Runner and independent Verifier must have distinct identities and distinct credential decisions. Credential bytes are never serialized into V-One evidence objects.

The runtime must not fall back to ambient shell credentials, developer-local Git state, legacy `ExecutionService`, or a generic provider client with mutation permission.

Missing/ambiguous configuration fails closed.

## Authority ceiling

G8 R1 exposes only the exact canonical READ capability:

```text
terminal_profile = READ_ONLY_VERIFIED
capability       = github.read-ref/v1
```

The default runtime pack must contain no provider mutation transport and no callable CREATE_REF, DELETE_REF, rollback, generic execute, or arbitrary API method surface.

## Acceptance automation

The repository includes `g8-live-product-read-acceptance`, a manual main-only GitHub Actions gate. It requires separately provisioned fine-grained READ credentials `VONE_G8_RUNNER_GITHUB_TOKEN` and `VONE_G8_VERIFIER_GITHUB_TOKEN` bound to distinct GitHub user principals. The workflow-level `contents: read` permission remains only the Actions checkout ceiling; the installation-scoped `github.token` is not used as a G8 user credential because it cannot satisfy the released `/user` principal attestation contract. The workflow performs no provider mutation, release or deployment.

The workflow is the official parity path. On 2026-09-19 GitHub returned HTTP 422 before run creation because Actions were disabled by account-level policy for the user, so the owner authorized a one-time alternative external Linux run using the existing G8 acceptance semantics as the evidence standard. That alternative run verified exact `main` SHA `2f9ab7fdfe8793a9b2c977bc620c0f10921f4e3f` with separate Runner and Verifier credentials, GitHub-only egress, no provider write, no release, no deployment and durable sanitized evidence under `/Users/eimyna/0_EVIDENCE/Voodoo-One/G8_ALT_EXTERNAL_LINUX_20260919_2f9ab7f`.

Missing Runner or Verifier credentials, inability to attest either credential through GitHub `/user`, identical Runner/Verifier principals, target-SHA drift, duplicate durable lineage or a non-`VERIFIED` result all fail closed.

The R3 decision record is `docs/governance/G8_LIVE_ACCEPTANCE_R3_DECISION_CARD.md`.

## Acceptance sequence

A G8 candidate is not product-ready until one exact candidate head demonstrates:

```text
1. full repository CI / verify = SUCCESS
2. product readiness = SUCCESS
3. dependency audit = SUCCESS
4. image build + smoke = SUCCESS
5. authenticated canonical HTTP admission = SUCCESS
6. durable canonical preparation/admission reaches ACTIVE epoch + current lease/capsule = VERIFIED
7. process interruption/restart occurs before Runner completion = VERIFIED
8. durable resume reconstructs the same execution while ACTIVE = SUCCESS
9. no duplicate prepare/grant/consume/outbox/envelope/inbox/epoch/lease = VERIFIED
10. resumed governed real READ Runner = SUCCESS
11. durable completion of resumed execution = SUCCESS
12. independent Verifier observation with separate identity/credential decision = SUCCESS
13. VerificationResult/v1 evaluation = SUCCESS
14. authenticated canonical HTTP READ E2E = SUCCESS
15. failure injection / corrupt or revoked durable evidence = FAIL-CLOSED
16. fresh independent R3 review = CLEAN
```

The restart gate explicitly exercises the existing `ACTIVE`-execution resume contract. It does not require or claim resumption of an already `COMPLETED` execution.

Repeated READ E2E evidence must be retained before ADR-0019 can make WRITE runtime merely `ELIGIBLE`.

## Retained alternative acceptance evidence

```text
G8_READ_ACCEPTANCE          = VERIFIED_ALT_EXTERNAL_LINUX
EXACT_MAIN_SHA              = 2f9ab7fdfe8793a9b2c977bc620c0f10921f4e3f
RUNNER_VERIFIER_SEPARATION  = VERIFIED
AUTHENTICATED_HTTP_READ     = VERIFIED
ACTIVE_INTERRUPTION_RESUME  = VERIFIED
INDEPENDENT_VERIFIER_READ   = VERIFIED
PROVIDER_WRITE              = NOT_PERFORMED
RELEASE                     = NOT_PERFORMED
DEPLOYMENT                  = NOT_PERFORMED
GITHUB_ACTIONS_PARITY       = PENDING_ACCOUNT_ACTIONS_POLICY
EVIDENCE_ROOT               = /Users/eimyna/0_EVIDENCE/Voodoo-One/G8_ALT_EXTERNAL_LINUX_20260919_2f9ab7f
EVIDENCE_MANIFEST_SHA256    = b4ced161adc99c98243b523c3bf15a1055e92a5096e0839755d2a2f86f889d92
```

## Non-scope

- no CREATE_REF provider call;
- no DELETE_REF provider call;
- no rollback effect;
- no generic provider mutation client;
- no production WRITE;
- no completed-execution recovery/reverification contract;
- no release;
- no deployment;
- no weakening of ADR-0019.

## Exit state

G8 R1 may only claim:

```text
DEFAULT_READ_PROVIDER_RUNTIME = IMPLEMENTED / VERIFIED
REAL_CANONICAL_READ_E2E       = VERIFIED_ALT_EXTERNAL_LINUX
GITHUB_ACTIONS_PARITY         = PENDING_ACCOUNT_ACTIONS_POLICY
WRITE_RUNTIME_GATE            = BLOCKED or ELIGIBLE per ADR-0019 evidence
```

It must not claim release, deployment, unrestricted provider authority, or production WRITE.
