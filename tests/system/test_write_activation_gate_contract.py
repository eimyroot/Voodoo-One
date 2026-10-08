from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADR = ROOT / "docs/adr/ADR-0027-bounded-github-create-ref-write-activation.md"
CARD = ROOT / "docs/governance/CREATE_REF_WRITE_ACTIVATION_R1_DECISION_CARD.md"
GATE = ROOT / "docs/governance/CREATE_REF_WRITE_ACTIVATION_R1_GATE.json"
HISTORICAL_F4B = ROOT / ".github/workflows/f4b-live-canary-create-ref.yml"

TOKEN_ISSUER_SHA = "bcd2ba49218906704ab6c1aa796996da409d3eb1"


def _gate() -> dict[str, object]:
    return json.loads(GATE.read_text(encoding="utf-8"))


def test_create_ref_gate_is_proposed_and_effect_specific() -> None:
    value = _gate()

    assert value["schema"] == "VoodooCreateRefWriteActivationGate/v1"
    assert value["status"] == "PROPOSED"
    assert value["effect"] == {
        "provider": "github",
        "repository": "eimyroot/Voodoo-One",
        "environment": "staging",
        "capability": "github.create-ref/v1",
        "operation": "CREATE_REF",
        "target_kind": "git_ref",
        "ref_namespace": "refs/heads/vone-canary/*",
        "ref_namespace_prefix": "refs/heads/vone-canary/",
        "exact_ref_authorization_required": True,
        "exact_ref_must_match_namespace_prefix": True,
        "create_semantics": "CREATE_ONLY",
        "max_provider_mutations": 1,
        "automatic_retry": False,
        "update_fallback": False,
        "force_update_fallback": False,
        "delete_fallback": False,
        "generic_execute": False,
        "production_effects": False,
    }


def test_effect_authorization_structurally_binds_exact_effect_and_non_authority() -> None:
    assert _gate()["effect_authorization"] == {
        "schema": "CreateRefEffectAuthorization/v1",
        "attributable_owner_authorization_required": True,
        "immutable_digest_required": True,
        "digest_algorithm": "sha256",
        "digest_match_required_before_effect": True,
        "required_bindings": {
            "provider": "github",
            "activation_sha": "EXACT_ACTIVATION_MAIN_SHA",
            "repository": "eimyroot/Voodoo-One",
            "environment": "staging",
            "operation": "CREATE_REF",
            "exact_ref": "EXACT_CANARY_REF",
            "ref_namespace_prefix": "refs/heads/vone-canary/",
            "exact_target_sha": "EXACT_AUTHORIZED_SHA",
            "max_provider_mutations": 1,
            "automatic_retry": False,
            "release_authorized": False,
            "deployment_authorized": False,
            "production_effects": False,
        },
    }


def test_writer_is_dedicated_exact_repo_app_with_exact_permission_and_credential_ceiling() -> None:
    writer = _gate()["writer_identity"]

    assert writer == {
        "required_principal_class": "github-app-installation",
        "required_owner": "eimyroot",
        "required_repository_scope": ["eimyroot/Voodoo-One"],
        "required_permissions": {"contents": "write", "metadata": "read"},
        "exact_permission_set_required": True,
        "additional_permissions_forbidden": True,
        "token_lifetime": "ephemeral-installation-token",
        "token_issuer": {
            "action": "actions/create-github-app-token",
            "commit_sha": TOKEN_ISSUER_SHA,
        },
        "standing_token_forbidden": True,
        "workflow_github_token_forbidden": True,
        "personal_pat_forbidden": True,
        "read_runner_credential_for_write_forbidden": True,
        "verifier_app_credential_for_write_forbidden": True,
        "ambient_fallback_forbidden": True,
        "credential_reuse_outside_exact_authorized_attempt_forbidden": True,
        "must_differ_from_verifier_principal": True,
    }


def test_verifier_stays_distinct_exact_repo_read_only_app() -> None:
    assert _gate()["verifier_identity"] == {
        "required_principal_class": "github-app-installation",
        "required_app_slug": "voodoo-one-g8-verifier",
        "required_repository_scope": ["eimyroot/Voodoo-One"],
        "required_permissions": {"contents": "read", "metadata": "read"},
        "permission_widening_forbidden": True,
    }


