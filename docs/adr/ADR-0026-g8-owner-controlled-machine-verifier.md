# ADR-0026 — G8 Owner-Controlled Machine Verifier Identity

- Status: PROPOSED — governed adoption pending
- Date: 2026-10-06
- Scope: G8 GitHub READ Verifier identity and credential topology
- Decision class: R3 — identity / credentials / independent verification
- Compatibility target: preserve or strengthen adopted ADR-0019
- Numbering note: ADR-0026 avoids colliding with ADR-0023 through ADR-0025 already present in the active engineering lineage outside the current hosted-main ancestry.

## Context

Adopted ADR-0019 requires independent Verifier execution with a separate identity and credential decision before repeated G8 READ evidence can make any future provider-WRITE runtime merely eligible. It does not require the separate provider principal to be controlled by a separate human.

The original G8 GitHub acceptance topology used two long-lived user credentials. The official GitHub Actions parity attempt on 2026-10-06 proved that Actions can execute on current main but failed closed when the Runner user credential returned HTTP 401 during `/user` attestation. Maintaining a second personal GitHub user solely to obtain Verifier principal separation also adds credential lifecycle and account-operational cost without increasing human governance independence.

The owner requires human authority to remain with the VOODOO owner while preserving technical Runner/Verifier separation.

## Proposed decision

G8 uses two independently authenticated provider principals with different credential classes:

    Runner
      principal        = github-principal/user/<user-id>
      credential       = explicitly configured GitHub user credential
      attestation      = authenticated GET /user
      provider effect  = READ only

    Verifier
      principal        = github-principal/app-installation/<installation-id>
      credential       = ephemeral GitHub App installation access token
      attestation      = trusted issuer installation-id
                         + authenticated GET /installation/repositories
      repository scope = exactly the G8 target repository
      provider effect  = READ only

The Verifier GitHub App is owner-controlled machine identity. No second human approver, second personal GitHub account or collaborator is required by this decision.

The official GitHub Actions gate mints the Verifier installation token at run time using `actions/create-github-app-token` pinned to exact commit `bcd2ba49218906704ab6c1aa796996da409d3eb1`. The token request is restricted to the current repository and `contents: read`.

The App private key is used only by the token-minting step. It is not passed into the product runtime, container, evidence files or provider read transport.

## Attestation and fail-closed rules

The machine Verifier is accepted only when all applicable checks pass:

1. Runner credential authenticates through GitHub `/user`.
2. Verifier token is an installation-token-shaped credential from the `ghs_` family.
3. The trusted token issuer supplies a positive installation ID.
4. `/installation/repositories` succeeds using the exact Verifier token.
5. The effective installation token exposes exactly one repository.
6. That repository is exactly the configured G8 target repository.
7. Runner and Verifier credential material are distinct.
8. Runner and Verifier principal identities are distinct.
9. Runner and Verifier credential classes and provider-instance identities are distinct.
10. Both credentials independently READ the exact target ref and observe the exact expected SHA.
11. A bound App Verifier transport refuses a provider READ for any repository outside its attested repository scope.

Missing, expired, malformed, wrong-scope, multi-repository, mismatched or otherwise ambiguous Verifier credentials fail closed.

The installation ID is not treated as self-authenticating caller text. Its provenance is the pinned token issuer in the GitHub Actions gate; provider observation separately proves that the resulting credential has exactly the expected repository scope.

## Independence model

G8 distinguishes three independent properties:

    IDENTITY_INDEPENDENCE
      Runner user principal != Verifier App installation principal

    EXECUTION_INDEPENDENCE
      separate verifier runtime profile, credential decision and provider readback

    EVIDENCE_INDEPENDENCE
      verifier evaluates fresh provider-observed state, not the Runner success claim

A different principal alone is not proof that a verification conclusion is epistemically independent. G8 remains a deterministic Git-ref readback gate and does not add an LLM adjudicator, majority vote or consensus mechanism.

## Supporting research

`VeriHarness: Scaling Agentic Verification for Long-Horizon Tasks` (arXiv:2610.00972, 2026) is non-normative supporting research. Its separation of evidence gathering, disagreement resolution and consensus challenge supports the broader principle that verification quality depends on independent evidence acquisition rather than mere agreement. Those agentic mechanisms are not introduced into G8 by this ADR; they are candidates for future Rook/Relore verification work.

## Security consequences

This proposal reduces standing Verifier credential lifetime and removes the need for a second personal-user Verifier credential while preserving provider-principal separation.

It does not:

- authorize provider mutation;
- add CREATE_REF, DELETE_REF, rollback or generic provider transport;
- authorize production effects;
- authorize release or deployment;
- make a GitHub App private key available to the product runtime;
- weaken ADR-0019;
- establish that the GitHub App is already provisioned or live-verified.

## Required repository configuration after adoption

The official gate expects:

    repository variable:
      VONE_G8_VERIFIER_GITHUB_APP_CLIENT_ID

    repository secret:
      VONE_G8_VERIFIER_GITHUB_APP_PRIVATE_KEY

The corresponding GitHub App must be installed on the G8 target repository with only the permissions needed for the READ gate. For the current Git-ref verification path that means repository contents READ and no repository write permission.

Provisioning the App, storing its private key, rotating credentials and executing a live G8 run are separate protected operations. This ADR and its implementation candidate do not perform them.

## Compatibility and migration

Until this candidate is merged and effectively adopted, current main remains authoritative.

After adoption, the old second-user Verifier credential path is superseded for official G8 GitHub Actions acceptance. Historical evidence produced under the previous topology remains valid for the exact source/runtime state it recorded and is not rewritten.

The Runner user credential path remains unchanged.

## Verification requirements

Before adoption:

- focused runtime and activation tests;
- explicit App-attestation negative tests;
- workflow contract tests proving exact action pin and READ-only permission;
- Ruff and compile checks;
- full repository regression;
- product readiness;
- exact scoped diff review;
- protected-main review/merge gates.

After App provisioning, official G8 acceptance must additionally prove:

- App token minting succeeds;
- installation repository scope is exact;
- user/App principal separation is retained;
- both principals observe exact main;
- canonical HTTP READ, ACTIVE interruption/resume and independent VerificationResult/v1 remain VERIFIED;
- sanitized evidence contains no raw credentials or App private key.

Repeated READ maturity remains open until fresh live evidence closes it.

## Rollback

Before merge, discard or supersede the candidate branch.

After merge but before live activation, revert the focused implementation commit and keep G8 disabled.

After provisioning, disable the official G8 gate or remove the App installation/secret, then revert the implementation through the normal protected-main path. No provider state mutation exists to undo because this capability is READ-only.

## Adoption gate

This ADR changes an identity/trust boundary and therefore does not become effective through repository presence or a candidate commit alone. Effective adoption requires the normal exact-content owner/adoption protocol and protected-main review gates.

    PROVIDER_WRITE      = NOT_AUTHORIZED
    RELEASE             = NOT_AUTHORIZED
    DEPLOYMENT          = NOT_AUTHORIZED
    PRODUCTION_EFFECTS  = BLOCKED
