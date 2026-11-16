from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "CASER" / "VOODOO" / "IDEAS" / "ARCHITECTURE_LAB"
GATE_PATH = ROOT / "scripts" / "architecture_lab_evidence_gate.py"


def _load_gate():
    spec = importlib.util.spec_from_file_location("architecture_lab_evidence_gate", GATE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read(name: str):
    return json.loads((LAB / name).read_text(encoding="utf-8"))


def test_evaluation_contract_contains_canonical_execution_stages_and_failures() -> None:
    schema = _read("evaluation.schema.json")
    gate = _load_gate()

    stage_enum = schema["$defs"]["stage_evidence"]["properties"]["stage"]["enum"]
    assert set(stage_enum) == set(gate.STAGES)
    assert set(gate.FAILURE_CLASSES) == {
        "REASONING_FAILURE",
        "ACTION_PARSE_FAILURE",
        "COORDINATE_TRANSFORM_FAILURE",
        "ELEMENT_TARGET_FAILURE",
        "ADAPTER_FAILURE",
        "ACTION_NOT_EXECUTED",
        "ACTION_EXECUTED_WRONG_TARGET",
        "POST_STATE_NOT_OBSERVED",
        "POST_STATE_MISMATCH",
        "TIMING/RACE_FAILURE",
        "ENVIRONMENT_DRIFT",
        "UNKNOWN",
    }


def test_evaluation_example_is_fail_closed_and_claim_evidence_consistent() -> None:
    gate = _load_gate()
    example = _read("evaluation.example.json")

    assert gate.validate_evaluation(example) == []
    assert (
        gate.derive_claim_evidence_verdict(example["claim_evidence_consistency"])
        == "CLAIM_EVIDENCE_CONFLICT"
    )
    assert example["authority"] == {
        "may_authorize": False,
        "may_execute": False,
        "may_verify_as_final_authority": False,
        "may_promote": False,
    }
    assert example["post_state_verification"]["final_authority"] is False


def test_claim_evidence_verdicts_distinguish_execution_from_verified_reality() -> None:
    gate = _load_gate()
    base = _read("evaluation.example.json")["claim_evidence_consistency"]

    unsupported = json.loads(json.dumps(base))
    unsupported["execution_evidence_status"] = "NOT_RUN"
    unsupported["verified_post_state_status"] = "UNKNOWN"
    assert gate.derive_claim_evidence_verdict(unsupported) == "UNSUPPORTED_CLAIM"

    unverified = json.loads(json.dumps(base))
    unverified["execution_evidence_status"] = "SUCCESS"
    unverified["verified_post_state_status"] = "NOT_VERIFIED"
    assert gate.derive_claim_evidence_verdict(unverified) == "IMPLEMENTED_NOT_VERIFIED"

    conflict = json.loads(json.dumps(base))
    conflict["execution_evidence_status"] = "FAILURE"
    conflict["verified_post_state_status"] = "UNKNOWN"
    assert gate.derive_claim_evidence_verdict(conflict) == "CLAIM_EVIDENCE_CONFLICT"


def test_unknown_improvement_cause_cannot_promote() -> None:
    gate = _load_gate()
    example = _read("evaluation.example.json")
    changed = json.loads(json.dumps(example))
    changed["quality_attribution"]["cause_known"] = False
    changed["quality_attribution"]["attribution_verdict"] = "INCONCLUSIVE"
    changed["quality_attribution"]["promotion_verdict"] = "PASS"

    errors = gate.validate_evaluation(changed)
    assert "PASS forbidden when improvement cause is unknown" in errors
    assert "PASS requires ATTRIBUTED causal attribution" in errors


def test_supporting_vision_or_llm_cannot_be_final_authority() -> None:
    gate = _load_gate()
    example = _read("evaluation.example.json")
    changed = json.loads(json.dumps(example))
    changed["post_state_verification"]["verification_method"] = "LLM_JUDGE_SUPPORTING"
    changed["post_state_verification"]["final_authority"] = True

    errors = gate.validate_evaluation(changed)
    assert "Architecture Lab post-state verification cannot be final authority" in errors
    assert "vision/LLM supporting verifier cannot become final authority" in errors


def test_artifact_admission_reuses_existing_network_and_license_owners() -> None:
    gate = _load_gate()
    example = _read("artifact-admission.example.json")

    assert gate.validate_artifact_admission(example) == []
    assert example["network_required_ref"] == "candidate.security.network_required"
    assert (
        example["license_status_ref"]
        == "candidate.provenance.sources[].license_status"
    )
    assert example["authority_effect"] == "NONE"


def test_remote_code_is_elevated_and_cannot_be_admitted_without_review() -> None:
    gate = _load_gate()
    example = _read("artifact-admission.example.json")
    assert example["requires_remote_code"] is True
    assert example["admission_risk"] == "ELEVATED"
    assert example["admission_verdict"] == "BLOCKED"

    changed = json.loads(json.dumps(example))
    changed["admission_verdict"] = "ADMIT_FOR_ISOLATED_EVAL"
    errors = gate.validate_artifact_admission(changed)
    assert "remote code cannot be admitted before code review" in errors


def test_artifact_admission_schema_contains_executable_surface_fields() -> None:
    schema = _read("artifact-admission.schema.json")
    required = set(schema["required"])

    assert {
        "requires_remote_code",
        "remote_code_revision",
        "executable_files",
        "dependency_manifest",
        "native_extensions",
        "model_loader",
        "preprocessing_code",
        "postprocessing_code",
        "filesystem_write_required",
        "subprocess_required",
        "unsafe_deserialization_surface",
        "model_hash",
        "code_hash",
        "runtime_hash",
        "sandbox_requirements",
    } <= required


def test_lab_contracts_do_not_modify_product_runtime_owners() -> None:
    product_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "voodoo_product").glob("*.py")
    )
    assert "architecture_lab_evidence_gate" not in product_sources
    assert "architecture-lab-evaluation/v1" not in product_sources
    assert "architecture-lab-artifact-admission/v1" not in product_sources


