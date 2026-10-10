# ADR-0028 — Durable GitHub Dependency Graph Refresh Ownership

- Status: PROPOSED — exact-content owner adoption required
- Date: 2026-10-08
- Scope: GitHub dependency graph provider-state ownership for accepted `main` changes
- Decision class: R2 supply-chain / CI authority / provider-state reconciliation
- Runtime effect: NONE
- Release / deploy effect: NONE
- Production effect: NONE

## Context

On `main@1831d180fe86af0dff75b79a985a4d48a7f79351`, VOODOO One had already merged a
development dependency security remediation, but GitHub's dependency graph remained stale. Repository
truth contained `httpx2==2.12.0`, while GitHub's SBOM still reported `httpx2 2.10.0` and kept three
Dependabot alerts open.

One governed dependency snapshot submission reconciled the provider state successfully:

- exact main remained `1831d180fe86af0dff75b79a985a4d48a7f79351`;
- snapshot id `107819601` returned `SUCCESS`;
- GitHub SBOM moved to `httpx2 2.12.0`;
- stale vulnerable `httpx2 2.10.0`, `urllib3 2.7.0`, and `virtualenv 21.7.0` were no longer observed;
- Dependabot open alert count moved from three to zero.

That manual snapshot now has provider-side precedence. Leaving refresh ownership manual would create a
new stale-authority risk after later accepted dependency changes.

GitHub's dependency submission endpoint requires repository `contents: write`. That permission is
broader than the logical dependency-graph effect and therefore must be isolated from build, test and
verification code.

## Decision

VOODOO One will own one canonical dependency-snapshot stream:

```text
detector.name  = voodoo-one-dependency-reconciliation
job.correlator = voodoo-one-provider-reconciliation
```

The durable workflow runs only after a push to protected `main`.

The workflow is separated into three authority zones:

```text
BUILD / VALIDATE
contents:read
repository code may execute
        ↓
SUBMIT
contents:write
NO checkout
NO repository script execution
exact-main freshness check
one dependency snapshot POST
        ↓
VERIFY
contents:read
repository verifier may execute
bounded SBOM propagation retry
```

No pull-request trigger and no manual workflow-dispatch path is part of this contract.

## Snapshot contract

The repository-owned builder generates two exact manifests from current repository truth:

```text
requirements-product.txt + requirements-product.lock
→ scope = runtime

requirements-dev.in + requirements-dev.lock
→ scope = development
```

Package identities are normalized PyPI PURLs. Direct relationships come only from exact direct input
files. Lockfile-only packages are `indirect`. No dependency edge is invented when the repository does
not prove it.

The snapshot reports the resolved version from the lockfile. Input files establish direct dependency
identity, not the resolved provider version. An input/lock pin mismatch is therefore visible repository
debt but does not cause this provider-state owner to invent a different resolved version or silently
rewrite dependencies. Unexpected requirement include paths still fail closed.

The payload is bound to:

- exact 40-character `github.sha`;
- exact `refs/heads/main`;
- the stable detector and correlator above;
- the exact current runtime and development dependency closures.

For identical file inputs, SHA/ref and explicit scan timestamp, serialization is deterministic.

## Monotonic freshness

The workflow uses one repository-wide concurrency group with `queue: max` and `cancel-in-progress: false`. Current GitHub Actions concurrency semantics allow up to 100 pending runs in this queue. This prevents overlapping dependency snapshot provider writes while preserving accepted main updates instead of replacing the older pending run with the newest one.

Queue order is not treated as sufficient freshness proof. Immediately before the provider write, the submit job re-reads GitHub's current `main`. If hosted `main` differs from the workflow SHA, that run fails closed without submitting a snapshot.

If a newer push occurs after the freshness read but before the POST completes, the newer accepted-main workflow remains responsible for final convergence. The verify job independently checks current `main` before treating its own SBOM observation as authoritative.

This provides bounded monotonic convergence rather than pretending the Git ref update and dependency submission form one atomic transaction. Provider freshness therefore depends on exact-main readback plus serial provider writes, not on queue order alone.

