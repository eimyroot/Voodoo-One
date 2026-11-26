"""Portable HTTP contract tests: CASEBOOK is an *optional* read source.

These tests run without a local CASEBOOK checkout. Additional source-pinned
SQLite integration tests may run when that separately reviewed source exists.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from voodoo_product.casebook_task_gateway import TaskScope, attach_casebook_task_gateway
from voodoo_product.composition import install_composed_product_platform
from voodoo_product.config import ProductConfig

SESSION = "caser-portable-task-001"
PROJECT = "synthetic/project-a"
GOAL = "Read bounded evidence without executing"


@pytest.fixture
def native(tmp_path: Path):
    config = ProductConfig(
        environment="test", database_path=tmp_path / "product.sqlite3",
        sandbox_root=tmp_path / "sandboxes",
        session_signing_secret="S" * 64, bootstrap_token="T" * 48,
    )
    app = FastAPI()
    composition = install_composed_product_platform(
        app, config=config, repository_root=tmp_path,
    )
    client = TestClient(app)
    result = client.post("/api/v1/auth/bootstrap", json={
        "username": "synthetic-admin", "password": "SyntheticTestingPassword2026!",
        "bootstrap_token": "T" * 48,
    })
    assert result.status_code == 201, result.text
    token = result.json()["token"]
    workspace = next(row for row in composition.service.list_workspaces()
                     if row["environment"] == "local")
    scope = TaskScope(
        session_id=SESSION, workspace_id=workspace["id"],
        environment="local", project=PROJECT,
    )
    return app, composition, client, token, scope


def projection() -> dict:
    timeline = [
        {
            "seq": 1, "event_id": "evt-portable-001", "type": "GOAL",
            "timestamp": "2026-11-23T17:00:00Z", "source_claim": "user",
            "summary": GOAL, "status_claim": "OPEN", "event_hash": "a" * 64,
        },
        {
            "seq": 2, "event_id": "evt-portable-002", "type": "RESULT",
            "timestamp": "2026-11-23T17:01:00Z", "source_claim": "tool",
            "summary": "Unattested result", "status_claim": "RESOLVED",
            "event_hash": "b" * 64,
        },
    ]
    return {
        "schema": "voodoo-casebook/task-view/v1",
        "session_id": SESSION, "project": PROJECT, "goal": GOAL,
        "created_at": "2026-11-23T17:00:00Z",
        "journal_integrity": "LOCAL_HASH_CHAIN_VERIFIED_ONLY",
        "display_state": "RESULT_RECORDED_UNVERIFIED",
        "native_approval": "NOT_ATTESTED",
        "isolated_runner_execution": "NOT_ATTESTED",
        "independent_verifier": "NOT_ATTESTED",
        "execution_authorized_by_this_view": False,
        "execution_verified_by_this_view": False,
        "recorded_event_count": 2,
        "timeline": timeline,
        "metadata": {"credential": "must-not-expose"},
        "next_action": "UNREVIEWED_MUTATION",
    }


def test_default_console_does_not_expose_unattached_casebook(native):
    _, _, client, token, _ = native
    url = f"/api/v1/casebook/tasks/{SESSION}"
    assert client.get(url).status_code == 401
    resp = client.get(url, headers={"Authorization": "Bearer " + token})
    assert resp.status_code == 503
    assert resp.json()["detail"] == "CASEBOOK task view is not configured"


def test_optional_reader_respects_native_auth_and_safe_projection(native):
    app, composition, client, token, scope = native
    attach_casebook_task_gateway(
        app=app, composition=composition,
        reader=lambda _: projection(), scopes=[scope],
    )
    url = f"/api/v1/casebook/tasks/{SESSION}"
    assert client.get(url).status_code == 401
    resp = client.get(url, headers={"Authorization": "Bearer " + token})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["workspace_id"] == scope.workspace_id
    assert data["display_state"] == "RESULT_RECORDED_UNVERIFIED"
    assert data["execution_verified_by_this_view"] is False
    assert data["execution_authorized_by_this_view"] is False
    assert data["independent_verifier"] == "NOT_ATTESTED"
    assert data["next_action"] == "VERIFY_NATIVE_APPROVAL_EXECUTION_AND_INDEPENDENT_RESULT"
    assert "must-not-expose" not in resp.text
    assert "UNREVIEWED_MUTATION" not in resp.text
    assert resp.headers["cache-control"] == "no-store"
    assert client.get(
        "/api/v1/casebook/tasks/caser-unapproved-session",
        headers={"Authorization": "Bearer " + token},
    ).status_code == 404


def test_bound_index_is_authorized_metadata_only(native):
    app, composition, client, token, scope = native
    calls = []
    hidden = TaskScope(
        session_id="caser-other-private", workspace_id="missing-workspace",
        environment="local", project="private/project",
    )
    attach_casebook_task_gateway(
        app=app, composition=composition,
        reader=lambda session: (calls.append(session), projection())[1],
        scopes=[scope, hidden],
    )
    url = "/api/v1/casebook/tasks"
    auth = {"Authorization": "Bearer " + token}
    assert client.get(url).status_code == 401
    response = client.get(url, headers=auth)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "schema": "voodoo-casebook/bound-task-index/v1",
        "items": [{
            "session_id": scope.session_id,
            "workspace_id": scope.workspace_id,
            "environment": scope.environment,
            "project": scope.project,
        }],
        "has_more": False,
        "journal_integrity": "NOT_CHECKED_BY_INDEX",
    }
    assert "private/project" not in response.text
    assert calls == []
    assert client.get(url + "/" + SESSION, headers=auth).status_code == 200
    assert calls == [SESSION]
    assert client.post("/api/v1/auth/logout", headers=auth).status_code == 204
    assert client.get(url, headers=auth).status_code == 401


def test_unconfigured_bound_index_is_not_empty_success(native):
    _, _, client, token, _ = native
    assert client.get("/api/v1/casebook/tasks").status_code == 401
    assert client.get(
        "/api/v1/casebook/tasks", headers={"Authorization": "Bearer " + token},
    ).status_code == 503


def test_passport_correlation_default_disabled_and_never_executes(native):
    app, composition, client, token, scope = native
    calls = []
    attach_casebook_task_gateway(
        app=app, composition=composition,
        reader=lambda session: (calls.append(session), projection())[1],
        scopes=[scope],
    )
    auth = {"Authorization": "Bearer " + token}
    url = f"/api/v1/casebook/tasks/{SESSION}/passport/exec_sample"
    assert client.get(url).status_code == 401
    assert client.get(url, headers=auth).status_code == 503
    assert calls == []
    assert client.post(url, headers=auth).status_code == 405
    detail = client.get(f"/api/v1/casebook/tasks/{SESSION}", headers=auth)
    assert detail.json()["passport_correlation_available"] is False


def test_untrusted_verification_claim_is_denied(native):
    app, composition, client, token, scope = native
    bad = projection()
    bad["independent_verifier"] = "VERIFIED"
    attach_casebook_task_gateway(
        app=app, composition=composition, reader=lambda _: bad, scopes=[scope],
    )
    resp = client.get(
        f"/api/v1/casebook/tasks/{SESSION}",
        headers={"Authorization": "Bearer " + token},
    )
    assert resp.status_code == 503
    assert "VERIFIED" not in resp.text


def test_session_revocation_is_effective(native):
    app, composition, client, token, scope = native
    attach_casebook_task_gateway(
        app=app, composition=composition,
        reader=lambda _: projection(), scopes=[scope],
    )
    url = f"/api/v1/casebook/tasks/{SESSION}"
    auth = {"Authorization": "Bearer " + token}
    assert client.get(url, headers=auth).status_code == 200
    assert client.post("/api/v1/auth/logout", headers=auth).status_code == 204
    assert client.get(url, headers=auth).status_code == 401