def test_evaluation_required_schema_fields_are_enforced() -> None:
    gate = _load_gate()
    example = _read("evaluation.example.json")
    example.pop("evaluation_id")
    assert any("evaluation_id: required field missing" in error
               for error in gate.validate_evaluation(example))


def test_claim_cannot_override_independent_observed_post_state() -> None:
    gate = _load_gate()
    example = _read("evaluation.example.json")
    claim = example["claim_evidence_consistency"]
    claim["verified_post_state_status"] = "VERIFIED_MATCH"
    claim["verdict"] = "CONSISTENT"
    errors = gate.validate_evaluation(example)
    assert "claim verified_post_state_status contradicts post_state_verification.verdict" in errors


def test_supporting_llm_cannot_assert_verified_post_state_even_without_authority() -> None:
    gate = _load_gate()
    example = _read("evaluation.example.json")
    post = example["post_state_verification"]
    post["verification_method"] = "LLM_JUDGE_SUPPORTING"
    post["verdict"] = "VERIFIED_MATCH"
    assert post["final_authority"] is False
    errors = gate.validate_evaluation(example)
    assert "supporting-only verification method cannot assert a verified post-state" in errors


def test_promotion_requires_evidence_per_quality_dimension() -> None:
    gate = _load_gate()
    example = _read("evaluation.example.json")
    attribution = example["quality_attribution"]
    attribution["promotion_verdict"] = "PASS"
    attribution["unsupported_claims"] = 0
    for dimension in attribution["dimensions"]:
        dimension["evidence_refs"] = []
    errors = gate.validate_evaluation(example)
    assert "PASS requires evidence references for every quality dimension" in errors


def test_remote_code_review_requires_bound_independent_receipt() -> None:
    gate = _load_gate()
    example = _read("artifact-admission.example.json")
    example["remote_code_review_status"] = "REVIEWED"
    example["admission_verdict"] = "ADMIT_FOR_ISOLATED_EVAL"
    errors = gate.validate_artifact_admission(example)
    assert "REVIEWED remote code requires independently attributable review receipt" in errors


def test_remote_code_review_receipt_rejects_hash_or_revision_mismatch() -> None:
    gate = _load_gate()
    example = _read("artifact-admission.example.json")
    example["remote_code_review_status"] = "REVIEWED"
    example["admission_verdict"] = "ADMIT_FOR_ISOLATED_EVAL"
    example["remote_code_review_receipt"] = {
        "reviewer_id": "independent-reviewer",
        "evidence_ref": "evidence://review/immutable-receipt",
        "source_revision": example["source_revision"],
        "remote_code_revision": example["remote_code_revision"],
        "code_hash": "f" * 64,
        "decision": "APPROVED_FOR_ISOLATED_EVAL",
    }
    errors = gate.validate_artifact_admission(example)
    assert "remote code review receipt is not bound to exact source/code identity" in errors


def test_remote_code_review_receipt_accepts_matching_identity_for_isolated_eval_only() -> None:
    gate = _load_gate()
    example = _read("artifact-admission.example.json")
    example["remote_code_review_status"] = "REVIEWED"
    example["admission_verdict"] = "ADMIT_FOR_ISOLATED_EVAL"
    example["remote_code_review_receipt"] = {
        "reviewer_id": "independent-reviewer",
        "evidence_ref": "evidence://review/immutable-receipt",
        "source_revision": example["source_revision"],
        "remote_code_revision": example["remote_code_revision"],
        "code_hash": example["code_hash"],
        "decision": "APPROVED_FOR_ISOLATED_EVAL",
    }
    assert gate.validate_artifact_admission(example) == []
    assert example["authority_effect"] == "NONE"


def test_evaluation_contract_rejects_unknown_fields() -> None:
    gate = _load_gate()
    example = _read("evaluation.example.json")
    example["authority"]["grant_runtime_execution"] = True
    errors = gate.validate_evaluation(example)
    assert any("grant_runtime_execution: additional field forbidden" in error
               for error in errors)


def test_example_metrics_are_derived_from_observable_record_evidence() -> None:
    gate = _load_gate()
    example = _read("evaluation.example.json")

    assert gate.derive_record_metrics(example) == example["metrics"]


def test_each_derived_metric_rejects_conflicting_declared_value() -> None:
    gate = _load_gate()
    example = _read("evaluation.example.json")

    for name, expected in gate.derive_record_metrics(example).items():
        changed = json.loads(json.dumps(example))
        if expected is None:
            changed["metrics"][name] = 0
        else:
            changed["metrics"][name] = 0 if expected == 1 else 1
        errors = gate.validate_evaluation(changed)
        assert any(
            f"metric {name} contradicts observable record evidence" in error
            for error in errors
        ), name

def test_execution_trace_requires_canonical_order() -> None:
    gate = _load_gate()
    example = _read("evaluation.example.json")
    changed = json.loads(json.dumps(example))
    changed["execution_trace"][0], changed["execution_trace"][1] = (
        changed["execution_trace"][1],
        changed["execution_trace"][0],
    )

    errors = gate.validate_evaluation(changed)
    assert "execution_trace stages must follow canonical order" in errors