The canonical correlator/detector combination is intentionally the same one used by the successful one-time reconciliation so that durable automation assumes ownership of the same provider-state stream rather than creating a second competing authority.

## Provider WRITE boundary

The only job with `contents: write` is the submit job.

That job must not:

- checkout repository content;
- execute repository-owned Python, shell or binaries;
- mutate refs, issues, pull requests, releases, packages or repository files;
- receive deployment or production credentials;
- dismiss Dependabot alerts.

Its allowed provider effect is exactly:

```text
POST /repos/eimyroot/Voodoo-One/dependency-graph/snapshots
```

The job validates the snapshot digest, exact SHA/ref, detector identity, correlator identity and
manifest set before the POST.

GitHub's permission model cannot express "dependency snapshot only" separately from
`contents: write`. The broader token capability is a residual provider limitation compensated by
job isolation, no checkout, exact-main freshness and one fixed API operation.

## Verification contract

Provider response `SUCCESS` is execution evidence, not final verification.

A separate read-only job fetches the GitHub SBOM and verifies:

1. every exact expected package PURL from the submitted current locks is observable;
2. package versions that changed from the prior accepted main are no longer observable as stale PURLs.

Verification uses bounded propagation retry only. It does not loop indefinitely.

If a newer `main` supersedes the workflow between submission and verification, the older verifier
reports `SUPERSEDED` and exits without treating its older snapshot as current authority. The newer main
run owns the final verification obligation.

Dependabot alert closure is intentionally not a synchronous workflow gate because provider alert
re-evaluation may lag SBOM convergence. Alert state is a downstream observation, not a reason to widen
workflow permissions or dismiss alerts automatically.

## Security properties

This decision adds no dependency, model, service, database, runtime provider capability, release path
or production effect.

Required invariants:

- default workflow permissions are empty;
- BUILD and VERIFY use only `contents: read`;
- `contents: write` appears only in SUBMIT;
- SUBMIT never checks out repository code;
- dependency snapshot provider writes do not overlap; GitHub concurrency may replace an older pending run, so freshness never depends on FIFO ordering;
- exact-main freshness is checked immediately before write;
- the provider write is a single fixed dependency snapshot endpoint;
- stale dependency versions changed by the accepted main transition fail read-back verification;
- verification failure cannot be converted into success;
- retry is bounded;
- no Dependabot dismissal is automated.

## Failure semantics

Before submission, any malformed payload, digest mismatch, non-main ref, wrong SHA, stale hosted main,
unexpected detector/correlator or unexpected manifest set fails closed with no provider write.

After submission, an HTTP/API failure or non-`SUCCESS` result fails the workflow.

Read-back failure retries only within the bounded verification budget. If GitHub SBOM does not converge,
the workflow fails. No second provider snapshot is submitted automatically by the same run.

## Testing

Repository tests must cover:

- deterministic payload serialization;
- exact SHA and main-ref binding;
- runtime/development scope mapping;
- direct/indirect relationship mapping;
- prior-version stale PURL derivation;
- stale PURL rejection during SBOM read-back;
- missing expected dependency rejection;
- workflow main-only trigger;
- WRITE permission isolation;
- no checkout/repository execution in the submit job;
- exact-main freshness check;
- serialized provider-write concurrency with no in-progress cancellation;
- bounded verifier retry.

## Rollback

Before merge, rollback is a focused revert of the candidate files.

After merge, rollback of automation is a focused revert of this workflow, builder/verifier and tests.
Removing the workflow does not erase the latest already-submitted provider snapshot. That provider state
remains evidence of the accepted main on which it was submitted until another higher-priority snapshot
supersedes it.

Rollback does not authorize provider deletion, release, deployment or production effects.

## Adoption boundary

Implementation and CI success do not by themselves make this ADR effectively adopted.

Effective adoption requires an attributable owner decision over the exact ADR bytes and the normal
external adoption record when project governance requires it.

No release, deployment or production authorization is created by this decision.