def test_canonical_authority_path_is_complete_and_rejects_parallel_authority() -> None:
    assert _gate()["canonical_authority_path"] == {
        "required_chain": [
            "ReviewedChangeRequest",
            "DatabasePermissionAuthority/current-workspace-membership",
            "AuthorizationSnapshot",
            "ExecutionGrant/v2",
            "GrantConsumptionWitness/v1/exactly-once",
            "DurableOutbox",
            "DispatchEnvelope",
            "DurableInbox",
            "ExecutionEpoch/ACTIVE",
            "ExecutionLease/current",
            "ExecutionCapsule/current",
            "TerminalProfile/BOUNDED_MUTATION_VERIFIED",
            "A09CreateRefPreparer",
            "WriteEffectPreflight/v1",
            "CurrentExecutionFence/recheck-immediately-before-effect",
            "GitHub/CREATE_REF/one-exact-call",
        ],
        "required_terminal_profile": "BOUNDED_MUTATION_VERIFIED",
        "immediate_pre_effect_fence_revalidation": True,
        "caller_controlled_terminal_profile_forbidden": True,
        "parallel_database_forbidden": True,
        "parallel_permission_authority_forbidden": True,
        "parallel_fence_forbidden": True,
        "historical_pilot_seed_shortcut_forbidden": True,
        "direct_transport_invocation_forbidden": True,
    }


def test_live_gate_requires_exact_sha_governance_authority_path_and_structured_effect_authorization() -> None:
    prerequisites = set(_gate()["live_prerequisites"])
    required = {
        "ADR_0019_EFFECTIVE_STATUS=ADOPTED",
        "ADR_0027_EFFECTIVE_STATUS=ADOPTED",
        "EXACT_ACTIVATION_MAIN_SHA=PINNED",
        "EXACT_HEAD_CI=SUCCESS",
        "INDEPENDENT_REVIEW=CLEAN",
        "BLOCKING_REVIEW_THREADS=0",
        "G0_ON_EXACT_ACTIVATION_SHA=VERIFIED",
        "TWO_RUN_G8_ON_EXACT_ACTIVATION_SHA=VERIFIED",
        "WRITER_APP_EXACT_REPO_SCOPE=VERIFIED",
        "WRITER_APP_PERMISSION_CEILING=VERIFIED",
        "WRITER_VERIFIER_PRINCIPALS=DISTINCT",
        "CANARY_REF_PRE_STATE=ABSENT",
        "CANARY_REF_NAMESPACE=STRICT_PREFIX",
        "EXACT_AUTHORIZED_REF=MATCH_REQUESTED_REF",
        "TARGET_SHA=EXACT_AUTHORIZED_SHA",
        "A09_CANONICAL_AUTHORITY_PATH=VERIFIED",
        "A09_CURRENT_FENCE_PREFLIGHT=PASS",
        "IMMEDIATE_PRE_EFFECT_FENCE_REVALIDATION=PASS",
        "DEFAULT_DENY_EGRESS=PASS",
        "SANITIZED_EVIDENCE_NO_CREDENTIAL_BYTES=PASS",
        "ROLLBACK_READINESS=VERIFIED",
        "EXACT_EFFECT_AUTHORIZATION_ENVELOPE=VERIFIED",
    }
    assert prerequisites == required
    assert "EXACT_EFFECT_AUTHORIZATION=RECORDED" not in prerequisites


def test_post_effect_requires_fresh_runner_and_independent_verifier_observations() -> None:
    assert _gate()["post_effect"] == {
        "provider_mutation_count": 1,
        "automatic_retry": False,
        "durable_completion_required": True,
        "execution_receipt_v2_required": True,
        "fresh_runner_observation": {
            "required": True,
            "provider_read_only": True,
            "exact_ref": "EXACT_CANARY_REF",
            "observed_ref_sha": "EXACT_AUTHORIZED_SHA",
        },
        "independent_verifier_observation": {
            "required": True,
            "app_slug": "voodoo-one-g8-verifier",
            "provider_read_only": True,
            "exact_ref": "EXACT_CANARY_REF",
            "observed_ref_sha": "EXACT_AUTHORIZED_SHA",
        },
        "observed_post_state_v1_required": True,
        "verification_strength_v1": "INDEPENDENT_PROVIDER_READBACK",
        "verification_result_v1": "VERIFIED",
        "accepted_ref_state": {
            "exists": True,
            "exact_ref": "EXACT_CANARY_REF",
            "ref_namespace_prefix": "refs/heads/vone-canary/",
            "exact_target_sha": "EXACT_AUTHORIZED_SHA",
        },
    }