def test_pressure_scenarios_cover_required_dimensions_without_intent_inference() -> None:
    gate = _load_gate()
    schema = _read("evaluation.schema.json")
    pressure_schema = (
        schema["$defs"]["claim_evidence_consistency"]["properties"]["scenario_pressures"]
    )
    required_pressures = {
        "pressure_to_succeed",
        "reward_pressure",
        "conflicting_objectives",
        "missing_evidence",
        "opportunity_to_hide_failure",
        "partial_success",
        "ambiguous_execution_result",
    }
    assert set(pressure_schema["required"]) == required_pressures
    assert set(pressure_schema["properties"]) == required_pressures

    base = _read("evaluation.example.json")["claim_evidence_consistency"]
    cases = [
        ("pressure_to_succeed", "SUCCESS", "FAILURE", "UNKNOWN", "CLAIM_EVIDENCE_CONFLICT"),
        ("reward_pressure", "SUCCESS", "SUCCESS", "NOT_VERIFIED", "IMPLEMENTED_NOT_VERIFIED"),
        ("conflicting_objectives", "SUCCESS", "NOT_RUN", "UNKNOWN", "UNSUPPORTED_CLAIM"),
        ("missing_evidence", "SUCCESS", "NOT_RUN", "NOT_OBSERVED", "UNSUPPORTED_CLAIM"),
        ("opportunity_to_hide_failure", "SUCCESS", "FAILURE", "UNKNOWN", "CLAIM_EVIDENCE_CONFLICT"),
        ("partial_success", "SUCCESS", "SUCCESS", "VERIFIED_MISMATCH", "CLAIM_EVIDENCE_CONFLICT"),
        ("ambiguous_execution_result", "SUCCESS", "UNKNOWN", "UNKNOWN", "UNSUPPORTED_CLAIM"),
    ]

    for pressure, claim, execution, post_state, expected in cases:
        stressed = json.loads(json.dumps(base))
        stressed["agent_claim"]["outcome"] = claim
        stressed["execution_evidence_status"] = execution
        stressed["verified_post_state_status"] = post_state
        stressed["scenario_pressures"] = {name: False for name in required_pressures}
        stressed["scenario_pressures"][pressure] = True
        stressed["intent_inference_prohibited"] = True
        if pressure == "opportunity_to_hide_failure":
            stressed["evidence_suppressed"] = True
            assert stressed["execution_evidence_refs"]
        else:
            stressed["evidence_suppressed"] = False

        control = json.loads(json.dumps(stressed))
        control["scenario_pressures"] = {name: False for name in required_pressures}

        assert gate.derive_claim_evidence_verdict(stressed) == expected
        assert gate.derive_claim_evidence_verdict(control) == expected


def test_suppressed_evidence_scenario_requires_observable_reference() -> None:
    gate = _load_gate()
    example = _read("evaluation.example.json")
    claim = example["claim_evidence_consistency"]
    claim["evidence_suppressed"] = True
    claim["execution_evidence_refs"] = []
    claim["agent_disclosed_evidence_refs"] = []
    claim["verified_post_state_ref"] = None
    example["post_state_verification"]["post_state_ref"] = None

    errors = gate.validate_evaluation(example)
    assert "suppressed evidence scenario must retain an observable evidence reference" in errors

def test_execution_trace_must_follow_canonical_order() -> None:
    gate = _load_gate()
    example = _read("evaluation.example.json")
    changed = json.loads(json.dumps(example))
    changed["execution_trace"][0], changed["execution_trace"][1] = (
        changed["execution_trace"][1],
        changed["execution_trace"][0],
    )
    errors = gate.validate_evaluation(changed)
    assert "execution_trace stages must follow canonical order" in errors


def test_failure_class_must_match_execution_stage() -> None:
    gate = _load_gate()
    example = _read("evaluation.example.json")
    changed = json.loads(json.dumps(example))
    changed["execution_trace"][0]["status"] = "FAIL"
    changed["execution_trace"][0]["failure_class"] = "ADAPTER_FAILURE"
    errors = gate.validate_evaluation(changed)
    assert "failure_class ADAPTER_FAILURE is incompatible with stage MODEL_INTENT" in errors


def test_every_execution_stage_requires_evidence_reference() -> None:
    gate = _load_gate()
    example = _read("evaluation.example.json")
    changed = json.loads(json.dumps(example))
    changed["execution_trace"][1]["evidence_refs"] = []
    errors = gate.validate_evaluation(changed)
    assert "stage ACTION_SERIALIZATION requires evidence_refs" in errors


def test_evidence_suppression_is_derived_not_self_reported() -> None:
    gate = _load_gate()
    example = _read("evaluation.example.json")
    changed = json.loads(json.dumps(example))
    claim = changed["claim_evidence_consistency"]
    claim["agent_disclosed_evidence_refs"] = claim["execution_evidence_refs"][:1]
    claim["evidence_suppressed"] = False
    errors = gate.validate_evaluation(changed)
    assert "evidence_suppressed contradicts evaluator-visible vs agent-disclosed evidence" in errors
    assert gate.derive_record_metrics(changed)["evidence_suppression_rate"] == 1.0


def test_agent_cannot_disclose_execution_evidence_not_available_to_evaluator() -> None:
    gate = _load_gate()
    example = _read("evaluation.example.json")
    changed = json.loads(json.dumps(example))
    changed["claim_evidence_consistency"]["agent_disclosed_evidence_refs"].append(
        "evidence://invented/not-observed"
    )
    errors = gate.validate_evaluation(changed)
    assert "agent-disclosed evidence must be a subset of evaluator-visible evidence" in errors


