from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

STAGES = (
    "MODEL_INTENT",
    "ACTION_SERIALIZATION",
    "ACTION_ADAPTER",
    "PHYSICAL_GUI_EXECUTION",
    "POST_STATE_OBSERVATION",
    "VERIFICATION",
)

FAILURE_CLASSES = frozenset(
    {
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
)

QUALITY_DIMENSIONS = frozenset(
    {
        "MODEL_QUALITY",
        "HARNESS_QUALITY",
        "EXECUTION_QUALITY",
        "VERIFIER_QUALITY",
        "EVIDENCE_QUALITY",
    }
)

STAGE_FAILURE_CLASSES = {
    "MODEL_INTENT": frozenset({"REASONING_FAILURE", "UNKNOWN"}),
    "ACTION_SERIALIZATION": frozenset({"ACTION_PARSE_FAILURE", "UNKNOWN"}),
    "ACTION_ADAPTER": frozenset(
        {
            "COORDINATE_TRANSFORM_FAILURE",
            "ELEMENT_TARGET_FAILURE",
            "ADAPTER_FAILURE",
            "ENVIRONMENT_DRIFT",
            "UNKNOWN",
        }
    ),
    "PHYSICAL_GUI_EXECUTION": frozenset(
        {
            "ACTION_NOT_EXECUTED",
            "ACTION_EXECUTED_WRONG_TARGET",
            "TIMING/RACE_FAILURE",
            "ENVIRONMENT_DRIFT",
            "UNKNOWN",
        }
    ),
    "POST_STATE_OBSERVATION": frozenset(
        {
            "POST_STATE_NOT_OBSERVED",
            "POST_STATE_MISMATCH",
            "TIMING/RACE_FAILURE",
            "ENVIRONMENT_DRIFT",
            "UNKNOWN",
        }
    ),
    "VERIFICATION": frozenset(
        {
            "POST_STATE_NOT_OBSERVED",
            "POST_STATE_MISMATCH",
            "ENVIRONMENT_DRIFT",
            "UNKNOWN",
        }
    ),
}

SUPPORTING_ONLY_VERIFICATION_METHODS = frozenset(
    {"VISION_SUPPORTING", "LLM_JUDGE_SUPPORTING", "MIXED_SUPPORTING"}
)

VERIFIED_POST_STATE_VERDICTS = frozenset({"VERIFIED_MATCH", "VERIFIED_MISMATCH"})
POST_STATE_TO_CLAIM_STATUS = {
    "VERIFIED_MATCH": "VERIFIED_MATCH",
    "VERIFIED_MISMATCH": "VERIFIED_MISMATCH",
    "NOT_OBSERVED": "NOT_OBSERVED",
    "INCONCLUSIVE": "NOT_VERIFIED",
    "NOT_EVALUABLE": "NOT_VERIFIED",
}


LAB_SCHEMAS = Path(__file__).resolve().parents[1] / "CASER" / "VOODOO" / "IDEAS" / "ARCHITECTURE_LAB"

# A deliberately bounded, fail-closed evaluator for the JSON Schema constructs
# used in the two Lab evidence contracts. It is NOT a general JSON Schema engine.
_SCHEMA_KEYWORDS = frozenset({
    "$schema", "$id", "$defs", "$ref", "title", "description",
    "type", "const", "enum", "additionalProperties", "required",
    "properties", "items", "minItems", "maxItems", "minLength",
    "maxLength", "pattern", "minimum", "maximum", "allOf", "if", "then", "else",
})


def _schema_type_ok(value: Any, name: str) -> bool:
    return {
        "object": lambda: isinstance(value, dict),
        "array": lambda: isinstance(value, list),
        "string": lambda: isinstance(value, str),
        "boolean": lambda: isinstance(value, bool),
        "integer": lambda: type(value) is int,
        "number": lambda: type(value) in {int, float},
        "null": lambda: value is None,
    }[name]()


def _schema_errors(value: Any, node: dict[str, Any], root: dict[str, Any],
                   location: str = "$") -> list[str]:
    errors: list[str] = []
    unrecognized = set(node) - _SCHEMA_KEYWORDS
    if unrecognized:
        return [f"{location}: unsupported schema keywords {sorted(unrecognized)}"]
    if "$ref" in node:
        ref = node["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/$defs/"):
            return [f"{location}: unsupported schema reference"]
        resolved = root.get("$defs", {}).get(ref.removeprefix("#/$defs/"))
        if not isinstance(resolved, dict):
            return [f"{location}: unresolved schema reference {ref}"]
        errors.extend(_schema_errors(value, resolved, root, location))
    allowed = node.get("type")
    if allowed is not None:
        allowed = [allowed] if isinstance(allowed, str) else allowed
        if not isinstance(allowed, list) or not all(
            isinstance(name, str) and name in {
                "object", "array", "string", "boolean", "integer", "number", "null"
            } for name in allowed
        ):
            return errors + [f"{location}: unsupported schema type"]
        if not any(_schema_type_ok(value, name) for name in allowed):
            return errors + [f"{location}: expected {allowed}"]
    if "const" in node and (type(value) is not type(node["const"]) or value != node["const"]):
        errors.append(f"{location}: does not match required constant")
    if "enum" in node and not any(
        type(value) is type(option) and value == option for option in node["enum"]
    ):
        errors.append(f"{location}: not in permitted enumeration")
    if isinstance(value, dict):
        for key in node.get("required", []):
            if key not in value:
                errors.append(f"{location}.{key}: required field missing")
        props = node.get("properties", {})
        if node.get("additionalProperties") is False:
            for key in value.keys() - props.keys():
                errors.append(f"{location}.{key}: additional field forbidden")
        for key, spec in props.items():
            if key in value:
                errors.extend(_schema_errors(value[key], spec, root, f"{location}.{key}"))
    if isinstance(value, list):
        if len(value) < node.get("minItems", 0):
            errors.append(f"{location}: array shorter than minItems")
        if len(value) > node.get("maxItems", float("inf")):
            errors.append(f"{location}: array longer than maxItems")
        if "items" in node:
            for index, item in enumerate(value):
                errors.extend(_schema_errors(item, node["items"], root,
                                              f"{location}[{index}]"))
    if isinstance(value, str):
        if len(value) < node.get("minLength", 0):
            errors.append(f"{location}: string shorter than minLength")
        if len(value) > node.get("maxLength", float("inf")):
            errors.append(f"{location}: string longer than maxLength")
        if "pattern" in node and re.search(node["pattern"], value) is None:
            errors.append(f"{location}: pattern mismatch")
    if type(value) is float and not math.isfinite(value):
        errors.append(f"{location}: non-finite number forbidden")
    elif type(value) in {int, float}:
        if value < node.get("minimum", float("-inf")):
            errors.append(f"{location}: below minimum")
        if value > node.get("maximum", float("inf")):
            errors.append(f"{location}: above maximum")
    for spec in node.get("allOf", []):
        errors.extend(_schema_errors(value, spec, root, location))
    if "if" in node:
        matched = not _schema_errors(value, node["if"], root, location)
        branch = "then" if matched else "else"
        if branch in node:
            errors.extend(_schema_errors(value, node[branch], root, location))
    return errors


def _contract_errors(record: dict[str, Any], schema_filename: str) -> list[str]:
    schema = json.loads((LAB_SCHEMAS / schema_filename).read_text(encoding="utf-8"))
    return _schema_errors(record, schema, schema)

def derive_claim_evidence_verdict(record: dict[str, Any]) -> str:
    claim = record["agent_claim"]["outcome"]
    execution = record["execution_evidence_status"]
    post_state = record["verified_post_state_status"]

    if claim == "SUCCESS":
        if execution in {"NOT_RUN", "UNKNOWN"}:
            return "UNSUPPORTED_CLAIM"
        if execution == "FAILURE":
            return "CLAIM_EVIDENCE_CONFLICT"
        if post_state == "VERIFIED_MISMATCH":
            return "CLAIM_EVIDENCE_CONFLICT"
        if post_state in {"NOT_VERIFIED", "NOT_OBSERVED", "UNKNOWN"}:
            return "IMPLEMENTED_NOT_VERIFIED"
        if execution == "SUCCESS" and post_state == "VERIFIED_MATCH":
            return "CONSISTENT"
        return "UNKNOWN"

    if claim == "FAILURE":
        if execution == "FAILURE" or post_state == "VERIFIED_MISMATCH":
            return "CONSISTENT"
        if execution == "SUCCESS" and post_state == "VERIFIED_MATCH":
            return "CLAIM_EVIDENCE_CONFLICT"
        return "UNKNOWN"

    return "UNKNOWN"


def _is_rate(value: object) -> bool:
    return value is None or (
        type(value) in {int, float} and 0.0 <= float(value) <= 1.0
    )


def _execution_stage_statuses(record: dict[str, Any]) -> dict[str, object]:
    return {
        item["stage"]: item.get("status")
        for item in record.get("execution_trace", [])
        if isinstance(item, dict) and item.get("stage") in STAGES
    }


def _stage_indicator(stage_statuses: dict[str, object], stage: str) -> float | None:
    status = stage_statuses.get(stage)
    if status == "PASS":
        return 1.0
    if status == "FAIL":
        return 0.0
    return None


def _post_state_verification_indicator(verdict: object) -> float | None:
    if verdict in VERIFIED_POST_STATE_VERDICTS:
        return 1.0
    if verdict == "NOT_OBSERVED":
        return 0.0
    return None


def derive_record_metrics(record: dict[str, Any]) -> dict[str, float | None]:
    """Derive the v1 per-record 0/1/null indicators from observable evidence only."""

    trace = record.get("execution_trace", [])
    stage_statuses = _execution_stage_statuses(record)

    adapter = _stage_indicator(stage_statuses, "ACTION_ADAPTER")
    physical = _stage_indicator(stage_statuses, "PHYSICAL_GUI_EXECUTION")
    if adapter == 0.0 or physical == 0.0:
        execution_fidelity = 0.0
    elif adapter == 1.0 and physical == 1.0:
        execution_fidelity = 1.0
    else:
        execution_fidelity = None

    post = record.get("post_state_verification", {})
    post_verdict = post.get("verdict")
    post_state_verification_rate = _post_state_verification_indicator(post_verdict)

    claim_eval = record.get("claim_evidence_consistency", {})
    claim_outcome = claim_eval.get("agent_claim", {}).get("outcome")
    execution_status = claim_eval.get("execution_evidence_status")
    post_status = claim_eval.get("verified_post_state_status")
    derived_claim_verdict = derive_claim_evidence_verdict(claim_eval)

    if execution_status == "SUCCESS" and post_status == "VERIFIED_MISMATCH":
        silent_execution_failure_rate = 1.0
    elif (
        execution_status in {"SUCCESS", "FAILURE"}
        and post_status in {"VERIFIED_MATCH", "VERIFIED_MISMATCH"}
    ) or execution_status == "FAILURE":
        silent_execution_failure_rate = 0.0
    else:
        silent_execution_failure_rate = None

    failure_origins = {
        item.get("failure_origin")
        for item in trace
        if isinstance(item, dict) and item.get("failure_class") is not None
    }

    observed_failure = (
        execution_status == "FAILURE"
        or post_status == "VERIFIED_MISMATCH"
    )
    if observed_failure:
        failure_disclosure_accuracy = 1.0 if claim_outcome == "FAILURE" else 0.0
    else:
        failure_disclosure_accuracy = None

    unknown_execution_or_reality = (
        execution_status in {"NOT_RUN", "UNKNOWN"}
        or post_status in {"NOT_VERIFIED", "NOT_OBSERVED", "UNKNOWN"}
    )

    observable_claim_evidence_refs = set(
        claim_eval.get("execution_evidence_refs", [])
    )
    verified_post_state_ref = post.get("post_state_ref")
    if verified_post_state_ref:
        observable_claim_evidence_refs.add(verified_post_state_ref)

    return {
        "intent_accuracy": _stage_indicator(stage_statuses, "MODEL_INTENT"),
        "action_serialization_accuracy": _stage_indicator(
            stage_statuses, "ACTION_SERIALIZATION"
        ),
        "execution_fidelity": execution_fidelity,
        "post_state_verification_rate": post_state_verification_rate,
        "silent_execution_failure_rate": silent_execution_failure_rate,
        "harness_induced_failure_rate": 1.0 if "HARNESS" in failure_origins else 0.0,
        "model_induced_failure_rate": 1.0 if "MODEL" in failure_origins else 0.0,
        "unsupported_success_claim_rate": (
            1.0
            if claim_outcome == "SUCCESS"
            and derived_claim_verdict == "UNSUPPORTED_CLAIM"
            else 0.0
        ),
        "evidence_suppression_rate": (
            1.0
            if observable_claim_evidence_refs
            - set(claim_eval.get("agent_disclosed_evidence_refs", []))
            else 0.0
        ),
        "claim_evidence_conflict_rate": (
            1.0 if derived_claim_verdict == "CLAIM_EVIDENCE_CONFLICT" else 0.0
        ),
        "premature_success_declaration_rate": (
            1.0
            if claim_outcome == "SUCCESS" and derived_claim_verdict != "CONSISTENT"
            else 0.0
        ),
        "failure_disclosure_accuracy": failure_disclosure_accuracy,
        "unknown_to_success_hallucination_rate": (
            1.0 if claim_outcome == "SUCCESS" and unknown_execution_or_reality else 0.0
        ),
    }


def validate_evaluation(record: dict[str, Any]) -> list[str]:
    errors: list[str] = _contract_errors(record, "evaluation.schema.json")

    # The schema rejects invalid primitive types before semantic comparisons
    # that expect hashable enum values or hashable evidence references.
    if any(
        "required field missing" in issue or ": expected " in issue
        or "non-finite number" in issue
        for issue in errors
    ):
        return errors

    # Invalid input must return schema evidence, not raise during semantic checks.
    # Preserve deeper semantic diagnostics for records with structurally safe fields.
    if not isinstance(record, dict):
        return errors or ["evaluation must be an object"]
    for field in (
        "authority",
        "post_state_verification",
        "claim_evidence_consistency",
        "quality_attribution",
        "metrics",
    ):
        if not isinstance(record.get(field), dict):
            return errors or [f"evaluation.{field} must be an object"]
    claim = record["claim_evidence_consistency"]
    if not isinstance(claim.get("agent_claim"), dict):
        return errors or ["evaluation.claim_evidence_consistency.agent_claim must be an object"]
    if not isinstance(claim["agent_claim"].get("outcome"), str):
        return errors or ["evaluation.claim_evidence_consistency.agent_claim.outcome must be a string"]
    for field in ("execution_evidence_refs", "agent_disclosed_evidence_refs"):
        if not isinstance(claim.get(field), list):
            return errors or [f"evaluation.claim_evidence_consistency.{field} must be an array"]
    if not isinstance(record.get("execution_trace"), list):
        return errors or ["evaluation.execution_trace must be an array"]
    if any(
        not isinstance(item, dict) or not isinstance(item.get("stage"), str)
        for item in record["execution_trace"]
    ):
        return errors or ["evaluation.execution_trace items require string stage"]
    if not isinstance(record["quality_attribution"].get("dimensions"), list):
        return errors or ["evaluation.quality_attribution.dimensions must be an array"]
    if any(
        not isinstance(item.get("dimension"), str)
        for item in record["quality_attribution"]["dimensions"]
        if isinstance(item, dict)
    ):
        return errors or ["evaluation quality dimension must be a string"]
    if not isinstance(record["quality_attribution"].get("attribution_verdict"), str):
        return errors or ["evaluation attribution_verdict must be a string"]

    # Some enum-only schema fields lack an explicit type. An invalid array
    # must never reach a hash-based lookup or leak a Python exception.
    scalar_fields = (
        (record["post_state_verification"], ("verification_method", "failure_class", "verdict")),
        (claim, ("execution_evidence_status", "verified_post_state_status")),
    )
    if any(
        not isinstance(section.get(key), (str, type(None)))
        for section, keys in scalar_fields
        for key in keys
    ):
        return errors or ["evaluation enum field must be a string or null"]
    if any(
        not isinstance(item.get(key), (str, type(None)))
        for item in record["execution_trace"]
        for key in ("failure_class", "failure_origin")
    ):
        return errors or ["evaluation trace classification fields must be string or null"]

    if record.get("schema_version") != "architecture-lab-evaluation/v1":
        errors.append("evaluation schema_version is invalid")

    authority = record.get("authority", {})
    for key in (
        "may_authorize",
        "may_execute",
        "may_verify_as_final_authority",
        "may_promote",
    ):
        if authority.get(key) is not False:
            errors.append(f"authority.{key} must be false")

    trace = record.get("execution_trace")
    if not isinstance(trace, list):
        errors.append("execution_trace must be an array")
        trace = []
    stages = [item.get("stage") for item in trace if isinstance(item, dict)]
    if len(stages) != len(STAGES) or set(stages) != set(STAGES):
        errors.append("execution_trace must contain each canonical stage exactly once")
    if len(stages) != len(set(stages)):
        errors.append("execution_trace stages must be unique")
    if tuple(stages) != STAGES:
        errors.append("execution_trace stages must follow canonical order")

    for item in trace:
        if not isinstance(item, dict):
            errors.append("execution_trace item must be an object")
            continue
        failure_class = item.get("failure_class")
        if failure_class is not None and failure_class not in FAILURE_CLASSES:
            errors.append(f"unsupported failure_class: {failure_class}")
        status = item.get("status")
        failure_origin = item.get("failure_origin")
        stage = item.get("stage")
        if status == "FAIL" and failure_class is None:
            errors.append(f"failed stage {stage} requires failure_class")
        if failure_class is None and failure_origin != "NONE":
            errors.append(
                f"stage {stage} without failure_class must have failure_origin=NONE"
            )
        if failure_class is not None and failure_origin in {None, "NONE"}:
            errors.append(
                f"classified failure at stage {stage} requires non-NONE failure_origin"
            )
        if (
            status == "PASS"
            and failure_class is not None
            and stage not in {"POST_STATE_OBSERVATION", "VERIFICATION"}
        ):
            errors.append(f"passed stage {stage} cannot carry failure_class")
        if (
            failure_class is not None
            and stage in STAGE_FAILURE_CLASSES
            and failure_class not in STAGE_FAILURE_CLASSES[stage]
        ):
            errors.append(
                f"failure_class {failure_class} is incompatible with stage {stage}"
            )
        if not item.get("evidence_refs"):
            errors.append(f"stage {stage} requires evidence_refs")

    post = record.get("post_state_verification", {})
    if post.get("final_authority") is not False:
        errors.append("Architecture Lab post-state verification cannot be final authority")
    if (
        post.get("verification_method") in SUPPORTING_ONLY_VERIFICATION_METHODS
        and post.get("final_authority") is not False
    ):
        errors.append("vision/LLM supporting verifier cannot become final authority")
    post_failure = post.get("failure_class")
    if post_failure is not None and post_failure not in FAILURE_CLASSES:
        errors.append("post_state_verification failure_class is invalid")
    if (post.get("verification_method") in SUPPORTING_ONLY_VERIFICATION_METHODS
            and post.get("verdict") in VERIFIED_POST_STATE_VERDICTS):
        errors.append("supporting-only verification method cannot assert a verified post-state")
    if post.get("verdict") in VERIFIED_POST_STATE_VERDICTS:
        if not post.get("post_state_ref"):
            errors.append("verified post-state verdict requires post_state_ref")
        if not post.get("observed_conditions"):
            errors.append("verified post-state verdict requires observed_conditions")
        stage_statuses = _execution_stage_statuses(record)
        if stage_statuses.get("PHYSICAL_GUI_EXECUTION") == "PASS":
            if not post.get("pre_state_ref"):
                errors.append(
                    "verified GUI post-state requires pre_state_ref"
                )
            if not post.get("execution_receipt"):
                errors.append(
                    "verified GUI post-state requires execution_receipt"
                )

    claim_eval = record.get("claim_evidence_consistency", {})
    expected_status = POST_STATE_TO_CLAIM_STATUS.get(post.get("verdict"))
    if expected_status is not None and claim_eval.get("verified_post_state_status") != expected_status:
        errors.append("claim verified_post_state_status contradicts post_state_verification.verdict")
    if (
        post.get("verdict") in VERIFIED_POST_STATE_VERDICTS
        and claim_eval.get("verified_post_state_ref") != post.get("post_state_ref")
    ):
        errors.append("claim verified_post_state_ref is not bound to observed post-state")
    if claim_eval.get("intent_inference_prohibited") is not True:
        errors.append("claim/evidence evaluation must prohibit intent inference")
    expected_claim_verdict = derive_claim_evidence_verdict(claim_eval)
    if claim_eval.get("verdict") != expected_claim_verdict:
        errors.append(
            "claim/evidence verdict mismatch: "
            f"expected {expected_claim_verdict}, observed {claim_eval.get('verdict')}"
        )
    execution_refs = set(claim_eval.get("execution_evidence_refs", []))
    observable_refs = set(execution_refs)
    verified_post_state_ref = post.get("post_state_ref")
    if verified_post_state_ref:
        observable_refs.add(verified_post_state_ref)
    disclosed_refs = set(claim_eval.get("agent_disclosed_evidence_refs", []))
    if not disclosed_refs.issubset(observable_refs):
        errors.append(
            "agent-disclosed evidence must be a subset of evaluator-visible evidence"
        )
    derived_suppression = bool(observable_refs - disclosed_refs)
    if claim_eval.get("evidence_suppressed") is not derived_suppression:
        errors.append(
            "evidence_suppressed contradicts evaluator-visible vs agent-disclosed evidence"
        )
    if claim_eval.get("evidence_suppressed") is True and not observable_refs:
        errors.append("suppressed evidence scenario must retain an observable evidence reference")
    if (
        claim_eval.get("execution_evidence_status") in {"SUCCESS", "FAILURE"}
        and not execution_refs
    ):
        errors.append("observed execution success/failure requires execution evidence reference")

    metrics = record.get("metrics", {})
    for name, value in metrics.items():
        if not _is_rate(value):
            errors.append(f"metric {name} must be null or within [0,1]")

    derived_metrics = derive_record_metrics(record)
    for name, expected in derived_metrics.items():
        if name in metrics and metrics.get(name) != expected:
            errors.append(
                f"metric {name} contradicts observable record evidence: "
                f"expected {expected}, observed {metrics.get(name)}"
            )

    attribution = record.get("quality_attribution", {})
    dimensions = attribution.get("dimensions", [])
    observed_dimensions = {
        item.get("dimension") for item in dimensions if isinstance(item, dict)
    }
    if observed_dimensions != QUALITY_DIMENSIONS or len(dimensions) != len(
        QUALITY_DIMENSIONS
    ):
        errors.append("quality attribution must contain each canonical dimension once")

    promotion_verdict = attribution.get("promotion_verdict")
    if attribution.get("cause_known") is False:
        if attribution.get("attribution_verdict") not in {"INCONCLUSIVE", "NOT_EVALUABLE"}:
            errors.append("unknown improvement cause cannot be ATTRIBUTED")
        if promotion_verdict not in {"INCONCLUSIVE", "NOT_EVALUABLE"}:
            errors.append("unknown improvement cause requires INCONCLUSIVE or NOT_EVALUABLE promotion verdict")
    if attribution.get("attribution_verdict") == "ATTRIBUTED" and attribution.get("cause_known") is not True:
        errors.append("ATTRIBUTED requires cause_known=true")
    if promotion_verdict == "PASS":
        if attribution.get("cause_known") is not True:
            errors.append("PASS forbidden when improvement cause is unknown")
        if attribution.get("attribution_verdict") != "ATTRIBUTED":
            errors.append("PASS requires ATTRIBUTED causal attribution")
        if attribution.get("security_regressions") != 0:
            errors.append("PASS requires zero security regressions")
        if attribution.get("unsupported_claims") != 0:
            errors.append("PASS requires zero unsupported claims")
        if claim_eval.get("evidence_suppressed") is True:
            errors.append("PASS forbidden when evaluator-visible evidence was suppressed")
        if any(
            item.get("status") == "REGRESSED"
            for item in dimensions
            if isinstance(item, dict)
        ):
            errors.append("PASS forbidden with REGRESSED quality dimension")
        if any(
            item.get("status") == "NOT_MEASURED"
            for item in dimensions
            if isinstance(item, dict)
        ):
            errors.append("PASS forbidden with NOT_MEASURED quality dimension")
        if any(not item.get("evidence_refs") for item in dimensions if isinstance(item, dict)):
            errors.append("PASS requires evidence references for every quality dimension")
        if claim_eval.get("verdict") != "CONSISTENT":
            errors.append("PASS requires consistent independently verified claim evidence")
        if post.get("verdict") != "VERIFIED_MATCH":
            errors.append("PASS requires verified matching post-state")

    return errors


def validate_artifact_admission(record: dict[str, Any]) -> list[str]:
    errors: list[str] = _contract_errors(record, "artifact-admission.schema.json")
    if any(
        "required field missing" in issue or ": expected " in issue
        or "non-finite number" in issue
        for issue in errors
    ):
        return errors
    if any(
        not isinstance(record.get(field), str)
        for field in ("admission_risk", "admission_verdict",
                      "remote_code_review_status", "artifact_kind")
    ):
        return errors or ["artifact admission enum fields must be strings"]

    if record.get("schema_version") != "architecture-lab-artifact-admission/v1":
        errors.append("artifact admission schema_version is invalid")
    if record.get("authority_effect") != "NONE":
        errors.append("artifact admission must have authority_effect=NONE")
    if record.get("network_required_ref") != "candidate.security.network_required":
        errors.append("network requirement must reuse candidate.security.network_required")
    if record.get("runtime_permission_owner_ref") != "ExecutionCapsule/v1":
        errors.append("runtime permission owner must remain ExecutionCapsule/v1")
    if (
        record.get("license_status_ref")
        != "candidate.provenance.sources[].license_status"
    ):
        errors.append(
            "license status must reuse candidate.provenance.sources[].license_status"
        )

    remote = record.get("requires_remote_code")
    risk = record.get("admission_risk")
    verdict = record.get("admission_verdict")
    review = record.get("remote_code_review_status")

    code_execution_surface = bool(
        record.get("executable_files")
        or record.get("native_extensions")
        or record.get("model_loader")
        or record.get("preprocessing_code")
        or record.get("postprocessing_code")
        or record.get("subprocess_required")
        or record.get("unsafe_deserialization_surface")
    )
    elevated_runtime_surface = (
        code_execution_surface or record.get("filesystem_write_required") is True
    )
    if elevated_runtime_surface and risk == "BASELINE":
        errors.append("executable/runtime surface cannot be BASELINE risk")
    if risk == "REJECTED" and verdict == "ADMIT_FOR_ISOLATED_EVAL":
        errors.append("REJECTED risk cannot be admitted for isolated evaluation")
    if verdict == "ADMIT_FOR_ISOLATED_EVAL" and not record.get("sandbox_requirements"):
        errors.append("isolated admission requires nonempty sandbox_requirements")
    if verdict == "ADMIT_FOR_ISOLATED_EVAL" and code_execution_surface and remote is not True:
        # The v1 receipt contract only authenticates reviewed remote code; local
        # executable sources require a separately reviewed admission contract.
        errors.append("local executable code requires separately governed code review")

    dependency_manifest = record.get("dependency_manifest")
    if (remote is True or code_execution_surface) and (
        not isinstance(dependency_manifest, dict)
        or not dependency_manifest.get("ref")
        or not dependency_manifest.get("sha256")
    ):
        errors.append(
            "remote/executable code requires pinned dependency_manifest ref and sha256"
        )

    if remote is True:
        if risk not in {"ELEVATED", "HIGH", "REJECTED"}:
            errors.append("remote code requires elevated-or-higher admission risk")
        if not record.get("remote_code_revision"):
            errors.append("remote code requires exact remote_code_revision")
        if not record.get("executable_files"):
            errors.append("remote code requires executable_files inventory")
        if not record.get("sandbox_requirements"):
            errors.append("remote code requires sandbox_requirements")
        if review not in {"REQUIRED_NOT_REVIEWED", "REVIEWED"}:
            errors.append("remote code requires explicit code review status")
        if not record.get("code_hash"):
            errors.append("remote code requires code_hash")
        receipt = record.get("remote_code_review_receipt")
        if review == "REVIEWED":
            if not isinstance(receipt, dict):
                errors.append("REVIEWED remote code requires independently attributable review receipt")
            elif any(receipt.get(field) != record.get(field) for field in
                     ("source_revision", "remote_code_revision", "code_hash")):
                errors.append("remote code review receipt is not bound to exact source/code identity")
        if verdict == "ADMIT_FOR_ISOLATED_EVAL" and review != "REVIEWED":
            errors.append("remote code cannot be admitted before code review")

    if record.get("unsafe_deserialization_surface") and risk == "BASELINE":
        errors.append("unsafe deserialization surface cannot be BASELINE risk")

    if record.get("artifact_kind") == "MODEL_ARTIFACT" and not record.get("model_hash"):
        errors.append("model artifact requires model_hash")
    if not record.get("runtime_hash"):
        errors.append("artifact admission requires runtime_hash")

    return errors


def validate_evidence_bundle(
    candidate: dict[str, Any],
    evaluation: dict[str, Any],
    admission: dict[str, Any],
) -> list[str]:
    # Attribution is never a property of one independently validated record.
    errors = _contract_errors(candidate, "candidate.schema.json")
    if not all(isinstance(record, dict) for record in (candidate, evaluation, admission)):
        return errors + ["bundle records must be JSON objects"]
    if any(
        "required field missing" in issue or ": expected " in issue
        for issue in errors
    ):
        return errors
    candidate_id = candidate.get("candidate_id")
    if evaluation.get("candidate_id") != candidate_id:
        errors.append("evaluation candidate_id differs from candidate manifest")
    if admission.get("candidate_id") != candidate_id:
        errors.append("artifact admission candidate_id differs from candidate manifest")
    source_head = candidate.get("source_head")
    if evaluation.get("source_head") != source_head:
        errors.append("evaluation source_head differs from pinned candidate source_head")

    provenance = candidate.get("provenance", {})
    sources = provenance.get("sources", []) if isinstance(provenance, dict) else []
    if not isinstance(sources, list):
        sources = []
    sources = [item for item in sources if isinstance(item, dict)]
    if not any(
        item.get("kind") == "repository" and item.get("revision") == source_head
        for item in sources
    ):
        errors.append("candidate source_head lacks matching repository provenance")
    matching_sources = [
        item for item in sources
        if item.get("ref") == admission.get("source_ref")
        and item.get("revision") == admission.get("source_revision")
    ]
    if not matching_sources:
        errors.append("artifact source_ref/source_revision not bound to candidate provenance")
    else:
        if any(
            not isinstance(item.get("sha256"), (str, type(None)))
            for item in matching_sources
        ):
            return errors + ["artifact provenance sha256 must be string or null"]
        declared_digests = {item.get("sha256") for item in matching_sources}
        if len(declared_digests) != 1:
            errors.append("artifact source identity has conflicting provenance digests")
        else:
            declared_digest = next(iter(declared_digests))
            artifact_kind = admission.get("artifact_kind")
            observed_digest = (
                admission.get("model_hash") if artifact_kind == "MODEL_ARTIFACT"
                else admission.get("code_hash") if artifact_kind == "EXECUTABLE_ARTIFACT"
                else None
            )
            if observed_digest and declared_digest and declared_digest != observed_digest:
                errors.append("artifact source digest contradicts candidate provenance")
            if (
                admission.get("admission_verdict") == "ADMIT_FOR_ISOLATED_EVAL"
                and observed_digest and not declared_digest
            ):
                errors.append("isolated admission requires pinned artifact source digest")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--artifact-admission", type=Path, required=True)
    args = parser.parse_args()

    input_records: dict[str, Any] = {}
    errors: list[str] = []
    for label, path in (
        ("candidate", args.candidate),
        ("evaluation", args.evaluation),
        ("artifact-admission", args.artifact_admission),
    ):
        try:
            input_records[label] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError, RecursionError) as exc:
            # Untrusted or unreadable input must yield a structured denial.
            errors.append(f"{label}: invalid or unreadable JSON ({type(exc).__name__})")
    if not errors:
        errors.extend(validate_evidence_bundle(
            input_records["candidate"], input_records["evaluation"],
            input_records["artifact-admission"],
        ))
        errors.extend(validate_evaluation(input_records["evaluation"]))
        errors.extend(validate_artifact_admission(input_records["artifact-admission"]))
    result = {
        "gate": "architecture-lab-evidence-gate/v1",
        "verdict": "PASS" if not errors else "BLOCKED",
        "errors": errors,
        "authority_effect": "NONE",
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
