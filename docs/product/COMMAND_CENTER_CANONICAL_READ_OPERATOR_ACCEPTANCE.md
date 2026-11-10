# Command Center — Operator canonical GitHub READ acceptance

STATUS: IMPLEMENTED in isolated review branch; independent human review and live provider E2E required.

## Purpose and boundary

This slice makes the **existing** canonical `github.read-ref/v1` route discoverable and operable in the web console. It does not introduce a second policy, permission, execution, provider, verification, or evidence owner.

The source of truth remains: reviewed `ChangeRequest` → independent approval → `CanonicalOperationRuntime.run_read_only` → isolated G8 READ terminal → independent `VerificationResult/v1` → existing read-only Operation Passport. The UI never issues grants or asserts post-state on its own.

This is **not** a general agent execution launcher and never enables GitHub WRITE, production effects, or the G8 provider runtime. G8 defaults disabled.

## Operator journey

1. A requester with `change.write` selects a non-production workspace in **Plans → Nový požadavek**, chooses **GitHub READ · canonical**, and supplies exactly:
   `{"repository":"owner/repository","ref":"refs/heads/main"}` (also supports fully qualified tag refs). The payload is intentionally not auto-filled with any actual target.
2. The request is submitted for review. A distinct authorized approver decides it through the existing **Approval Inbox**; the requester cannot self-approve.
3. In **Plans**, the canonical button appears only for an approved request with matching raw server-side change-request data, the exact GitHub READ adapter and a positive `GET /api/v1/operations/status` declaration (`configured`, `read_terminal_configured`, and both WRITE flags false). If the runtime or data are missing, it shows READ DISABLED or UNKNOWN, never legacy Execute.
4. Before effect, clicking **Canonical READ** fetches fresh authorized request and runtime state; mismatch, invalid target, revoked/missing approval or production environment abort the UI. Explicit operator confirmation shows the repository and exact ref.
5. The web client posts `/api/v1/operations/{request_id}/read` with `Idempotency-Key` and matching `correlation_id`, preserving the attempt key in tab-scoped session storage across a reload/ambiguous response. **The canonical backend always revalidates authority**, independent of the UI.
6. Only an exact canonical response bound to the request, with `execution.status=SUCCEEDED`, `verification.verdict=VERIFIED`, `verification.strength_class=INDEPENDENT_PROVIDER_READBACK` and a non-empty result digest, is displayed as independently verified by the **READ API**. The UI opens **Runs → Operation Passport** for that execution.
7. Passport is rendered from its existing read-only endpoint. `NOT_PERSISTED`, `UNKNOWN` or missing independent verification in the Passport **must remain visibly UNKNOWN** even after a successful READ API response; no UI reconstruction or invented proof.
8. Cancellation, errors, ambiguities and failed verification are reported as UNKNOWN/NEOVĚŘENO. There is no automatic retry; any explicit later attempt reuses the same tab-scoped idempotency key. For an ambiguous operation, the operator must inspect durable evidence before proceeding.

## Threats, controls, and rollback

- No new provider credentials, endpoints, secret loaders, GitHub write grants, production effects, database tables or elevated permissions.
- Legacy `change-requests/{id}/execute` remains restricted to locally allowed legacy adapters in non-production; it is not called for GitHub READ or GitHub CREATE_REF.
- Runtime availability in the UI is a **convenience**, never a grant. Server-side role, membership, approval, target binding, fence and single-use grant controls remain authoritative.
- No response or any HTTP 200 by itself implies `VerificationResult/v1`.
- Node VM-simulated browser test controls include runtime unavailable, stale approval, cancellation, network ambiguity, stable idempotency across explicit attempts, unverified result, and Passport with unknown durable verification.
- Rollback: revert only this reviewed UI/CI/test slice. Default provider runtime remains disabled independently of the frontend.
- GitHub official main-only live E2E `g8-live-product-read.yml` still requires explicit exact-SHA operator confirmation, separate Runner and GitHub-App Verifier credentials, and retained sanitized evidence. **Not run by this implementation.**
- No claim of product-ready, human-accepted, staged or production-deployed status until manual browser acceptance, independent reviewer, and exact-SHA live G8 E2E.

## Verification

```text
node --check voodoo_product/static/control_room.js
node --check tests/system/test_operator_canonical_read.cjs
node tests/system/test_operator_canonical_read.cjs
node tests/system/test_workflow_boards_render.cjs
python -m pytest -q tests/system/test_control_room_operation_passport_ux.py tests/system/test_canonical_operation_http.py tests/system/test_g8_product_activation.py
python -m ruff check .
python scripts/product_readiness_gate.py
```

Readiness admission requires committed source and all required test files in exact `HEAD`; do not treat an untracked preview as a release artifact.
