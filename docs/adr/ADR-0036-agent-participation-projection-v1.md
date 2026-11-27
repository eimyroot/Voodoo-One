# ADR-0036: Agent participation projection v1

Status: PROPOSED — isolated candidate; owner adoption and independent review pending.
Date: 2026-11-27.

## Decision

Expose an additive `agent_participation` field in the existing authenticated GET /api/v1/control-room read model. Its schema is `vone.agent-participation/v1`. Reuse the same bounded recent canonical OperationPassport list already acquired by ProductService; no second query, persistence owner, agent registry or authority. The window is recent authorization snapshots, not a complete inventory of active executions or a verifier history. Rows contain only execution ID, lifecycle stage, capability, Runner class (nullable), operation runtime status, and validated persisted independent verdict/digest/strength/checked_at (otherwise UNKNOWN/null). Instance presence is always UNKNOWN. No identity inference from class, execution state, configuration or receipts. Legacy executions are not canonical participation. Empty recent window is distinct from read failure.

Native Agents view describes Runner/Verifier responsibilities, shows recent records and delegates Passport navigation to the existing Runs view and canonical endpoint. Session/view/refresh guards, strict schema validation and escaped fields are mandatory. Existing read permission unchanged; no credentials, raw contracts, provider effects, execution controls, G8 activation, roster or heartbeat. No new architecture owner.

## Acceptance and rollback

Use canonical Passport fixtures to test validated, missing and contradictory verification evidence, bounded/empty windows, legacy exclusion, authentication and revocation. Test browser projection schema, escape, stale refresh/navigation/logout, empty vs unavailable, canonical Passport drilldown, and no mutations. Review independently before integration. Actual authenticated acceptance and deployment are separate gates. Rollback by reverting the focused change; no database or runtime migration.
