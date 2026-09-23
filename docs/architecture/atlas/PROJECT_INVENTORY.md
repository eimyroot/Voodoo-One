# A. Project Inventory

Audit date: 2026-09-19. This inventory describes the observed repository and explicitly separates implementation from runtime verification.

## Repository and governance

| Item | Observed state | Classification |
| --- | --- | --- |
| Canonical local project | `/Users/eimyna/0_DEV/Voodoo-One` | VERIFIED |
| Bootstrap | `/Users/eimyna/0_DEV/AI_PROJECT_BOOTSTRAP.md` loaded and applied | VERIFIED |
| Engineering standard hash | `36d2798f377ee5e6ba05ea8a565fc053ad58182d95a3af4f466050d536285bed` | VERIFIED |
| Current integration branch | `integration/local-verified-work-on-current-root-20260919` | VERIFIED locally |
| Current integration lineage | current root `9b61450` plus replayed verified local architecture/runtime commits | VERIFIED locally |
| Current local `origin/main` | `10a8ed6`; proprietary-license commit over `2f9ab7f...` | VERIFIED locally |
| Current release | no GitHub release; repo docs say pre-production `0.9.0-rc2-dev` | NOT RELEASED |

## Code and repository shape

| Area | Evidence | Responsibility |
| --- | --- | --- |
| `voodoo_product/` | 141 tracked entries; 123 top-level Python modules; ~45.9k Python LOC | Product runtime and control plane |
| `tests/system/` | 123 tracked test files | System/contract verification |
| `docs/` | 108+ tracked entries before this Atlas | Product, architecture, governance, security and evidence docs |
| `scripts/` | 7 tracked entries | Readiness/checkpoint/repository tooling |
| `.github/workflows/` | 8 tracked workflows | CI, governance, live pilots, RC packaging |
| `schemas/` | CyberCore intake and VOP registry JSON schemas | Contract schemas |
| `foundation/` | terminology/foundation docs | Semantic foundation |
| `CASER/` | mirror/source/ideas documentation | Non-runtime source/mirror material |

## Runtime and entrypoints

- `voodoo_product/main.py` is the application entrypoint and installs one FastAPI application through `install_composed_product_platform(...)`.
- `voodoo_product/composition.py` is the principal composition root. It wires auth, sessions, workspaces, requests, approval, safety, execution, evidence, permission authority, passports and optional canonical runtime.
- `voodoo_product/api.py` exposes 28 routes, including health/auth/users/workspaces/change requests/approvals/executions/evidence/audit/emergency stop plus console/root.
- `voodoo_product/canonical_operation_http.py` exposes 3 canonical-operation routes: status, passport and READ execution.
- Static UI is served from the same application via `voodoo_product/static/`.
- Current runtime dependency surface is deliberately small: FastAPI, Pydantic and Uvicorn.

## Persistence

Current persistence is SQLite. `voodoo_product/db.py` enables foreign keys, WAL, FULL synchronous mode, busy timeout, serialized write transactions and checksummed contiguous migrations.

Migrations `0001` through `0015` create the core identity/workspace/change/approval/execution/evidence tables plus auth rate limits, active sessions, external identity bindings, immutable review bindings, authorization snapshots, durable execution grants, grant consumptions, dispatch outbox/inbox, execution epoch leases, workspace memberships and immutable durable `VerificationResult/v1` rows.

`postgresql` exists as a configuration enum/target but is rejected as unreleased by the current runtime. There is no implemented production PostgreSQL adapter in the observed product.

## Processes, queues and external systems

There is no standalone product worker, broker or queue service in the repository. Durable dispatch uses SQLite outbox/inbox tables and in-process orchestration. The isolated Runner and independent Verifier are architectural/runtime identities and contracts, not separately deployed daemons in the current product.

The principal implemented external provider path is GitHub. G8 READ can call `api.github.com` with distinct Runner and Verifier credentials when explicitly enabled. OIDC, CyberCore runtime integration and SandCloud production execution are not current product runtime integrations.

## Deployment and local runtime observation

- `Dockerfile.product` and `docker-compose.product.yml` define a hardened single-container local/product runtime.
- No Terraform, OpenTofu, Kubernetes, Helm, Pulumi, Ansible or CloudFormation deployment definition is tracked.
- The compose surface binds to `127.0.0.1:8000`, uses a non-root/read-only container, drops capabilities, limits CPU/memory/PIDs and persists SQLite in a named volume.
- At audit time this checkout had no `.env.product.local`, no `storage/` database and no listener on TCP 8000. Therefore the observed local checkout was **not running as the product runtime**.
- GitHub currently has no release for the repository.

## Verification snapshot

| Capability/fact | Status | Evidence boundary |
| --- | --- | --- |
| Governance/bootstrap identity | VERIFIED | local files + exact SHA-256 |
| Ruff static checks | VERIFIED | current audit run passed |
| Python compileall | VERIFIED | current audit run passed |
| Import graph has no internal cycles | VERIFIED | AST scan of 123 modules |
| SQLite migration integrity controls | VERIFIED | current targeted migration/composition test selection passed; full suite separately NOT VERIFIED |
| Auth/RBAC/session revocation | IMPLEMENTED | code + tests exist |
| Approval / requester separation | IMPLEMENTED | code + policy contracts/tests exist |
| Canonical READ composition | VERIFIED | current wiring plus targeted composition/G8 activation tests passed |
| G8 live GitHub READ E2E | VERIFIED_ALT_EXTERNAL_LINUX | owner-authorized exact-main external Linux acceptance passed; official GitHub Actions dispatch remains externally blocked |
| Production provider effects | BLOCKED | configuration and governance fail closed |
| PostgreSQL production persistence | PLANNED | enum/target only; runtime rejects it |
| OIDC identity provider | PLANNED | contract/config surface only; unreleased |
| Production deployment | NOT VERIFIED | packaging exists; no release/deploy evidence found |
