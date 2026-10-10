from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

from voodoo_product.control_plane import (
    CONTROL_PLANE_USEFULNESS_GATE,
    AcceptanceGate,
    ControlPlaneBoundary,
    ControlPlaneDecisionError,
    EvidenceReference,
    VOneControlPlaneDecision,
)
from voodoo_product.evidence_primitives import canonical_json
from voodoo_product.operation_semantics import (
    MEMBER_ROLES,
    OperationMember,
    OperationSemantics,
    TechniqueEvidence,
)
from voodoo_product.skill_orchestration import (
    DEVELOPMENT_USEFULNESS_GATE,
    SkillOrchestrationPlan,
    select_relevant_skills,
)

SEMANTICS_SOURCE_IDENTITY = (
    "repo:eimyroot/Voodoo-One@ad66fc2a6a032a7151055a603aac0fffc5ee2f2b:"
    "voodoo_product/operation_semantics.py"
)
SKILL_PLAN_SOURCE_IDENTITY = (
    "repo:eimyroot/Voodoo-One@ad66fc2a6a032a7151055a603aac0fffc5ee2f2b:"
    "voodoo_product/skill_orchestration.py"
)


def digest_without(payload: dict[str, object], digest_field: str) -> str:
    return hashlib.sha256(
        canonical_json(
            {key: value for key, value in payload.items() if key != digest_field}
        ).encode("utf-8")
    ).hexdigest()


def semantics() -> OperationSemantics:
    return OperationSemantics.create(
        operation_id="system_control_plane_contract",
        capability="vone.control-plane.decide/v1",
        members=tuple(
            OperationMember(role=role, member_id=f"id_{role}") for role in MEMBER_ROLES
        ),
        techniques=tuple(
            TechniqueEvidence.from_name(name)
            for name in ("slsa", "mcp", "sigstore", "a2a", "aws_agentcore", "spiffe")
        ),
    )


def skill_plan() -> SkillOrchestrationPlan:
    return SkillOrchestrationPlan.create(
        task_id="system_control_plane_contract",
        task_type="architecture",
        source_of_truth="github:nulleimy/V-One/pull/69",
        objective="Unify V-One operation semantics, proof, and skill orchestration.",
        purpose="Make every system action produce one useful control-plane decision.",
        system_benefit="Prevents implementation work from adding unauditable surface area.",
        selected_skills=select_relevant_skills(task_type="architecture"),
        excluded_operations=(
            "runtime_plugin_trust",
            "tool_execution",
            "self_approval",
            "production_effect",
        ),
        acceptance_gates=(
            DEVELOPMENT_USEFULNESS_GATE,
            "decision_has_boundary",
            "decision_has_evidence",
            "decision_has_acceptance_gates",
            "decision_digest_matches_claims",
        ),
    )


def boundary() -> ControlPlaneBoundary:
    return ControlPlaneBoundary(
        boundary_type="contract_only",
        scope="Control-plane decision contract without runtime side effects.",
        purpose="Fence control-plane decisions before any runtime integration exists.",
        system_benefit="Prevents contract records from implying hidden execution authority.",
        allowed_effects=("canonical_decision_record",),
        prohibited_effects=("runtime_execution", "approval_bypass", "production_effect"),
    )


def evidence() -> tuple[EvidenceReference, ...]:
    operation_id = semantics().operation_id
    return (
        EvidenceReference(
            evidence_type="operation_semantics",
            operation_id=operation_id,
            source_kind="repository",
            source_authority="AUTHORITATIVE",
            source_identity=SEMANTICS_SOURCE_IDENTITY,
            source="voodoo_product/operation_semantics.py",
            digest=semantics().semantics_digest,
            purpose="Bind the decision to the shared V-One operation language.",
            system_benefit="Prevents member roles and operation stages from drifting.",
        ),
        EvidenceReference(
            evidence_type="skill_orchestration",
            operation_id=operation_id,
            source_kind="repository",
            source_authority="AUTHORITATIVE",
            source_identity=SKILL_PLAN_SOURCE_IDENTITY,
            source="voodoo_product/skill_orchestration.py",
            digest=skill_plan().plan_digest,
            purpose="Bind the decision to the selected specialist workflow.",
            system_benefit="Prevents unowned or overlapping skill authority.",
        ),
    )


