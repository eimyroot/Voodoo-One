"""Read-only structural verification of one V-One to CASEBOOK handoff.

The verifier correlates an immutable ExecutionGrant/v2 and its one-time
GrantConsumptionWitness/v1 with one append-only CASEBOOK CONTEXT event.  It
does not write either database, authorize execution, attest identity, or
claim independent verification of the executed effect.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final

from .authoritative_grant import ExecutionGrantV2
from .evidence_primitives import canonical_json
from .grant_consumption import GrantConsumptionWitness
from .operation_passport import OperationPassport

HANDOFF_SCHEMA: Final = "voodoo-casebook/v-one-execution-handoff/v1"
CASEBOOK_EVENT_SCHEMA: Final = "voodoo-casebook/event/v1"
CASEBOOK_GENESIS_HASH: Final = "0" * 64
_CASEBOOK_EVENT_TYPES: Final = {
    "GOAL", "CONTEXT", "IDEA", "DECISION", "ISSUE", "TODO",
    "COMMAND_PLAN", "COMMAND_RESULT", "EVIDENCE", "LINK", "BLOCKER",
    "RISK", "LEARNING", "RESULT", "CANONICAL_CANDIDATE",
}
_CASEBOOK_SOURCES: Final = {"user", "assistant", "tool", "system"}
_CASEBOOK_STATUSES: Final = {"OPEN", "RESOLVED", "SUPERSEDED", "CANDIDATE"}

_VONE_TABLE_COLUMNS: Final = {
    "execution_grants_v2": {
        "jti", "grant_id", "execution_id", "request_id", "workspace_id",
        "environment", "authorization_snapshot_digest",
        "execution_capsule_digest", "grant_digest", "grant_json",
    },
    "grant_consumptions_v1": {
        "consumption_id", "jti", "grant_digest", "execution_id",
        "authorization_snapshot_digest", "execution_capsule_digest",
        "runner_class", "consumption_digest", "consumption_json",
    },
}
_VONE_TRIGGERS: Final = {
    "trg_execution_grants_v2_snapshot_binding_insert",
    "trg_execution_grants_v2_immutable_update",
    "trg_execution_grants_v2_immutable_delete",
    "trg_grant_consumptions_v1_grant_binding_insert",
    "trg_grant_consumptions_v1_immutable_update",
    "trg_grant_consumptions_v1_immutable_delete",
}
_CASEBOOK_TABLE_COLUMNS: Final = {
    "meta": {"id", "schema_version", "head_seq", "head_hash"},
    "sessions": {"session_id", "project", "goal", "created_at"},
    "events": {
        "seq", "event_id", "session_id", "project", "timestamp", "type",
        "summary", "source", "evidence_refs_json", "status",
        "metadata_json", "prev_hash", "event_hash",
    },
}
_CASEBOOK_TRIGGERS: Final = {
    "events_no_update", "events_no_delete",
    "sessions_no_update", "sessions_no_delete",
}
_TRIGGER_MARKERS: Final = {
    "trg_execution_grants_v2_snapshot_binding_insert": (
        "BEFORE INSERT ON EXECUTION_GRANTS_V2", "RAISE(ABORT",
    ),
    "trg_execution_grants_v2_immutable_update": (
        "BEFORE UPDATE ON EXECUTION_GRANTS_V2", "RAISE(ABORT",
    ),
    "trg_execution_grants_v2_immutable_delete": (
        "BEFORE DELETE ON EXECUTION_GRANTS_V2", "RAISE(ABORT",
    ),
    "trg_grant_consumptions_v1_grant_binding_insert": (
        "BEFORE INSERT ON GRANT_CONSUMPTIONS_V1", "RAISE(ABORT",
    ),
    "trg_grant_consumptions_v1_immutable_update": (
        "BEFORE UPDATE ON GRANT_CONSUMPTIONS_V1", "RAISE(ABORT",
    ),
    "trg_grant_consumptions_v1_immutable_delete": (
        "BEFORE DELETE ON GRANT_CONSUMPTIONS_V1", "RAISE(ABORT",
    ),
    "events_no_update": ("BEFORE UPDATE ON EVENTS", "RAISE(ABORT"),
    "events_no_delete": ("BEFORE DELETE ON EVENTS", "RAISE(ABORT"),
    "sessions_no_update": ("BEFORE UPDATE ON SESSIONS", "RAISE(ABORT"),
    "sessions_no_delete": ("BEFORE DELETE ON SESSIONS", "RAISE(ABORT"),
}
_HANDOFF_FIELDS: Final = {
    "schema", "execution_id", "request_id", "workspace_id", "environment",
    "grant_digest", "consumption_witness_digest", "payload_digest",
    "target_digest",
}


class CasebookHandoffRejected(RuntimeError):
    """The local records cannot support the requested structural claim."""


@dataclass(frozen=True, slots=True)
class CasebookHandoffVerification:
    schema: str
    verdict: str
    execution_id: str
    request_id: str
    workspace_id: str
    environment: str
    session_id: str
    grant_digest: str
    consumption_witness_digest: str
    casebook_event_hash: str
    independent_identity_attested: bool
    production_connected: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _reject(condition: bool, reason: str) -> None:
    if not condition:
        raise CasebookHandoffRejected(reason)


def _database_path(value: Path, *, label: str) -> Path:
    path = Path(value)
    _reject(path.is_absolute(), f"{label} database path must be absolute")
    _reject(not path.is_symlink(), f"{label} database must not be a symlink")
    _reject(path.is_file(), f"{label} database is unavailable")
    _reject(path.resolve() == path, f"{label} database path must be canonical")
    return path


def _open_read_only(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(
        path.as_uri() + "?mode=ro", uri=True, isolation_level=None, timeout=10,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    connection.execute("PRAGMA trusted_schema=OFF")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("BEGIN")
    return connection


def _verify_sqlite(connection: sqlite3.Connection, *, label: str) -> None:
    row = connection.execute("PRAGMA integrity_check").fetchone()
    _reject(row is not None and row[0] == "ok", f"{label} integrity check failed")


def _verify_schema(
    connection: sqlite3.Connection,
    *,
    tables: dict[str, set[str]],
    triggers: set[str],
    label: str,
) -> None:
    for table, required in tables.items():
        actual = {
            row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')
        }
        _reject(required.issubset(actual), f"{label} table contract is incomplete")
    actual_triggers = {
        row[0]: row[1] for row in connection.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='trigger'"
        )
    }
    _reject(triggers.issubset(actual_triggers), f"{label} immutability contract is incomplete")
    for name in triggers:
        sql = actual_triggers[name]
        normalized = " ".join(sql.upper().split()) if isinstance(sql, str) else ""
        _reject(
            all(marker in normalized for marker in _TRIGGER_MARKERS[name]),
            f"{label} trigger contract is invalid",
        )


def _json_object(raw: object, *, label: str) -> dict[str, Any]:
    _reject(isinstance(raw, str), f"{label} must be JSON text")
    try:
        value = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise CasebookHandoffRejected(f"{label} is invalid JSON") from exc
    _reject(type(value) is dict, f"{label} must be a JSON object")
    _reject(canonical_json(value) == raw, f"{label} must be canonical JSON")
    return value


def _casebook_json(row: sqlite3.Row) -> tuple[list[str], dict[str, Any]]:
    try:
        refs = json.loads(row["evidence_refs_json"])
    except (TypeError, ValueError) as exc:
        raise CasebookHandoffRejected("CASEBOOK evidence references are invalid") from exc
    metadata = _json_object(row["metadata_json"], label="CASEBOOK event metadata")
    _reject(
        isinstance(refs, list)
        and len(refs) <= 32
        and all(isinstance(item, str) and 0 < len(item) <= 1024 for item in refs)
        and canonical_json(refs) == row["evidence_refs_json"],
        "CASEBOOK evidence references are invalid",
    )
    _reject(
        len(row["metadata_json"].encode("utf-8")) <= 8192,
        "CASEBOOK event metadata is too large",
    )
    return refs, metadata


def _read_vone(
    connection: sqlite3.Connection,
    *,
    execution_id: str,
    workspace_id: str,
) -> tuple[ExecutionGrantV2, GrantConsumptionWitness]:
    _verify_sqlite(connection, label="V-One")
    _verify_schema(
        connection,
        tables=_VONE_TABLE_COLUMNS,
        triggers=_VONE_TRIGGERS,
        label="V-One",
    )
    rows = connection.execute(
        """
        SELECT
            grant_row.*,
            consumption.consumption_id AS c_consumption_id,
            consumption.jti AS c_jti,
            consumption.grant_digest AS c_grant_digest,
            consumption.execution_id AS c_execution_id,
            consumption.authorization_snapshot_digest AS c_snapshot_digest,
            consumption.execution_capsule_digest AS c_capsule_digest,
            consumption.runner_class AS c_runner_class,
            consumption.consumption_digest AS c_consumption_digest,
            consumption.consumption_json AS c_consumption_json
        FROM execution_grants_v2 AS grant_row
        LEFT JOIN grant_consumptions_v1 AS consumption
          ON consumption.execution_id = grant_row.execution_id
        WHERE grant_row.execution_id = ?
        """,
        (execution_id,),
    ).fetchall()
    _reject(len(rows) == 1, "exactly one execution grant is required")
    row = rows[0]
    _reject(row["c_consumption_id"] is not None, "grant consumption is missing")
    try:
        grant = ExecutionGrantV2.from_dict(
            _json_object(row["grant_json"], label="execution grant")
        )
        witness = GrantConsumptionWitness.from_dict(
            _json_object(row["c_consumption_json"], label="grant consumption")
        )
    except ValueError as exc:
        raise CasebookHandoffRejected("V-One contract validation failed") from exc
    _reject(grant.execution_id == execution_id, "execution grant binding mismatch")
    _reject(grant.workspace_id == workspace_id, "execution workspace mismatch")
    _reject(grant.environment != "production", "production handoff is not supported")
    grant_bindings = {
        "jti": row["jti"], "grant_id": row["grant_id"],
        "execution_id": row["execution_id"], "request_id": row["request_id"],
        "workspace_id": row["workspace_id"], "environment": row["environment"],
        "authorization_snapshot_digest": row["authorization_snapshot_digest"],
        "execution_capsule_digest": row["execution_capsule_digest"],
        "grant_digest": row["grant_digest"],
    }
    _reject(
        all(getattr(grant, key) == value for key, value in grant_bindings.items()),
        "execution grant row does not match its contract",
    )
    consumption_bindings = {
        "consumption_id": row["c_consumption_id"], "jti": row["c_jti"],
        "grant_digest": row["c_grant_digest"],
        "execution_id": row["c_execution_id"],
        "authorization_snapshot_digest": row["c_snapshot_digest"],
        "execution_capsule_digest": row["c_capsule_digest"],
        "runner_class": row["c_runner_class"],
        "witness_digest": row["c_consumption_digest"],
    }
    _reject(
        all(getattr(witness, key) == value for key, value in consumption_bindings.items()),
        "grant consumption row does not match its contract",
    )
    _reject(
        all(
            getattr(witness, key) == getattr(grant, key)
            for key in (
                "execution_id", "jti", "grant_id", "grant_digest",
                "authorization_snapshot_digest", "execution_capsule_digest", "runner_class",
            )
        ),
        "consumption grant binding mismatch",
    )
    return grant, witness


def _casebook_event(row: sqlite3.Row, refs: list[Any], metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": CASEBOOK_EVENT_SCHEMA,
        "seq": row["seq"], "event_id": row["event_id"],
        "session_id": row["session_id"], "project": row["project"],
        "timestamp": row["timestamp"], "type": row["type"],
        "summary": row["summary"], "source": row["source"],
        "evidence_refs": refs, "status": row["status"],
        "metadata": metadata, "prev_hash": row["prev_hash"],
    }


def _read_casebook(
    connection: sqlite3.Connection,
    *,
    session_id: str,
    expected_metadata: dict[str, Any],
) -> str:
    _verify_sqlite(connection, label="CASEBOOK")
    _verify_schema(
        connection,
        tables=_CASEBOOK_TABLE_COLUMNS,
        triggers=_CASEBOOK_TRIGGERS,
        label="CASEBOOK",
    )
    meta_rows = connection.execute(
        "SELECT id, schema_version, head_seq, head_hash FROM meta"
    ).fetchall()
    _reject(
        len(meta_rows) == 1 and meta_rows[0]["id"] == 1
        and meta_rows[0]["schema_version"] == 1,
        "CASEBOOK schema metadata is invalid",
    )
    sessions = {
        row["session_id"]: dict(row)
        for row in connection.execute(
            "SELECT session_id, project, goal, created_at FROM sessions"
        )
    }
    _reject(session_id in sessions, "CASEBOOK session is unavailable")
    previous = CASEBOOK_GENESIS_HASH
    matches: list[str] = []
    count = 0
    first_sessions: set[str] = set()
    for row in connection.execute("SELECT * FROM events ORDER BY seq"):
        count += 1
        _reject(row["seq"] == count, "CASEBOOK event sequence is not contiguous")
        _reject(row["prev_hash"] == previous, "CASEBOOK predecessor hash mismatch")
        session = sessions.get(row["session_id"])
        _reject(
            session is not None and row["project"] == session["project"],
            "CASEBOOK event session binding mismatch",
        )
        refs, metadata = _casebook_json(row)
        _reject(
            row["type"] in _CASEBOOK_EVENT_TYPES
            and row["source"] in _CASEBOOK_SOURCES
            and row["status"] in _CASEBOOK_STATUSES
            and isinstance(row["summary"], str)
            and 0 < len(row["summary"]) <= 8192
            and "\x00" not in row["summary"],
            "CASEBOOK event contract is invalid",
        )
        event = _casebook_event(row, refs, metadata)
        digest = hashlib.sha256(canonical_json(event).encode("utf-8")).hexdigest()
        _reject(digest == row["event_hash"], "CASEBOOK event digest mismatch")
        previous = digest
        if row["session_id"] not in first_sessions:
            _reject(
                row["type"] == "GOAL"
                and row["summary"] == session["goal"]
                and row["timestamp"] == session["created_at"],
                "CASEBOOK initial GOAL is invalid",
            )
            first_sessions.add(row["session_id"])
        if (
            row["session_id"] == session_id
            and row["type"] == "CONTEXT"
            and row["source"] == "system"
            and row["status"] == "OPEN"
            and metadata.get("schema") == HANDOFF_SCHEMA
        ):
            _reject(set(metadata) == _HANDOFF_FIELDS, "CASEBOOK handoff fields are invalid")
            if metadata == expected_metadata:
                matches.append(digest)
    _reject(first_sessions == set(sessions), "CASEBOOK session lacks an initial GOAL")
    head = meta_rows[0]
    _reject(
        head["head_seq"] == count and head["head_hash"] == previous,
        "CASEBOOK journal head mismatch",
    )
    _reject(len(matches) == 1, "exactly one matching CASEBOOK handoff is required")
    return matches[0]


def verify_casebook_handoff(
    *,
    vone_database: Path,
    casebook_database: Path,
    execution_id: str,
    workspace_id: str,
    session_id: str,
) -> CasebookHandoffVerification:
    """Verify one non-production local handoff without creating any effect."""
    for value, label in (
        (execution_id, "execution_id"),
        (workspace_id, "workspace_id"),
        (session_id, "session_id"),
    ):
        _reject(isinstance(value, str) and value == value.strip() and value, f"{label} is invalid")
    vone_path = _database_path(vone_database, label="V-One")
    casebook_path = _database_path(casebook_database, label="CASEBOOK")
    _reject(vone_path != casebook_path, "V-One and CASEBOOK databases must be separate")
    try:
        with closing(_open_read_only(vone_path)) as vone:
            grant, witness = _read_vone(
                vone, execution_id=execution_id, workspace_id=workspace_id,
            )
        metadata = {
            "schema": HANDOFF_SCHEMA,
            "execution_id": grant.execution_id,
            "request_id": grant.request_id,
            "workspace_id": grant.workspace_id,
            "environment": grant.environment,
            "grant_digest": grant.grant_digest,
            "consumption_witness_digest": witness.witness_digest,
            "payload_digest": grant.payload_digest,
            "target_digest": grant.target_digest,
        }
        with closing(_open_read_only(casebook_path)) as casebook:
            event_hash = _read_casebook(
                casebook, session_id=session_id, expected_metadata=metadata,
            )
    except sqlite3.Error as exc:
        raise CasebookHandoffRejected("local database verification failed") from exc
    return CasebookHandoffVerification(
        schema="voodoo-one/casebook-handoff-verification/v1",
        verdict="LOCAL_CROSS_DATABASE_STRUCTURAL_MATCH",
        execution_id=grant.execution_id,
        request_id=grant.request_id,
        workspace_id=grant.workspace_id,
        environment=grant.environment,
        session_id=session_id,
        grant_digest=grant.grant_digest,
        consumption_witness_digest=witness.witness_digest,
        casebook_event_hash=event_hash,
        independent_identity_attested=False,
        production_connected=False,
    )

def correlate_casebook_passport(
    *, handoff: CasebookHandoffVerification, passport: OperationPassport,
) -> dict[str, Any]:
    """Compare structural evidence with a native Passport, never authorize resume.

    Callers must separately establish current native authority and retrieve both
    inputs from their canonical sources. This is a pure candidate contract,
    not a runtime attachment or proof of identity.
    """
    _reject(
        isinstance(handoff, CasebookHandoffVerification)
        and isinstance(passport, OperationPassport)
        and handoff.verdict == "LOCAL_CROSS_DATABASE_STRUCTURAL_MATCH"
        and handoff.independent_identity_attested is False
        and handoff.production_connected is False
        and handoff.environment in {"local", "development", "staging"},
        "handoff structural claim is invalid",
    )
    _reject(
        passport.integrity.get("canonical_json_validated") is True
        and passport.integrity.get("lineage_bindings_validated") is True,
        "Passport lineage is not validated",
    )
    grant = passport.authority.get("grant")
    consumption = passport.authority.get("consumption")
    _reject(
        isinstance(grant, dict) and isinstance(consumption, dict)
        and passport.execution_id == handoff.execution_id
        and passport.operation.get("request_id") == handoff.request_id
        and passport.operation.get("workspace_id") == handoff.workspace_id
        and passport.operation.get("environment") == handoff.environment
        and grant.get("grant_digest") == handoff.grant_digest
        and consumption.get("consumption_digest") == handoff.consumption_witness_digest,
        "Passport handoff binding mismatch",
    )
    return {
        "schema": "voodoo-one/casebook-passport-correlation/v1",
        "verdict": "LOCAL_STRUCTURAL_PASSPORT_MATCH",
        "session_id": handoff.session_id,
        "execution_id": passport.execution_id,
        "request_id": handoff.request_id,
        "casebook_event_hash": handoff.casebook_event_hash,
        "execution_authorized_by_this_view": False,
        "execution_verified_by_this_view": False,
        "resume_authorized": False,
    }
