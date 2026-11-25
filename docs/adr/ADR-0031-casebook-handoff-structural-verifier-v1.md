# ADR-0031 — CASEBOOK handoff structural verifier v1

- Status: PROPOSED — exact-content owner adoption and independent review required
- Date: 2026-11-25
- Scope: non-production, read-only correlation of V-One execution evidence with CASEBOOK
- Decision class: T2 trust boundary / persistence evidence
- Runtime effect: NONE
- Release / deploy effect: NONE
- Production effect: NONE

## Context

The Living Core can read an intact CASEBOOK session, but the current P0 session
still reports `CASER HANDOFF = NOT_ESTABLISHED`, `RUNNER = NOT_ATTESTED`, and
`RESULT = NOT_RECORDED`. Journal integrity proves that recorded bytes are
append-only; it does not prove that a V-One operation was authorized, consumed,
or independently verified.

An uncommitted CASEBOOK candidate separately validates an incoming CASER goal as
`VALIDATED_NOT_PERSISTED`. That contract is upstream intake and remains outside
this decision. This ADR defines the downstream read-only correlation boundary
after an authorized writer has recorded a handoff event.

## Decision

Add one pure verifier that opens the V-One and CASEBOOK SQLite databases in
read-only transactions and accepts a correlation only when all of these hold:

1. both SQLite databases pass `integrity_check`;
2. required tables and fail-closed/append-only triggers are present;
3. `ExecutionGrant/v2` parses through the canonical V-One value object and its
   stored row matches the parsed contract;
4. exactly one `GrantConsumptionWitness/v1` exists and matches the grant;
5. the grant is non-production and belongs to the requested workspace;
6. the complete CASEBOOK global hash chain and stored head are intact;
7. exactly one `CONTEXT/system/OPEN` event in the requested session contains the
   exact execution, request, workspace, environment, grant, consumption,
   payload, and target bindings.

The only positive verdict is:

```text
LOCAL_CROSS_DATABASE_STRUCTURAL_MATCH
independent_identity_attested = false
production_connected = false
```

## Trust boundary

The verifier proves local structural consistency between two append-only data
sets. It does not prove CASER identity, user approval, Runner identity,
independent post-state verification, external provider effect, or production
state. An unkeyed digest is integrity evidence, not signer authenticity.

The verifier imports the canonical V-One grant and consumption parsers. It does
not call the issuer, consumer, CASEBOOK writer, runtime, network, or provider.

## Threats and controls

| Threat | Control |
|---|---|
| Rehashed CASEBOOK event points to a different payload | exact metadata binding to canonical grant fields |
| Grant exists but was never consumed | exactly one parsed consumption witness required |
| Row JSON and indexed columns diverge | explicit row-to-contract comparison |
| Journal rows are modified or removed | trigger contract plus complete hash-chain/head verification |
| V-One authority rows are mutable | required binding and immutability trigger contracts |
| Structural match is presented as independent verification | fixed conservative verdict and negative attestation flags |
| Accidental production use | production grant rejected and production flag always false |

## Verification

The contract suite must cover a valid match and reject missing consumption,
different but internally intact payload binding, missing CASEBOOK append-only
trigger, production scope, and missing V-One immutability trigger. Repository
readiness must include the verifier and its tests.

## Rollback

Before adoption, delete/revert the verifier, its test, this ADR, its decision
card, documentation index entry, and readiness inventory entries. No database
or external state exists to undo because the slice has no writer or runtime
composition.

## Adoption boundary

Passing tests do not adopt this ADR and do not authorize a writer, runtime
attachment, commit, push, merge, release, deployment, real journal mutation, or
production effect. Those remain separate gates.

## Isolated integration follow-through

The operator-workspace candidate strengthens every shared grant/consumption binding and adds a pure correlation against the existing native OperationPassport. It compares exact execution, request, workspace, environment, grant and consumption digests and requires validated Passport lineage. LOCAL_STRUCTURAL_PASSPORT_MATCH is not independent attestation or resume permission. This source-only integration does not attach a reader, expose a route, select a session or activate execution. The original candidate remains untouched. Native authorization, durable resume preconditions, owner adoption and independent review remain separate prerequisites.

A proposed follow-through candidate adds an explicitly opt-in, disabled-by-default read-only Passport route through CasebookTaskGateway. It requires a source-pinned reader, exact bound session/project/workspace/environment, fresh native evidence.read and read decisions, canonical Passport service owned by the same database, and exact matching event hash. The route returns the already scoped Passport without a second unrestricted lookup; no POST or execution route is added. The native installer propagates the typed explicit local binding flag (default false; environment opt-in VOODOO_CASEBOOK_READ_PASSPORT_CORRELATION=1). This does not change any running instance. This candidate is not adopted or activated, and is subject to the same R3 independent review and rollback gate.
