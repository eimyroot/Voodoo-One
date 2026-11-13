# Project Control Map R1 — optional read-only Control Room projection

Status: **IMPLEMENTED IN REVIEW BRANCH / NOT RELEASED / NO AUTHORITY EFFECT**.

## Scope

An authenticated, opt-in observation screen in the existing VOODOO One Control Room.
It reads a pre-collected, SHA-256-pinned `ProjectControlMapSnapshot/v1`. It does not
run Git or GitHub commands, synchronize cross-repository state, change FinishGate,
merge Git branches, issue an approval, mutate a project, or create a registry.

The original Architecture Atlas, each project's Git source and adopted
`docs/governance/AUTHORITY_AND_ADOPTION_REGISTER.md` remain canonical within their
respective domains. VOODOO-WORKFLOW attestations remain proposed.

## Runtime activation (disabled by default)

Supply both settings through the normal private runtime configuration mechanism:

```text
VOODOO_PROJECT_CONTROL_MAP_SNAPSHOT_PATH=/absolute/outside-repo/evidence/map.json
VOODOO_PROJECT_CONTROL_MAP_SNAPSHOT_SHA256=<64-character lowercase sha256>
```

Do **not** commit local absolute paths, credentials, private snapshots or real
operator data. Both settings are required. The SHA-256 must match the exact bytes.
Runtime startup validates the configuration; every authenticated read checks the
pinned SHA again. An unspecified, missing, replaced, oversized, malformed, symlinked,
or semantically unauthorized snapshot results in HTTP 503 with a generic message.
An unauthenticated request is rejected by existing session/role logic before reading
the evidence file. The response includes `Cache-Control: no-store`.

To avoid exposing an evidence filesystem through HTTP, the response only contains
an allowlisted selection of project names, Git references, status/freshness labels,
explicit dependency relations and bounded gaps. It omits local filesystem paths,
actor identities, raw receipts and unrecognized fields.

## Endpoints and UI

`GET /api/v1/project-control-map` — existing `require_permission("read")` policy.
This is a **separate** endpoint; the original `GET /api/v1/control-room` response
contract is unchanged. The existing Control Room adds a new "Project Control Map"
navigation tab that fetches only the authenticated read-only endpoint.

`CURRENT_SNAPSHOT` means that the *observation timestamp* is at most 24 hours old.
It does **not** mean that Git/GitHub state was re-queried during this request.
Older evidence is labelled `STALE_SNAPSHOT` and remains visibly historical.
Missing proof never becomes PASS. No auto-refresh or provider polling exists.

## Trust and rollout

The source collector is out of scope. R1 assumes evidence was collected by an
approved process and pinned through deliberate configuration; it does not elevate
collector claims to independent runtime proof. VOODOO One's current MRC, SKILLSET
and WORKFLOW relations remain evidence-scoped. Do not wire this endpoint into the
trust kernel or authorization path.

The isolated review branch is based on the exact hosted `main@e678f75f...`.
Do not overwrite the separate dirty local
`audit/codebase-refactoring-analysis` worktree, including its uncommitted
`ControlRoomService` extraction. A merge, runtime activation or deployment each
requires separate governed review/acceptance.

### Review checks

- Python unit and API tests for authentication, no path/secret leakage, disabled
  default, digest mismatch, malformed snapshot, symlink, timestamp, path segments,
  denial of write authority and stale-evidence labeling.
- Control Room UI renders only allowlisted values using existing HTML escaping.
- Existing exact-shape `/api/v1/control-room` regression tests must remain PASS.
- JS syntax and repository lint.
- Independent review, pull-request CI and exact head revalidation before merge.

Rollback: unset the two environment settings and restart through the separately
approved release process (or revert the review commit before merge). Existing
Control Room API behavior is unchanged and no database migration is introduced.

### Evidence

Local evidence and prototype live outside the repository:

`/Users/eimyna/0_EVIDENCE/Voodoo-One/PROJECT_CONTROL_MAP/R1/`

The original snapshot is not bundled with the product. Deploying code alone
displays "UNAVAILABLE / UNVERIFIED" until an operator configures a trusted snapshot.
