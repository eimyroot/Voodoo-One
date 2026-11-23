# Living Core × CASEBOOK Tasks — reconciled desktop UI candidate

Date: 2026-11-23
State: **source implementation + targeted regression VERIFIED; review-only candidate, not deployed**.

## Source of truth / lineage

- Base: actual GitHub `eimyroot/Voodoo-One` **main@3ca9261a035074dba8e3878ad258262ed618312f**, merge of PR #211.
- Original Living Core visual implementation: local dirty, uncommitted `feat/living-core-desktop-20261123` based on `main@71bcc781da5e90834ee73db5f25c59de7254d2d0`. The source was READ and copied into this isolated review candidate. That original worktree was not edited.
- New bounded candidate: `review/living-core-post-pr211-20261123` under the evidence root. No direct changes to the dirty canonical checkout.
- PR #211 already merged native CASEBOOK Task pane and G8 expiry UX; this increment changes **only the existing Control Room UI**, with an additional native HTTP regression test. It does not create an alternative backend or a second standalone desktop app.

## Product behavior

The existing authenticated `/console` view becomes **Living Core**, with one layered motion/flow composition (CSS/SVG), live overview projection, truthful phase status, risk and evidence views, compact responsive navigation and reduced-motion fallback.

- `living_core.js` wraps the *existing* Control Room data projection. It never acquires additional authority; missing JIT/agent/skills/throughput/latency/success-rate data must remain `UNKNOWN` / `Nedostupné`.
- Login, logout, authorizations and the G8 canonical HTTP expiry controls remain in the original `control_room.js` and backend.
- All existing screens are retained; **CASEBOOK Tasks** remains a first-class sidebar entry and the full read-only native task detail section from merged PR #211 remains in the same HTML document.
- `living_core.css` contains mobile/wrapping navigation, reduced-motion and no-backdrop-filter fallbacks.
- All content originating from untrusted projection data is HTML-escaped before inserting into visual cards. A failed Control Room request clears stale status indicators rather than retaining previous success claims.
- CASEBOOK does **not** automatically attach, create an execution grant or claim independent verification. Without an explicitly approved single session/workspace/data source it remains fail-closed.

## Tested

- `node tests/system/test_living_core_ui.cjs` PASS: real projection mapping, missing JIT, safe HTML escaping, failure clearing and no fake metrics.
- `node tests/system/casebook_task_contract.cjs` PASS 7/7: CASEBOOK task view contract.
- `node tests/system/test_operator_canonical_read.cjs` PASS: G8 approval expiry and canonical READ denial.
- `node tests/system/test_workflow_boards_render.cjs` PASS, `node tests/system/test_project_control_map_mobile.cjs` PASS.
- New `tests/system/test_living_core_casebook_native_http.py`: **1 PASS**, native FastAPI composition serves the joined HTML, JS and CSS; unique HTML IDs; expected retained controls; no default CASEBOOK attachment.
- CASEBOOK native startup/config: **6 PASS**; CASEBOOK portable HTTP/auth: **4 PASS**.
- Control Room overview/Passport and plan regression: **11 PASS**.
- G8 canonical-operation and approval expiry HTTP: **15 PASS**.
- Ruff and JavaScript syntax PASS; `git diff --check` PASS.

These are source/HTTP and Node-level results. **Actual logged-in browser visual QA, standalone desktop packaging, accessibility audit across devices, independent reviewer, GitHub CI for this head, merge, production deploy and installed desktop runtime validation are not yet verified.**

## Release gates and rollback

1. Independent review of actual exact-head diff against merged main, with particular attention to the CASEBOOK sidebar, G8 expiry controls and Living Core's interception of Control Room loading.
2. Browser acceptance in a bounded nonproduction session at desktop/tablet/mobile widths; reduced-motion behavior, keyboard navigation, actual auth/logout and negative data states. The previous visual screenshots of the original, pre-merge candidate are not a substitute.
3. Review/CI/merge requires its own governance; PR #211's authorization does not carry over to this new candidate.
4. Separate release/deploy decision to update the currently running **port 10000** application, whose process CWD was independently observed at `.../MOBILE_UX_LOCAL_COMMIT_20261120` (older `6fb0b405...`). The running process is not modified by this code commit.
5. Rollback would restore the previous exact service code/image from an approved, verified checkpoint; never overwrite the dirty canonical checkout or mutate G8 10002 or demo 10003 as a shortcut.

## Architecture/provenance boundary

Project repository code, security rules, permission DB, runtime tests, `AGENTS.md` and authoritative constitutions take priority over supporting architecture notes. The supporting VOODOO OS evolution workflow and derived diagrams were consulted for flow vocabulary (Intent → Approval → Execution → Verification → Evidence), **not** as proof of actual runtime status, and never to authorize an operation. The project's current Control Room projection remains the sole source for displayed state.
