# Architecture Atlas Evidence Log

Initial audit date: 2026-09-19. Current-primary evidence refresh: 2026-09-20.

## Repository baseline

- Local project: `/Users/eimyna/0_DEV/Voodoo-One`.
- Bootstrap: `/Users/eimyna/0_DEV/AI_PROJECT_BOOTSTRAP.md` loaded before project work.
- Engineering standard SHA-256: `36d2798f377ee5e6ba05ea8a565fc053ad58182d95a3af4f466050d536285bed`.
- Current reconciliation candidate: `integration/main-ancestry-reconcile-20260920`; ancestry merge checkpoint `3be0c5f37a1b830d9a69ac73662863fc13751a53`; verified pre-reconciliation PRIMARY `88625355057e7ec653f9d08bf48991df794fcdda`.
- R3 proposal commit: `33a82f3ecbb930154e415dc4e8325ad9670ae6f9`.
- AS-IS Atlas baseline commit: `ae4d425`.
- Current remote/local `origin/main`: `9933fe65a5f8ff68703ccb434b4ec0ba31fb4592`; reconciliation commit `3be0c5f...` has parents `8862535...` and `9933fe65...`, makes current main an ancestor, and has zero tree delta against its PRIMARY parent. The earlier divergence is therefore reconciled without replacing newer PRIMARY truth. Retained alternative G8 acceptance remains bound to historical exact `main@2f9ab7f...`.
- Atlas expansion/drift-gate checkpoint: `028cc02`; external G8 Actions blocker checkpoint: `63f89f6`.

## Current local verification

- `python -m ruff check .` -> PASS.
- `python -m compileall -q voodoo_product tests scripts` -> PASS.
- Static AST import scan -> 123 top-level product modules, 0 multi-module strongly connected import components.
- Targeted architecture-critical pytest selection -> `68 passed in 13.51s`.
- Targeted files: database migrations, canonical product composition, G8 activation, G8 live-workflow contract, operation passport and project documentation.
- Additional product-boundary pytest selection -> `112 passed in 26.65s` covering auth/session, permission/workspace, change requests, legacy execution/idempotency/recovery, receipts, HTTP security and operational safety.
- Architecture manifest checker -> PASS on the current tree.
- Atlas/documentation checker tests -> `23 passed in 0.83s`.
- Expanded documentation/release/workflow regression selection -> `49 passed in 2.25s`.
- Control Room architecture-truth regression -> `42 passed in 14.71s`; backend `architecture` projection exposes AS-IS legacy + canonical READ flows, and UI no longer contains `Intent Compiler`, `Capability Router`, or `Dynamic DAG`.
- Atlas relative-link scan -> no missing local Atlas links; YAML parse -> PASS; 33 Atlas source files observed.
- Ruff + compile checks for the new checker/readiness integration -> PASS.
- G-05 RED proof: 35 new negative durable schema-object tests all failed before the validator change (`35 failed, 18 deselected`).
- G-05 GREEN proof: the same 35 negative tests pass after the validator change; complete migration suite -> `53 passed`; related grant/dispatch/lease/resume/G8 composition selection -> `133 passed`.
- G-06 characterization/cleanup: behavioral runtime topology and module-level R2-rebind resistance are explicitly tested; duplicate `_G8RoleBound*` definitions were removed. Immutable credential binding/pin/pair definitions moved unchanged into `g8_credential_pins.py`, then assembly anchor/resume-binding/transport-provenance guards moved unchanged into `g8_assembly_guards.py`; both seams have exact AST parity and runtime alias identity preserved. Extraction-source gate: `49 passed` focused G8 runtime/activation and `253 passed` cross-surface G8/READ/provider/persistence/HTTP/Atlas. Current-primary integration gate at `348936c...`: `181 passed` across G8 runtime/activation, migration, Passport/HTTP, Control Room, mandate and documentation surfaces; Ruff, compile, Node, Atlas and `git diff --check` PASS.
- G-02 durable verification: migration suite `58 passed` including explicit v14→v15 upgrade preservation; restart-safe Passport/store/G8/runtime relevant selection `162 passed`; Ruff and compile PASS. Premature durable result insertion is DB-denied, exact replay is idempotent, and conflicting second result is rejected.
- Current-root replay integration: final migration/Passport/G8/runtime/HTTP/Control-Room/Passport-UX/docs/Atlas selection `199 passed`; focused R3 security/persistence selection `106 passed`; Node syntax, Ruff, compile, Atlas checker and `git diff --check` PASS on the reconciled tree.
- CR-4 global Evidence Timeline convergence at exact feature checkpoint `5d396fb...`: focused post-commit gate `87 passed`; broader G8/migration/Passport/HTTP/composition/Control-Room/mandate/docs integration gate `228 passed`; Ruff, compile, Node, Atlas and `git diff --check` PASS. Canonical timeline events are derived only from validated Operation Passports, legacy evidence remains visible through bounded fair mixing, and missing durable `VerificationResult/v1` is not fabricated as a timestamped verification event. Evidence: `/Users/eimyna/0_EVIDENCE/Voodoo-One/CR4_EVIDENCE_TIMELINE_20260920/`; focused log SHA-256 `768d03df2c626b90aafddfbeb7bb4f9d1609b0adc7302f37d3413283c30aa849`; integration log SHA-256 `3edccaabccc0b63cb6ee981ef4454d5f25c99a292b9ea1512e747a2d6ffe13c4`.
- Main ancestry reconciliation at `3be0c5f37a1b830d9a69ac73662863fc13751a53`: two parents `8862535...` + `9933fe65...`, current main is now an ancestor, and the merge has zero tree delta against the verified PRIMARY parent. Pre-commit reconciled-tree gate: `170 passed in 22.67s`; Ruff, compile, Node, Atlas and `git diff --check` PASS. Evidence log SHA-256: `5905bed981f03ac76a6f437da54afc5eebf4d62d87732f14f67553eff871e2aa` under `/Users/eimyna/0_EVIDENCE/Voodoo-One/MAIN_ANCESTRY_RECONCILIATION_20260920/`.
- PR #166 re-evaluation on 2026-09-20: remote PR remains OPEN / DRAFT / NOT MERGED and reports `mergeable=false`. Its first two commits are patch-equivalent on reconciled PRIMARY; ADR-0021 and the R3 thesis retain identical SHA-256 bytes (`7e49c7b...`, `5107b55...`). Its third G8 documentation commit is not patch-equivalent because the current line retains the historical exact-main alternative acceptance while adding newer schema-v15 durable-verification/live-READ evidence. PR #166 is therefore `SUPERSEDED` for new development/review composition and must not be merged as-is; no remote PR mutation was performed.

