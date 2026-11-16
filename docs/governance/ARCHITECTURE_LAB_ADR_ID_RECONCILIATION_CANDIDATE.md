# Architecture Lab ADR identity reconciliation — proposed

Status: PROPOSED / NO ADOPTION / NO NEW AUTHORITY.

Canonical main ADR-0026 is the G8 Owner-Controlled Machine Verifier decision and its section-17 adoption remains unchanged. Historical isolated Architecture Lab ADR-0026 was also owner-adopted with original candidate commit 23d2d8e7666fcac534c182b02196107218b3b295 and SHA-256 6ba4a935af4610280f0520c524ddab32c130de0124917e7a226e7231e3d0fa26. Historical register section 20 stays only in the original local lineage; it must not be replayed on main as another ADR-0026.

ADR-0030 is a NEW candidate identity and must be exact-content owner-adopted separately. Original bytes/hash/adoption remain available in the original worktree. Main adoption register is intentionally unchanged. Lab retains zero implementation, authorization, provider-write, release or deploy effects.

Baseline pinned: 2627b7d17064608059794347a6dd46fd40a7de11. Review the exact diff, recompute SHA-256, validate deterministic Lab gate and contract regressions, then independent verification. No commit, push or merge.

Further collision (2026-10-11): Parallel isolated Architecture Graph worktree holds its own PROPOSED ADR-0029 at docs/adr/ADR-0029-living-architecture-graph-v1.md. It is kept untouched. The Lab proposal therefore takes ADR-0030 as a new content identity. New exact-content adoption is required. The original Lab ADR-0029 digest remains historical proposal evidence only.
