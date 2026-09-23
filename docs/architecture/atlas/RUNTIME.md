# Runtime Architecture

## Default application startup

`voodoo_product.main:app` builds `ProductConfig` from environment and installs one `ProductComposition`. The composition creates `ProductService`, SQLite-backed services, `DatabasePermissionAuthority`, `OperationPassportService`, identity provider, HTTP routers, middleware and static assets.

`main.py` also calls `resolve_g8_read_runtime_factory(config)`. This does **not** mean G8 is active by default: the resolver returns `None` unless `VOODOO_G8_READ_RUNTIME=enabled` and all bounded configuration is valid.

## Processes and workers

AS-IS product deployment defines one Uvicorn process. No separate product worker, scheduler, broker or verifier daemon is defined.

The canonical dispatch chain is persisted in SQLite (`grant consumption -> outbox -> envelope -> inbox -> epoch/lease`). It is a durability/coordination model inside the product, not an external queue topology.

## Runtime modes

| Mode | Behavior |
| --- | --- |
| Default local/dev/staging | Product API/UI + legacy bounded adapters; canonical Operation runtime absent unless explicitly activated. |
| G8 opt-in local/dev/staging | Canonical `github.read-ref/v1` runtime assembled with distinct Runner/Verifier credentials and immutable runtime/capsule bindings. |
| Production | Effects default disabled; G8 activation explicitly rejected. |
| PostgreSQL | Startup rejects backend as unreleased. |
| OIDC | Startup validates configuration then aborts as unreleased. |
## Observed local state during Atlas audit

The canonical checkout had no `.env.product.local`, no `storage/` runtime database and no listener on port `8000`. Therefore the repository was inspected as source/configuration plus test evidence, not as a currently running local product instance.

Docker Desktop being present on the host is not deployment evidence for VOODOO One.

## External runtime calls

G8 uses GitHub provider handlers through bounded Runner and separate Verifier roles. Legacy `run_validation` may spawn only allowlisted local commands (`compileall`, `pytest`, or a `frontend_build` preset if that directory exists). `write_artifact` writes only under the governed sandbox path.

Primary runtime diagram: [as-is-runtime.mmd](diagrams/as-is-runtime.mmd).