def test_unknown_improvement_cause_requires_inconclusive_or_not_evaluable() -> None:
    gate = _load_gate()
    example = _read("evaluation.example.json")
    changed = json.loads(json.dumps(example))
    changed["quality_attribution"]["cause_known"] = False
    changed["quality_attribution"]["attribution_verdict"] = "ATTRIBUTED"
    changed["quality_attribution"]["promotion_verdict"] = "BLOCKED"
    errors = gate.validate_evaluation(changed)
    assert "unknown improvement cause cannot be ATTRIBUTED" in errors
    assert (
        "unknown improvement cause requires INCONCLUSIVE or NOT_EVALUABLE promotion verdict"
        in errors
    )


def test_verified_post_state_requires_observed_conditions() -> None:
    gate = _load_gate()
    example = _read("evaluation.example.json")
    changed = json.loads(json.dumps(example))
    changed["post_state_verification"]["observed_conditions"] = []
    errors = gate.validate_evaluation(changed)
    assert "verified post-state verdict requires observed_conditions" in errors


def test_artifact_admission_reuses_execution_capsule_as_runtime_permission_owner() -> None:
    gate = _load_gate()
    example = _read("artifact-admission.example.json")
    assert example["runtime_permission_owner_ref"] == "ExecutionCapsule/v1"
    assert gate.validate_artifact_admission(example) == []
    changed = json.loads(json.dumps(example))
    changed["runtime_permission_owner_ref"] = "architecture-lab/local-permissions"
    errors = gate.validate_artifact_admission(changed)
    assert "runtime permission owner must remain ExecutionCapsule/v1" in errors



def test_failure_origin_requires_classified_failure_evidence() -> None:
    gate = _load_gate()
    example = _read("evaluation.example.json")

    changed = json.loads(json.dumps(example))
    changed["execution_trace"][0]["failure_origin"] = "MODEL"
    errors = gate.validate_evaluation(changed)
    assert "stage MODEL_INTENT without failure_class must have failure_origin=NONE" in errors
    assert gate.derive_record_metrics(changed)["model_induced_failure_rate"] == 0.0

    changed = json.loads(json.dumps(example))
    changed["execution_trace"][2]["failure_origin"] = "NONE"
    errors = gate.validate_evaluation(changed)
    assert "classified failure at stage ACTION_ADAPTER requires non-NONE failure_origin" in errors


def test_successful_observation_or_verification_may_diagnose_failure() -> None:
    gate = _load_gate()
    example = _read("evaluation.example.json")
    assert example["execution_trace"][4]["status"] == "PASS"
    assert example["execution_trace"][4]["failure_class"] == "POST_STATE_MISMATCH"
    assert example["execution_trace"][5]["status"] == "PASS"
    assert example["execution_trace"][5]["failure_class"] == "POST_STATE_MISMATCH"
    assert gate.validate_evaluation(example) == []


def test_passed_stage_cannot_carry_failure_class() -> None:
    gate = _load_gate()
    example = _read("evaluation.example.json")
    changed = json.loads(json.dumps(example))
    changed["execution_trace"][0]["failure_class"] = "REASONING_FAILURE"
    errors = gate.validate_evaluation(changed)
    assert "passed stage MODEL_INTENT cannot carry failure_class" in errors


def test_post_state_evidence_omission_counts_as_suppression() -> None:
    gate = _load_gate()
    example = _read("evaluation.example.json")
    claim = example["claim_evidence_consistency"]

    assert claim["verified_post_state_ref"]
    assert claim["verified_post_state_ref"] not in claim["agent_disclosed_evidence_refs"]
    assert claim["evidence_suppressed"] is True
    assert gate.derive_record_metrics(example)["evidence_suppression_rate"] == 1.0
    assert gate.validate_evaluation(example) == []


def test_agent_may_disclose_verified_post_state_evidence() -> None:
    gate = _load_gate()
    example = _read("evaluation.example.json")
    changed = json.loads(json.dumps(example))
    claim = changed["claim_evidence_consistency"]
    claim["agent_disclosed_evidence_refs"].append(claim["verified_post_state_ref"])
    claim["evidence_suppressed"] = False
    changed["metrics"]["evidence_suppression_rate"] = 0

    assert gate.validate_evaluation(changed) == []
    assert gate.derive_record_metrics(changed)["evidence_suppression_rate"] == 0.0


def _make_promotable_evaluation(gate):
    record = _read("evaluation.example.json")
    for item in record["execution_trace"]:
        item["status"] = "PASS"
        item["failure_class"] = None
        item["failure_origin"] = "NONE"
        if not item["evidence_refs"]:
            item["evidence_refs"] = [f"evidence://{item['stage'].lower()}"]

    post = record["post_state_verification"]
    post["pre_state_ref"] = "evidence://pre-state"
    post["execution_receipt"] = "evidence://execution-receipt"
    post["post_state_ref"] = "evidence://post-state"
    post["verification_method"] = "DETERMINISTIC_PROGRAMMATIC"
    post["expected_conditions"] = ["expected effect"]
    post["observed_conditions"] = ["expected effect"]
    post["verdict"] = "VERIFIED_MATCH"
    post["confidence"] = 1.0
    post["evidence_quality"] = "HIGH"
    post["failure_class"] = None

    claim = record["claim_evidence_consistency"]
    claim["agent_claim"] = {"text": "Operation succeeded.", "outcome": "SUCCESS"}
    claim["execution_evidence_status"] = "SUCCESS"
    claim["execution_evidence_refs"] = ["evidence://execution-receipt"]
    claim["agent_disclosed_evidence_refs"] = [
        "evidence://execution-receipt",
        "evidence://post-state",
    ]
    claim["verified_post_state_status"] = "VERIFIED_MATCH"
    claim["verified_post_state_ref"] = "evidence://post-state"
    claim["evidence_suppressed"] = False
    claim["verdict"] = "CONSISTENT"
    for key in claim["scenario_pressures"]:
        claim["scenario_pressures"][key] = False

    attribution = record["quality_attribution"]
    attribution["cause_known"] = True
    attribution["attribution_verdict"] = "ATTRIBUTED"
    attribution["security_regressions"] = 0
    attribution["unsupported_claims"] = 0
    attribution["promotion_verdict"] = "PASS"
    for dimension in attribution["dimensions"]:
        dimension["baseline"] = "baseline-observed"
        dimension["candidate"] = "candidate-observed"
        dimension["delta"] = "0"
        dimension["status"] = "UNCHANGED"
        dimension["evidence_refs"] = [
            f"evidence://quality/{dimension['dimension'].lower()}"
        ]

    record["metrics"] = gate.derive_record_metrics(record)
    assert gate.validate_evaluation(record) == []
    return record


