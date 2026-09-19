from __future__ import annotations

from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any

import pytest

from voodoo_product.db import SQLiteProductDatabase
from voodoo_product.evidence_primitives import canonical_json
from voodoo_product.operation_passport import OperationPassportService

D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64
D4 = "4" * 64
D5 = "5" * 64
D6 = "6" * 64
D7 = "7" * 64
D8 = "8" * 64
D9 = "9" * 64
DA = "a" * 64
DB = "b" * 64
DC = "c" * 64
DD = "d" * 64
DE = "e" * 64


class Cursor:
    def __init__(self, row: dict[str, Any] | None) -> None:
        self.row = row

    def fetchone(self) -> dict[str, Any] | None:
        return self.row

    def fetchall(self) -> list[dict[str, Any]]:
        return [] if self.row is None else [self.row]


class Connection:
    def __init__(self, database: FakeDatabase) -> None:
        self.database = database

    def execute(self, statement: Any, parameters: Any = ()) -> Cursor:
        self.database.executed.append((statement.name, statement.mode, tuple(parameters)))
        return Cursor(self.database.row)

    def commit(self) -> None:
        raise AssertionError("operation passport must not commit")

    def rollback(self) -> None:
        raise AssertionError("operation passport must not roll back")

    def close(self) -> None:
        return None

    def __enter__(self) -> Connection:
        return self

    def __exit__(self, *_: object) -> bool:
        return False


class FakeDatabase:
    backend_name = "sqlite"
    write_serialization = "global"

    def __init__(self, row: dict[str, Any] | None) -> None:
        self.row = row
        self.executed: list[tuple[str, str, tuple[Any, ...]]] = []

    def initialize(self) -> None:
        return None

    def connect(self) -> Connection:
        return Connection(self)

    def transaction(self) -> AbstractContextManager[Any]:
        raise AssertionError("operation passport must not open a write transaction")

    def schema_version(self) -> int:
        return 14


