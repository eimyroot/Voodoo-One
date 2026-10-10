# Contribution and patch policy

## Required flow

1. Create a focused branch from `main`.
2. Keep production effects disabled.
3. Add or update tests for every behavior change.
4. Open a pull request using the repository template.
5. Require green CI and owner review before merge.

## Risk classes

| Class | Examples | Merge requirement |
| --- | --- | --- |
| R0 | Documentation, comments | Green CI + owner oversight |
| R1 | Tests, internal refactor without behavior change | Green CI + owner oversight |
| R2 | API behavior, adapters, dependency updates | Green CI + explicit owner approval |
| R3 | Authentication, authorization, persistence, audit, CI/release | Green CI + explicit owner approval + rollback evidence |
| R4 | Production effects, destructive migration, public API break | Separate design review and explicit release authorization |

Automation may classify and verify a patch. It must not approve its own R2–R4 change or bypass
branch protection.

## Documentation changes

- Use only the capability states `VERIFIED`, `IMPLEMENTED`, `PROPOSED`, `INFERRED`, `UNKNOWN`, and
  `BLOCKED`.
- Update `docs/product/CURRENT_CAPABILITIES.md` when current behavior or evidence changes.
- Update `ROADMAP.md` and `docs/product/TARGET_CAPABILITIES.md` when accepted future scope changes.
- Record material architecture or trust-boundary changes in an ADR.
- Keep runtime logs, databases, secrets, and generated evidence outside the Git worktree.
- Follow `docs/governance/DOCUMENTATION_POLICY.md`; roadmap and vision text are not implementation
  evidence.

## Dependency lock updates

Dependency PRs must update the manifest **and** the hash-locked resolution tested by CI.
A green run that installs an older lockfile does not validate the requested upgrade.

- Product input: `requirements-product.txt` → `requirements-product.lock`.
- Development input: `requirements-dev.in` (which includes the product input) → `requirements-dev.lock`.
- When a product pin changes, regenerate **both** lockfiles. When only a development pin changes, regenerate the development lockfile.

In a reviewed Python 3.12 environment with `pip-compile` available, regenerate and verify using:

```bash
pip-compile --generate-hashes --output-file=requirements-product.lock requirements-product.txt
pip-compile --generate-hashes --output-file=requirements-dev.lock requirements-dev.in
python scripts/check_requirements_lock_drift.py
python -m pip install --require-hashes -r requirements-dev.lock
python -m pip check
```

Review transitive-version changes and vulnerability audit results before submitting the PR. The `ci/verify` workflow rejects mismatched direct pins before dependency installation, installs the locked development set, and audits the locked product and development sets. Dependabot input-only bumps are intentionally **blocked**, not silently accepted. Do not bypass required checks or assume that a green check from an older lock tested the new version.
