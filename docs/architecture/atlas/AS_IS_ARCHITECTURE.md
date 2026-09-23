# B. AS-IS Architecture

This document describes the current product before any target redesign.

## System context

VOODOO One is a governed operations control plane for human and AI-initiated operational intent. Its current responsibility is to turn an allowed request into bounded execution with explicit authority, approval/safety controls and durable evidence.

Current human roles are viewer, developer, operator, security reviewer, auditor and administrator. External proposal/intelligence systems are not trusted authorities. GitHub is the concrete external provider used by the implemented G8 READ path.

System inputs include authenticated API/console requests, change-request payloads, approval decisions, idempotency keys and explicit runtime configuration. Outputs include execution state, receipts/audit evidence, operation passports, health/trust status and provider READ results.

See `diagrams/as-is-system-context.mmd`.

## C4 C2: containers

The current product is a **modular monolith**, not a microservice system.

1. Browser receives the static Control Room from the product application.
2. One FastAPI/Uvicorn application owns API, authentication, authorization, orchestration, evidence and optional G8 runtime composition.
3. One SQLite database owns durable product state and execution lineage.
4. A governed local sandbox filesystem is available to allowlisted adapters/runtime preparation.
5. GitHub API is contacted only by explicitly activated provider paths.
6. GitHub Actions is CI/live-acceptance infrastructure, not a product runtime container.

See `diagrams/as-is-containers.mmd`.

## C4 C3: important in-process components

| Component | Concrete implementation | Current responsibility |
| --- | --- | --- |
| Composition root | `main.py`, `composition.py` | Construct and bind product services/runtime |
| HTTP surfaces | `api.py`, `canonical_operation_http.py` | Product and canonical-operation APIs |
| Identity/session | `security.py`, identity/session services | Local auth, signed sessions, roles, revocation |
| Authority | `permission_authority.py`, authorization snapshot/grant modules | Bind actor, workspace, environment and approved authority |
| Approval/safety | `approval_policy.py`, `operational_safety.py` | Review constraints, emergency stop, fail-closed gates |
| Canonical pipeline | `canonical_pipeline.py` | Snapshot -> grant -> outbox -> inbox -> lease preparation |
| G8 activation | `g8_product_activation.py`, `g8_read_runtime.py`, `g8_credential_pins.py`, `g8_assembly_guards.py` | Optional non-production GitHub READ runtime; immutable credential and assembly provenance guards are isolated from provider-effect execution |
| Runner | `isolated_runner.py`, GitHub provider handlers | Execute bounded READ under Runner identity |
| Verifier | verifier identity/readback modules | Independently re-observe provider state |
| Evidence | receipt/audit/passport modules | Durable lineage and evidence projections |
| Persistence | `db.py`, `persistence.py`, migration/service modules | SQLite durability and schema enforcement |

## Current runtime lifecycle

The ordinary product change-request lifecycle and the canonical operation path coexist. The canonical READ path performs authority snapshot/grant creation, durable dispatch admission and lease acquisition before the provider effect. The Runner performs the bounded GitHub read, completion evidence is recorded, then a separate Verifier credential/identity performs authoritative readback.

A `VerificationResult/v1` is produced by the READ terminal and schema v15 can store exactly one immutable final result per execution after durable Runner completion. Operation Passport revalidates the stored canonical result against execution/epoch/target/completion lineage after restart; absence remains explicit `NOT_PERSISTED / UNKNOWN`. This schema-v15 persistence is locally verified and has now been exercised by fresh live-provider READ acceptance on exact runtime source `f417d78060304f0d427794641b72692b063efbde`; provider WRITE remains separately gated.

See `diagrams/as-is-g8-read-sequence.mmd`.

## Data architecture

Primary durable entities are users, active sessions, external identity bindings, workspaces, workspace memberships, change requests, approvals, executions, receipts, audit events, authorization snapshots, execution grants, grant consumptions, dispatch outbox/inbox records, execution leases and execution epoch state.

Mutations occur through repository-owned services and explicit transactions. Several later migrations add immutable/binding triggers so authority/evidence records cannot be casually rewritten. There is no second database or shared CyberCore store in the current product.

See `diagrams/as-is-data.mmd`.

## Security and trust boundaries

- Session tokens are signed and bounded by issuer/audience/TTL; server-side active-session state supports revocation.
- API routes enforce named role permissions; administrator has wildcard authority.
- Requester/approval/execution roles are separated by product policy rather than left to UI convention.
- Provider credentials are configuration/secrets, not database product records.
- G8 activation requires distinct Runner and Verifier credentials and distinct observed provider identities.
- Production effects remain disabled and G8 is disabled by default.
- Host/CORS policy is deny-by-default unless explicitly configured.
- Allowlisted adapters avoid arbitrary user-provided shell commands.

## Deployment AS-IS

Development/local operation can run Uvicorn directly or the hardened Docker Compose container. CI builds and smoke-tests a Docker image and runs lint/tests/readiness/supply-chain checks. Separate workflows implement bounded live pilots and release-candidate packaging.

There is no repository-defined persistent staging cluster or production deployment topology. Production deployment, production database, autoscaling, external load balancing and a production observability stack are therefore **not AS-IS components**.