def contract_row(*, epoch_status: str | None = "COMPLETED") -> dict[str, Any]:
    snapshot = {
        "snapshot_id": "snap-1",
        "execution_id": "exec-1",
        "request_id": "req-1",
        "actor_id": "usr-1",
        "workspace_id": "ws-1",
        "environment": "staging",
        "review_content_sha256": D1,
        "snapshot_digest": D2,
        "target_kind": "git_ref",
        "target_digest": D3,
        "approval_set_digest": D4,
        "authorized_at": "2026-09-17T12:00:00.000+00:00",
        "policy_version": "policy-v1",
        "policy_identity": D5,
        "approval_valid_until": "2026-09-17T12:10:00.000+00:00",
        "capability": "github.read-ref/v1",
        "capability_definition_identity": D6,
        "payload_digest": D7,
    }
    target = {"target_kind": "git_ref", "target_digest": D3}
    approval = {"approval_set_digest": D4}
    grant = {
        "grant_id": "grant-1",
        "jti": "jti-1",
        "grant_digest": D8,
        "execution_id": "exec-1",
        "request_id": "req-1",
        "actor_id": "usr-1",
        "workspace_id": "ws-1",
        "environment": "staging",
        "capability": "github.read-ref/v1",
        "capability_definition_identity": D6,
        "target_kind": "git_ref",
        "target_digest": D3,
        "payload_digest": D7,
        "authorization_snapshot_digest": D2,
        "execution_capsule_digest": D9,
        "runner_class": "github.runner/v1",
        "issued_at": "2026-09-17T12:00:01.000+00:00",
        "expires_at": "2026-09-17T12:05:01.000+00:00",
        "revocation_epoch": 3,
        "use_semantics": "ONE_TIME",
    }
    consumption = {
        "consumption_id": "consume-1",
        "witness_digest": DA,
        "execution_id": "exec-1",
        "jti": "jti-1",
        "grant_id": "grant-1",
        "grant_digest": D8,
        "authorization_snapshot_digest": D2,
        "execution_capsule_digest": D9,
        "runner_class": "github.runner/v1",
        "consumed_at": "2026-09-17T12:00:02.000+00:00",
        "authority_revision": "grant-consumption/r1",
    }
    outbox = {
        "outbox_id": "outbox-1",
        "entry_digest": DB,
        "execution_id": "exec-1",
        "request_id": "req-1",
        "actor_id": "usr-1",
        "workspace_id": "ws-1",
        "environment": "staging",
        "capability": "github.read-ref/v1",
        "capability_definition_identity": D6,
        "authorization_snapshot_digest": D2,
        "target_kind": "git_ref",
        "target_digest": D3,
        "payload_digest": D7,
        "execution_capsule_digest": D9,
        "runner_class": "github.runner/v1",
        "consumption_id": "consume-1",
        "consumption_witness_digest": DA,
        "created_at": "2026-09-17T12:00:02.000+00:00",
    }
    inbox = {
        "admission_id": DC,
        "admission_digest": DD,
        "dispatch_id": DE,
        "envelope_digest": "f" * 64,
        "execution_id": "exec-1",
        "workspace_id": "ws-1",
        "environment": "staging",
        "execution_capsule_digest": D9,
        "runner_class": "github.runner/v1",
        "outbox_id": "outbox-1",
        "outbox_entry_digest": DB,
    }
    lease = {
        "lease_id": "0" * 64,
        "lease_digest": "1" * 64,
        "execution_id": "exec-1",
        "workspace_id": "ws-1",
        "environment": "staging",
        "execution_capsule_digest": D9,
        "runner_class": "github.runner/v1",
        "admission_id": DC,
        "admission_digest": DD,
        "execution_epoch": 2,
        "acquired_at": "2026-09-17T12:00:03.000+00:00",
        "expires_at": "2026-09-17T12:03:03.000+00:00",
    }
    return {
        "snapshot_row_id": "snap-1",
        "snapshot_execution_id": "exec-1",
        "snapshot_request_id": "req-1",
        "snapshot_actor_id": "usr-1",
        "snapshot_workspace_id": "ws-1",
        "snapshot_environment": "staging",
        "snapshot_review_content_sha256": D1,
        "snapshot_row_digest": D2,
        "snapshot_json": canonical_json(snapshot),
        "execution_target_json": canonical_json(target),
        "approval_evidence_json": canonical_json(approval),
        "grant_row_id": "grant-1",
        "grant_row_digest": D8,
        "grant_json": canonical_json(grant),
        "consumption_row_id": "consume-1",
        "consumption_row_digest": DA,
        "consumption_json": canonical_json(consumption),
        "outbox_row_id": "outbox-1",
        "outbox_row_digest": DB,
        "entry_json": canonical_json(outbox),
        "inbox_row_id": DC,
        "inbox_row_digest": DD,
        "admission_json": canonical_json(inbox),
        "current_epoch": 2 if epoch_status is not None else None,
        "current_lease_id": lease["lease_id"] if epoch_status is not None else None,
        "current_lease_digest": lease["lease_digest"] if epoch_status is not None else None,
        "epoch_status": epoch_status,
        "completion_digest": "2" * 64 if epoch_status == "COMPLETED" else None,
        "completed_at": "2026-09-17T12:01:00.000+00:00" if epoch_status == "COMPLETED" else None,
        "epoch_updated_at": "2026-09-17T12:01:00.000+00:00" if epoch_status is not None else None,
        "lease_row_id": lease["lease_id"] if epoch_status is not None else None,
        "lease_row_digest": lease["lease_digest"] if epoch_status is not None else None,
        "lease_json": canonical_json(lease) if epoch_status is not None else None,
    }


