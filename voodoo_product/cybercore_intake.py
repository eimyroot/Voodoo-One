from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Self

from .evidence_primitives import canonical_json

SCHEMA_VERSION = 1
INTAKE_TYPE = "v-one-cybercore-intake/v1"
SOURCE_SYSTEM = "CyberCore"
CXP_SCHEMA = "cxp/v1"

CYBERCORE_RISKS = ("low", "medium", "high", "critical")
V_ONE_RISK_BY_CYBERCORE_RISK = {
    "low": "R1",
    "medium": "R2",
    "high": "R3",
    "critical": "R4",
}
SIGNATURE_STATUSES = (
    "NOT_PRESENT",
    "PRESENT_UNVERIFIED",
    "VERIFIED_VALID",
    "VERIFIED_INVALID",
)
EXPECTED_EFFECTS = (
    "READ_ONLY",
    "MUTATION_PROPOSAL",
)

_ARTIFACT_ID_RE = re.compile(r"^WB-[0-9]{4}-[a-z0-9][a-z0-9-]*$")
_KNOWLEDGE_BLOCK_RE = re.compile(r"^KB-[0-9]{4}$")
_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")


class CyberCoreIntakeError(ValueError):
    """Fail-closed error for the read-only CyberCore intake contract."""


@dataclass(frozen=True, slots=True)
class CyberCoreIntakeRecord:
    artifact_id: str
    artifact_version: str
    artifact_digest: str
    payload_digest: str
    source_reference: str
    knowledge_block_reference: str
    knowledge_block_digest: str
    target_reference: str
    cybercore_risk: str
    v_one_risk_class: str
    signature_status: str
    expected_effect: str
    verification_plan: tuple[str, ...]
    may_approve: bool
    may_authorize: bool
    may_execute: bool
    production_effect: bool
    intake_digest: str

    def __post_init__(self) -> None:
        if not isinstance(self.artifact_id, str) or not _ARTIFACT_ID_RE.fullmatch(self.artifact_id):
            raise CyberCoreIntakeError("artifact_id must match the CXP/1 Work Block identity")
        if not isinstance(self.artifact_version, str) or not _VERSION_RE.fullmatch(self.artifact_version):
            raise CyberCoreIntakeError("artifact_version must be semantic-version shaped")
        _require_digest(self.artifact_digest, field="artifact_digest")
        _require_digest(self.payload_digest, field="payload_digest")
        _require_text(self.source_reference, field="source_reference")
        if (
            not isinstance(self.knowledge_block_reference, str)
            or not _KNOWLEDGE_BLOCK_RE.fullmatch(self.knowledge_block_reference)
        ):
            raise CyberCoreIntakeError("knowledge_block_reference must match KB-XXXX")
        _require_digest(self.knowledge_block_digest, field="knowledge_block_digest")
        _require_text(self.target_reference, field="target_reference")
        if self.cybercore_risk not in CYBERCORE_RISKS:
            raise CyberCoreIntakeError("cybercore_risk is unsupported")
        expected_risk = V_ONE_RISK_BY_CYBERCORE_RISK[self.cybercore_risk]
        if self.v_one_risk_class != expected_risk:
            raise CyberCoreIntakeError("v_one_risk_class does not match fail-closed risk mapping")
        if self.signature_status not in SIGNATURE_STATUSES:
            raise CyberCoreIntakeError("signature_status is unsupported")
        if self.expected_effect not in EXPECTED_EFFECTS:
            raise CyberCoreIntakeError("expected_effect is unsupported")
        _require_text_tuple(self.verification_plan, field="verification_plan")
        if len(self.verification_plan) != len(set(self.verification_plan)):
            raise CyberCoreIntakeError("verification_plan entries must be unique")
        authority_flags = (
            self.may_approve,
            self.may_authorize,
            self.may_execute,
            self.production_effect,
        )
        if any(value is not False for value in authority_flags):
            raise CyberCoreIntakeError("CyberCore intake cannot carry V-One authority or production effect")
        if self.intake_digest != _digest(self._claims_without_digest()):
            raise CyberCoreIntakeError("intake_digest does not match CyberCore intake claims")

    @classmethod
    def create(
        cls,
        *,
        artifact_id: str,
        artifact_version: str,
        artifact_digest: str,
        payload_digest: str,
        source_reference: str,
        knowledge_block_reference: str,
        knowledge_block_digest: str,
        target_reference: str,
        cybercore_risk: str,
        signature_status: str,
        expected_effect: str,
        verification_plan: Sequence[str],
    ) -> Self:
        plan = tuple(verification_plan)
        if not isinstance(cybercore_risk, str):
            raise CyberCoreIntakeError("cybercore_risk is unsupported")
        risk_class = V_ONE_RISK_BY_CYBERCORE_RISK.get(cybercore_risk)
        if risk_class is None:
            raise CyberCoreIntakeError("cybercore_risk is unsupported")
        claims = {
            "schema_version": SCHEMA_VERSION,
            "intake_type": INTAKE_TYPE,
            "source_system": SOURCE_SYSTEM,
            "cxp_schema": CXP_SCHEMA,
            "artifact_id": artifact_id,
            "artifact_version": artifact_version,
            "artifact_digest": artifact_digest,
            "payload_digest": payload_digest,
            "source_reference": source_reference,
            "knowledge_block_reference": knowledge_block_reference,
            "knowledge_block_digest": knowledge_block_digest,
            "target_reference": target_reference,
            "cybercore_risk": cybercore_risk,
            "v_one_risk_class": risk_class,
            "signature_status": signature_status,
            "expected_effect": expected_effect,
            "verification_plan": list(plan),
            "may_approve": False,
            "may_authorize": False,
            "may_execute": False,
            "production_effect": False,
        }
        return cls(
            artifact_id=artifact_id,
            artifact_version=artifact_version,
            artifact_digest=artifact_digest,
            payload_digest=payload_digest,
            source_reference=source_reference,
            knowledge_block_reference=knowledge_block_reference,
            knowledge_block_digest=knowledge_block_digest,
            target_reference=target_reference,
            cybercore_risk=cybercore_risk,
            v_one_risk_class=risk_class,
            signature_status=signature_status,
            expected_effect=expected_effect,
            verification_plan=plan,
            may_approve=False,
            may_authorize=False,
            may_execute=False,
            production_effect=False,
            intake_digest=_digest(claims),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Self:
        expected = frozenset(
            {
                "schema_version",
                "intake_type",
                "source_system",
                "cxp_schema",
                "artifact_id",
                "artifact_version",
                "artifact_digest",
                "payload_digest",
                "source_reference",
                "knowledge_block_reference",
                "knowledge_block_digest",
                "target_reference",
                "cybercore_risk",
                "v_one_risk_class",
                "signature_status",
                "expected_effect",
                "verification_plan",
                "may_approve",
                "may_authorize",
                "may_execute",
                "production_effect",
                "intake_digest",
            }
        )
        _require_exact_fields(value, expected)
        if value["schema_version"] != SCHEMA_VERSION:
            raise CyberCoreIntakeError("schema_version is unsupported")
        if value["intake_type"] != INTAKE_TYPE:
            raise CyberCoreIntakeError("intake_type is unsupported")
        if value["source_system"] != SOURCE_SYSTEM:
            raise CyberCoreIntakeError("source_system must be CyberCore")
        if value["cxp_schema"] != CXP_SCHEMA:
            raise CyberCoreIntakeError("cxp_schema must be cxp/v1")
        plan = value["verification_plan"]
        if not isinstance(plan, list):
            raise CyberCoreIntakeError("verification_plan must be an array")
        return cls(
            artifact_id=value["artifact_id"],
            artifact_version=value["artifact_version"],
            artifact_digest=value["artifact_digest"],
            payload_digest=value["payload_digest"],
            source_reference=value["source_reference"],
            knowledge_block_reference=value["knowledge_block_reference"],
            knowledge_block_digest=value["knowledge_block_digest"],
            target_reference=value["target_reference"],
            cybercore_risk=value["cybercore_risk"],
            v_one_risk_class=value["v_one_risk_class"],
            signature_status=value["signature_status"],
            expected_effect=value["expected_effect"],
            verification_plan=tuple(plan),
            may_approve=value["may_approve"],
            may_authorize=value["may_authorize"],
            may_execute=value["may_execute"],
            production_effect=value["production_effect"],
            intake_digest=value["intake_digest"],
        )

    def _claims_without_digest(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "intake_type": INTAKE_TYPE,
            "source_system": SOURCE_SYSTEM,
            "cxp_schema": CXP_SCHEMA,
            "artifact_id": self.artifact_id,
            "artifact_version": self.artifact_version,
            "artifact_digest": self.artifact_digest,
            "payload_digest": self.payload_digest,
            "source_reference": self.source_reference,
            "knowledge_block_reference": self.knowledge_block_reference,
            "knowledge_block_digest": self.knowledge_block_digest,
            "target_reference": self.target_reference,
            "cybercore_risk": self.cybercore_risk,
            "v_one_risk_class": self.v_one_risk_class,
            "signature_status": self.signature_status,
            "expected_effect": self.expected_effect,
            "verification_plan": list(self.verification_plan),
            "may_approve": self.may_approve,
            "may_authorize": self.may_authorize,
            "may_execute": self.may_execute,
            "production_effect": self.production_effect,
        }

    def to_dict(self) -> dict[str, Any]:
        payload = self._claims_without_digest()
        payload["intake_digest"] = self.intake_digest
        return payload


def _require_exact_fields(value: Mapping[str, Any], expected: frozenset[str]) -> None:
    if not isinstance(value, Mapping):
        raise CyberCoreIntakeError(f"{INTAKE_TYPE} must be an object")
    actual = frozenset(value)
    if actual != expected:
        raise CyberCoreIntakeError(
            "CyberCore intake fields are invalid; "
            f"missing={sorted(expected - actual)}, unknown={sorted(actual - expected)}"
        )


def _require_text_tuple(values: tuple[str, ...], *, field: str) -> None:
    if not values or not all(isinstance(item, str) for item in values):
        raise CyberCoreIntakeError(f"{field} must be a non-empty tuple of strings")
    for item in values:
        _require_text(item, field=field)


def _require_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or "\x00" in value:
        raise CyberCoreIntakeError(f"{field} is invalid")
    return value


def _require_digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value.casefold() != value
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise CyberCoreIntakeError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
