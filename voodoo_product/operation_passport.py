from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .evidence_primitives import canonical_json
from .persistence import DatabaseRow, DatabaseStatement, ProductDatabaseAdapter

OPERATION_PASSPORT_SCHEMA = "vone.operation-passport/v1"
VERIFICATION_NOT_PERSISTED = "NOT_PERSISTED"
VERIFICATION_UNKNOWN = "UNKNOWN"

SELECT_OPERATION_PASSPORT = DatabaseStatement(
    name="operation_passport.select_by_execution",
    mode="read",
    sqlite_sql="""
        SELECT
            snapshot.id AS snapshot_row_id,
            snapshot.execution_id AS snapshot_execution_id,
            snapshot.request_id AS snapshot_request_id,
            snapshot.actor_id AS snapshot_actor_id,
            snapshot.workspace_id AS snapshot_workspace_id,
            snapshot.environment AS snapshot_environment,
            snapshot.review_content_sha256 AS snapshot_review_content_sha256,
            snapshot.snapshot_digest AS snapshot_row_digest,
            snapshot.snapshot_json,
            snapshot.execution_target_json,
            snapshot.approval_evidence_json,
            grant_row.grant_id AS grant_row_id,
            grant_row.grant_digest AS grant_row_digest,
            grant_row.grant_json,
            consumption.consumption_id AS consumption_row_id,
            consumption.consumption_digest AS consumption_row_digest,
            consumption.consumption_json,
            outbox.outbox_id AS outbox_row_id,
            outbox.entry_digest AS outbox_row_digest,
            outbox.entry_json,
            inbox.admission_id AS inbox_row_id,
            inbox.admission_digest AS inbox_row_digest,
            inbox.admission_json,
            epoch.current_epoch,
            epoch.current_lease_id,
            epoch.current_lease_digest,
            epoch.status AS epoch_status,
            epoch.completion_digest,
            epoch.completed_at,
            epoch.updated_at AS epoch_updated_at,
            lease.lease_id AS lease_row_id,
            lease.lease_digest AS lease_row_digest,
            lease.lease_json
        FROM authorization_snapshots AS snapshot
        LEFT JOIN execution_grants_v2 AS grant_row
          ON grant_row.execution_id = snapshot.execution_id
        LEFT JOIN grant_consumptions_v1 AS consumption
          ON consumption.execution_id = snapshot.execution_id
        LEFT JOIN dispatch_outbox_v1 AS outbox
          ON outbox.execution_id = snapshot.execution_id
        LEFT JOIN dispatch_inbox_v1 AS inbox
          ON inbox.execution_id = snapshot.execution_id
        LEFT JOIN execution_epoch_state_v1 AS epoch
          ON epoch.execution_id = snapshot.execution_id
        LEFT JOIN execution_leases_v1 AS lease
          ON lease.lease_id = epoch.current_lease_id
        WHERE snapshot.execution_id = ?
    """,
)


@dataclass(frozen=True, slots=True)
class OperationPassport:
    execution_id: str
    lifecycle_stage: str
    operation: dict[str, Any]
    authority: dict[str, Any]
    dispatch: dict[str, Any]
    runtime: dict[str, Any]
    verification: dict[str, Any]
    integrity: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": OPERATION_PASSPORT_SCHEMA,
            "execution_id": self.execution_id,
            "lifecycle_stage": self.lifecycle_stage,
            "operation": dict(self.operation),
            "authority": dict(self.authority),
            "dispatch": dict(self.dispatch),
            "runtime": dict(self.runtime),
            "verification": dict(self.verification),
            "integrity": dict(self.integrity),
        }


