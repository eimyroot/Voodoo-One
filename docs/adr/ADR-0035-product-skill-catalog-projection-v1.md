# ADR-0035: Product skill catalog projection v1

Status: PROPOSED — isolated candidate; owner adoption and independent review pending.
Date: 2026-11-26.

## Context and decision

The native Skills navigation is unavailable despite the existing product-owned planning catalog in `skill_orchestration.py`. Expose an additive `skill_catalog` field in the existing authenticated GET /api/v1/control-room read model, schema `vone.skill-catalog/v1`. Reuse the catalog and `select_relevant_skills`; do not create a second catalog or authorization authority.

The field contains source, schema, runtime_availability (UNKNOWN), primary_coordinator, supported task_types, sorted skills (id, role, purpose, authority, task_types), and per-task selections derived by the existing function. The native view filters this snapshot and previews selection. Labels and purposes are escaped; malformed or unavailable projections fail closed and clear old content. Session, navigation and refresh generations reject stale responses. Existing read authorization is unchanged. The catalog is source-defined planning metadata, not installed, enabled, live, verified, or authorized execution.

## Boundaries and verification

No filesystem skill discovery, prompt loading, external connector, credential, database schema, permission, agent roster or execution changes. No runtime or production activation. Existing clients may ignore the additive field; exact-contract tests must account for it. Verify deterministic projection and parity with canonical plan selections, mutation isolation, authenticated read and revocation, stale/outage/malformed UI, filtering and escaping, existing JS/Python regressions. Independent review and browser acceptance remain separate.

Rollback: revert the focused source changes and the proposed decision; no database or runtime migration. Deployment requires separate authorization and evidence.
