# Incident 2026-09-10 — GitHub Actions disabled for user eimyroot

## Detected
2026-09-10 ~08:03 UTC

## Symptom
- `gh workflow run` → HTTP 422: Actions has been disabled for this user
- Repo permissions: enabled=true, allowed_actions=all
- Repo is public, fork=false, no billing issue
- `ci.yml` cannot produce `verify` check run on new commits
- G0 verifier returns UNKNOWN

## Impact
- required_status_checks cannot be satisfied → PRs cannot merge without bypass
- G8/C blocked (all pilots are workflow_dispatch)

## Mitigation
- 2026-09-10 10:03 CEST: ruleset required_status_checks restored
- 2026-09-10 ~10:XX CEST: temporary bypass_actors added for owner
- GitHub Support ticket: <ticket-id>

## Resolution criteria
- Actions restored for user eimyroot
- Fresh G0 returns VERIFIED
- bypass_actors removed from ruleset 20915283

## Evidence
- /Users/eimyna/00_DEV/V-ONE-EVIDENCE/CODEX/ACTIONS_DISABLED_20260910T080824Z/
- /Users/eimyna/00_DEV/V-ONE-EVIDENCE/CODEX/RULESET_RESTORE_20260910T080313Z/