class OperationPassportService:
    """Read-only projection over existing canonical durable operation state.

    The service owns no persistence and creates no authority. It reads the exact ProductService
    database and refuses to project non-canonical JSON or broken cross-row lineage. Independent
    VerificationResult/v1 is intentionally not inferred from execution completion or evidence
    integrity because current READ verification results are not durably persisted in this schema.
    """

    def __init__(self, *, database: ProductDatabaseAdapter) -> None:
        self.db = database

    def get(self, execution_id: str) -> OperationPassport:
        normalized_execution_id = _require_identifier(execution_id, field="execution_id")
        with self.db.connect() as connection:
            row = connection.execute(
                SELECT_OPERATION_PASSPORT,
                (normalized_execution_id,),
            ).fetchone()
        if row is None:
            raise LookupError("canonical operation passport not found")
        return self._project(row)

    @classmethod
    def _project(cls, row: DatabaseRow) -> OperationPassport:
        snapshot = _decode_canonical_object(row["snapshot_json"], field="snapshot_json")
        target = _decode_canonical_object(
            row["execution_target_json"],
            field="execution_target_json",
        )
        approval = _decode_canonical_object(
            row["approval_evidence_json"],
            field="approval_evidence_json",
        )
        _require_claim_bindings(
            snapshot,
            {
                "snapshot_id": row["snapshot_row_id"],
                "execution_id": row["snapshot_execution_id"],
                "request_id": row["snapshot_request_id"],
                "actor_id": row["snapshot_actor_id"],
                "workspace_id": row["snapshot_workspace_id"],
                "environment": row["snapshot_environment"],
                "review_content_sha256": row["snapshot_review_content_sha256"],
                "snapshot_digest": row["snapshot_row_digest"],
            },
            contract="authorization snapshot",
        )
        _require_claim_bindings(
            snapshot,
            {
                "target_kind": target.get("target_kind"),
                "target_digest": target.get("target_digest"),
                "approval_set_digest": approval.get("approval_set_digest"),
            },
            contract="authorization snapshot child",
        )

        grant = _decode_optional_contract(row["grant_json"], field="grant_json")
        consumption = _decode_optional_contract(
            row["consumption_json"],
            field="consumption_json",
        )
        outbox = _decode_optional_contract(row["entry_json"], field="entry_json")
        inbox = _decode_optional_contract(row["admission_json"], field="admission_json")
        lease = _decode_optional_contract(row["lease_json"], field="lease_json")

        _validate_optional_row_digest(
            grant,
            row_id=row["grant_row_id"],
            row_digest=row["grant_row_digest"],
            id_field="grant_id",
            digest_field="grant_digest",
            contract="execution grant",
        )
        _validate_optional_row_digest(
            consumption,
            row_id=row["consumption_row_id"],
            row_digest=row["consumption_row_digest"],
            id_field="consumption_id",
            digest_field="witness_digest",
            contract="grant consumption",
        )
        _validate_optional_row_digest(
            outbox,
            row_id=row["outbox_row_id"],
            row_digest=row["outbox_row_digest"],
            id_field="outbox_id",
            digest_field="entry_digest",
            contract="dispatch outbox",
        )
        _validate_optional_row_digest(
            inbox,
            row_id=row["inbox_row_id"],
            row_digest=row["inbox_row_digest"],
            id_field="admission_id",
            digest_field="admission_digest",
            contract="dispatch inbox",
        )
        _validate_optional_row_digest(
            lease,
            row_id=row["lease_row_id"],
            row_digest=row["lease_row_digest"],
            id_field="lease_id",
            digest_field="lease_digest",
            contract="execution lease",
        )

        cls._validate_lineage(
            snapshot=snapshot,
            grant=grant,
            consumption=consumption,
            outbox=outbox,
            inbox=inbox,
            lease=lease,
            row=row,
        )

        stage = _lifecycle_stage(
            grant=grant,
            consumption=consumption,
            outbox=outbox,
            inbox=inbox,
            lease=lease,
            epoch_status=row["epoch_status"],
        )
        execution_id = str(snapshot["execution_id"])

        authority = {
            "snapshot": {
                "snapshot_id": snapshot["snapshot_id"],
                "snapshot_digest": snapshot["snapshot_digest"],
                "authorized_at": snapshot["authorized_at"],
                "policy_version": snapshot["policy_version"],
                "policy_identity": snapshot["policy_identity"],
                "approval_set_digest": snapshot["approval_set_digest"],
                "approval_valid_until": snapshot["approval_valid_until"],
            },
            "grant": None if grant is None else {
                "grant_id": grant["grant_id"],
                "jti": grant["jti"],
                "grant_digest": grant["grant_digest"],
                "issued_at": grant["issued_at"],
                "expires_at": grant["expires_at"],
                "revocation_epoch": grant["revocation_epoch"],
                "use_semantics": grant["use_semantics"],
            },
            "consumption": None if consumption is None else {
                "consumption_id": consumption["consumption_id"],
                "consumption_digest": consumption["witness_digest"],
                "consumed_at": consumption["consumed_at"],
                "authority_revision": consumption["authority_revision"],
            },
        }
        dispatch = {
            "outbox": None if outbox is None else {
                "outbox_id": outbox["outbox_id"],
                "entry_digest": outbox["entry_digest"],
                "created_at": outbox["created_at"],
            },
            "inbox": None if inbox is None else {
                "admission_id": inbox["admission_id"],
                "admission_digest": inbox["admission_digest"],
                "dispatch_id": inbox["dispatch_id"],
                "envelope_digest": inbox["envelope_digest"],
            },
        }
        runtime = {
            "status": "NOT_STARTED" if row["epoch_status"] is None else str(row["epoch_status"]),
            "execution_epoch": row["current_epoch"],
            "execution_capsule_digest": _first_present(
                lease,
                inbox,
                outbox,
                grant,
                key="execution_capsule_digest",
            ),
            "runner_class": _first_present(lease, inbox, outbox, consumption, key="runner_class"),
            "current_lease": None if lease is None else {
                "lease_id": lease["lease_id"],
                "lease_digest": lease["lease_digest"],
                "acquired_at": lease["acquired_at"],
                "expires_at": lease["expires_at"],
            },
            "completion_digest": row["completion_digest"],
            "completed_at": row["completed_at"],
            "updated_at": row["epoch_updated_at"],
        }
        verification = {
            "status": VERIFICATION_NOT_PERSISTED,
            "verdict": VERIFICATION_UNKNOWN,
            "result_digest": None,
            "independent_verification_exposed": False,
            "reason": (
                "No durable VerificationResult/v1 is stored for this execution; "
                "execution/runtime state must not be promoted to VERIFIED."
            ),
        }
        operation = {
            "request_id": snapshot["request_id"],
            "actor_id": snapshot["actor_id"],
            "workspace_id": snapshot["workspace_id"],
            "environment": snapshot["environment"],
            "capability": snapshot["capability"],
            "capability_definition_identity": snapshot["capability_definition_identity"],
            "target_kind": snapshot["target_kind"],
            "target_digest": snapshot["target_digest"],
            "payload_digest": snapshot["payload_digest"],
            "review_content_sha256": snapshot["review_content_sha256"],
        }
        return OperationPassport(
            execution_id=execution_id,
            lifecycle_stage=stage,
            operation=operation,
            authority=authority,
            dispatch=dispatch,
            runtime=runtime,
            verification=verification,
            integrity={
                "canonical_json_validated": True,
                "lineage_bindings_validated": True,
                "independent_verification_validated": False,
            },
        )

    @staticmethod
    def _validate_lineage(
        *,
        snapshot: dict[str, Any],
        grant: dict[str, Any] | None,
        consumption: dict[str, Any] | None,
        outbox: dict[str, Any] | None,
        inbox: dict[str, Any] | None,
        lease: dict[str, Any] | None,
        row: DatabaseRow,
    ) -> None:
        _require_parent_chain(grant, consumption, outbox, inbox, lease)
        if grant is not None:
            _require_claim_bindings(
                grant,
                {
                    "execution_id": snapshot["execution_id"],
                    "request_id": snapshot["request_id"],
                    "actor_id": snapshot["actor_id"],
                    "workspace_id": snapshot["workspace_id"],
                    "environment": snapshot["environment"],
                    "capability": snapshot["capability"],
                    "capability_definition_identity": snapshot["capability_definition_identity"],
                    "target_kind": snapshot["target_kind"],
                    "target_digest": snapshot["target_digest"],
                    "payload_digest": snapshot["payload_digest"],
                    "authorization_snapshot_digest": snapshot["snapshot_digest"],
                },
                contract="execution grant lineage",
            )
        if consumption is not None and grant is not None:
            _require_claim_bindings(
                consumption,
                {
                    "execution_id": grant["execution_id"],
                    "jti": grant["jti"],
                    "grant_id": grant["grant_id"],
                    "grant_digest": grant["grant_digest"],
                    "authorization_snapshot_digest": grant["authorization_snapshot_digest"],
                    "execution_capsule_digest": grant["execution_capsule_digest"],
                    "runner_class": grant["runner_class"],
                },
                contract="grant consumption lineage",
            )
        if outbox is not None and grant is not None and consumption is not None:
            _require_claim_bindings(
                outbox,
                {
                    "execution_id": grant["execution_id"],
                    "request_id": grant["request_id"],
                    "actor_id": grant["actor_id"],
                    "workspace_id": grant["workspace_id"],
                    "environment": grant["environment"],
                    "capability": grant["capability"],
                    "capability_definition_identity": grant["capability_definition_identity"],
                    "authorization_snapshot_digest": grant["authorization_snapshot_digest"],
                    "target_kind": grant["target_kind"],
                    "target_digest": grant["target_digest"],
                    "payload_digest": grant["payload_digest"],
                    "execution_capsule_digest": grant["execution_capsule_digest"],
                    "runner_class": grant["runner_class"],
                    "consumption_id": consumption["consumption_id"],
                    "consumption_witness_digest": consumption["witness_digest"],
                },
                contract="dispatch outbox lineage",
            )
        if inbox is not None and outbox is not None:
            _require_claim_bindings(
                inbox,
                {
                    "execution_id": outbox["execution_id"],
                    "workspace_id": outbox["workspace_id"],
                    "environment": outbox["environment"],
                    "execution_capsule_digest": outbox["execution_capsule_digest"],
                    "runner_class": outbox["runner_class"],
                    "outbox_id": outbox["outbox_id"],
                    "outbox_entry_digest": outbox["entry_digest"],
                },
                contract="dispatch inbox lineage",
            )
        if lease is not None and inbox is not None:
            _require_claim_bindings(
                lease,
                {
                    "execution_id": inbox["execution_id"],
                    "workspace_id": inbox["workspace_id"],
                    "environment": inbox["environment"],
                    "execution_capsule_digest": inbox["execution_capsule_digest"],
                    "runner_class": inbox["runner_class"],
                    "admission_id": inbox["admission_id"],
                    "admission_digest": inbox["admission_digest"],
                },
                contract="execution lease lineage",
            )
            if int(lease["execution_epoch"]) != int(row["current_epoch"]):
                raise RuntimeError("operation passport current epoch does not match current lease")
            if str(lease["lease_id"]) != str(row["current_lease_id"]):
                raise RuntimeError("operation passport current lease id does not match epoch state")
            if str(lease["lease_digest"]) != str(row["current_lease_digest"]):
                raise RuntimeError("operation passport current lease digest does not match epoch state")
        elif row["epoch_status"] is not None:
            raise RuntimeError("operation passport epoch state exists without current lease")


