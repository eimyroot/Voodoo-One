from __future__ import annotations

import sqlite3

from voodoo_product.statements import GET_CHANGE_REQUEST, LIST_CHANGE_REQUESTS

EARLY = "2026-11-23T14:56:55.841+00:00"
LATE = "2026-11-23T14:59:55.841+00:00"


def _approval_db() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE users (id TEXT PRIMARY KEY, username TEXT NOT NULL);
        CREATE TABLE change_requests (
            id TEXT PRIMARY KEY, requested_by TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE approvals (
            request_id TEXT NOT NULL, decision TEXT NOT NULL, created_at TEXT NOT NULL
        );
        INSERT INTO users VALUES ('usr_developer', 'g8-requester');
        INSERT INTO change_requests VALUES ('cr_approved', 'usr_developer',
            '2026-11-23T15:00:00.000+00:00');
        INSERT INTO change_requests VALUES ('cr_draft', 'usr_developer',
            '2026-11-23T14:30:00.000+00:00');
    """)
    return db


def test_first_approved_at_is_earliest_independent_approval_and_not_request_updated_at() -> None:
    db = _approval_db()
    try:
        db.executemany(
            "INSERT INTO approvals VALUES ('cr_approved', 'APPROVED', ?)",
            [(LATE,), (EARLY,)],
        )
        # A DENIED record and a later request update must not extend
        # approval expiry. The authoritative runtime uses min(created_at).
        db.execute(
            "INSERT INTO approvals VALUES ('cr_approved','DENIED',?)", (EARLY,)
        )
        by_id = db.execute(GET_CHANGE_REQUEST.sqlite_sql, ("cr_approved",)).fetchone()
        assert by_id["approval_count"] == 2
        assert by_id["first_approved_at"] == EARLY
        all_rows = db.execute(LIST_CHANGE_REQUESTS.sqlite_sql, (100,)).fetchall()
        rows = {row["id"]: row for row in all_rows}
        assert rows["cr_approved"]["first_approved_at"] == EARLY
        assert rows["cr_draft"]["first_approved_at"] is None
        assert rows["cr_draft"]["approval_count"] == 0
    finally:
        db.close()
