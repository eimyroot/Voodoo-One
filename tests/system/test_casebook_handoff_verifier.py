"""Disposable cross-database checks for the read-only CASEBOOK handoff verifier."""
from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from voodoo_product.casebook_handoff_verifier import (
    HANDOFF_SCHEMA,
    CasebookHandoffRejected,
    correlate_casebook_passport,
    verify_casebook_handoff,
)
from voodoo_product.evidence_primitives import canonical_json
from voodoo_product.operation_passport import OperationPassport

DIGESTS = [format(index, "x") * 64 for index in range(1, 16)]
EXECUTION = "exe_casebook_handoff_001"
REQUEST = "cr_casebook_handoff_001"
WORKSPACE = "wrk_casebook_handoff_001"
SESSION = "voodoo-one-casebook-handoff-test"


def _sealed_grant(*, environment: str = "staging") -> dict:
    value = {
        "schema_version": 2,
        "grant_type": "execution-grant/v2",
        "grant_id": "grant_casebook_001",
        "jti": "jti_casebook_001",
        "execution_id": EXECUTION,
        "request_id": REQUEST,
        "authorization_snapshot_digest": DIGESTS[0],
        "snapshot_authority_witness_set_digest": DIGESTS[1],
        "snapshot_authority_event_hash": DIGESTS[2],
        "parent_scope_digest": DIGESTS[3],
        "authority_constraint_digest": DIGESTS[4],
        "monotonic_authority_decision_digest": DIGESTS[5],
        "actor_id": "user_casebook_test",
        "workspace_id": WORKSPACE,
        "environment": environment,
        "capability": "casebook.test",
        "capability_definition_identity": DIGESTS[6],
        "target_kind": "casebook-session",
        "target_digest": DIGESTS[7],
        "payload_digest": DIGESTS[8],
        "policy_version": "test-policy/v1",
        "policy_identity": DIGESTS[9],
        "approval_set_digest": DIGESTS[10],
        "required_permission": "execution.run",
        "precondition_requirement_digest": DIGESTS[11],
        "precondition_expectation_digest": DIGESTS[12],
        "precondition_observation_digest": DIGESTS[13],
        "precondition_witness_digest": DIGESTS[14],
        "precondition_enforcement_class": "READ_THEN_COMPARE",
        "precondition_checked_at": "2026-11-25T12:00:00.000+00:00",
        "execution_binding_digest": DIGESTS[5],
        "execution_capsule_digest": DIGESTS[6],
        "runner_class": "synthetic-local-runner",
        "execution_binding_authority_revision": "test-binding-r1",
        "issued_at": "2026-11-25T12:00:01.000+00:00",
        "expires_at": "2026-11-25T12:04:01.000+00:00",
        "revocation_epoch": 0,
        "use_semantics": "ONE_TIME",
        "issuer_identity": "synthetic-test-issuer",
        "issuer_revision": "test-issuer-r1",
    }
    value["grant_digest"] = hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()
    return value


def _sealed_witness(grant: dict) -> dict:
    value = {
        "schema_version": 1,
        "witness_type": "grant-consumption-witness/v1",
        "consumption_id": "consume_casebook_001",
        "jti": grant["jti"],
        "grant_id": grant["grant_id"],
        "grant_digest": grant["grant_digest"],
        "execution_id": grant["execution_id"],
        "authorization_snapshot_digest": grant["authorization_snapshot_digest"],
        "execution_capsule_digest": grant["execution_capsule_digest"],
        "runner_class": grant["runner_class"],
        "conformance_witness_digest": DIGESTS[12],
        "clock_witness_digest": DIGESTS[13],
        "live_revocation_epoch": 0,
        "consumed_at": "2026-11-25T12:00:02.000+00:00",
        "serialization_contract": "sqlite-begin-immediate/v1",
        "authority_revision": "synthetic-consumption-r1",
    }
    value["witness_digest"] = hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()
    return value