def _require_identifier(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 256 or "\x00" in value:
        raise ValueError(f"{field} is invalid")
    return value


def _decode_canonical_object(value: object, *, field: str) -> dict[str, Any]:
    if not isinstance(value, str):
        raise RuntimeError(f"operation passport {field} is missing")
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"operation passport {field} is not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise RuntimeError(f"operation passport {field} must be an object")
    if canonical_json(decoded) != value:
        raise RuntimeError(f"operation passport {field} is not canonical JSON")
    return decoded


def _decode_optional_contract(value: object, *, field: str) -> dict[str, Any] | None:
    return None if value is None else _decode_canonical_object(value, field=field)


def _require_claim_bindings(
    contract_value: dict[str, Any],
    expected: dict[str, object],
    *,
    contract: str,
) -> None:
    missing = sorted(field for field in expected if field not in contract_value)
    if missing:
        raise RuntimeError(f"operation passport {contract} fields missing: {missing}")
    mismatches = sorted(
        field
        for field, expected_value in expected.items()
        if contract_value[field] != expected_value
    )
    if mismatches:
        raise RuntimeError(f"operation passport {contract} bindings mismatch: {mismatches}")


def _validate_optional_row_digest(
    value: dict[str, Any] | None,
    *,
    row_id: object,
    row_digest: object,
    id_field: str,
    digest_field: str,
    contract: str,
) -> None:
    if value is None:
        if row_id is not None or row_digest is not None:
            raise RuntimeError(f"operation passport {contract} row exists without contract JSON")
        return
    _require_claim_bindings(
        value,
        {id_field: row_id, digest_field: row_digest},
        contract=contract,
    )


def _require_parent_chain(*values: dict[str, Any] | None) -> None:
    parent_seen_missing = False
    labels = ("grant", "consumption", "outbox", "inbox", "lease")
    for label, value in zip(labels, values, strict=True):
        if value is None:
            parent_seen_missing = True
        elif parent_seen_missing:
            raise RuntimeError(f"operation passport {label} exists without complete parent lineage")


def _lifecycle_stage(
    *,
    grant: dict[str, Any] | None,
    consumption: dict[str, Any] | None,
    outbox: dict[str, Any] | None,
    inbox: dict[str, Any] | None,
    lease: dict[str, Any] | None,
    epoch_status: object,
) -> str:
    if epoch_status == "COMPLETED":
        return "EXECUTION_COMPLETED"
    if lease is not None:
        if epoch_status != "ACTIVE":
            raise RuntimeError("operation passport active lease requires ACTIVE epoch state")
        return "EXECUTION_ACTIVE"
    if inbox is not None:
        return "DISPATCH_ADMITTED"
    if outbox is not None:
        return "DISPATCH_ENQUEUED"
    if consumption is not None:
        return "GRANT_CONSUMED"
    if grant is not None:
        return "GRANT_ISSUED"
    return "SNAPSHOT_CREATED"


def _first_present(*values: dict[str, Any] | None, key: str) -> object | None:
    for value in values:
        if value is not None and key in value:
            return value[key]
    return None
