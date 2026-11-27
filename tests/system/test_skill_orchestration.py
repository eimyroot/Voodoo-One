from __future__ import annotations

import hashlib
from dataclasses import replace
from typing import Any

import pytest

from voodoo_product.evidence_primitives import canonical_json
from voodoo_product.skill_orchestration import (
    DEVELOPMENT_USEFULNESS_GATE,
    PRIMARY_COORDINATOR,
    TASK_TYPES,
    SkillOrchestrationPlan,
    select_relevant_skills,
    skill_catalog_projection,
)


def digest_without(payload: dict[str, object], digest_field: str) -> str:
    return hashlib.sha256(
        canonical_json(
            {key: value for key, value in payload.items() if key != digest_field}
        ).encode("utf-8")
    ).hexdigest()


def plan(**changes: Any) -> SkillOrchestrationPlan:
    selected = select_relevant_skills(task_type="ci_cd")
    values = {
        "task_id": "pr_69_ci_recovery",
        "task_type": "ci_cd",
        "source_of_truth": "github:nulleimy/V-One/pull/69",
        "objective": "Get PR #69 from failed checks to review-ready without scope expansion.",
        "purpose": "Recover the review branch using bounded, evidence-backed engineering work.",
        "system_benefit": "Prevents CI recovery from becoming unscoped or unauditable change.",
        "selected_skills": selected,
        "excluded_operations": (
            "merge",
            "deploy",
            "production_effect",
            "runtime_authorization_change",
        ),
        "acceptance_gates": (
            DEVELOPMENT_USEFULNESS_GATE,
            "github_actions_green",
            "full_pytest_passes",
            "ruff_passes",
            "documentation_does_not_overclaim_runtime_authority",
        ),
    }
    values.update(changes)
    return SkillOrchestrationPlan.create(**values)


def test_relevant_skill_selection_uses_one_primary_coordinator() -> None:
    selected = select_relevant_skills(task_type="ci_cd")

    assert PRIMARY_COORDINATOR in selected
    assert "systematic-debugging-and-root-cause-engineer" in selected
    assert "quality-evidence-verifier" in selected
    assert "supply-chain-provenance-governor" in selected


def test_skill_orchestration_plan_is_deterministic_and_round_trippable() -> None:
    first = plan()
    second = plan(selected_skills=tuple(reversed(select_relevant_skills(task_type="ci_cd"))))

    assert first.to_dict() == second.to_dict()
    assert first.primary_coordinator == PRIMARY_COORDINATOR
    assert first.plan_digest == digest_without(first.to_dict(), "plan_digest")
    assert SkillOrchestrationPlan.from_dict(first.to_dict()) == first


def test_skill_orchestration_plan_covers_catalog_with_reasons() -> None:
    value = plan()

    assert value.selections == tuple(sorted(value.selections, key=lambda item: item.skill))
    assert all(selection.reason for selection in value.selections)
    assert all(selection.purpose for selection in value.selections)
    assert all(selection.authority for selection in value.selections)
    assert DEVELOPMENT_USEFULNESS_GATE in value.acceptance_gates


def test_skill_orchestration_rejects_unknown_selected_skill() -> None:
    with pytest.raises(ValueError, match="unknown"):
        plan(selected_skills=("made-up-skill",))


def test_skill_orchestration_rejects_development_without_usefulness_gate() -> None:
    with pytest.raises(ValueError, match="usefulness gate"):
        plan(
            acceptance_gates=(
                "github_actions_green",
                "full_pytest_passes",
                "ruff_passes",
            )
        )


def test_skill_orchestration_rejects_development_without_system_benefit() -> None:
    with pytest.raises(ValueError, match="system_benefit"):
        plan(system_benefit="")


def test_skill_orchestration_rejects_selected_irrelevant_skill() -> None:
    with pytest.raises(ValueError, match="not relevant"):
        plan(selected_skills=("product-value-and-discovery-governor",))


def test_skill_orchestration_rejects_tampered_skill_authority() -> None:
    value = plan().to_dict()
    value["selections"][0]["authority"] = "competing_authority"
    value["plan_digest"] = digest_without(value, "plan_digest")

    with pytest.raises(ValueError, match="authority"):
        SkillOrchestrationPlan.from_dict(value)


def test_skill_orchestration_rejects_competing_selected_coordinator() -> None:
    value = plan()

    with pytest.raises(ValueError, match="role"):
        tuple(
            replace(item, role="coordinator")
            if item.skill == "quality-evidence-verifier"
            else item
            for item in value.selections
        )

def test_catalog_projection_is_exact_and_non_authorizing() -> None:
    projection = skill_catalog_projection()
    assert projection["schema"] == "vone.skill-catalog/v1"
    assert projection["source"] == "voodoo_product.skill_orchestration"
    assert projection["runtime_availability"] == "UNKNOWN"
    assert projection["primary_coordinator"] == PRIMARY_COORDINATOR
    assert projection["task_types"] == list(TASK_TYPES)
    rows = projection["skills"]
    assert [row["id"] for row in rows] == sorted({row["id"] for row in rows})
    for task_type in TASK_TYPES:
        expected = SkillOrchestrationPlan.create(
            task_id="synthetic-catalog", task_type=task_type,
            source_of_truth="test", objective="inspect", purpose="test",
            system_benefit="catalog parity", selected_skills=select_relevant_skills(task_type=task_type),
            excluded_operations=("execute",), acceptance_gates=(DEVELOPMENT_USEFULNESS_GATE,),
        )
        assert projection["selections"][task_type] == list(expected.selected_skills)
        assert [row["id"] for row in rows] == [item.skill for item in expected.selections]
        for row, item in zip(rows, expected.selections, strict=True):
            assert set(row) == {"id", "role", "purpose", "authority", "task_types"}
            assert (row["role"], row["purpose"], row["authority"]) == (
                item.role, item.purpose, item.authority,
            )
            assert (task_type in row["task_types"]) == item.selected
    rows[0]["purpose"] = "tampered"
    projection["selections"][TASK_TYPES[0]].clear()
    assert skill_catalog_projection()["skills"][0]["purpose"] != "tampered"
    assert skill_catalog_projection()["selections"][TASK_TYPES[0]]
