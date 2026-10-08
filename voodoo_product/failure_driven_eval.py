from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final, Self

from .evidence_primitives import canonical_json

FAILURE_RECORD_TYPE: Final = "failure-record/v1"
GENERATED_EVAL_CASE_TYPE: Final = "generated-eval-case/v1"
GENERATED_EVAL_SET_TYPE: Final = "generated-eval-set/v1"

DEVELOPMENT: Final = "DEVELOPMENT"
GENERATED_ADVERSARIAL: Final = "GENERATED_ADVERSARIAL"
FROZEN: Final = "FROZEN"
POST_FREEZE_SHADOW: Final = "POST_FREEZE_SHADOW"
EVAL_CORPUS_CLASSES: Final = (
    DEVELOPMENT,
    GENERATED_ADVERSARIAL,
    FROZEN,
    POST_FREEZE_SHADOW,
)

DETERMINISTIC_GENERATOR: Final = "DETERMINISTIC"
LLM_CANDIDATE_GENERATOR: Final = "LLM_CANDIDATE"
GENERATOR_KINDS: Final = (DETERMINISTIC_GENERATOR, LLM_CANDIDATE_GENERATOR)

DETERMINISTIC_VALIDATION: Final = "DETERMINISTIC"
HUMAN_VALIDATION: Final = "HUMAN_REVIEW"
VALIDATION_KINDS: Final = (DETERMINISTIC_VALIDATION, HUMAN_VALIDATION)

COVERAGE_ONLY: Final = "COVERAGE_ONLY"
VALIDATED: Final = "VALIDATED"


class FailureDrivenEvalError(ValueError):
    """Fail-closed error for failure-derived eval lifecycle invariants."""


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _require_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or "\x00" in value:
        raise FailureDrivenEvalError(f"{field} is invalid")
    return value


def _require_digest(value: object, *, field: str) -> str:
    text = _require_text(value, field=field)
    if (
        len(text) != 64
        or text.casefold() != text
        or any(character not in "0123456789abcdef" for character in text)
    ):
        raise FailureDrivenEvalError(f"{field} must be a lowercase SHA-256 digest")
    return text


def _require_exact_fields(
    value: Mapping[str, Any],
    expected: frozenset[str],
    *,
    contract: str,
) -> None:
    if not isinstance(value, Mapping):
        raise FailureDrivenEvalError(f"{contract} must be an object")
    actual = frozenset(value)
    if actual != expected:
        raise FailureDrivenEvalError(
            f"{contract} fields are invalid; "
            f"missing={sorted(expected - actual)}, unknown={sorted(actual - expected)}"
        )


def _canonical_string_mapping(value: Mapping[str, str], *, field: str) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, Mapping) or not value:
        raise FailureDrivenEvalError(f"{field} must be a non-empty object")
    pairs: list[tuple[str, str]] = []
    for key, item in value.items():
        pairs.append(
            (
                _require_text(key, field=f"{field} key"),
                _require_text(item, field=f"{field}[{key!r}]"),
            )
        )
    ordered = tuple(sorted(pairs))
    if len({key for key, _ in ordered}) != len(ordered):
        raise FailureDrivenEvalError(f"{field} keys must be unique")
    return ordered