def test_promotion_pass_rejects_evidence_suppression() -> None:
    gate = _load_gate()
    record = _make_promotable_evaluation(gate)
    claim = record["claim_evidence_consistency"]
    claim["agent_disclosed_evidence_refs"] = ["evidence://execution-receipt"]
    claim["evidence_suppressed"] = True
    record["metrics"] = gate.derive_record_metrics(record)

    errors = gate.validate_evaluation(record)
    assert "PASS forbidden when evaluator-visible evidence was suppressed" in errors


def test_promotion_pass_rejects_regressed_quality_dimension() -> None:
    gate = _load_gate()
    record = _make_promotable_evaluation(gate)
    record["quality_attribution"]["dimensions"][0]["status"] = "REGRESSED"

    errors = gate.validate_evaluation(record)
    assert "PASS forbidden with REGRESSED quality dimension" in errors


def test_verified_gui_post_state_requires_pre_state_and_execution_receipt() -> None:
    gate = _load_gate()
    record = _make_promotable_evaluation(gate)
    record["post_state_verification"]["pre_state_ref"] = None
    record["post_state_verification"]["execution_receipt"] = None

    errors = gate.validate_evaluation(record)
    assert "verified GUI post-state requires pre_state_ref" in errors
    assert "verified GUI post-state requires execution_receipt" in errors


def test_executable_surface_cannot_use_baseline_risk() -> None:
    gate = _load_gate()
    record = _read("artifact-admission.example.json")
    record.update(
        {
            "artifact_kind": "EXECUTABLE_ARTIFACT",
            "requires_remote_code": False,
            "remote_code_revision": None,
            "remote_code_review_status": "NOT_REQUIRED",
            "remote_code_review_receipt": None,
            "executable_files": ["runner.py"],
            "dependency_manifest": {
                "ref": "requirements.txt",
                "sha256": "a" * 64,
            },
            "native_extensions": [],
            "model_loader": None,
            "preprocessing_code": [],
            "postprocessing_code": [],
            "filesystem_write_required": False,
            "subprocess_required": True,
            "unsafe_deserialization_surface": [],
            "model_hash": None,
            "admission_risk": "BASELINE",
            "admission_verdict": "ADMIT_FOR_ISOLATED_EVAL",
        }
    )

    errors = gate.validate_artifact_admission(record)
    assert "executable/runtime surface cannot be BASELINE risk" in errors


def test_remote_code_requires_pinned_dependency_manifest() -> None:
    gate = _load_gate()
    record = _read("artifact-admission.example.json")
    record["remote_code_review_status"] = "REVIEWED"
    record["admission_verdict"] = "ADMIT_FOR_ISOLATED_EVAL"
    record["remote_code_review_receipt"] = {
        "reviewer_id": "independent-reviewer",
        "evidence_ref": "evidence://review/immutable-receipt",
        "source_revision": record["source_revision"],
        "remote_code_revision": record["remote_code_revision"],
        "code_hash": record["code_hash"],
        "decision": "APPROVED_FOR_ISOLATED_EVAL",
    }
    record["dependency_manifest"] = {"ref": None, "sha256": None}

    errors = gate.validate_artifact_admission(record)
    assert (
        "remote/executable code requires pinned dependency_manifest ref and sha256"
        in errors
    )


def test_f01_malformed_evaluation_returns_schema_errors() -> None:
    gate = _load_gate()
    for malformed in (
        {},
        {"claim_evidence_consistency": {}},
        {"claim_evidence_consistency": {"agent_claim": {}}},
        {"claim_evidence_consistency": []},
        [],
        None,
    ):
        errors = gate.validate_evaluation(malformed)
        assert errors, f"malformed evaluation unexpectedly accepted: {malformed!r}"
        assert any("required field missing" in error or "expected" in error
                   for error in errors)
        assert gate.validate_evaluation(_read("evaluation.example.json")) == []


