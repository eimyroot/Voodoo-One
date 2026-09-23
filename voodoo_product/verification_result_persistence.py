from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Final

from .evidence_primitives import canonical_json
from .persistence import (
    DatabaseIntegrityError,
    DatabaseRow,
    DatabaseStatement,
    ProductDatabaseAdapter,
)
from .verification_result import VerificationResult

MINIMUM_VERIFICATION_RESULT_SCHEMA_VERSION: Final = 15

_REQUIRED_COLUMNS: Final = {
    "execution_id",
    "execution_epoch",
    "target_digest",
    "runner_observation_digest",
    "verifier_observation_digest",
    "observed_post_state_digest",
    "verification_boundary_digest",
    "verifier_id",
    "verifier_identity_digest",
    "verification_strength_digest",
    "verification_strength_class",
    "verdict",
    "reason",
    "checked_at",
    "result_revision",
    "result_digest",
    "result_json",
}

_REQUIRED_TRIGGERS: Final = {
    "trg_verification_results_v1_binding_insert",
    "trg_verification_results_v1_immutable_update",
    "trg_verification_results_v1_immutable_delete",
}

SELECT_VERIFICATION_RESULT_BY_EXECUTION = DatabaseStatement(
    name="verification_results.select_by_execution",
    mode="read",
    sqlite_sql="""
        SELECT execution_id, execution_epoch, target_digest,
               runner_observation_digest, verifier_observation_digest,
               observed_post_state_digest, verification_boundary_digest,
               verifier_id, verifier_identity_digest, verification_strength_digest,
               verification_strength_class, verdict, reason, checked_at,
               result_revision, result_digest, result_json
        FROM verification_results_v1
        WHERE execution_id = ?
    """,
)

INSERT_VERIFICATION_RESULT = DatabaseStatement(
    name="verification_results.insert",
    mode="write",
    sqlite_sql="""
        INSERT INTO verification_results_v1(
            execution_id, execution_epoch, target_digest,
            runner_observation_digest, verifier_observation_digest,
            observed_post_state_digest, verification_boundary_digest,
            verifier_id, verifier_identity_digest, verification_strength_digest,
            verification_strength_class, verdict, reason, checked_at,
            result_revision, result_digest, result_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
)


class VerificationResultPersistenceConflict(RuntimeError):
    """A different final verification result already exists for one execution."""


class VerificationResultPersistenceDenied(PermissionError):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True, slots=True)
class DurableVerificationResultStore:
    """Store one immutable final VerificationResult/v1 in canonical SQLite truth."""

    db: ProductDatabaseAdapter

    def __post_init__(self) -> None:
        if not isinstance(self.db, ProductDatabaseAdapter):
            raise ValueError("database must implement ProductDatabaseAdapter")
        if self.db.backend_name != "sqlite" or self.db.write_serialization != "global":
            raise RuntimeError("durable verification result store requires released SQLite")
        if self.db.schema_version() < MINIMUM_VERIFICATION_RESULT_SCHEMA_VERSION:
            raise RuntimeError("durable verification result store requires schema version 15 or newer")
        self._validate_schema()

    def get(self, execution_id: str) -> VerificationResult | None:
        if not isinstance(execution_id, str) or not execution_id or "\x00" in execution_id:
            raise ValueError("execution_id is invalid")
        with self.db.connect() as connection:
            row = connection.execute(
                SELECT_VERIFICATION_RESULT_BY_EXECUTION,
                (execution_id,),
            ).fetchone()
        return None if row is None else self._decode_row(row)

    def store(self, *, result: VerificationResult) -> VerificationResult:
        if not isinstance(result, VerificationResult):
            raise ValueError("result must be VerificationResult")

        with self.db.transaction() as connection:
            existing_row = connection.execute(
                SELECT_VERIFICATION_RESULT_BY_EXECUTION,
                (result.execution_id,),
            ).fetchone()
            if existing_row is not None:
                existing = self._decode_row(existing_row)
                if existing != result:
                    raise VerificationResultPersistenceConflict(
                        "VERIFICATION_RESULT_CONFLICT"
                    )
                return existing

            try:
                connection.execute(
                    INSERT_VERIFICATION_RESULT,
                    self._parameters(result),
                )
            except DatabaseIntegrityError as exc:
                raise VerificationResultPersistenceDenied(
                    "VERIFICATION_RESULT_PERSISTENCE_DENIED"
                ) from exc

        return result

    @staticmethod
    def _parameters(result: VerificationResult) -> tuple[object, ...]:
        return (
            result.execution_id,
            result.execution_epoch,
            result.target_digest,
            result.runner_observation_digest,
            result.verifier_observation_digest,
            result.observed_post_state_digest,
            result.verification_boundary_digest,
            result.verifier_id,
            result.verifier_identity_digest,
            result.verification_strength_digest,
            result.verification_strength_class,
            result.verdict,
            result.reason,
            result.checked_at,
            result.result_revision,
            result.result_digest,
            canonical_json(result.to_dict()),
        )

    @classmethod
    def _decode_row(cls, row: DatabaseRow) -> VerificationResult:
        try:
            raw_json = str(row["result_json"])
            raw = json.loads(raw_json)
            if not isinstance(raw, dict) or canonical_json(raw) != raw_json:
                raise ValueError("result_json is not canonical")
            result = VerificationResult.from_dict(raw)
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise VerificationResultPersistenceDenied(
                "VERIFICATION_RESULT_ROW_INVALID"
            ) from exc

        expected = {
            "execution_id": result.execution_id,
            "execution_epoch": result.execution_epoch,
            "target_digest": result.target_digest,
            "runner_observation_digest": result.runner_observation_digest,
            "verifier_observation_digest": result.verifier_observation_digest,
            "observed_post_state_digest": result.observed_post_state_digest,
            "verification_boundary_digest": result.verification_boundary_digest,
            "verifier_id": result.verifier_id,
            "verifier_identity_digest": result.verifier_identity_digest,
            "verification_strength_digest": result.verification_strength_digest,
            "verification_strength_class": result.verification_strength_class,
            "verdict": result.verdict,
            "reason": result.reason,
            "checked_at": result.checked_at,
            "result_revision": result.result_revision,
            "result_digest": result.result_digest,
        }
        if {key: row[key] for key in expected} != expected:
            raise VerificationResultPersistenceDenied(
                "VERIFICATION_RESULT_ROW_BINDING_INVALID"
            )
        return result

    def _validate_schema(self) -> None:
        with self.db.connect() as connection:
            columns = {
                str(row["name"])
                for row in connection.execute(
                    'PRAGMA table_info("verification_results_v1")'
                ).fetchall()
            }
            if columns != _REQUIRED_COLUMNS:
                raise RuntimeError(
                    "verification result schema validation failed: "
                    f"expected {sorted(_REQUIRED_COLUMNS)}, found {sorted(columns)}"
                )
            triggers = {
                str(row["name"])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'trigger'"
                ).fetchall()
            }
            missing = _REQUIRED_TRIGGERS - triggers
            if missing:
                raise RuntimeError(
                    "verification result schema validation failed: missing triggers "
                    f"{sorted(missing)}"
                )