def _vone_database(
    path: Path,
    *,
    environment: str = "staging",
    include_consumption: bool = True,
    witness_override: dict | None = None,
) -> tuple[dict, dict]:
    grant = _sealed_grant(environment=environment)
    witness = _sealed_witness(grant)
    if witness_override:
        witness.update(witness_override)
        del witness["witness_digest"]
        witness["witness_digest"] = hashlib.sha256(
            canonical_json(witness).encode("utf-8")
        ).hexdigest()
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE execution_grants_v2(
                jti TEXT PRIMARY KEY, grant_id TEXT, execution_id TEXT UNIQUE,
                request_id TEXT, workspace_id TEXT, environment TEXT,
                authorization_snapshot_digest TEXT,
                execution_capsule_digest TEXT, grant_digest TEXT,
                grant_json TEXT
            );
            CREATE TABLE grant_consumptions_v1(
                consumption_id TEXT PRIMARY KEY, jti TEXT UNIQUE,
                grant_digest TEXT, execution_id TEXT UNIQUE,
                authorization_snapshot_digest TEXT,
                execution_capsule_digest TEXT, runner_class TEXT,
                consumption_digest TEXT, consumption_json TEXT
            );
        """)
        db.execute(
            "INSERT INTO execution_grants_v2 VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                grant["jti"], grant["grant_id"], grant["execution_id"],
                grant["request_id"], grant["workspace_id"], grant["environment"],
                grant["authorization_snapshot_digest"],
                grant["execution_capsule_digest"], grant["grant_digest"],
                canonical_json(grant),
            ),
        )
        if include_consumption:
            db.execute(
                "INSERT INTO grant_consumptions_v1 VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    witness["consumption_id"], witness["jti"],
                    witness["grant_digest"], witness["execution_id"],
                    witness["authorization_snapshot_digest"],
                    witness["execution_capsule_digest"], witness["runner_class"],
                    witness["witness_digest"], canonical_json(witness),
                ),
            )
        for table, prefix in (
            ("execution_grants_v2", "trg_execution_grants_v2"),
            ("grant_consumptions_v1", "trg_grant_consumptions_v1"),
        ):
            binding = (
                "snapshot_binding_insert" if table == "execution_grants_v2"
                else "grant_binding_insert"
            )
            db.execute(
                f"CREATE TRIGGER {prefix}_{binding} BEFORE INSERT ON {table} "
                "BEGIN SELECT CASE WHEN 0 THEN RAISE(ABORT,'binding') END; END"
            )
            for action in ("UPDATE", "DELETE"):
                db.execute(
                    f"CREATE TRIGGER {prefix}_immutable_{action.lower()} "
                    f"BEFORE {action} ON {table} "
                    "BEGIN SELECT RAISE(ABORT,'immutable'); END"
                )
    return grant, witness


def _event(
    *, seq: int, event_id: str, event_type: str, summary: str,
    timestamp: str, metadata: dict, previous: str,
) -> tuple[dict, str]:
    value = {
        "schema": "voodoo-casebook/event/v1",
        "seq": seq,
        "event_id": event_id,
        "session_id": SESSION,
        "project": "eimyroot/Voodoo-One",
        "timestamp": timestamp,
        "type": event_type,
        "summary": summary,
        "source": "user" if event_type == "GOAL" else "system",
        "evidence_refs": [],
        "status": "OPEN",
        "metadata": metadata,
        "prev_hash": previous,
    }
    digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    return value, digest


def _casebook_database(
    path: Path,
    *,
    grant: dict,
    witness: dict,
    payload_digest: str | None = None,
) -> None:
    metadata = {
        "schema": HANDOFF_SCHEMA,
        "execution_id": grant["execution_id"],
        "request_id": grant["request_id"],
        "workspace_id": grant["workspace_id"],
        "environment": grant["environment"],
        "grant_digest": grant["grant_digest"],
        "consumption_witness_digest": witness["witness_digest"],
        "payload_digest": payload_digest or grant["payload_digest"],
        "target_digest": grant["target_digest"],
    }
    goal = "Verify one synthetic CASEBOOK handoff"
    created = "2026-11-25T12:00:00.000000Z"
    first, first_hash = _event(
        seq=1, event_id="event_goal_001", event_type="GOAL",
        summary=goal, timestamp=created, metadata={}, previous="0" * 64,
    )
    second, second_hash = _event(
        seq=2, event_id="event_context_001", event_type="CONTEXT",
        summary="V-One consumption binding recorded", metadata=metadata,
        timestamp="2026-11-25T12:00:03.000000Z", previous=first_hash,
    )
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE meta(
                id INTEGER PRIMARY KEY, schema_version INTEGER,
                head_seq INTEGER, head_hash TEXT
            );
            CREATE TABLE sessions(
                session_id TEXT PRIMARY KEY, project TEXT,
                goal TEXT, created_at TEXT
            );
            CREATE TABLE events(
                seq INTEGER PRIMARY KEY, event_id TEXT UNIQUE,
                session_id TEXT, project TEXT, timestamp TEXT, type TEXT,
                summary TEXT, source TEXT, evidence_refs_json TEXT,
                status TEXT, metadata_json TEXT, prev_hash TEXT,
                event_hash TEXT
            );
        """)
        db.execute("INSERT INTO meta VALUES(1,1,2,?)", (second_hash,))
        db.execute(
            "INSERT INTO sessions VALUES(?,?,?,?)",
            (SESSION, "eimyroot/Voodoo-One", goal, created),
        )
        for value, digest in ((first, first_hash), (second, second_hash)):
            db.execute(
                "INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    value["seq"], value["event_id"], value["session_id"],
                    value["project"], value["timestamp"], value["type"],
                    value["summary"], value["source"],
                    canonical_json(value["evidence_refs"]), value["status"],
                    canonical_json(value["metadata"]), value["prev_hash"], digest,
                ),
            )
        for table in ("events", "sessions"):
            for action in ("UPDATE", "DELETE"):
                db.execute(
                    f"CREATE TRIGGER {table}_no_{action.lower()} "
                    f"BEFORE {action} ON {table} "
                    "BEGIN SELECT RAISE(ABORT,'append-only'); END"
                )


