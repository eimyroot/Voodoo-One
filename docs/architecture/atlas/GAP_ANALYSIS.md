# D. Architecture Gap Analysis

Severity is release/operational impact, not aesthetic discomfort.

| ID | Severity | Gap | Evidence / affected area |
| --- | --- | --- | --- |
| G-01 | CLOSED / HIGH | Canonical G8 live READ acceptance is verified by the owner-authorized alternative external Linux run on exact `main@2f9ab7f...`; official GitHub Actions parity remains externally blocked and is tracked separately. | G8 runtime modules, `docs/product/G8_READ_RUNTIME_GATE.md`, retained evidence manifest |
| G-02 | CLOSED / HIGH | Final independent `VerificationResult/v1` now has immutable SQLite persistence and restart-safe Passport binding; schema-v15 persistence itself remains locally verified and post-dates the retained live-provider acceptance. | `verification_result_persistence.py`, migration `0015`, `operation_passport.py`, G8/runtime tests |
| G-03 | HIGH | Production deployment architecture is absent from repo; PostgreSQL and OIDC remain unreleased. | deploy files, `config.py`, `db.py`, identity composition |
| G-04 | HIGH | Production observability has logs/health/evidence but no implemented metrics/tracing/SLO/alerting stack. | `observability.py`, health APIs, deployment surface |
| G-05 | CLOSED / MEDIUM | Startup schema validation previously omitted durable canonical tables, indexes and binding/immutability triggers from migrations `0010-0013`; the current branch now requires them explicitly. | `db.py` required schema/index/trigger sets + negative migration tests |
| G-06 | REDUCED / MEDIUM | G8 runtime assembly remains concentrated in one large module, but duplicate `_G8RoleBound*` definitions are removed, immutable credential pin/pair guards live in `g8_credential_pins.py`, and immutable assembly provenance guards live in `g8_assembly_guards.py`. Provider observer/transport execution, import-time implementation checks and the final public builder pin intentionally remain in `g8_read_runtime.py`. | `g8_read_runtime.py`, `g8_credential_pins.py`, `g8_assembly_guards.py`, `test_g8_read_runtime.py` |
| G-07 | MEDIUM | High orchestration fan-out creates a large change blast radius. | `g8_product_activation` and `f4b_live_write_pilot` each import ~31 internal modules; `composition` ~23 |
| G-08 | CLOSED | Control Room architecture is now projected from backend AS-IS runtime truth instead of hardcoded pseudo-topology labels. | `service.py`, `static/control_room.js`, product-platform tests |
| G-09 | MEDIUM | Architecture/documentation status is human-readable but not machine-bound to code/test evidence. | architecture docs and roadmap |
| G-10 | LOW/MEDIUM | Full test coverage is not quantified; test taxonomy is almost entirely `tests/system`. | test tree / CI configuration |
| G-11 | FUTURE | SQLite-backed in-process outbox/inbox is coherent for current modular monolith but constrains multi-instance scaling. | SQLite + canonical pipeline |

## Positive findings

- No internal Python import cycle was found across 123 top-level product modules.
- Runtime dependencies are small; framework sprawl is not the primary complexity driver.
- Database migrations use contiguous numbering and checksum drift detection.
- Numerous DB triggers enforce immutable authority/evidence bindings.
- Provider effects are fail-closed by default and production effects remain disabled.

## Candidate changes after AS-IS acceptance

| Change | Why | Exact scope | Risk | Verification |
| --- | --- | --- | --- | --- |
| Persist verifier result/proof projection | **CLOSED locally.** Final `VerificationResult/v1` is immutable, one-per-execution, completion-bound and restart-projectable. | verification result store, migration `0015`, runtime persistence, passport projection/tests | residual crash window between durable completion and verifier result persistence | migration suite; restart passport; premature/conflicting result negatives; 162 relevant tests PASS |
| Decompose G8 assembly without semantic change | **IN PROGRESS.** Duplicate class replacement is removed; credential pin/pair and assembly provenance guard layers are extracted behind identical aliases. Behavioral topology, alias identity and builder-pin characterization protect later seams. | `g8_read_runtime.py`, `g8_credential_pins.py`, `g8_assembly_guards.py`, focused G8 tests | Hidden ordering/identity binding regression | exact AST parity for both extracted seams + 49 focused G8 tests + 253 cross-surface tests after the assembly-guard extraction |
| Extend startup schema invariants | **IMPLEMENTED on current branch.** Durable canonical tables/indexes/triggers from `0010-0013` are explicit startup invariants. | `db.py`, `test_database_migrations.py` | False startup failures on valid legacy states | 35 negative object-loss tests + full migration suite + related durable-runtime tests |
| Replace UI pseudo-topology with evidence-backed status model | CLOSED: backend now emits explicit AS-IS flows and runtime status; UI renders that projection. | `service.py`, `static/control_room.js`, `static/styles.css`, product-platform tests | Additive payload/UI regression risk | 42 product-platform/HTTP/operational tests PASS; invented labels absent from JS |
| Add architecture manifest + drift check | Current truth reconciliation is manual. | `docs/architecture/atlas/architecture-manifest.yaml`, verification script, CI | Brittle paths if schema is overfit | CI fixture tests; fail on removed path/route/migration; pass on current tree |
| Define production deployment contract before enabling effects | Packaging alone cannot establish operational safety. | deployment docs/IaC, PostgreSQL/OIDC adapters, secrets/observability | Large scope if attempted as big bang | staged acceptance gates; rollback drill; SLO/alert test; production-effect gate remains false until proven |

No item above should be implemented as a broad refactor before this AS-IS baseline is reviewed and accepted.
