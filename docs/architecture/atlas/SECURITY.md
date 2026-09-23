# Security & Trust Boundaries

Security posture is deny-by-default / fail-closed. This Atlas summarizes the implemented boundaries; `docs/architecture/TRUST_BOUNDARIES.md` remains the detailed trust-boundary inventory.

## Authentication

Released authentication is local username/password plus signed session tokens. Session tokens use purpose-derived HMAC keys, bounded TTL, active-session registration and live account/role revalidation. Raw session identifiers are represented through derived references in durable lifecycle state.

OIDC configuration has validation contracts but `validate_identity_provider_startup()` deliberately raises because the provider is unreleased.

## Authorization

Outer API permissions use role permissions (`viewer`, `developer`, `operator`, `security_reviewer`, `auditor`, `administrator`). Canonical operation authority additionally uses `DatabasePermissionAuthority`, which rereads current active user, role permission, exact workspace/environment and explicit membership from the product database.

A stale in-memory principal is therefore not sufficient canonical authority.

## Secrets

Product startup requires a session signing secret and bootstrap token. G8 activation additionally requires distinct Runner and Verifier GitHub tokens plus provider instance IDs and runtime/capsule digests. There is no generic `GITHUB_TOKEN` fallback in the activation contract.
## HTTP boundary controls

- explicit trusted hosts; wildcard hosts are rejected;
- explicit CORS origins only, with wildcard origin rejected;
- CSP, no-store, clickjacking/content-type/referrer/permissions headers;
- HSTS only when `VOODOO_ENV=production`;
- bounded route/path/header models and authentication rate limiting.

## Privileged/effect boundaries

Legacy local execution requires an approved request, matching workspace/environment and inactive emergency stop. Production requests additionally require `VOODOO_ALLOW_PRODUCTION_EFFECTS=true`.

Canonical READ authority is narrowed server-side to `READ_ONLY_VERIFIED + github.read-ref/v1`; callers cannot select a stronger terminal profile. G8 is non-production only, SQLite-only, and requires distinct Runner/Verifier credentials and provider instances.

Provider WRITE is currently blocked on the canonical product path. Historical write pilots are evidence, not standing authority.

## Trust-boundary gaps

Production secrets management, released OIDC/MFA, tenant isolation, released PostgreSQL/HA, production network policy enforcement and production deployment controls are not current verified capabilities.

Primary diagram: [as-is-security-boundaries.mmd](diagrams/as-is-security-boundaries.mmd).