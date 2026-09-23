# C4 C2 — Containers

VOODOO One is currently a modular monolith, not a deployed microservice system.

## Runtime containers

| Container | Technology | Responsibility | Persistence / external dependency |
| --- | --- | --- | --- |
| Web/control-plane process | Python 3.12, FastAPI, Uvicorn | HTTP API, Control Room, identity, governance, execution orchestration, health/evidence projections | SQLite; optional GitHub READ runtime |
| Static Control Room | HTML/CSS/JavaScript served by FastAPI | Operator UI over `/api/v1` projections/actions | Same-origin API |
| SQLite database | SQLite file | Product state, authority lineage, sessions, audit/receipts, dispatch/lease state | Local persistent volume/file |
| Governed sandbox | Filesystem path | Legacy `write_artifact` output boundary | Local volume/path |

GitHub and GitHub Actions are external systems, not internal product containers.

## Process topology

The Docker/Compose product shape runs one Uvicorn process in one container. No separate queue worker, verifier service, scheduler, broker, cache or database server is defined in current deployment files.

The canonical pipeline's outbox/inbox are durable SQLite records. They model dispatch semantics but do not imply an external queue service.
## Environment-specific container state

| Environment | Current AS-IS |
| --- | --- |
| local/development | Supported by config and Docker Compose; SQLite is released path. |
| test | Used by automated tests with local/in-memory-ish temporary SQLite paths. |
| staging | Supported config; G8 opt-in allowed; one exact-main alternative external Linux acceptance is VERIFIED while default activation remains OFF. |
| production | Config value exists, but G8 activation is rejected and effects default disabled; no deployment topology is evidenced. |

## C2 constraints

- `ProductComposition` owns one shared ProductService database and permission authority.
- Optional canonical runtime must reuse that exact database/authority; parallel authority is rejected.
- Local identity is the only released identity provider.
- PostgreSQL configuration is syntactically accepted by `ProductConfig` but database construction fails closed.
- The G8 pack is absent unless `VOODOO_G8_READ_RUNTIME=enabled` and all bounded settings are supplied.

Primary diagram: [as-is-containers.mmd](diagrams/as-is-containers.mmd).