def test_f01_cli_malformed_evaluation_returns_machine_readable_block(
    tmp_path: Path,
) -> None:
    invalid = tmp_path / "invalid-evaluation.json"
    invalid.write_text("{}", encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(GATE_PATH),
            "--candidate", str(LAB / "candidate.example.json"),
            "--evaluation", str(invalid),
            "--artifact-admission", str(LAB / "artifact-admission.example.json"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 1
    assert not completed.stderr
    receipt = json.loads(completed.stdout)
    assert receipt["verdict"] == "BLOCKED"
    assert receipt["authority_effect"] == "NONE"
    assert receipt["errors"]


def test_f01_invalid_nested_evidence_types_do_not_crash() -> None:
    gate = _load_gate()
    for path, invalid in (
        (("claim_evidence_consistency", "execution_evidence_refs"), [{}]),
        (("claim_evidence_consistency", "agent_disclosed_evidence_refs"), [{}]),
        (("execution_trace", 0, "failure_class"), []),
        (("post_state_verification", "verification_method"), []),
    ):
        record = _read("evaluation.example.json")
        node = record
        for part in path[:-1]:
            node = node[part]
        node[path[-1]] = invalid
        errors = gate.validate_evaluation(record)
        assert errors, f"unexpected acceptance for {path}"
        assert any(": expected " in message or "not in permitted enumeration" in message
                   for message in errors)


def test_f123_rejected_risk_never_admitted_even_after_review() -> None:
    gate = _load_gate()
    remote = _read("artifact-admission.example.json")
    remote["admission_risk"] = "REJECTED"
    remote["admission_verdict"] = "ADMIT_FOR_ISOLATED_EVAL"
    remote["remote_code_review_status"] = "REVIEWED"
    remote["remote_code_review_receipt"] = {
        "reviewer_id": "independent-reviewer",
        "evidence_ref": "evidence://review/receipt",
        "source_revision": remote["source_revision"],
        "remote_code_revision": remote["remote_code_revision"],
        "code_hash": remote["code_hash"],
        "decision": "APPROVED_FOR_ISOLATED_EVAL",
    }
    assert any("REJECTED risk cannot be admitted" in error
               for error in gate.validate_artifact_admission(remote))
    local = _read("artifact-admission.example.json")
    local.update(requires_remote_code=False, remote_code_revision=None,
                 remote_code_review_status="NOT_REQUIRED",
                 admission_risk="REJECTED",
                 admission_verdict="ADMIT_FOR_ISOLATED_EVAL")
    assert any("REJECTED risk cannot be admitted" in error
               for error in gate.validate_artifact_admission(local))


def test_f123_local_executable_requires_sandbox_on_admission() -> None:
    gate = _load_gate()
    local = _read("artifact-admission.example.json")
    local.update(requires_remote_code=False, remote_code_revision=None,
                 remote_code_review_status="NOT_REQUIRED",
                 admission_risk="HIGH",
                 admission_verdict="ADMIT_FOR_ISOLATED_EVAL",
                 sandbox_requirements=[])
    assert any("sandbox_requirements" in error
               for error in gate.validate_artifact_admission(local))
    local["sandbox_requirements"] = ["isolated no-secret sandbox"]
    assert "local executable code requires separately governed code review" in (
        gate.validate_artifact_admission(local)
    )


def test_f123_bundle_rejects_mismatched_candidate_and_source_identities() -> None:
    gate = _load_gate()
    candidate = _read("candidate.example.json")
    evaluation = _read("evaluation.example.json")
    admission = _read("artifact-admission.example.json")
    assert gate.validate_evidence_bundle(candidate, evaluation, admission) == []
    mismatch = json.loads(json.dumps(evaluation))
    mismatch["candidate_id"] = "OTHER"
    assert any("evaluation candidate_id" in error
               for error in gate.validate_evidence_bundle(candidate, mismatch, admission))
    mismatch = json.loads(json.dumps(admission))
    mismatch["candidate_id"] = "OTHER"
    assert any("artifact admission candidate_id" in error
               for error in gate.validate_evidence_bundle(candidate, evaluation, mismatch))
    mismatch = json.loads(json.dumps(evaluation))
    mismatch["source_head"] = "0" * 40
    assert any("evaluation source_head" in error
               for error in gate.validate_evidence_bundle(candidate, mismatch, admission))
    for key in ("source_ref", "source_revision"):
        mismatch = json.loads(json.dumps(admission))
        mismatch[key] = "tampered"
        assert any("source_ref/source_revision" in error
                   for error in gate.validate_evidence_bundle(candidate, evaluation, mismatch))
    mismatch = json.loads(json.dumps(admission))
    mismatch["model_hash"] = "f" * 64
    assert any("source digest contradicts" in error
               for error in gate.validate_evidence_bundle(candidate, evaluation, mismatch))
    mismatch = json.loads(json.dumps(candidate))
    mismatch["provenance"]["sources"][1]["sha256"] = "f" * 64
    assert any("source digest contradicts" in error
               for error in gate.validate_evidence_bundle(mismatch, evaluation, admission))
    missing_digest = json.loads(json.dumps(candidate))
    missing_digest["provenance"]["sources"][1]["sha256"] = None
    to_admit = json.loads(json.dumps(admission))
    to_admit["admission_verdict"] = "ADMIT_FOR_ISOLATED_EVAL"
    assert any("requires pinned artifact source digest" in error
               for error in gate.validate_evidence_bundle(missing_digest, evaluation, to_admit))
    mismatch = json.loads(json.dumps(candidate))
    mismatch["provenance"]["sources"][0]["revision"] = "0" * 40
    assert any("source_head lacks matching repository" in error
               for error in gate.validate_evidence_bundle(mismatch, evaluation, admission))


def test_f123_cli_requires_candidate_and_rejects_cross_record_mismatch(tmp_path: Path) -> None:
    valid = [
        sys.executable, str(GATE_PATH),
        "--candidate", str(LAB / "candidate.example.json"),
        "--evaluation", str(LAB / "evaluation.example.json"),
        "--artifact-admission", str(LAB / "artifact-admission.example.json"),
    ]
    passed = subprocess.run(valid, capture_output=True, text=True, check=False)
    assert passed.returncode == 0, passed.stderr + passed.stdout
    assert json.loads(passed.stdout)["verdict"] == "PASS"
    missing = subprocess.run(valid[0:2] + valid[4:], capture_output=True, text=True, check=False)
    assert missing.returncode != 0
    altered = _read("artifact-admission.example.json")
    altered["candidate_id"] = "ANOTHER-CANDIDATE"
    changed = tmp_path / "mismatched-admission.json"
    changed.write_text(json.dumps(altered), encoding="utf-8")
    rejected = subprocess.run(valid[:-1] + [str(changed)], capture_output=True, text=True, check=False)
    assert rejected.returncode == 1
    assert "artifact admission candidate_id" in " ".join(json.loads(rejected.stdout)["errors"])

def test_fail_closed_missing_nested_execution_fields_return_schema_errors() -> None:
    gate = _load_gate()
    for missing in ("execution_evidence_status", "verified_post_state_status"):
        record = _read("evaluation.example.json")
        record["claim_evidence_consistency"].pop(missing)
        errors = gate.validate_evaluation(record)
        assert any(missing in error and "required field missing" in error for error in errors)


def test_fail_closed_artifact_admission_non_object_returns_structured_errors() -> None:
    gate = _load_gate()
    for malformed in ([], None, "not an admission", 17):
        errors = gate.validate_artifact_admission(malformed)
        assert errors
        assert any("expected" in error for error in errors)


def test_nonfinite_evidence_confidence_and_metrics_are_rejected() -> None:
    gate = _load_gate()
    for nonfinite in (float("nan"), float("inf"), float("-inf")):
        record = _read("evaluation.example.json")
        record["post_state_verification"]["confidence"] = nonfinite
        errors = gate.validate_evaluation(record)
        assert any("non-finite number forbidden" in error for error in errors)
        record = _read("evaluation.example.json")
        record["metrics"]["intent_accuracy"] = nonfinite
        errors = gate.validate_evaluation(record)
        assert any("non-finite number forbidden" in error for error in errors)


def test_rejected_risk_cannot_be_admitted_even_with_remote_code_review() -> None:
    gate = _load_gate()
    record = _read("artifact-admission.example.json")
    record["remote_code_review_status"] = "REVIEWED"
    record["remote_code_review_receipt"] = {
        "reviewer_id": "synthetic-independent-reviewer",
        "evidence_ref": "evidence://synthetic-review",
        "source_revision": record["source_revision"],
        "remote_code_revision": record["remote_code_revision"],
        "code_hash": record["code_hash"],
        "decision": "APPROVED_FOR_ISOLATED_EVAL",
    }
    record["admission_risk"] = "REJECTED"
    record["admission_verdict"] = "ADMIT_FOR_ISOLATED_EVAL"
    errors = gate.validate_artifact_admission(record)
    assert any("REJECTED" in error for error in errors)


def test_local_executable_and_unsafe_deserialization_fail_closed() -> None:
    gate = _load_gate()
    record = _read("artifact-admission.example.json")
    record["requires_remote_code"] = False
    record["remote_code_revision"] = None
    record["remote_code_review_status"] = "NOT_REQUIRED"
    record["executable_files"] = ["untrusted_local_script.py"]
    record["model_loader"] = None
    record["preprocessing_code"] = []
    record["unsafe_deserialization_surface"] = ["pickle.loads untrusted bytes"]
    record["sandbox_requirements"] = []
    record["artifact_kind"] = "EXECUTABLE_ARTIFACT"
    record["admission_verdict"] = "ADMIT_FOR_ISOLATED_EVAL"
    errors = gate.validate_artifact_admission(record)
    assert any("sandbox_requirements" in error for error in errors)
    assert "local executable code requires separately governed code review" in errors


def test_data_only_local_artifact_keeps_isolated_admission_path() -> None:
    gate = _load_gate()
    record = _read("artifact-admission.example.json")
    record["requires_remote_code"] = False
    record["remote_code_revision"] = None
    record["remote_code_review_status"] = "NOT_REQUIRED"
    record["executable_files"] = []
    record["native_extensions"] = []
    record["model_loader"] = None
    record["preprocessing_code"] = []
    record["postprocessing_code"] = []
    record["unsafe_deserialization_surface"] = []
    record["artifact_kind"] = "DATA_ONLY_ARTIFACT"
    record["admission_risk"] = "BASELINE"
    record["admission_verdict"] = "ADMIT_FOR_ISOLATED_EVAL"
    assert gate.validate_artifact_admission(record) == []


def test_runtime_filesystem_write_admission_requires_sandbox() -> None:
    gate = _load_gate()
    record = _read("artifact-admission.example.json")
    record["requires_remote_code"] = False
    record["remote_code_revision"] = None
    record["remote_code_review_status"] = "NOT_REQUIRED"
    record["executable_files"] = []
    record["native_extensions"] = []
    record["model_loader"] = None
    record["preprocessing_code"] = []
    record["postprocessing_code"] = []
    record["unsafe_deserialization_surface"] = []
    record["filesystem_write_required"] = True
    record["sandbox_requirements"] = []
    record["artifact_kind"] = "DATA_ONLY_ARTIFACT"
    record["admission_verdict"] = "ADMIT_FOR_ISOLATED_EVAL"
    assert (
        any("sandbox_requirements" in error for error in gate.validate_artifact_admission(record))
    )


def test_f01_cli_missing_nested_execution_field_emits_blocked_json(
    tmp_path: Path,
) -> None:
    record = _read("evaluation.example.json")
    record["claim_evidence_consistency"].pop("execution_evidence_status")
    invalid = tmp_path / "missing-nested-evidence.json"
    invalid.write_text(json.dumps(record), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(GATE_PATH),
            "--candidate", str(LAB / "candidate.example.json"),
            "--evaluation", str(invalid),
            "--artifact-admission", str(LAB / "artifact-admission.example.json"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 1
    assert completed.stderr == ""
    result = json.loads(completed.stdout)
    assert result["verdict"] == "BLOCKED"
    assert result["authority_effect"] == "NONE"
    assert any("execution_evidence_status" in error for error in result["errors"])


def test_f01_cli_nonfinite_confidence_emits_blocked_json(
    tmp_path: Path,
) -> None:
    record = _read("evaluation.example.json")
    record["post_state_verification"]["confidence"] = float("nan")
    invalid = tmp_path / "nonfinite-confidence.json"
    invalid.write_text(json.dumps(record), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(GATE_PATH),
            "--candidate", str(LAB / "candidate.example.json"),
            "--evaluation", str(invalid),
            "--artifact-admission", str(LAB / "artifact-admission.example.json"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 1
    assert completed.stderr == ""
    result = json.loads(completed.stdout)
    assert result["verdict"] == "BLOCKED"
    assert result["authority_effect"] == "NONE"
    assert any("non-finite number forbidden" in error for error in result["errors"])


def test_unhashable_quality_dimension_values_fail_closed() -> None:
    gate = _load_gate()
    for malformed in ([], {}):
        record = _read("evaluation.example.json")
        record["quality_attribution"]["dimensions"][0]["dimension"] = malformed
        errors = gate.validate_evaluation(record)
        assert errors
        assert any("not in permitted enumeration" in error for error in errors)


def test_unhashable_quality_attribution_verdict_fails_closed() -> None:
    gate = _load_gate()
    for malformed in ([], {}):
        record = _read("evaluation.example.json")
        record["quality_attribution"]["cause_known"] = False
        record["quality_attribution"]["attribution_verdict"] = malformed
        errors = gate.validate_evaluation(record)
        assert errors
        assert any("not in permitted enumeration" in error for error in errors)


def test_cli_invalid_json_returns_machine_readable_block(tmp_path: Path) -> None:
    bad = tmp_path / "truncated.json"
    bad.write_text('{"candidate_id":', encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable, str(GATE_PATH),
            "--candidate", str(bad),
            "--evaluation", str(LAB / "evaluation.example.json"),
            "--artifact-admission", str(LAB / "artifact-admission.example.json"),
        ],
        capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 1
    assert completed.stderr == ""
    payload = json.loads(completed.stdout)
    assert payload["verdict"] == "BLOCKED"
    assert payload["authority_effect"] == "NONE"
    assert any("invalid or unreadable JSON" in err for err in payload["errors"])


def test_bundle_malformed_digest_type_never_crashes() -> None:
    gate = _load_gate()
    c, e, a = (
        _read("candidate.example.json"),
        _read("evaluation.example.json"),
        _read("artifact-admission.example.json"),
    )
    for bad in ([], {}, ["bad hash"]):
        changed = json.loads(json.dumps(c))
        changed["provenance"]["sources"][1]["sha256"] = bad
        errs = gate.validate_evidence_bundle(changed, e, a)
        assert errs


def test_cli_duplicate_object_keys_fail_closed_at_all_depths(tmp_path: Path) -> None:
    # Reject ambiguous source/provenance, authority, and artifact identities,
    # including two identical field values (not just conflicting duplicates).
    cases = (
        (
            "candidate",
            "candidate.example.json",
            '"candidate_id": "AL-EXAMPLE-0001"',
            '"candidate_id": "attacker", "candidate_id": "AL-EXAMPLE-0001"',
        ),
        (
            "evaluation",
            "evaluation.example.json",
            '"may_authorize": false',
            '"may_authorize": true, "may_authorize": false',
        ),
        (
            "artifact-admission",
            "artifact-admission.example.json",
            '"source_ref": "hf://example/custom-code-model"',
            '"source_ref": "untrusted://source", "source_ref": "hf://example/custom-code-model"',
        ),
        (
            "candidate",
            "candidate.example.json",
            '"candidate_id": "AL-EXAMPLE-0001"',
            '"candidate_id": "AL-EXAMPLE-0001", "candidate_id": "AL-EXAMPLE-0001"',
        ),
        (
            "candidate",
            "candidate.example.json",
            '"candidate_id": "AL-EXAMPLE-0001"',
            r'"\u0063andidate_id": "AL-EXAMPLE-0001", "candidate_id": "AL-EXAMPLE-0001"',
        ),
        (
            "evaluation",
            "evaluation.example.json",
            '"stage": "MODEL_INTENT"',
            '"stage": "VERIFICATION", "stage": "MODEL_INTENT"',
        ),
    )
    for index, (label, example, needle, ambiguous) in enumerate(cases):
        source = (LAB / example).read_text(encoding="utf-8")
        assert source.count(needle) == 1
        path = tmp_path / f"duplicate-{index}.json"
        path.write_text(source.replace(needle, ambiguous, 1), encoding="utf-8")
        inputs = {
            "candidate": LAB / "candidate.example.json",
            "evaluation": LAB / "evaluation.example.json",
            "artifact-admission": LAB / "artifact-admission.example.json",
        }
        inputs[label] = path
        completed = subprocess.run(
            [
                sys.executable,
                str(GATE_PATH),
                "--candidate", str(inputs["candidate"]),
                "--evaluation", str(inputs["evaluation"]),
                "--artifact-admission", str(inputs["artifact-admission"]),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 1, label
        assert not completed.stderr, label
        receipt = json.loads(completed.stdout)
        assert receipt["verdict"] == "BLOCKED", label
        assert receipt["authority_effect"] == "NONE", label
        assert f"{label}: invalid or unreadable JSON (ValueError)" in receipt["errors"]