## Explicitly not verified by this audit

- Full `pytest -q` suite did not complete: it reached 25% with no observed failure and was terminated to avoid leaving a background process. Full-suite status is `NOT VERIFIED`, not `FAILED`.
- Product readiness gate is not claimed PASS. A G-05 re-run entered the full `tests/system` suite and was deliberately terminated while still progressing through checkpoint/ProofGraph tests; no failure was observed before termination, but the gate did not complete.
- Owner-authorized alternative external Linux G8 acceptance was later observed as `VERIFIED_ALT_EXTERNAL_LINUX` for exact `main@2f9ab7fdfe8793a9b2c977bc620c0f10921f4e3f`; the retained `SHA256SUMS.txt` manifest hash is `b4ced161adc99c98243b523c3bf15a1055e92a5096e0839755d2a2f86f889d92`.
- G8 dispatch attempt at `2026-09-19T12:25:25+02:00` was rejected by GitHub before run creation with HTTP 422: `Actions has been disabled for this user.`
- Repository Actions permissions were observed as `enabled=true`, `allowed_actions=all`; G8 workflow state was `active`; post-attempt G8 run list remained empty.
- This is an external account/platform Actions blocker for the official workflow path, not a product READ acceptance failure; alternative external Linux acceptance succeeded separately.

## Live repository evidence

- Historical accepted GitHub `main` was observed at merge commit `2f9ab7f...` from PR #165; current remote `main` was freshly observed at `9933fe65a5f8ff68703ccb434b4ec0ba31fb4592` on 2026-09-20.
- No official GitHub Actions workflow run was returned for exact SHA `2f9ab7f...` in the queried Actions endpoint; the alternative external Linux acceptance is retained outside GitHub Actions.
- The queried manual workflow-dispatch history contained governance runs but no G8 live product READ acceptance run.
- GitHub release collection was empty.

These facts prove absence of official GitHub Actions evidence in the inspected GitHub surfaces. Separate retained external-Linux evidence proves the bounded G8 READ acceptance stated above; it does not constitute release or deployment evidence.

## Local runtime observation

At audit time:

- `.env.product.local` was absent;
- repository-local `storage/` was absent;
- no listener was bound to TCP 8000;
- therefore this checkout was not an active VOODOO One product runtime.

## Atlas validation

- All baseline and expanded Atlas files referenced by the Atlas index exist.
- `architecture-manifest.yaml` validates declared statuses, source paths, selected API routes, exact SQLite migration inventory and named workflows.
- `git diff --check` passes with the Atlas working tree changes.
- Mermaid files are retained as editable source; rendered images were not introduced.