def gates(status: str = "PASS") -> tuple[AcceptanceGate, ...]:
    semantics_digest = semantics().semantics_digest
    plan_digest = skill_plan().plan_digest
    return (
        AcceptanceGate(
            gate=CONTROL_PLANE_USEFULNESS_GATE,
            status=status,
            evidence_digest=semantics_digest,
            evidence_source_identity=SEMANTICS_SOURCE_IDENTITY,
            evidence_source_authority="AUTHORITATIVE",
            purpose="Confirm the decision and all decision elements state usefulness.",
            system_benefit="Blocks purposeless changes from entering the control plane.",
        ),
        AcceptanceGate(
            gate="decision_has_boundary",
            status=status,
            evidence_digest=semantics_digest,
            evidence_source_identity=SEMANTICS_SOURCE_IDENTITY,
            evidence_source_authority="AUTHORITATIVE",
            purpose="Confirm the decision has an explicit effect boundary.",
            system_benefit="Stops ambiguous records from becoming implicit authority.",
        ),
        AcceptanceGate(
            gate="decision_has_evidence",
            status=status,
            evidence_digest=plan_digest,
            evidence_source_identity=SKILL_PLAN_SOURCE_IDENTITY,
            evidence_source_authority="AUTHORITATIVE",
            purpose="Confirm the decision is linked to evidence.",
            system_benefit="Keeps every control-plane claim auditable.",
        ),
        AcceptanceGate(
            gate="decision_has_acceptance_gates",
            status=status,
            evidence_digest=plan_digest,
            evidence_source_identity=SKILL_PLAN_SOURCE_IDENTITY,
            evidence_source_authority="AUTHORITATIVE",
            purpose="Confirm acceptance is declared before status is trusted.",
            system_benefit="Prevents status labels from outrunning acceptance criteria.",
        ),
    )


def decision(status: str = "IMPLEMENTED") -> VOneControlPlaneDecision:
    gate_status = "PENDING" if status == "IMPLEMENTED" else "PASS"
    return VOneControlPlaneDecision.create(
        decision_id="cpd_system_control_plane_contract",
        status=status,
        rationale="Contract exists, but runtime API integration is deliberately out of scope.",
        purpose="Unify operation semantics, skill orchestration, and proof status.",
        system_benefit="Creates one auditable control-plane record for every system action.",
        semantics=semantics(),
        skill_plan=skill_plan(),
        boundary=boundary(),
        evidence=evidence(),
        acceptance_gates=gates(gate_status),
    )


def test_control_plane_decision_is_deterministic_and_round_trippable() -> None:
    first = decision()
    second = decision()

    assert first.to_dict() == second.to_dict()
    assert first.operation_id == "system_control_plane_contract"
    assert first.capability == "vone.control-plane.decide/v1"
    assert first.decision_digest == digest_without(first.to_dict(), "decision_digest")
    restored = VOneControlPlaneDecision.from_dict(first.to_dict())
    assert restored == first
    assert restored.evidence[0].operation_id == first.operation_id
    assert restored.evidence[0].source_identity == SEMANTICS_SOURCE_IDENTITY
    assert restored.evidence[0].source_authority == "AUTHORITATIVE"
    assert restored.acceptance_gates[0].evidence_source_identity == SEMANTICS_SOURCE_IDENTITY


def test_control_plane_decision_requires_boundary_evidence_and_gates() -> None:
    with pytest.raises(ControlPlaneDecisionError, match="evidence is required"):
        VOneControlPlaneDecision.create(
            decision_id="cpd_missing_evidence",
            status="IMPLEMENTED",
            rationale="Missing evidence must fail closed.",
            purpose="Ensure evidence is mandatory.",
            system_benefit="Prevents unsupported control-plane claims.",
            semantics=semantics(),
            skill_plan=skill_plan(),
            boundary=boundary(),
            evidence=(),
            acceptance_gates=gates("PENDING"),
        )

    with pytest.raises(ControlPlaneDecisionError, match="acceptance_gates are required"):
        VOneControlPlaneDecision.create(
            decision_id="cpd_missing_gates",
            status="IMPLEMENTED",
            rationale="Missing gates must fail closed.",
            purpose="Ensure acceptance gates are mandatory.",
            system_benefit="Prevents ungated control-plane status changes.",
            semantics=semantics(),
            skill_plan=skill_plan(),
            boundary=boundary(),
            evidence=evidence(),
            acceptance_gates=(),
        )


def test_verified_decision_requires_proof() -> None:
    with pytest.raises(ControlPlaneDecisionError, match="VERIFIED"):
        decision(status="VERIFIED")


