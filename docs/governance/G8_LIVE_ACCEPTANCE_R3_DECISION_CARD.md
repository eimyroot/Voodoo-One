# G8 Live Product READ Acceptance — R3 Decision Card

| Field | Decision |
|---|---|
| User | VOODOO One owner/operator validating the first real product READ path |
| Problem | G8 activation exists, but exact-head HTTP→Runner→Verifier→VerificationResult evidence is still missing |
| Expected outcome | One manual main-only gate proves authenticated READ, ACTIVE interruption, same-execution resume, independent verification and no duplicate durable lineage |
| Risk class | R3 — credentials, provider access, runtime isolation and evidence |
| Smallest safe slice | GitHub Actions acceptance workflow plus a fixed-purpose test driver; no provider mutation and no production effects |
| Source of truth | current repository, exact Git SHA, locked dependencies, exact image digest, live GitHub observations and retained artifact evidence |
| Data and permissions | Runner uses `VONE_G8_RUNNER_GITHUB_TOKEN`, a fine-grained READ-only credential bound to the Runner principal; Verifier uses separate `VONE_G8_VERIFIER_GITHUB_TOKEN`, a fine-grained READ-only/public-read credential bound to another principal |
| Success evidence | full repo tests/readiness, dependency audit, image/SBOM digests, distinct principals, exact SHA observations, HTTP VERIFIED result, restart/resume lineage and sanitized evidence artifact |
| Rollback | disable/remove workflow and secret; revert the workflow/driver commit; no provider state mutation exists to undo |
| Non-scope | provider WRITE, production effects, release, deployment, secret creation, merge authorization |
| Owner decision | 2026-09-19 instruction to proceed with CR-3 acceptance infrastructure |

## Safety decision

The workflow is `workflow_dispatch` only and runs only on `refs/heads/main`. It does not run on pull requests or pushes. The job permission ceiling is `contents: read`; no workflow permission grants write authority.

The Runner and Verifier credentials are never serialized into evidence. The gate fails closed when either provider credential secret is absent, when principal attestation fails, when both credentials resolve to the same principal, or when either credential does not observe the exact candidate SHA.

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

Current implementation status is **IMPLEMENTED / LOCALLY VERIFIED; LIVE G8 EXIT GATE NOT VERIFIED**. Full repository pytest, product readiness, workflow contract tests, YAML parsing, Python lint/compile checks and a fresh SQLite fixture smoke have passed locally on the CR-3 candidate bytes. The live G8 exit gate remains **NOT VERIFIED** until this workflow runs successfully on the exact main SHA with separately provisioned fine-grained READ-only Runner and Verifier credentials bound to distinct user principals.

## Subsequent evidence update — 2026-09-19

The historical decision above targeted the GitHub Actions path. After workflow dispatch was blocked by account-level Actions policy, the owner explicitly authorized a one-time alternative external Linux acceptance using the same G8 evidence semantics.

Exact source `2f9ab7fdfe8793a9b2c977bc620c0f10921f4e3f` subsequently passed authenticated canonical HTTP READ, ACTIVE interruption, same-execution restart/resume, zero duplicate lineage, distinct Runner/Verifier credentials, GitHub-only allowed egress and independent verification. The retained acceptance status is `VERIFIED_ALT_EXTERNAL_LINUX`.

This later evidence supersedes the card's earlier current-state statement that live acceptance was not verified for this exact source scope. It does not rewrite the original decision, does not establish repeated ADR-0019 evidence, and does not authorize provider WRITE, release, deployment or production effects.

Evidence root: `/Users/eimyna/0_EVIDENCE/Voodoo-One/G8_ALT_EXTERNAL_LINUX_20260919_2f9ab7f`.
