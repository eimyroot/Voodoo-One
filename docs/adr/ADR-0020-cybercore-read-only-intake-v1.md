# ADR-0020: CyberCore read-only intake contract v1

| Field | Value |
|---|---|
| Status | ACCEPTED FOR IMPLEMENTATION |
| Date | 2026-09-11 |
| Decision owner | Repository owner |
| Scope | Read-only, metadata-only CyberCore → V-One intake boundary |
| Risk class | R2 integration contract |
| Runtime effect | None |
| Production effect | None |

## Context

The product constitution assigns observations, Knowledge Blocks and Work Blocks to CyberCore while
V-One remains authoritative for identity, policy, approvals, authorization, execution lifecycle and
evidence of permitted effects. The owner supplied a CyberCore source archive whose CXP/1 specification
uses immutable SHA-256-addressed Work Block artifacts and explicitly separates artifact integrity from
local trust and authorization.

Directly importing CyberCore runtime code, sharing persistence, or treating a CXP artifact as an
execution grant would violate the V-One trust boundary. The smallest safe integration is therefore a
pure intake contract that represents only the metadata needed for later V-One review.

## Decision

Introduce `v-one-cybercore-intake/v1` in `voodoo_product/cybercore_intake.py` with a machine-readable
projection in `schemas/cybercore-intake-v1.schema.json`.

The record binds:

- CXP/1 Work Block artifact identity and version;
- canonical artifact and payload SHA-256 digests;
- CyberCore source reference;
- Knowledge Block reference and digest;
- target reference;
- CyberCore risk plus a deterministic non-downgradable V-One risk class;
- explicit signature-observation status;
- bounded expected effect category;
- an explicit verification plan.

The contract is deterministic and digest-bearing. It performs no I/O and has no API, persistence,
network, subprocess, execution, approval or production-effect capability.

## Authority boundary

Every serialized intake record MUST contain all of the following as `false`:

```text
may_approve
may_authorize
may_execute
production_effect
```

CyberCore metadata is context and proposal evidence only. A valid digest or a
`VERIFIED_VALID` signature-status observation is not V-One authorization and does not establish
publisher trust by itself.

## Risk mapping

V-One refuses risk downgrades at the intake boundary:

```text
CyberCore low      → V-One R1
CyberCore medium   → V-One R2
CyberCore high     → V-One R3
CyberCore critical → V-One R4
```

A caller cannot supply a lower V-One class than this mapping.

## Non-goals

This slice does not:

- parse or extract a `.cxp` archive;
- verify Ed25519 signatures or publisher trust;
- persist Knowledge Blocks or Work Blocks in V-One;
- execute CXP payload content;
- create a public HTTP API;
- create an approval, AuthorizationSnapshot or ExecutionGrant;
- enable provider WRITE, release, deployment or production effects.

## Verification

The contract has system tests for deterministic round-trip identity, risk mapping, digest binding,
unknown-field rejection, identifier and digest validation, authority hard-fail, bounded effects,
verification-plan requirements and dependency isolation.

Broader repository gates remain required before review publication.

## Rollback

Revert the single feature commit. No database migration, persisted state, runtime wiring or external
resource requires cleanup.
