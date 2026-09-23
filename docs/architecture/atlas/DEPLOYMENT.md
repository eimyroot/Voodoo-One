# Deployment Architecture

## Development / local

The repository provides `Dockerfile.product`, `docker-compose.product.yml` and `.env.product.example`. Compose binds `127.0.0.1:8000`, uses a persistent product volume, read-only root filesystem, tmpfs, dropped Linux capabilities, `no-new-privileges`, CPU/memory/PID limits and a single product service.

A local `.env.product.local` is intentionally not tracked. During this Atlas audit no local product instance was running from the canonical checkout.

## Test / CI

`.github/workflows/ci.yml` runs on pull requests and pushes. It installs hash-locked dependencies, lints, compiles, executes focused governance/security/migration gates, runs the full pytest suite, runs the product readiness gate, performs dependency audit, builds the product image and smoke-tests it.

Separate workflows retain narrower/historical live-evidence roles: D4b governed read, E3 verifier observation, E4b verification result, F4b historical write canary, G0 governance verification, and G8 live product READ acceptance.

## Staging

`staging` is a supported configuration environment and is the environment used by the G8 acceptance workflow. G8 activation is allowed only in local/development/staging, with production effects disabled and SQLite persistence.
## Release candidate

`release-candidate.yml` is manual, main-only, confirmation-gated and bound to the `release-candidate` GitHub environment. It verifies exact-main governance, version, lint/compile/tests/readiness/dependency audit, builds and smoke-tests an image, and uploads source archive + CycloneDX SBOM + governance evidence + SHA-256 checksums.

It creates a release-candidate artifact. It does **not** deploy the product and does not publish a GitHub Release.

## Production

No canonical production infrastructure topology, deployment workflow, managed database, ingress/load-balancer, secret store, autoscaling, backup/restore system, SLO/alerting stack or release record was found in the repository. GitHub Releases were empty at audit time.

Therefore `production` exists as a guarded application configuration state, not as a verified deployment architecture.

## Observability

Current observability consists of structured request logging, health status, evidence/audit integrity projections and checkpoint/smoke evidence. A production metrics/tracing/alerting/SLO platform is not implemented/evidenced.

Primary diagram: [as-is-deployment.mmd](diagrams/as-is-deployment.mmd).