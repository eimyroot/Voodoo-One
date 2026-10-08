from __future__ import annotations

import pytest

from voodoo_product.failure_driven_eval import (
    COVERAGE_ONLY,
    DETERMINISTIC_GENERATOR,
    DETERMINISTIC_VALIDATION,
    FROZEN,
    GENERATED_ADVERSARIAL,
    HUMAN_VALIDATION,
    LLM_CANDIDATE_GENERATOR,
    POST_FREEZE_SHADOW,
    FailureDrivenEvalError,
    FailureRecord,
    GeneratedEvalCase,
    GeneratedEvalSet,
    build_generated_eval_case,
)

D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64


def failure() -> FailureRecord:
    return FailureRecord.create(
        failure_id="failure_postcondition_mismatch_001",
        operation_id="operation_ref_update_001",
        classification="POSTCONDITION_MISMATCH",
        invariant="postcondition must be authoritative",
        failure_property="observed state does not match the expected state",
        source_kind="state_observation",
        source_identity="github-api:repository/eimyroot/Voodoo-One:ref/heads/main",
        source_evidence_digest=D1,
    )


def generated_case(case_id: str = "generated_001") -> GeneratedEvalCase:
    return build_generated_eval_case(
        case_id=case_id,
        failure=failure(),
        input_variant={"reported": "success", "observed": "unchanged"},
        generator_kind=DETERMINISTIC_GENERATOR,
        deterministic_validator_identity="validator:postcondition-structural/v1",
        deterministic_validator_evidence_digest=D2,
    )


def test_failure_record_round_trips_with_source_provenance() -> None:
    record = failure()
    restored = FailureRecord.from_dict(record.to_dict())
    assert restored == record
    assert restored.source_identity == record.source_identity


def test_generated_variants_preserve_failure_property() -> None:
    record = failure()
    first = generated_case("generated_001")
    second = build_generated_eval_case(
        case_id="generated_002",
        failure=record,
        input_variant={"reported": "ok", "observed": "old-value"},
        generator_kind=DETERMINISTIC_GENERATOR,
        deterministic_validator_identity="validator:postcondition-structural/v1",
        deterministic_validator_evidence_digest=D3,
    )
    assert first.failure_property == second.failure_property == record.failure_property


@pytest.mark.parametrize("forbidden_corpus", [FROZEN, POST_FREEZE_SHADOW])
def test_generated_eval_cannot_enter_frozen_or_shadow_corpus(
    forbidden_corpus: str,
) -> None:
    with pytest.raises(FailureDrivenEvalError, match="GENERATED_ADVERSARIAL"):
        GeneratedEvalCase.create(
            case_id="contamination_attempt",
            failure=failure(),
            input_variant={"case": "variant"},
            generator_kind=DETERMINISTIC_GENERATOR,
            validation_kind=DETERMINISTIC_VALIDATION,
            validator_identity="validator:deterministic/v1",
            validator_evidence_digest=D2,
            corpus_class=forbidden_corpus,
        )


def test_llm_generated_candidate_requires_independent_validation() -> None:
    with pytest.raises(FailureDrivenEvalError):
        build_generated_eval_case(
            case_id="llm_unvalidated",
            failure=failure(),
            input_variant={"variant": "llm-output"},
            generator_kind=LLM_CANDIDATE_GENERATOR,
            deterministic_validator_identity=None,
            deterministic_validator_evidence_digest=None,
        )

    validated = build_generated_eval_case(
        case_id="llm_human_validated",
        failure=failure(),
        input_variant={"variant": "llm-output"},
        generator_kind=LLM_CANDIDATE_GENERATOR,
        deterministic_validator_identity=None,
        deterministic_validator_evidence_digest=None,
        human_validator_identity="human:reviewer-001",
        human_validator_evidence_digest=D3,
    )
    assert validated.validation_kind == HUMAN_VALIDATION
    assert validated.evidence_strength == COVERAGE_ONLY


def test_deterministic_validator_is_preferred_over_human_fallback() -> None:
    candidate = build_generated_eval_case(
        case_id="deterministic_preferred",
        failure=failure(),
        input_variant={"variant": "candidate"},
        generator_kind=LLM_CANDIDATE_GENERATOR,
        deterministic_validator_identity="validator:structural/v1",
        deterministic_validator_evidence_digest=D2,
        human_validator_identity="human:reviewer-001",
        human_validator_evidence_digest=D3,
    )
    assert candidate.validation_kind == DETERMINISTIC_VALIDATION
    assert candidate.validator_identity == "validator:structural/v1"


def test_generated_eval_set_round_trips_without_promotion() -> None:
    record = failure()
    eval_set = GeneratedEvalSet.create(
        set_id="generated_set_failure_postcondition_mismatch_001",
        failure=record,
        cases=(generated_case("generated_002"), generated_case("generated_001")),
    )
    restored = GeneratedEvalSet.from_dict(eval_set.to_dict())
    assert restored == eval_set
    assert restored.corpus_class == GENERATED_ADVERSARIAL
    assert [item.case_id for item in restored.cases] == [
        "generated_001",
        "generated_002",
    ]
    assert all(item.evidence_strength == COVERAGE_ONLY for item in restored.cases)


def test_generated_eval_set_rejects_case_from_another_failure() -> None:
    record = failure()
    other_failure = FailureRecord.create(
        failure_id="failure_other",
        operation_id=record.operation_id,
        classification=record.classification,
        invariant=record.invariant,
        failure_property=record.failure_property,
        source_kind=record.source_kind,
        source_identity=record.source_identity,
        source_evidence_digest=D3,
    )
    foreign_case = GeneratedEvalCase.create(
        case_id="foreign",
        failure=other_failure,
        input_variant={"variant": "foreign"},
        generator_kind=DETERMINISTIC_GENERATOR,
        validation_kind=DETERMINISTIC_VALIDATION,
        validator_identity="validator:structural/v1",
        validator_evidence_digest=D2,
    )

    with pytest.raises(FailureDrivenEvalError, match="another failure"):
        GeneratedEvalSet.create(
            set_id="mixed_failure_set",
            failure=record,
            cases=(foreign_case,),
        )


def test_generated_eval_serialization_tamper_fails_closed() -> None:
    candidate = generated_case()
    payload = candidate.to_dict()
    payload["failure_property"] = "different property"

    with pytest.raises(FailureDrivenEvalError, match="case_digest"):
        GeneratedEvalCase.from_dict(payload)


def test_synthetic_evidence_strength_cannot_be_upgraded() -> None:
    candidate = generated_case()
    payload = candidate.to_dict()
    payload["evidence_strength"] = "AUTHORITATIVE"

    with pytest.raises(FailureDrivenEvalError, match="COVERAGE_ONLY"):
        GeneratedEvalCase.from_dict(payload)