@dataclass(frozen=True, slots=True)
class FailureRecord:
    failure_id: str
    operation_id: str
    classification: str
    invariant: str
    failure_property: str
    source_kind: str
    source_identity: str
    source_evidence_digest: str
    record_digest: str

    def __post_init__(self) -> None:
        for field in (
            "failure_id",
            "operation_id",
            "classification",
            "invariant",
            "failure_property",
            "source_kind",
            "source_identity",
        ):
            _require_text(getattr(self, field), field=field)
        _require_digest(self.source_evidence_digest, field="source_evidence_digest")
        _require_digest(self.record_digest, field="record_digest")
        if self.record_digest != _digest(self._claims_without_digest()):
            raise FailureDrivenEvalError("record_digest does not match failure record")

    @classmethod
    def create(
        cls,
        *,
        failure_id: str,
        operation_id: str,
        classification: str,
        invariant: str,
        failure_property: str,
        source_kind: str,
        source_identity: str,
        source_evidence_digest: str,
    ) -> Self:
        claims = {
            "schema_version": 1,
            "record_type": FAILURE_RECORD_TYPE,
            "failure_id": failure_id,
            "operation_id": operation_id,
            "classification": classification,
            "invariant": invariant,
            "failure_property": failure_property,
            "source_kind": source_kind,
            "source_identity": source_identity,
            "source_evidence_digest": source_evidence_digest,
        }
        values = {
            key: value
            for key, value in claims.items()
            if key not in {"schema_version", "record_type"}
        }
        return cls(**values, record_digest=_digest(claims))

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Self:
        expected = frozenset(
            {
                "schema_version",
                "record_type",
                "failure_id",
                "operation_id",
                "classification",
                "invariant",
                "failure_property",
                "source_kind",
                "source_identity",
                "source_evidence_digest",
                "record_digest",
            }
        )
        _require_exact_fields(value, expected, contract=FAILURE_RECORD_TYPE)
        if value["schema_version"] != 1 or value["record_type"] != FAILURE_RECORD_TYPE:
            raise FailureDrivenEvalError("failure-record/v1 schema or type is unsupported")
        return cls(
            failure_id=value["failure_id"],
            operation_id=value["operation_id"],
            classification=value["classification"],
            invariant=value["invariant"],
            failure_property=value["failure_property"],
            source_kind=value["source_kind"],
            source_identity=value["source_identity"],
            source_evidence_digest=value["source_evidence_digest"],
            record_digest=value["record_digest"],
        )

    def _claims_without_digest(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "record_type": FAILURE_RECORD_TYPE,
            "failure_id": self.failure_id,
            "operation_id": self.operation_id,
            "classification": self.classification,
            "invariant": self.invariant,
            "failure_property": self.failure_property,
            "source_kind": self.source_kind,
            "source_identity": self.source_identity,
            "source_evidence_digest": self.source_evidence_digest,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._claims_without_digest(), "record_digest": self.record_digest}


