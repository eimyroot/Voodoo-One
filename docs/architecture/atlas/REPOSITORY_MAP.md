# Repository / Code Map

| Path | Responsibility | Main entrypoints / dependencies | Capabilities |
| --- | --- | --- | --- |
| `voodoo_product/` | Product runtime and domain implementation | `main.py`, `__main__.py`, `cli.py`; FastAPI/Pydantic/Uvicorn + stdlib/SQLite | API, identity, governance, execution, evidence, G8 |
| `voodoo_product/migrations/sqlite/` | Durable schema evolution | migrations `0001` through `0014`; loaded by `db.py` | persistence, authority lineage, sessions |
| `voodoo_product/static/` | Static Control Room | `index.html`, `app.js`, `control_room.js`, `styles.css` | operator UI |
| `tests/system/` | Product/system contract evidence | pytest | all major current capabilities |
| `scripts/` | Readiness, release and evidence utilities | `voodoo`, readiness/release/G8 scripts | CI, acceptance, operator tooling |
| `.github/workflows/` | CI/governance/live-evidence/release-candidate workflows | GitHub Actions | CI, G0, historical live gates, G8 acceptance, RC build |
| `docs/` | Product, architecture, governance, ADR and evidence documentation | `docs/README.md`, `docs/adr/`, this Atlas | architecture/governance truth projection |
| `schemas/` | Machine-readable contracts | CyberCore intake + VOP registry | semantic/intake contracts |
| `foundation/` | Stable principles and terminology | `FOUNDATIONS.md`, `TERMINOLOGY.md` | governance vocabulary |
| `CASER/` | Mirror/source references and idea material | mirror policy/state | supporting provenance, not runtime |

Tracked-file concentration at the observed baseline: `voodoo_product` 141, `tests` 123, `docs` 121. The product is therefore one codebase with a large contract/test/documentation surface, not multiple deployable repositories.