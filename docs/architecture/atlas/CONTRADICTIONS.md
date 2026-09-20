# C. Contradictions and Unknowns

These are evidence conflicts, not stylistic disagreements.

| ID | Conflict / ambiguity | Evidence-based reading |
| --- | --- | --- |
| C-01 | `ROADMAP.md` says `main.py` does not install the G8 runtime factory. | Current `main.py` explicitly passes `resolve_g8_read_runtime_factory(config)` into product composition. The runtime still defaults OFF, but the wiring statement is stale. |
| C-02 | Historical Control Room rendered invented orchestration labels. | RESOLVED: backend now emits AS-IS architecture flows/status and the UI renders that projection instead of the hard-coded pseudo-topology. |
| C-03 | R3/ADR-0021 source bytes retain `PROPOSED / REVIEW REQUIRED`. | The authority register makes those exact bytes effectively ADOPTED; runtime realization remains separately gated and is not implied by governance adoption. |
| C-04 | Experimental VOODOO-SOURCES graphs contain Planner/Reasoner/Memory/Caster/Caser/SandCloud nodes. | Their own supporting material marks them conceptual/draft; they are hypotheses, not implementation evidence. |
| C-05 | Official GitHub Actions G8 dispatch is externally blocked. | Separate owner-authorized external Linux execution verified the bounded product READ semantics on exact `main@2f9ab7f...`; this does not prove the blocked Actions transport itself. |
| C-06 | Docker/RC packaging can look like deployment readiness. | There is no GitHub release and no repository-defined persistent staging/production deployment topology. Packaging is not deployment. |
| C-07 | Runtime verification and durable verification were historically different facts. | RESOLVED for the final result projection: schema v15 stores one immutable canonical `VerificationResult/v1`, and Passport revalidates its lineage after restart; absent results still remain `UNKNOWN`. |

## Unknowns requiring explicit evidence

- Exact production hosting target, network topology, persistence service and secret manager are not defined by current repository IaC.
- Current GitHub branch/ruleset enforcement is not sufficiently evidenced by the inspected API surface; do not infer merge protection from workflow files alone.
- Full runtime test-suite result for the audited checkout must be recorded separately from lint/compile success.
- Coverage percentage is unknown; the repository has extensive tests but no current coverage evidence in this audit.
