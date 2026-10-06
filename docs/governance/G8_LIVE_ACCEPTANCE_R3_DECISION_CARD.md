# G8 Live Product READ Acceptance — R3 Decision Card

| Field | Decision |
|---|---|
| User | VOODOO One owner/operator validating the first real product READ path |
| Problem | G8 activation exists, but exact-head HTTP→Runner→Verifier→VerificationResult evidence is still missing |
| Expected outcome | One manual main-only gate proves authenticated READ, ACTIVE interruption, same-execution resume, independent verification and no duplicate durable lineage |
| Risk class | R3 — credentials, provider access, runtime isolation and evidence |
| Smallest safe slice | GitHub Actions acceptance workflow plus a fixed-purpose test driver; no provider mutation and no production effects |
| Source of truth | current repository, exact Git SHA, locked dependencies, exact image digest, live GitHub observations and retained artifact evidence |
| Data and permissions | Runner uses `VONE_G8_RUNNER_GITHUB_TOKEN`, a fine-grained READ-only credential bound to the Runner user principal; candidate machine-Verifier flow mints an ephemeral repository-scoped GitHub App installation token from `VONE_G8_VERIFIER_GITHUB_APP_CLIENT_ID` + `VONE_G8_VERIFIER_GITHUB_APP_PRIVATE_KEY`, requests only `contents: read`, and binds it to a distinct App installation principal |
| Success evidence | full repo tests/readiness, dependency audit, image/SBOM digests, distinct principals, exact SHA observations, HTTP VERIFIED result, restart/resume lineage and sanitized evidence artifact |
| Rollback | disable/remove workflow and secret; revert the workflow/driver commit; no provider state mutation exists to undo |
| Non-scope | provider WRITE, production effects, release, deployment, secret creation, merge authorization |
| Owner decision | 2026-09-19 instruction to proceed with CR-3 acceptance infrastructure |

## Safety decision

The workflow is `workflow_dispatch` only and runs only on `refs/heads/main`. It does not run on pull requests or pushes. The job permission ceiling is `contents: read`; no workflow permission grants write authority.

The Runner and Verifier credentials are never serialized into evidence. In the candidate machine-Verifier flow, the Verifier installation token is ephemeral and its exact repository scope is provider-observed before runtime use. The gate fails closed when credential issuance is incomplete, principal attestation fails, repository scope is ambiguous or mismatched, or either credential does not observe the exact candidate SHA.

## 7×ANO gate

```text
JEDNODUCHÁ: ANO — one workflow and one fixed-purpose driver
ÚČELNÁ: ANO — closes the current G8 live-acceptance blocker
AUTOMATIZOVANÁ: ANO — one manual exact-head Actions gate
BEZPEČNÁ: ANO — read-only permissions, distinct principals, isolated runtime, fail-closed secret checks
MĚŘITELNÁ: ANO — exact SHA, digests, verification verdict and durable row counts
VRATNÁ: ANO — workflow/secret can be disabled; provider state is read-only
DŮKAZNĚ OVĚŘITELNÁ: ANO — sanitized retained artifact with SHA-256 checksums
```

Current implementation status is **IMPLEMENTED / OWNER-AUTHORIZED ALTERNATIVE EXTERNAL LINUX READ ACCEPTANCE VERIFIED; OFFICIAL GITHUB ACTIONS PARITY PENDING**.

On 2026-09-19 the official `g8-live-product-read-acceptance` workflow could not be dispatched because GitHub returned HTTP 422 before creating a run: account-level Actions policy had disabled Actions for the user. The owner authorized a one-time alternative external Linux acceptance run using the existing G8 acceptance workflow semantics as the evidence standard.

The alternative run verified exact `main` SHA `2f9ab7fdfe8793a9b2c977bc620c0f10921f4e3f` with distinct Runner and Verifier credentials, GitHub-only egress, authenticated canonical HTTP READ, ACTIVE interruption, same-execution resume, independent verifier readback and `VerificationResult/v1`. It performed no provider write, release, deployment or production effect. Durable sanitized evidence is retained at `/Users/eimyna/0_EVIDENCE/Voodoo-One/G8_ALT_EXTERNAL_LINUX_20260919_2f9ab7f`; `SHA256SUMS.txt` has SHA-256 `b4ced161adc99c98243b523c3bf15a1055e92a5096e0839755d2a2f86f889d92`.

The official GitHub Actions gate remains the parity rerun path once the account-level Actions policy blocker is removed. This pending parity item does not downgrade the owner-authorized product READ acceptance evidence and does not authorize provider WRITE, release or deployment.


## 2026-10-06 successor candidate — machine Verifier identity

The credential topology above is historical evidence for the original G8 acceptance design.
`ADR-0026-g8-owner-controlled-machine-verifier.md` is a new R3 candidate that preserves the
independent-provider-principal requirement while replacing the official second-user Verifier
credential with an owner-controlled GitHub App installation credential.

The candidate is not effective merely because code exists on a review branch. GitHub App
provisioning and live G8 verification remain separate protected steps. Historical acceptance
evidence above remains unchanged.