def _fixture(tmp_path: Path, **casebook_options):
    vone = tmp_path / "vone.sqlite3"
    casebook = tmp_path / "casebook.sqlite3"
    grant, witness = _vone_database(vone)
    _casebook_database(casebook, grant=grant, witness=witness, **casebook_options)
    return vone, casebook


def _verify(vone: Path, casebook: Path):
    return verify_casebook_handoff(
        vone_database=vone,
        casebook_database=casebook,
        execution_id=EXECUTION,
        workspace_id=WORKSPACE,
        session_id=SESSION,
    )


def test_exact_consumed_grant_and_append_only_event_match(tmp_path: Path) -> None:
    vone, casebook = _fixture(tmp_path)
    before = (vone.stat().st_mtime_ns, casebook.stat().st_mtime_ns)
    result = _verify(vone, casebook)
    assert result.verdict == "LOCAL_CROSS_DATABASE_STRUCTURAL_MATCH"
    assert result.independent_identity_attested is False
    assert result.production_connected is False
    assert before == (vone.stat().st_mtime_ns, casebook.stat().st_mtime_ns)


def test_missing_grant_consumption_is_rejected(tmp_path: Path) -> None:
    vone = tmp_path / "vone.sqlite3"
    casebook = tmp_path / "casebook.sqlite3"
    grant, witness = _vone_database(vone, include_consumption=False)
    _casebook_database(casebook, grant=grant, witness=witness)
    with pytest.raises(CasebookHandoffRejected, match="consumption is missing"):
        _verify(vone, casebook)


def test_intact_but_different_payload_binding_is_rejected(tmp_path: Path) -> None:
    vone, casebook = _fixture(tmp_path, payload_digest="f" * 64)
    with pytest.raises(CasebookHandoffRejected, match="exactly one matching"):
        _verify(vone, casebook)


