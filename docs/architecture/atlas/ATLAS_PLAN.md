# E. Johny Project Architecture Atlas Plan

The Atlas should remain a maintained product surface, not a one-time report.

## Target documentation tree

```text
docs/architecture/atlas/
  README.md
  PROJECT_INVENTORY.md
  AS_IS_ARCHITECTURE.md
  CONTRADICTIONS.md
  GAP_ANALYSIS.md
  SYSTEM_CONTEXT.md
  CAPABILITIES.md
  CONTAINERS.md
  COMPONENTS.md
  REPOSITORY_MAP.md
  RUNTIME.md
  DATA.md
  FLOWS.md
  SECURITY.md
  DEPLOYMENT.md
  RISKS.md
  ROADMAP.md
  EVIDENCE.md
  architecture-manifest.yaml
  diagrams/*.mmd
```

Canonical decisions stay in the existing `docs/adr/` directory. The Atlas links them; it does not fork or renumber them.

## Maintenance contract

Each architectural claim should carry: status, owning code/config path, runtime/deployment boundary, evidence source, relevant ADR/governance authority and last verified commit/date.

Mermaid `.mmd` is the editable source. Rendered images are disposable derivatives. Diagrams use the same semantic states as the Atlas README and must not show a planned component as if it were implemented.

The first CI automation should validate only objective drift: referenced files exist, declared API routes still exist, migration versions match, named workflows exist and manifest status values are valid. It should not attempt to infer architecture from code and then congratulate itself for replacing human judgment with regex.

## Implemented Atlas views

1. Capability, C2/C3, repository, runtime and data maps are now present.
2. Critical flows, security/trust boundaries and deployment views are now present.
3. Target Architecture + incremental Migration Plan are now present.
4. `architecture-manifest.yaml` plus `scripts/verify_architecture_atlas.py` provide objective drift checks for selected paths/routes/migrations/workflows.
5. The remaining work is evidence/adoption and iterative expansion, not creation of the basic Atlas skeleton.

## ADR candidates after R3 target adoption

ADR-0021 exact bytes are effectively ADOPTED through the authority register. Future ADR numbers still require normal repository governance; no numbering is inferred by this Atlas.

- `ADR-CANDIDATE-A`: modular monolith remains the deployment unit until an evidence-backed scaling boundary demands separation.
- `ADR-CANDIDATE-B`: SQLite is the bounded local/test persistence backend; production persistence requires a separately verified adapter.
- `ADR-CANDIDATE-C`: durable DB outbox/inbox is the current dispatch mechanism; no external broker is part of AS-IS.
- `ADR-CANDIDATE-D`: independent verification must have a durable projection sufficient for restart-safe passports/proof.
- `ADR-CANDIDATE-E`: architecture status is machine-indexed, but human review remains authoritative for semantic changes.

## Evidence-scoped roadmap baseline

### VERIFIED

- Canonical local repository identity and governance bootstrap/hash.
- Current repository structure, API route inventory, migrations and dependency map as captured by this audit.
- Ruff and Python compile checks for the observed code tree.
- 68 architecture-critical tests covering migrations, composition, G8 activation/workflow contract, passport and documentation.
- 112 additional current product-boundary tests covering auth/session, permission/workspace, change request, legacy execution/recovery, receipts and HTTP/safety boundaries.
- Architecture manifest checker + negative drift tests.
- Absence of internal Python import cycles in the scanned top-level product module graph.

### IMPLEMENTED BUT NOT VERIFIED

- Repeated/full ADR-0019 G8 evidence beyond the one exact-main alternative external Linux acceptance.
- Exact production-like Docker runtime on the current audited commit outside CI packaging definitions.
- Release-candidate workflow on the current HEAD.

### IN PROGRESS

- Core Kernel / Capability Cell runtime realization planning; the target governance itself is adopted.
- This Living Architecture Atlas baseline.

### NEXT

- Continue review of AS-IS drift before each material refactor.
- Complete capability/repository/runtime/data/security/deployment slices and evidence manifest.
- Build repeated/full ADR-0019 READ evidence; keep official GitHub Actions parity separate from the retained alternative acceptance.
- ✅ Durable verifier-result projection implemented under ADR-0022 + migration `0015`; keep the residual completion→verifier crash window explicit.

### BLOCKED

- Production provider effects, production release and production deployment until release/security/verification gates are satisfied.

### LATER

- PostgreSQL production persistence, OIDC, persistent staging/production IaC, richer telemetry/SLO stack and any SandCloud/CyberCore/fractal-cell runtime integration.