def test_ambiguous_transport_is_indeterminate_and_never_retried_or_rolled_back() -> None:
    assert _gate()["ambiguity"] == {
        "automatic_retry": False,
        "infer_absence_from_transport_error": False,
        "automatic_rollback": False,
        "required_status": "INDETERMINATE",
        "next_action": "fresh-read-only-provider-reconciliation",
    }


def test_rollback_is_separate_non_atomic_authority_and_blocks_uncertain_or_changed_state() -> None:
    assert _gate()["rollback"] == {
        "implied_by_create_authority": False,
        "separate_authorization_required": True,
        "strategy": "DELETE_EXACT_CREATED_REF",
        "temporal_model": "READ_THEN_DELETE_NON_ATOMIC",
        "fresh_predelete_read_required": True,
        "exact_predelete_sha_required": True,
        "required_predelete_ref_state": {
            "exact_ref": "EXACT_CANARY_REF",
            "exact_sha": "EXACT_CREATED_SHA",
        },
        "block_if_ref_changed": True,
        "block_if_state_ambiguous": True,
        "block_if_verification_unavailable": True,
        "block_if_exact_created_sha_cannot_be_reestablished": True,
        "delete_transport_success_not_sufficient": True,
        "max_provider_mutations": 1,
        "automatic_retry": False,
        "independent_absence_verification_required": True,
    }


def test_candidate_truth_is_blocked_before_writer_app_and_live_workflow() -> None:
    readiness = _gate()["current_readiness"]

    assert readiness["adr_0019_read_gate"] == "VERIFIED"
    assert readiness["write_runtime_gate"] == "ELIGIBLE"
    assert readiness["writer_github_app"] == "NOT_PROVISIONED"
    assert readiness["live_create_ref_workflow"] == "NOT_CREATED"
    assert readiness["create_ref_live_gate"] == "BLOCKED"
    assert readiness["provider_write"] == "NOT_AUTHORIZED / NOT_PERFORMED"
    assert readiness["release"] == "NOT_AUTHORIZED / NOT_PERFORMED"
    assert readiness["deployment"] == "NOT_AUTHORIZED / NOT_PERFORMED"
    assert readiness["production_effects"] == "BLOCKED / NOT_PERFORMED"


def test_adr_and_decision_card_do_not_self_authorize_provider_write() -> None:
    adr = ADR.read_text(encoding="utf-8")
    card = CARD.read_text(encoding="utf-8")

    assert "Status: PROPOSED" in adr
    assert "generic execute          = forbidden" in adr
    assert "commit-SHA-pinned actions/create-github-app-token" in adr
    assert "BOUNDED_MUTATION_VERIFIED terminal profile" in adr
    assert "fresh read-only Runner observation" in adr
    assert "If the ref changed, state is ambiguous, verification is unavailable" in adr
    assert "Merge, CI, review or adoption of this ADR does not itself authorize a CREATE_REF effect." in adr
    assert "DELETE_REF is not authorized by this CREATE_REF gate" in adr
    assert "Current decision | DESIGN / CANDIDATE ONLY; live effect remains BLOCKED" in card
    assert "EXACT_EFFECT_AUTHORIZATION_ENVELOPE = VERIFIED" in card
    assert "EXACT_EFFECT_AUTHORIZATION         = RECORDED" not in card
    assert "PROVIDER_WRITE = NOT_AUTHORIZED / NOT_PERFORMED" in card


def test_historical_f4b_workflow_is_not_current_repo_activation_authority() -> None:
    workflow = HISTORICAL_F4B.read_text(encoding="utf-8")

    assert 'F4B_EXPECTED_PR: "120"' in workflow
    assert 'F4B_TARGET_REPOSITORY: "nulleimy/V-One"' in workflow
    assert "workflow_dispatch:" not in workflow
    assert "pull_request:" in workflow