def test_non_final_decision_requires_pending_or_blocked_gate() -> None:
    with pytest.raises(ControlPlaneDecisionError, match="non-final"):
        VOneControlPlaneDecision.create(
            decision_id="cpd_overclaimed",
            status="IMPLEMENTED",
            rationale="Implemented source must not be treated as fully verified.",
            purpose="Ensure implemented status cannot pretend to be verified.",
            system_benefit="Keeps merge/readiness evidence honest.",
            semantics=semantics(),
            skill_plan=skill_plan(),
            boundary=boundary(),
            evidence=evidence(),
            acceptance_gates=gates("PASS"),
        )


def test_control_plane_rejects_cross_operation_evidence() -> None:
    mismatched_evidence = (
        replace(evidence()[0], operation_id="other_operation"),
        evidence()[1],
    )

    with pytest.raises(ControlPlaneDecisionError, match="operation_id"):
        VOneControlPlaneDecision.create(
            decision_id="cpd_cross_operation_evidence",
            status="IMPLEMENTED",
            rationale="Evidence from another operation must not satisfy this decision.",
            purpose="Bind evidence to the exact operation.",
            system_benefit="Prevents cross-operation evidence conflation.",
            semantics=semantics(),
            skill_plan=skill_plan(),
            boundary=boundary(),
            evidence=mismatched_evidence,
            acceptance_gates=gates("PENDING"),
        )


def test_control_plane_rejects_gate_evidence_from_wrong_source() -> None:
    gate_values = list(gates("PENDING"))
    gate_values[0] = replace(
        gate_values[0],
        evidence_source_identity="repo:eimyroot/other@deadbeef:unrelated",
    )

    with pytest.raises(ControlPlaneDecisionError, match="evidence/source binding"):
        VOneControlPlaneDecision.create(
            decision_id="cpd_wrong_source",
            status="IMPLEMENTED",
            rationale="A digest from one source must not silently prove a claim about another source.",
            purpose="Require exact claim-to-source binding.",
            system_benefit="Prevents cross-source evidence conflation.",
            semantics=semantics(),
            skill_plan=skill_plan(),
            boundary=boundary(),
            evidence=evidence(),
            acceptance_gates=tuple(gate_values),
        )


def test_control_plane_rejects_authority_class_substitution() -> None:
    evidence_values = list(evidence())
    evidence_values[0] = replace(
        evidence_values[0],
        source_authority="SUPPORTING",
    )

    with pytest.raises(ControlPlaneDecisionError, match="evidence/source binding"):
        VOneControlPlaneDecision.create(
            decision_id="cpd_wrong_authority",
            status="IMPLEMENTED",
            rationale="Supporting evidence must not silently satisfy an authoritative-source gate.",
            purpose="Keep source authority explicit at the decision boundary.",
            system_benefit="Distinguishes exact supporting evidence from authoritative evidence.",
            semantics=semantics(),
            skill_plan=skill_plan(),
            boundary=boundary(),
            evidence=tuple(evidence_values),
            acceptance_gates=gates("PENDING"),
        )


def test_control_plane_decision_rejects_tampering() -> None:
    payload = decision().to_dict()
    payload["status"] = "VERIFIED"
    payload["decision_digest"] = digest_without(payload, "decision_digest")

    with pytest.raises(ControlPlaneDecisionError, match="VERIFIED"):
        VOneControlPlaneDecision.from_dict(payload)


def test_control_plane_rejects_elements_without_purpose_or_benefit() -> None:
    with pytest.raises(ControlPlaneDecisionError, match="system_benefit"):
        AcceptanceGate(
            gate="decision_has_usefulness",
            status="PENDING",
            evidence_digest=semantics().semantics_digest,
            evidence_source_identity=SEMANTICS_SOURCE_IDENTITY,
            evidence_source_authority="AUTHORITATIVE",
            purpose="Confirm every element has a stated useful role.",
            system_benefit="",
        )


def test_control_plane_requires_explicit_usefulness_gate() -> None:
    with pytest.raises(ControlPlaneDecisionError, match="usefulness gate"):
        VOneControlPlaneDecision.create(
            decision_id="cpd_missing_usefulness_gate",
            status="IMPLEMENTED",
            rationale="Purpose fields alone are not enough without an explicit gate.",
            purpose="Ensure usefulness is accepted as a named gate.",
            system_benefit="Prevents implicit usefulness claims.",
            semantics=semantics(),
            skill_plan=skill_plan(),
            boundary=boundary(),
            evidence=evidence(),
            acceptance_gates=tuple(
                gate for gate in gates("PENDING")
                if gate.gate != CONTROL_PLANE_USEFULNESS_GATE
            ),
        )