def test_completed_passport_projects_canonical_lineage_without_inventing_verification() -> None:
    database = FakeDatabase(contract_row())
    service = OperationPassportService(database=database)  # type: ignore[arg-type]

    passport = service.get("exec-1").to_dict()

    assert passport["schema"] == "vone.operation-passport/v1"
    assert passport["execution_id"] == "exec-1"
    assert passport["lifecycle_stage"] == "EXECUTION_COMPLETED"
    assert passport["operation"]["capability"] == "github.read-ref/v1"
    assert passport["authority"]["snapshot"]["snapshot_digest"] == D2
    assert passport["authority"]["grant"]["grant_digest"] == D8
    assert passport["authority"]["consumption"]["consumption_digest"] == DA
    assert passport["dispatch"]["outbox"]["entry_digest"] == DB
    assert passport["dispatch"]["inbox"]["admission_digest"] == DD
    assert passport["runtime"]["status"] == "COMPLETED"
    assert passport["runtime"]["execution_epoch"] == 2
    assert passport["verification"] == {
        "status": "NOT_PERSISTED",
        "verdict": "UNKNOWN",
        "result_digest": None,
        "independent_verification_exposed": False,
        "reason": (
            "No durable VerificationResult/v1 is stored for this execution; "
            "execution/runtime state must not be promoted to VERIFIED."
        ),
    }
    assert passport["integrity"]["lineage_bindings_validated"] is True
    assert passport["integrity"]["independent_verification_validated"] is False
    assert database.executed == [
        ("operation_passport.select_by_execution", "read", ("exec-1",))
    ]


def test_snapshot_only_passport_reports_partial_lifecycle_truthfully() -> None:
    row = contract_row(epoch_status=None)
    for prefix in ("grant", "consumption", "outbox", "inbox", "lease"):
        for key in list(row):
            if key.startswith(f"{prefix}_"):
                row[key] = None
    row["grant_json"] = None
    row["consumption_json"] = None
    row["entry_json"] = None
    row["admission_json"] = None
    row["lease_json"] = None
    database = FakeDatabase(row)

    passport = OperationPassportService(database=database).get("exec-1").to_dict()  # type: ignore[arg-type]

    assert passport["lifecycle_stage"] == "SNAPSHOT_CREATED"
    assert passport["authority"]["grant"] is None
    assert passport["authority"]["consumption"] is None
    assert passport["dispatch"]["outbox"] is None
    assert passport["dispatch"]["inbox"] is None
    assert passport["runtime"]["status"] == "NOT_STARTED"
    assert passport["runtime"]["current_lease"] is None
    assert passport["verification"]["verdict"] == "UNKNOWN"


def test_passport_rejects_broken_cross_row_lineage() -> None:
    row = contract_row()
    grant = dict(__import__("json").loads(row["grant_json"]))
    grant["target_digest"] = "0" * 64
    row["grant_json"] = canonical_json(grant)

    with pytest.raises(RuntimeError, match="execution grant lineage bindings mismatch"):
        OperationPassportService(database=FakeDatabase(row)).get("exec-1")  # type: ignore[arg-type]


def test_passport_rejects_noncanonical_contract_json() -> None:
    row = contract_row()
    row["snapshot_json"] = '{"snapshot_id": "snap-1"}'

    with pytest.raises(RuntimeError, match="snapshot_json is not canonical JSON"):
        OperationPassportService(database=FakeDatabase(row)).get("exec-1")  # type: ignore[arg-type]


def test_unknown_execution_is_not_promoted_from_legacy_execution_state() -> None:
    service = OperationPassportService(database=FakeDatabase(None))  # type: ignore[arg-type]

    with pytest.raises(LookupError, match="canonical operation passport not found"):
        service.get("exec-404")


def test_passport_select_executes_against_current_sqlite_schema(tmp_path: Path) -> None:
    database = SQLiteProductDatabase(tmp_path / "product.db")
    database.initialize()
    service = OperationPassportService(database=database)

    with pytest.raises(LookupError, match="canonical operation passport not found"):
        service.get("exec-not-present")
