# G8 Owner-Controlled Machine Verifier — R3 Decision Card

| Field | Decision |
|---|---|
| User | VOODOO One owner/operator |
| Problem | G8 requires an independent provider principal, but a second long-lived personal-user Verifier credential adds account/credential lifecycle cost and is not a requirement for separate human authority |
| Expected outcome | Runner remains the owner user principal while Verifier becomes an owner-controlled, repository-scoped, ephemeral GitHub App installation principal |
| Risk class | R3 — identity, credentials, provider access and independent verification |
| Smallest safe slice | Add credential-class-specific App installation attestation, exact-repository scope enforcement, workflow token minting and fail-closed tests; no live App provisioning in the code slice |
| Source of truth | current repository, exact Git SHA, GitHub App installation-token semantics, executed tests and later live provider evidence |
| Data and permissions | Runner: explicit GitHub user READ credential. Verifier: ephemeral GitHub App installation token minted only for the target repository with `contents: read` |
| Success evidence | distinct user/App principals, exact repository scope, exact target SHA from both READ paths, canonical G8 restart/resume and independent VerificationResult/v1 |
| Rollback | keep G8 disabled; remove/disable App configuration; revert focused implementation through protected main |
| Non-scope | provider WRITE, second human approver, collaborator requirement, production effects, release, deployment, merge authorization |
| Owner decision | 2026-10-06 instruction to redesign G8 Verifier as an owner-controlled read-only machine identity and proceed with implementation |

## Independence contract

    IDENTITY
      Runner user != Verifier App installation

    EXECUTION
      separate role-bound verifier runtime and credential decision

    EVIDENCE
      fresh provider readback independent of Runner success

These are separate claims. Principal separation does not by itself prove evidence independence.

## Fail-closed contract

The slice is accepted only if the Verifier installation token is ephemeral, installation identity is present, effective repository access contains exactly the configured target repository, the App transport cannot read a different repository, both provider READs observe the exact expected SHA and no mutation surface is introduced.

Missing or ambiguous App configuration, a non-installation token, invalid installation ID, wrong or multi-repository scope, principal collapse, target drift or provider observation failure blocks the gate.

## Runtime configuration

After this candidate is adopted and the App is separately provisioned, the official workflow uses:

    VONE_G8_RUNNER_GITHUB_TOKEN                 repository secret
    VONE_G8_VERIFIER_GITHUB_APP_CLIENT_ID       repository variable
    VONE_G8_VERIFIER_GITHUB_APP_PRIVATE_KEY     repository secret

The App private key exists only at token issuance. The product runtime receives only the ephemeral installation token, installation ID and exact repository scope.

## 7×ANO candidate gate

    JEDNODUCHÁ: ANO — one user Runner plus one machine Verifier identity
    ÚČELNÁ: ANO — removes the second-personal-account dependency without weakening identity separation
    AUTOMATIZOVANÁ: ANO — official gate mints and revokes an ephemeral installation token
    BEZPEČNÁ: ANO — repository-scoped READ-only App token, exact principal/scope attestation, fail closed
    MĚŘITELNÁ: ANO — principal class, installation ID, repository scope and exact SHA are observable
    VRATNÁ: ANO — G8 remains disabled by default; App config and focused commit can be removed
    DŮKAZNĚ OVĚŘITELNÁ: ANO — focused/full tests plus later sanitized live G8 evidence

Current truth for this decision card is `IMPLEMENTED_IN_CANDIDATE / NOT_LIVE_PROVISIONED / NOT_LIVE_VERIFIED`.
