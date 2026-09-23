# Johny Project Architecture Atlas

Status: **AS-IS baseline + living checks locally verified; target governance adopted; incremental runtime work in progress**
Observed repository: `/Users/eimyna/0_DEV/Voodoo-One`
Observed integration branch: `integration/main-ancestry-reconcile-20260920`
AS-IS baseline commit: `ae4d425` (query live Git for the current Atlas HEAD)
Current reconciliation candidate `3be0c5f...` joins the verified PRIMARY `8862535...` with remote `main@9933fe65...` as a two-parent ancestry merge with zero tree delta against the PRIMARY parent. The newer PRIMARY product/runtime/documentation truth is therefore preserved byte-for-byte while current `main` ancestry is incorporated. The retained historical G8 acceptance remains bound to exact `main@2f9ab7f...`, with separate fresh schema-v15 live READ evidence bound to runtime source `f417d78...`.

This Atlas is evidence-first. Repository code, configuration, migrations, tests and executable workflows outrank diagrams and architectural prose when they disagree.

## Status legend

| Mark | Meaning |
| --- | --- |
| `VERIFIED` | There is current evidence that the claim works or is true. |
| `IMPLEMENTED BUT NOT VERIFIED` | Code/config exists, but required runtime or acceptance evidence is missing. |
| `IN PROGRESS` | Work exists but is not yet adopted/closed. |
| `NEXT` | Evidence-backed next increment after current gate. |
| `BLOCKED` | Deliberately unavailable until an explicit gate is satisfied. |
| `LATER` | Deferred target with no current delivery commitment. |

## Source precedence

1. executable runtime code and configuration;
2. migrations and persisted schema contracts;
3. current tests and generated/runtime evidence;
4. adopted governance and ADRs;
5. descriptive architecture documentation;
6. proposed ADRs, target theses and source images/graphs.

## Atlas baseline set

- [Project Inventory](PROJECT_INVENTORY.md)
- [AS-IS Architecture](AS_IS_ARCHITECTURE.md)
- [Contradictions and Unknowns](CONTRADICTIONS.md)
- [Architecture Gap Analysis](GAP_ANALYSIS.md)
- [Evidence Log](EVIDENCE.md)
- [System Context](SYSTEM_CONTEXT.md)
- [Capability Map](CAPABILITIES.md)
- [Containers](CONTAINERS.md) and [Components](COMPONENTS.md)
- [Repository Map](REPOSITORY_MAP.md)
- [Runtime](RUNTIME.md) and [Data](DATA.md)
- [Critical Flows](FLOWS.md)
- [Security](SECURITY.md) and [Deployment](DEPLOYMENT.md)
- [Architecture Decisions](ARCHITECTURE_DECISIONS.md)
- [Risks](RISKS.md) and [Architecture Roadmap](ROADMAP.md)
- [Target Architecture](TARGET_ARCHITECTURE.md) and [Migration Plan](MIGRATION_PLAN.md)
- [Machine-readable architecture manifest](architecture-manifest.yaml)
- [System Context diagram](diagrams/as-is-system-context.mmd)
- [Containers diagram](diagrams/as-is-containers.mmd)
- [Components diagram](diagrams/as-is-components.mmd)
- [G8 READ sequence](diagrams/as-is-g8-read-sequence.mmd)
- [Data architecture](diagrams/as-is-data.mmd)
- [Runtime diagram](diagrams/as-is-runtime.mmd)
- [Security boundaries](diagrams/as-is-security-boundaries.mmd)
- [Deployment diagram](diagrams/as-is-deployment.mmd)
- [Legacy execution sequence](diagrams/as-is-legacy-execution-sequence.mmd)
- [Recovery sequence](diagrams/as-is-recovery-sequence.mmd)

## Resulting long-lived Atlas structure

The long-lived Atlas slices are now present here without moving the existing canonical `docs/adr/` tree. Future changes extend these views rather than creating competing architecture roots.

Primary diagrams stay under `diagrams/*.mmd`. Rendered SVG/PNG files, if ever generated, are derived artifacts and must not become the editable source.

`architecture-manifest.yaml` now binds important architecture nodes to lifecycle status and objective source/evidence references. `scripts/verify_architecture_atlas.py` fails when selected source paths, API routes, migration inventory, workflow paths or status values drift.

## Phase gate

This baseline intentionally stops before implementation refactoring. The order is:

`AS-IS -> PROBLEMS -> TARGET ARCHITECTURE -> MIGRATION PLAN`

The R3 Core Kernel + fractal Capability Cell material at `VONE_PRODUCT_ARCHITECTURE_THESIS_R3.md` and ADR-0021 is therefore treated as **target/proposed architecture**, not silently folded into AS-IS.

See [ATLAS_PLAN.md](ATLAS_PLAN.md) for the target long-lived view set, maintenance contract, ADR candidates and evidence-scoped roadmap.