from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADR = ROOT / "docs/adr/ADR-0027-bounded-github-create-ref-write-activation.md"
CARD = ROOT / "docs/governance/CREATE_REF_WRITE_ACTIVATION_R1_DECISION_CARD.md"
GATE = ROOT / "docs/governance/CREATE_REF_WRITE_ACTIVATION_R1_GATE.json"
HISTORICAL_F4B = ROOT / ".github/workflows/f4b-live-canary-create-ref.yml"


def _gate() -> dict[str, object]:
    return json.loads(GATE.read_text(encoding="utf-8"))


def test_create_ref_gate_is_proposed_and_effect_specific() -> None:
    value = _gate()
    effect = value["effect"]

    assert value["schema"] == "VoodooCreateRefWriteActivationGate/v1"
    assert value["status"] == "PROPOSED"
    assert effect == {
        "provider": "github",
        "repository": "eimyroot/Voodoo-One",
        "environment": "staging",
        "capability": "github.create-ref/v1",
        "operation": "CREATE_REF",
        "target_kind": "git_ref",
        "ref_namespace": "refs/heads/vone-canary/*",
        "create_semantics": "CREATE_ONLY",
        "max_provider_mutations": 1,
        "automatic_retry": False,
        "update_fallback": False,
        "force_update_fallback": False,
        "delete_fallback": False,
        "production_effects": False,
    }


def test_writer_is_dedicated_exact_repo_app_and_verifier_stays_read_only() -> None:
    value = _gate()
    writer = value["writer_identity"]
    verifier = value["verifier_identity"]

    assert writer["required_principal_class"] == "github-app-installation"
    assert writer["required_repository_scope"] == ["eimyroot/Voodoo-One"]
    assert writer["required_permissions"] == {"contents": "write", "metadata": "read"}
    assert writer["standing_token_forbidden"] is True
    assert writer["workflow_github_token_forbidden"] is True
    assert writer["personal_pat_forbidden"] is True
    assert writer["ambient_fallback_forbidden"] is True
    assert writer["must_differ_from_verifier_principal"] is True

    assert verifier == {
        "required_principal_class": "github-app-installation",
        "required_app_slug": "voodoo-one-g8-verifier",
        "required_repository_scope": ["eimyroot/Voodoo-One"],
        "required_permissions": {"contents": "read", "metadata": "read"},
        "permission_widening_forbidden": True,
    }


def test_live_gate_requires_exact_sha_governance_read_maturity_and_effect_authorization() -> None:
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
        "TARGET_SHA=EXACT_AUTHORIZED_SHA",
        "A09_CURRENT_FENCE_PREFLIGHT=PASS",
        "DEFAULT_DENY_EGRESS=PASS",
        "ROLLBACK_READINESS=VERIFIED",
        "EXACT_EFFECT_AUTHORIZATION=RECORDED",
    }
    assert prerequisites == required


def test_post_effect_never_conflates_transport_success_with_verification() -> None:
    value = _gate()
    post = set(value["post_effect"])
    ambiguity = value["ambiguity"]

    assert "PROVIDER_MUTATION_COUNT=1" in post
    assert "AUTOMATIC_RETRY=false" in post
    assert "EXECUTION_RECEIPT_V2=PERSISTED" in post
    assert "INDEPENDENT_PROVIDER_READBACK=PASS" in post
    assert "VERIFICATION_RESULT_V1=VERIFIED" in post

    assert ambiguity == {
        "automatic_retry": False,
        "infer_absence_from_transport_error": False,
        "automatic_rollback": False,
        "required_status": "INDETERMINATE",
        "next_action": "fresh-read-only-provider-reconciliation",
    }


def test_rollback_is_separate_non_atomic_authority() -> None:
    rollback = _gate()["rollback"]

    assert rollback == {
        "implied_by_create_authority": False,
        "separate_authorization_required": True,
        "strategy": "DELETE_EXACT_CREATED_REF",
        "temporal_model": "READ_THEN_DELETE_NON_ATOMIC",
        "exact_predelete_sha_required": True,
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
    assert readiness["production_effects"] == "BLOCKED / NOT_PERFORMED"


def test_adr_and_decision_card_do_not_self_authorize_provider_write() -> None:
    adr = ADR.read_text(encoding="utf-8")
    card = CARD.read_text(encoding="utf-8")

    assert "Status: PROPOSED" in adr
    assert "Merge, CI, review or adoption of this ADR does not itself authorize a CREATE_REF effect." in adr
    assert "DELETE_REF is not authorized by this CREATE_REF gate" in adr
    assert "Current decision | DESIGN / CANDIDATE ONLY; live effect remains BLOCKED" in card
    assert "PROVIDER_WRITE = NOT_AUTHORIZED / NOT_PERFORMED" in card


def test_historical_f4b_workflow_is_not_current_repo_activation_authority() -> None:
    workflow = HISTORICAL_F4B.read_text(encoding="utf-8")

    assert 'F4B_EXPECTED_PR: "120"' in workflow
    assert 'F4B_TARGET_REPOSITORY: "nulleimy/V-One"' in workflow
    assert "workflow_dispatch:" not in workflow
    assert "pull_request:" in workflow
