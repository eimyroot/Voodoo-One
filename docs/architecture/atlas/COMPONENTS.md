# C4 C3 — Components

C3 is useful only inside the single control-plane process. The table below maps actual modules, not conceptual UI labels.

| Component group | Main modules | Responsibility |
| --- | --- | --- |
| Application composition | `main.py`, `composition.py`, `config.py` | Startup, dependency ownership, middleware, routers, optional runtime activation. |
| HTTP/API | `api.py`, `canonical_operation_http.py` | Legacy product routes plus canonical Operation READ/status/passport routes. |
| Identity/session | `identity.py`, `security.py`, bootstrap/session/user services | Local authentication, signed session tokens, active-session checks, roles. |
| Workspace authority | `permission_authority.py`, workspace/membership modules | Current user/role/active/workspace/environment/membership decisions. |
| Change governance | change request + approval policy/services | Review lifecycle, immutable review binding and approval decisions. |
| Operational safety | `operational_safety.py` | Durable emergency-stop state and audited transitions. |
| Legacy execution | `execution.py`, `adapters.py` | Approved bounded local adapters, leases/recovery, receipt production. |
| Canonical authority pipeline | `canonical_pipeline.py`, snapshot/grant services | Snapshot, profile binding, grant issuance/consumption, dispatch and lease preparation. |
| Durable coordination | outbox/inbox/coordinator/lease/fence modules | Exactly-once-ish durable lineage, admission, epoch/lease and stale-attempt fencing. |
| Canonical runtime router | `canonical_operation_runtime.py` | Server-side profile/capability routing; READ execution and mutation preflight only. |
| G8 activation/composition | `g8_product_activation.py`, `g8_read_runtime.py`, `g8_credential_pins.py`, `g8_assembly_guards.py` | Explicit bounded GitHub READ pack assembly; immutable credential and assembly-provenance guard layers are isolated from provider-effect execution. |
| READ terminal | `canonical_read_terminal.py`, GitHub provider modules | Runner observation, durable completion, independent verifier and `VerificationResult/v1`. |
| Evidence/read models | receipt/audit/passport/platform status modules | Hash chains, durable lineage projection, health/control-room truth. |
## High-coupling components

Static import analysis found no internal import cycles, but coupling is uneven. `g8_product_activation` and the historical write-pilot assembly have the highest internal fan-out, while `evidence_primitives`, persistence and execution contracts have high fan-in.

`g8_read_runtime.py` remains a maintainability hotspot, but duplicate role-bound definitions are removed and pure immutable credential plus assembly-provenance guards are extracted into `g8_credential_pins.py` and `g8_assembly_guards.py`. The late `G8ReadRuntimePack.build_runtime` replacement remains intentionally pinned and adversarially characterized as a security property, so later decomposition must preserve that behavior.

## Concept-only labels

Historical Control Room builds rendered `Intent Compiler`, `Capability Router` and `Dynamic DAG` as pseudo-topology labels. Current Control Room no longer presents those labels as AS-IS components: backend `architecture` projection supplies the real legacy-governed and canonical-READ flows, while Operation Passport, Verifier Center and the global Evidence Timeline remain read-only projections over existing validated evidence owners. The historical labels remain concept-only and must not re-enter C3 as implemented components without source/runtime evidence.

Target R3 Core Kernel / Capability Cell names must remain outside C3 until code ownership actually changes.

Primary C3 diagram: [as-is-components.mmd](diagrams/as-is-components.mmd).
