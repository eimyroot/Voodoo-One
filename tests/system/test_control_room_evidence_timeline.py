from __future__ import annotations

from voodoo_product.operation_passport import OperationPassport
from voodoo_product.service import ProductService

D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64
D4 = "4" * 64
D5 = "5" * 64
D6 = "6" * 64


def _passport(*, verified: bool) -> OperationPassport:
    verification: dict[str, object] = {
        "status": "NOT_PERSISTED",
        "verdict": "UNKNOWN",
        "result_digest": None,
        "independent_verification_exposed": False,
        "reason": "No durable VerificationResult/v1 is stored.",
    }
    if verified:
        verification = {
            "status": "PERSISTED",
            "verdict": "VERIFIED",
            "result_digest": D6,
            "independent_verification_exposed": True,
            "reason": "OBSERVED_STATE_MATCH",
            "checked_at": "2026-09-20T00:00:06.000+00:00",
            "verification_strength_class": "INDEPENDENT_PROVIDER_READBACK",
        }
    return OperationPassport(
        execution_id="exec-canonical-1",
        lifecycle_stage="EXECUTION_COMPLETED",
        operation={
            "request_id": "req-1",
            "capability": "github.read-ref/v1",
        },
        authority={
            "snapshot": {
                "snapshot_digest": D1,
                "authorized_at": "2026-09-20T00:00:00.000+00:00",
            },
            "grant": {
                "grant_digest": D2,
                "issued_at": "2026-09-20T00:00:01.000+00:00",
            },
            "consumption": {
                "consumption_digest": D3,
                "consumed_at": "2026-09-20T00:00:02.000+00:00",
            },
        },
        dispatch={
            "outbox": {
                "entry_digest": D4,
                "created_at": "2026-09-20T00:00:03.000+00:00",
            },
            "inbox": None,
        },
        runtime={
            "status": "COMPLETED",
            "execution_capsule_digest": D5,
            "completion_digest": D5,
            "completed_at": "2026-09-20T00:00:05.000+00:00",
            "updated_at": "2026-09-20T00:00:05.000+00:00",
        },
        verification=verification,
        integrity={
            "canonical_json_validated": True,
            "lineage_bindings_validated": True,
            "independent_verification_validated": verified,
        },
    )


def test_canonical_global_timeline_does_not_invent_missing_verification_event() -> None:
    items = ProductService._canonical_evidence_items([_passport(verified=False)])

    assert {item["kind"] for item in items} == {
        "CANONICAL_AUTHORIZATION",
        "CANONICAL_GRANT",
        "CANONICAL_GRANT_CONSUMPTION",
        "CANONICAL_DISPATCH",
        "CANONICAL_RUNTIME",
    }
    assert all(item["source"] == "OPERATION_PASSPORT" for item in items)
    assert all(item["execution_id"] == "exec-canonical-1" for item in items)
    assert not any(item["kind"] == "CANONICAL_VERIFICATION" for item in items)
    runtime = next(item for item in items if item["kind"] == "CANONICAL_RUNTIME")
    assert "verification NOT_PERSISTED / UNKNOWN" in runtime["detail"]


def test_canonical_global_timeline_exposes_real_durable_verification() -> None:
    items = ProductService._canonical_evidence_items([_passport(verified=True)])

    verification = next(
        item for item in items if item["kind"] == "CANONICAL_VERIFICATION"
    )
    assert verification["status"] == "VERIFIED"
    assert verification["timestamp"] == "2026-09-20T00:00:06.000+00:00"
    assert verification["reference"] == D6
    assert "INDEPENDENT_PROVIDER_READBACK" in verification["detail"]


def test_global_timeline_preserves_canonical_and_legacy_visibility() -> None:
    audits = [
        {
            "id": f"audit-{index}",
            "action": "TEST_EVENT",
            "created_at": f"2026-09-19T23:5{index}:00.000+00:00",
            "target_type": "test",
        }
        for index in range(6)
    ]
    timeline = ProductService._evidence_timeline(
        change_requests=[],
        executions=[],
        receipts=[],
        audits=audits,
        canonical_passports=[_passport(verified=True)],
    )

    canonical = [item for item in timeline if item["source"] == "OPERATION_PASSPORT"]
    legacy = [item for item in timeline if item["source"] != "OPERATION_PASSPORT"]
    assert len(timeline) == 12
    assert len(canonical) == 6
    assert len(legacy) == 6
    assert {item["source"] for item in legacy} == {"AUDIT_LEDGER"}
    assert any(item["kind"] == "CANONICAL_VERIFICATION" for item in canonical)
