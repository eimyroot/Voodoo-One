# Architecture Decisions

Canonical ADRs remain under `docs/adr/`. This page is an Atlas index and decision-gap map, not a second ADR authority.

## Decisions materially shaping AS-IS

| ADR | Repository status | AS-IS architectural consequence |
| --- | --- | --- |
| ADR-0001 | Accepted | Sandbox path resolution is portable and governed. |
| ADR-0002 | Accepted | Local checkpoint verification is an explicit ProofGraph slice. |
| ADR-0004 | Accepted | Checkpoint finalization is repository-owned. |
| ADR-0006 | Accepted | Policy Decision Graph is read-only projection, not independent authority. |
| ADR-0007 | Accepted | Historical pure grant/receipt contract informs current authority/evidence separation. |
| ADR-0013 | Accepted / partially superseded | Read-only Runner boundary remains an architectural constraint despite historical SandCloud naming. |
| ADR-0014 | Accepted | VOP terminology is intentionally frozen/versioned. |
| ADR-0020 | Accepted for implementation | CyberCore intake is read-only/context-only at the current boundary. |

Several later ADR files retain `PROPOSED` labels while other governance records/documentation describe adopted or implemented descendants. That is a documentation-authority inconsistency and should not be normalized silently.

There is no tracked ADR-0011; the Atlas does not fill the number by guesswork.
## ADR candidates requiring explicit decision

ADR-0021 exact bytes are effectively ADOPTED through the authority register while retaining their embedded proposal label. New ADR numbers still require normal repository numbering governance; the Atlas does not infer or backfill them.

### Candidate A — Keep the modular monolith as deployment unit

- **Context:** one FastAPI process currently owns tightly coupled authority/evidence transactions.
- **Decision:** retain one deployable until measured scaling, isolation or ownership evidence justifies a split.
- **Alternatives:** immediate service decomposition; extract only provider runtimes.
- **Consequences:** simpler transactional truth now; future seams must be designed rather than assumed.

### Candidate B — Persistence support policy

- **Context:** SQLite is implemented; PostgreSQL selector deliberately fails closed.
- **Decision:** declare SQLite the released bounded backend until a PostgreSQL adapter passes concurrency, migration and operations gates.
- **Alternatives:** opportunistic dual-backend support; immediate PostgreSQL migration.
- **Consequences:** honest capability boundary; production HA remains blocked until separately proven.

### Candidate C — Dispatch mechanism

- **Context:** durable outbox/inbox/lease semantics are database-backed; no broker exists.
- **Decision:** treat DB dispatch as canonical AS-IS and introduce an external broker only behind equivalent lineage/fencing guarantees.
- **Alternatives:** broker-first redesign; dual dispatch paths.
- **Consequences:** avoids parallel authority; throughput scaling may later require a governed migration.
### Resolved D — Durable independent verification projection

ADR-0022 plus migration `0015` implement one immutable canonical `VerificationResult/v1` per execution, bound to durable execution lineage and revalidated by Operation Passport. The residual crash window before verifier-result creation remains explicit.

### Candidate E — Living Architecture evidence manifest

- **Context:** architecture truth currently spans code, tests, workflows, ADRs and prose.
- **Decision:** maintain a machine-readable manifest of architecture nodes, status, owners and objective evidence links, while semantic review stays human-governed.
- **Alternatives:** prose-only maintenance; fully inferred architecture generation.
- **Consequences:** CI can catch objective drift without pretending static analysis understands product semantics.

### Candidate F — G8 runtime decomposition strategy

- **Context:** `g8_read_runtime.py` accumulated multiple hardening generations in one large module. Duplicate class redefinitions are now removed; immutable credential pin/pair and assembly-provenance guard layers are extracted; the late public builder pin remains intentional and characterized.
- **Decision:** after live G8 acceptance, refactor behavior-preservingly into explicit assembly/binding layers behind unchanged public contracts.
- **Alternatives:** leave layered module intact; redesign G8 and canonical runtime together.
- **Consequences:** better reviewability and smaller blast radius, but only safe after current behavior is independently evidenced.