def test_casebook_without_append_only_trigger_is_rejected(tmp_path: Path) -> None:
    vone, casebook = _fixture(tmp_path)
    with sqlite3.connect(casebook) as db:
        db.execute("DROP TRIGGER events_no_update")
    with pytest.raises(CasebookHandoffRejected, match="immutability"):
        _verify(vone, casebook)


def test_production_grant_is_rejected(tmp_path: Path) -> None:
    vone = tmp_path / "vone.sqlite3"
    casebook = tmp_path / "casebook.sqlite3"
    grant, witness = _vone_database(vone, environment="production")
    _casebook_database(casebook, grant=grant, witness=witness)
    with pytest.raises(CasebookHandoffRejected, match="production"):
        _verify(vone, casebook)


def test_vone_without_immutable_grant_trigger_is_rejected(tmp_path: Path) -> None:
    vone, casebook = _fixture(tmp_path)
    with sqlite3.connect(vone) as db:
        db.execute("DROP TRIGGER trg_execution_grants_v2_immutable_update")
    with pytest.raises(CasebookHandoffRejected, match="immutability"):
        _verify(vone, casebook)


def test_rehashed_or_tampered_invalid_casebook_claim_is_not_accepted(tmp_path: Path) -> None:
    vone, casebook = _fixture(tmp_path)
    with sqlite3.connect(casebook) as db:
        db.execute("DROP TRIGGER events_no_update")
        db.execute("UPDATE events SET status='VERIFIED' WHERE seq=2")
        db.execute(
            "CREATE TRIGGER events_no_update BEFORE UPDATE ON events "
            "BEGIN SELECT RAISE(ABORT,'append-only'); END"
        )
    with pytest.raises(CasebookHandoffRejected, match="event contract"):
        _verify(vone, casebook)

@pytest.mark.parametrize("override", [
    {"jti": "another_jti"},
    {"grant_digest": "f" * 64},
    {"authorization_snapshot_digest": "f" * 64},
    {"execution_capsule_digest": "f" * 64},
    {"runner_class": "other-synthetic-runner"},
])
def test_self_consistent_consumption_cannot_bind_another_grant(tmp_path, override):
    vone = tmp_path / "vone.sqlite3"
    casebook = tmp_path / "casebook.sqlite3"
    grant, witness = _vone_database(vone, witness_override=override)
    _casebook_database(casebook, grant=grant, witness=witness)
    with pytest.raises(CasebookHandoffRejected, match="consumption grant binding mismatch"):
        _verify(vone, casebook)


def test_passport_correlation_is_exact_and_never_grants_resume(tmp_path):
    vone, casebook = _fixture(tmp_path)
    handoff = _verify(vone, casebook)
    passport = OperationPassport(
        execution_id=handoff.execution_id,
        lifecycle_stage="EXECUTION_COMPLETED",
        operation={
            "request_id": handoff.request_id,
            "workspace_id": handoff.workspace_id,
            "environment": handoff.environment,
        },
        authority={
            "grant": {"grant_digest": handoff.grant_digest},
            "consumption": {"consumption_digest": handoff.consumption_witness_digest},
        },
        dispatch={}, runtime={"status": "COMPLETED"},
        verification={"verdict": "UNKNOWN"},
        integrity={"canonical_json_validated": True, "lineage_bindings_validated": True},
    )
    correlation = correlate_casebook_passport(handoff=handoff, passport=passport)
    assert correlation["verdict"] == "LOCAL_STRUCTURAL_PASSPORT_MATCH"
    assert correlation["execution_id"] == handoff.execution_id
    assert correlation["resume_authorized"] is False
    assert correlation["execution_verified_by_this_view"] is False
    assert correlation["execution_authorized_by_this_view"] is False
    for changed in (
        replace(passport, execution_id="exec_other"),
        replace(passport, operation={**passport.operation, "workspace_id": "wrk_other"}),
        replace(passport, operation={**passport.operation, "environment": "local"}),
        replace(passport, authority={**passport.authority, "consumption": None}),
        replace(passport, integrity={"lineage_bindings_validated": False}),
    ):
        with pytest.raises(CasebookHandoffRejected):
            correlate_casebook_passport(handoff=handoff, passport=changed)
