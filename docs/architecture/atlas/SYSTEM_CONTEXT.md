# System Context

Status: **AS-IS / evidence-scoped**

VOODOO One is a control plane for governed human/AI operations. It turns a reviewed change intent into bounded execution and evidence while keeping authorization, execution and verification separate.

## Primary users and actors

| Actor | AS-IS relationship |
| --- | --- |
| Developer / requester | Creates and submits change requests. |
| Operator | Reviews approvals and may run approved operations when permitted. |
| Security reviewer | Reviews evidence, controls emergency stop and execution recovery. |
| Auditor / viewer | Reads system/evidence projections without execution authority. |
| Administrator | Manages users/workspaces and has wildcard product permission. |
| AI / CyberCore source | May provide proposals/context only; it is not authority. |

## System boundary

Inside the current product boundary are the FastAPI application, static Control Room, local identity/session services, permission/approval logic, canonical operation pipeline, legacy bounded adapters, SQLite persistence, evidence ledgers and optional G8 READ runtime composition.

Outside the boundary are browsers/clients, GitHub APIs, GitHub Actions, identity systems not yet released, deployment infrastructure, and future CyberCore runtime integration.
## External systems

| External system | Current use | Status |
| --- | --- | --- |
| GitHub REST API | Provider target for governed `github.read-ref/v1`; historical bounded write pilots exist. | READ pack IMPLEMENTED BUT NOT LIVE VERIFIED |
| GitHub Actions | CI, governance verification, historical live read/write evidence and G8 acceptance workflow. | IMPLEMENTED; exact gates have different evidence scopes |
| External OIDC provider | Configuration contract only; selecting OIDC aborts startup. | BLOCKED |
| PostgreSQL | Backend selector exists but startup rejects it. | BLOCKED |
| CyberCore | Read-only intake contract/context source only. | IMPLEMENTED CONTRACT-ONLY |

## Main inputs

Authenticated HTTP/API requests, reviewed change requests, approval decisions, environment/runtime configuration, explicit G8 activation data, provider observations and recovery/emergency-control actions.

## Main outputs

Durable change/execution state, audit events, receipt/evidence chains, Operation Passport projections, runtime health/control-room projections, provider READ observations and independent `VerificationResult/v1` values when the canonical READ terminal actually runs.

## Non-goals in the current implementation

VOODOO One is not currently a multi-service orchestration mesh, general message broker, released enterprise identity platform, released PostgreSQL/HA service, generic AI planner, or unrestricted provider mutation engine.

Primary diagram: [as-is-system-context.mmd](diagrams/as-is-system-context.mmd).