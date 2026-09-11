from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from voodoo_product.cybercore_intake import (
    CyberCoreIntakeError,
    CyberCoreIntakeRecord,
)

ROOT = Path(__file__).resolve().parents[2]
DIGEST_A = hashlib.sha256(b"cxp artifact").hexdigest()
DIGEST_B = hashlib.sha256(b"payload").hexdigest()
DIGEST_C = hashlib.sha256(b"knowledge block").hexdigest()


def _record(**overrides: object) -> CyberCoreIntakeRecord:
    values: dict[str, object] = {
        "artifact_id": "WB-0042-read-only-intake",
        "artifact_version": "1.2.3",
        "artifact_digest": DIGEST_A,
        "payload_digest": DIGEST_B,
        "source_reference": "cybercore://work-block/WB-0042-read-only-intake",
        "knowledge_block_reference": "KB-0042",
        "knowledge_block_digest": DIGEST_C,
        "target_reference": "github:eimyroot/Voodoo-One",
        "cybercore_risk": "medium",
        "signature_status": "PRESENT_UNVERIFIED",
        "expected_effect": "MUTATION_PROPOSAL",
        "verification_plan": ("validate target identity", "verify post-state independently"),
    }
    values.update(overrides)
    return CyberCoreIntakeRecord.create(**values)  # type: ignore[arg-type]


def test_cybercore_intake_round_trips_with_deterministic_digest() -> None:
    record = _record()

    assert record.v_one_risk_class == "R2"
    assert CyberCoreIntakeRecord.from_dict(record.to_dict()) == record
    assert _record().intake_digest == record.intake_digest


def test_cybercore_intake_maps_risk_without_allowing_downgrade() -> None:
    payload = _record(cybercore_risk="critical").to_dict()

    assert payload["v_one_risk_class"] == "R4"
    payload["v_one_risk_class"] = "R1"
    with pytest.raises(CyberCoreIntakeError, match="risk mapping"):
        CyberCoreIntakeRecord.from_dict(payload)


def test_cybercore_intake_never_carries_v_one_authority() -> None:
    payload = _record().to_dict()

    for field in ("may_approve", "may_authorize", "may_execute", "production_effect"):
        assert payload[field] is False
        tampered = dict(payload)
        tampered[field] = True
        with pytest.raises(CyberCoreIntakeError, match="cannot carry V-One authority"):
            CyberCoreIntakeRecord.from_dict(tampered)


def test_cybercore_intake_digest_binds_knowledge_and_target() -> None:
    base = _record()
    changed_knowledge = _record(knowledge_block_digest=hashlib.sha256(b"changed").hexdigest())
    changed_target = _record(target_reference="github:eimyroot/other")

    assert base.intake_digest != changed_knowledge.intake_digest
    assert base.intake_digest != changed_target.intake_digest


def test_cybercore_intake_rejects_unknown_fields() -> None:
    payload = _record().to_dict()
    payload["surprise"] = "authority"

    with pytest.raises(CyberCoreIntakeError, match="unknown"):
        CyberCoreIntakeRecord.from_dict(payload)


def test_cybercore_intake_rejects_invalid_identifiers_and_digests() -> None:
    with pytest.raises(CyberCoreIntakeError, match="Work Block"):
        _record(artifact_id="../../payload")
    with pytest.raises(CyberCoreIntakeError, match="KB-XXXX"):
        _record(knowledge_block_reference="knowledge-42")
    with pytest.raises(CyberCoreIntakeError, match="lowercase SHA-256"):
        _record(artifact_digest=DIGEST_A.upper())


def test_cybercore_intake_requires_bounded_effect_and_verification_plan() -> None:
    with pytest.raises(CyberCoreIntakeError, match="expected_effect"):
        _record(expected_effect="EXECUTE_NOW")
    with pytest.raises(CyberCoreIntakeError, match="non-empty"):
        _record(verification_plan=())
    with pytest.raises(CyberCoreIntakeError, match="unique"):
        _record(verification_plan=("verify", "verify"))


def test_cybercore_intake_signature_status_is_explicit_but_not_authority() -> None:
    for status in (
        "NOT_PRESENT",
        "PRESENT_UNVERIFIED",
        "VERIFIED_VALID",
        "VERIFIED_INVALID",
    ):
        record = _record(signature_status=status)
        assert record.signature_status == status
        assert record.may_authorize is False
        assert record.may_execute is False


def test_cybercore_intake_module_has_no_runtime_or_cybercore_dependency() -> None:
    source = ROOT / "voodoo_product" / "cybercore_intake.py"
    source_text = source.read_text(encoding="utf-8")
    tree = ast.parse(source_text, filename=str(source))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert ".service" not in source_text
    assert ".persistence" not in source_text
    assert "fastapi" not in source_text.casefold()
    assert "subprocess" not in source_text
    assert "requests" not in source_text
    assert not any(module.startswith("cybercore") for module in imports)



def test_cybercore_intake_json_schema_preserves_fail_closed_boundary() -> None:
    schema = json.loads(
        (ROOT / "schemas" / "cybercore-intake-v1.schema.json").read_text(encoding="utf-8")
    )

    assert schema["additionalProperties"] is False
    properties = schema["properties"]
    assert properties["source_system"]["const"] == "CyberCore"
    assert properties["cxp_schema"]["const"] == "cxp/v1"
    assert properties["may_approve"]["const"] is False
    assert properties["may_authorize"]["const"] is False
    assert properties["may_execute"]["const"] is False
    assert properties["production_effect"]["const"] is False
    assert properties["verification_plan"]["minItems"] == 1
    assert properties["verification_plan"]["uniqueItems"] is True



def test_cybercore_intake_rejects_type_confusion_fail_closed() -> None:
    payload = _record().to_dict()
    payload["artifact_id"] = 42
    with pytest.raises(CyberCoreIntakeError, match="Work Block"):
        CyberCoreIntakeRecord.from_dict(payload)

    payload = _record().to_dict()
    payload["knowledge_block_reference"] = None
    with pytest.raises(CyberCoreIntakeError, match="KB-XXXX"):
        CyberCoreIntakeRecord.from_dict(payload)

    payload = _record().to_dict()
    payload["may_execute"] = 0
    with pytest.raises(CyberCoreIntakeError, match="cannot carry V-One authority"):
        CyberCoreIntakeRecord.from_dict(payload)

    with pytest.raises(CyberCoreIntakeError, match="cybercore_risk"):
        _record(cybercore_risk=["low"])
