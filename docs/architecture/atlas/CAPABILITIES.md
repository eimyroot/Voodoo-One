# Capability Map

Status values in this Atlas are deliberately evidence-scoped: `VERIFIED`, `IMPLEMENTED BUT NOT VERIFIED`, `IN PROGRESS`, `NEXT`, `BLOCKED`, `LATER`.

`VERIFIED` requires current evidence for the stated scope. Historical provider evidence is labelled historical and does not automatically verify today's default runtime.

## Product capabilities

| Capability | Owning implementation | Current status | Evidence / limitation |
| --- | --- | --- | --- |
| Product HTTP + Control Room | `api.py`, `composition.py`, `static/` | VERIFIED | Current source + targeted HTTP/security/product tests. |
| Local bootstrap/login/session | identity/bootstrap/session modules | VERIFIED | Current targeted auth/session tests; OIDC excluded. |
| RBAC + workspace scope | `security.py`, `permission_authority.py`, membership schema | VERIFIED | Current targeted permission/workspace tests. |
| Change request + approval lifecycle | `change_request.py`, approval policy/services | VERIFIED | Current targeted service tests. |
| Emergency stop + recovery guard | `operational_safety.py`, `execution.py` | VERIFIED | Current targeted safety/recovery tests. |
| Legacy bounded adapters | `execution.py`, `adapters.py` | VERIFIED | Current execution/idempotency tests; not canonical provider authority. |
| Receipt + audit integrity | `receipt.py`, `audit.py` | VERIFIED | Current receipt tests plus durable hash-chain implementation. |
| SQLite persistence/migrations | `db.py`, migrations `0001-0015` | VERIFIED | Current migration tests including explicit v14→v15 preservation; single-node scope. |
| Canonical authority/dispatch pipeline | `canonical_pipeline.py` and durable services | VERIFIED | Current composition/migration/G8 activation test selection. |
| Operation Passport projection | `operation_passport.py` | VERIFIED | Same-DB restart-safe lineage projection includes canonical durable `VerificationResult/v1` when present; absence remains `UNKNOWN`. |
| Canonical READ HTTP route | `canonical_operation_http.py` | VERIFIED | Owner-authorized alternative external Linux acceptance proved authenticated canonical HTTP READ on exact `main@2f9ab7f...`. |
| G8 GitHub READ runtime pack | `g8_product_activation.py`, `g8_read_runtime.py`, `g8_credential_pins.py`, `g8_assembly_guards.py` | VERIFIED | Exact-scope alternative external Linux acceptance passed; local refactor keeps provider-effect semantics unchanged while isolating immutable credential and assembly-provenance guards; opt-in only, default OFF. |
| Independent GitHub verifier readback | canonical READ terminal + verifier modules | VERIFIED | Distinct Runner/Verifier identities produced independent provider readback and `VerificationResult/v1 = VERIFIED` on exact accepted source. |
| Durable resume | `canonical_operation_resume.py` | VERIFIED | Alternative external Linux acceptance interrupted ACTIVE execution and resumed the same execution with zero duplicate lineage. |
| Durable final `VerificationResult/v1` | `verification_result_persistence.py`, migration `0015` | VERIFIED | Immutable one-result persistence is bound to execution/epoch/target/Runner completion; missing result remains `NOT_PERSISTED/UNKNOWN`. |
| Provider CREATE_REF/DELETE_REF | A09 preparation + historical pilot runtimes | BLOCKED | Current reusable path stops pre-effect; no canonical WRITE HTTP route. |
| CyberCore read-only intake | intake schema/contract | IMPLEMENTED BUT NOT VERIFIED | Contract-only; no runtime/API/persistence integration. |
| CyberCore active runtime integration | none | BLOCKED | Must enter canonical V-One authority gates. |
| OIDC identity | config/contract validation only | BLOCKED | Startup deliberately aborts when selected. |
| PostgreSQL / HA persistence | selector/fail-closed branch only | BLOCKED | No released adapter/concurrency/ops proof. |
| Production deployment | packaging/workflows only | BLOCKED | No release/deployment evidence. |
| R3 Core Kernel + fractal target governance | R3 thesis + ADR-0021 + adoption register | VERIFIED | Exact candidate `33a82f3` is effectively ADOPTED; embedded proposal labels remain immutable. |
| Core Kernel / Capability Cell runtime realization | separately governed future slices | NEXT | Adoption creates no implicit runtime/package/schema authority. |
| AI Change Copilot / learning loop | target documentation | LATER | No current authoritative runtime implementation. |

## Capability ownership rule

A capability is not considered present merely because a label appears in the Control Room or a target document. It must map to implementation paths and, for `VERIFIED`, to evidence appropriate to the claim.

The existing detailed inventories remain useful supporting material: `docs/product/CURRENT_CAPABILITIES.md` and `docs/product/TARGET_CAPABILITIES.md`. This Atlas supersedes neither; it provides a concise current evidence projection.