@dataclass(frozen=True, slots=True)
class GeneratedEvalCase:
    case_id: str
    parent_failure_digest: str
    operation_id: str
    classification: str
    invariant: str
    failure_property: str
    corpus_class: str
    input_variant: tuple[tuple[str, str], ...]
    generator_kind: str
    validation_kind: str
    validation_status: str
    validator_identity: str
    validator_evidence_digest: str
    evidence_strength: str
    case_digest: str

    def __post_init__(self) -> None:
        for field in (
            "case_id",
            "operation_id",
            "classification",
            "invariant",
            "failure_property",
            "validator_identity",
        ):
            _require_text(getattr(self, field), field=field)
        _require_digest(self.parent_failure_digest, field="parent_failure_digest")
        _require_digest(self.validator_evidence_digest, field="validator_evidence_digest")
        _require_digest(self.case_digest, field="case_digest")
        if self.corpus_class not in EVAL_CORPUS_CLASSES:
            raise FailureDrivenEvalError("corpus_class is unsupported")
        if self.corpus_class != GENERATED_ADVERSARIAL:
            raise FailureDrivenEvalError(
                "failure-derived cases may only enter GENERATED_ADVERSARIAL"
            )
        if self.generator_kind not in GENERATOR_KINDS:
            raise FailureDrivenEvalError("generator_kind is unsupported")
        if self.validation_kind not in VALIDATION_KINDS:
            raise FailureDrivenEvalError("validation_kind is unsupported")
        if self.validation_status != VALIDATED:
            raise FailureDrivenEvalError("generated eval candidates must be validated")
        if self.evidence_strength != COVERAGE_ONLY:
            raise FailureDrivenEvalError("synthetic eval evidence must remain COVERAGE_ONLY")
        if not self.input_variant:
            raise FailureDrivenEvalError("input_variant must not be empty")
        if tuple(sorted(self.input_variant)) != self.input_variant:
            raise FailureDrivenEvalError("input_variant must be canonical and sorted")
        if self.case_digest != _digest(self._claims_without_digest()):
            raise FailureDrivenEvalError("case_digest does not match generated eval case")

    @classmethod
    def create(
        cls,
        *,
        case_id: str,
        failure: FailureRecord,
        input_variant: Mapping[str, str],
        generator_kind: str,
        validation_kind: str,
        validator_identity: str,
        validator_evidence_digest: str,
        corpus_class: str = GENERATED_ADVERSARIAL,
    ) -> Self:
        if not isinstance(failure, FailureRecord):
            raise FailureDrivenEvalError("failure must be failure-record/v1")
        pairs = _canonical_string_mapping(input_variant, field="input_variant")
        claims = {
            "schema_version": 1,
            "case_type": GENERATED_EVAL_CASE_TYPE,
            "case_id": case_id,
            "parent_failure_digest": failure.record_digest,
            "operation_id": failure.operation_id,
            "classification": failure.classification,
            "invariant": failure.invariant,
            "failure_property": failure.failure_property,
            "corpus_class": corpus_class,
            "input_variant": dict(pairs),
            "generator_kind": generator_kind,
            "validation_kind": validation_kind,
            "validation_status": VALIDATED,
            "validator_identity": validator_identity,
            "validator_evidence_digest": validator_evidence_digest,
            "evidence_strength": COVERAGE_ONLY,
        }
        values = {
            key: value
            for key, value in claims.items()
            if key not in {"schema_version", "case_type", "input_variant"}
        }
        return cls(
            **values,
            input_variant=pairs,
            case_digest=_digest(claims),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Self:
        expected = frozenset(
            {
                "schema_version",
                "case_type",
                "case_id",
                "parent_failure_digest",
                "operation_id",
                "classification",
                "invariant",
                "failure_property",
                "corpus_class",
                "input_variant",
                "generator_kind",
                "validation_kind",
                "validation_status",
                "validator_identity",
                "validator_evidence_digest",
                "evidence_strength",
                "case_digest",
            }
        )
        _require_exact_fields(value, expected, contract=GENERATED_EVAL_CASE_TYPE)
        if value["schema_version"] != 1 or value["case_type"] != GENERATED_EVAL_CASE_TYPE:
            raise FailureDrivenEvalError("generated-eval-case/v1 schema or type is unsupported")
        return cls(
            case_id=value["case_id"],
            parent_failure_digest=value["parent_failure_digest"],
            operation_id=value["operation_id"],
            classification=value["classification"],
            invariant=value["invariant"],
            failure_property=value["failure_property"],
            corpus_class=value["corpus_class"],
            input_variant=_canonical_string_mapping(
                value["input_variant"], field="input_variant"
            ),
            generator_kind=value["generator_kind"],
            validation_kind=value["validation_kind"],
            validation_status=value["validation_status"],
            validator_identity=value["validator_identity"],
            validator_evidence_digest=value["validator_evidence_digest"],
            evidence_strength=value["evidence_strength"],
            case_digest=value["case_digest"],
        )

    def _claims_without_digest(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "case_type": GENERATED_EVAL_CASE_TYPE,
            "case_id": self.case_id,
            "parent_failure_digest": self.parent_failure_digest,
            "operation_id": self.operation_id,
            "classification": self.classification,
            "invariant": self.invariant,
            "failure_property": self.failure_property,
            "corpus_class": self.corpus_class,
            "input_variant": dict(self.input_variant),
            "generator_kind": self.generator_kind,
            "validation_kind": self.validation_kind,
            "validation_status": self.validation_status,
            "validator_identity": self.validator_identity,
            "validator_evidence_digest": self.validator_evidence_digest,
            "evidence_strength": self.evidence_strength,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._claims_without_digest(), "case_digest": self.case_digest}


@dataclass(frozen=True, slots=True)
class GeneratedEvalSet:
    set_id: str
    parent_failure_digest: str
    corpus_class: str
    cases: tuple[GeneratedEvalCase, ...]
    set_digest: str

    def __post_init__(self) -> None:
        _require_text(self.set_id, field="set_id")
        _require_digest(self.parent_failure_digest, field="parent_failure_digest")
        _require_digest(self.set_digest, field="set_digest")
        if self.corpus_class != GENERATED_ADVERSARIAL:
            raise FailureDrivenEvalError("generated eval set must remain GENERATED_ADVERSARIAL")
        if not self.cases:
            raise FailureDrivenEvalError("generated eval set requires at least one case")
        if not all(isinstance(item, GeneratedEvalCase) for item in self.cases):
            raise FailureDrivenEvalError("generated eval set contains an invalid case")
        if len({item.case_id for item in self.cases}) != len(self.cases):
            raise FailureDrivenEvalError("generated eval case ids must be unique")
        if len({item.case_digest for item in self.cases}) != len(self.cases):
            raise FailureDrivenEvalError("generated eval case digests must be unique")
        for item in self.cases:
            if item.parent_failure_digest != self.parent_failure_digest:
                raise FailureDrivenEvalError("generated eval case belongs to another failure")
            if item.corpus_class != GENERATED_ADVERSARIAL:
                raise FailureDrivenEvalError("generated eval case corpus contamination detected")
        if self.set_digest != _digest(self._claims_without_digest()):
            raise FailureDrivenEvalError("set_digest does not match generated eval set")

    @classmethod
    def create(
        cls,
        *,
        set_id: str,
        failure: FailureRecord,
        cases: Sequence[GeneratedEvalCase],
    ) -> Self:
        if not isinstance(failure, FailureRecord):
            raise FailureDrivenEvalError("failure must be failure-record/v1")
        canonical_cases = tuple(sorted(cases, key=lambda item: item.case_id))
        claims = {
            "schema_version": 1,
            "set_type": GENERATED_EVAL_SET_TYPE,
            "set_id": set_id,
            "parent_failure_digest": failure.record_digest,
            "corpus_class": GENERATED_ADVERSARIAL,
            "cases": [item.to_dict() for item in canonical_cases],
        }
        return cls(
            set_id=set_id,
            parent_failure_digest=failure.record_digest,
            corpus_class=GENERATED_ADVERSARIAL,
            cases=canonical_cases,
            set_digest=_digest(claims),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Self:
        expected = frozenset(
            {
                "schema_version",
                "set_type",
                "set_id",
                "parent_failure_digest",
                "corpus_class",
                "cases",
                "set_digest",
            }
        )
        _require_exact_fields(value, expected, contract=GENERATED_EVAL_SET_TYPE)
        if value["schema_version"] != 1 or value["set_type"] != GENERATED_EVAL_SET_TYPE:
            raise FailureDrivenEvalError("generated-eval-set/v1 schema or type is unsupported")
        cases_value = value["cases"]
        if not isinstance(cases_value, list):
            raise FailureDrivenEvalError("generated eval cases must be an array")
        return cls(
            set_id=value["set_id"],
            parent_failure_digest=value["parent_failure_digest"],
            corpus_class=value["corpus_class"],
            cases=tuple(GeneratedEvalCase.from_dict(item) for item in cases_value),
            set_digest=value["set_digest"],
        )

    def _claims_without_digest(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "set_type": GENERATED_EVAL_SET_TYPE,
            "set_id": self.set_id,
            "parent_failure_digest": self.parent_failure_digest,
            "corpus_class": self.corpus_class,
            "cases": [item.to_dict() for item in self.cases],
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._claims_without_digest(), "set_digest": self.set_digest}


def build_generated_eval_case(
    *,
    case_id: str,
    failure: FailureRecord,
    input_variant: Mapping[str, str],
    generator_kind: str,
    deterministic_validator_identity: str | None,
    deterministic_validator_evidence_digest: str | None,
    human_validator_identity: str | None = None,
    human_validator_evidence_digest: str | None = None,
) -> GeneratedEvalCase:
    """Create one validated generated/adversarial eval without benchmark promotion.

    Deterministic validation is always preferred when provided. Human validation is the only
    fallback in this contract. An LLM generator may propose a candidate, but it never becomes
    its own verifier and its output remains COVERAGE_ONLY evidence.
    """

    if deterministic_validator_identity is not None or deterministic_validator_evidence_digest is not None:
        if deterministic_validator_identity is None or deterministic_validator_evidence_digest is None:
            raise FailureDrivenEvalError("deterministic validator identity/evidence must be paired")
        validation_kind = DETERMINISTIC_VALIDATION
        validator_identity = deterministic_validator_identity
        validator_evidence_digest = deterministic_validator_evidence_digest
    else:
        if human_validator_identity is None or human_validator_evidence_digest is None:
            raise FailureDrivenEvalError(
                "generated eval candidate requires deterministic or human validation"
            )
        validation_kind = HUMAN_VALIDATION
        validator_identity = human_validator_identity
        validator_evidence_digest = human_validator_evidence_digest

    return GeneratedEvalCase.create(
        case_id=case_id,
        failure=failure,
        input_variant=input_variant,
        generator_kind=generator_kind,
        validation_kind=validation_kind,
        validator_identity=validator_identity,
        validator_evidence_digest=validator_evidence_digest,
    )
