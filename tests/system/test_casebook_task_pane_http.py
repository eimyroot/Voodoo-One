"""HTTP and native workspace tests for opt-in CASEBOOK task detail.

Only disposable ProductService SQLite + CASEBOOK journal in pytest tmp_path.
The external CASEBOOK source is SHA-256 pinned; there is no test-time
permission to access actual owner CASEBOOK data, Keychain, G8, or provider.
"""
from __future__ import annotations

import hashlib
import os
import pwd
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from voodoo_product.casebook_task_gateway import (
    CasebookTaskAccessDenied,
    CasebookTaskGateway,
    TaskScope,
    attach_casebook_task_gateway,
)
from voodoo_product.composition import install_composed_product_platform
from voodoo_product.config import ProductConfig
from voodoo_product.permission_authority import PermissionQuery

PINNED_CASEBOOK = (
    Path(pwd.getpwuid(os.getuid()).pw_dir) / "0_EVIDENCE" / "VOODOO-CASEBOOK" / "TASK_TIMELINE_CANDIDATE_20261123"
)
PINNED_TASK_VIEW_SHA256 = (
    "a784f3495cda7926a68af14d36cb9f87f1f9cb6edf2ac517c93475507cf24036"
)
PROJECT = "synthetic/CyberCaser"
SESSION = "caser-task-pane-001"


@pytest.fixture()
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Use a real already-versioned CASEBOOK projection and isolated data."""
    source = PINNED_CASEBOOK / "voodoo_casebook" / "task_view.py"
    if not source.is_file():
        pytest.skip("Pinned CASEBOOK source absent; HTTP integration unverified")
    assert hashlib.sha256(source.read_bytes()).hexdigest() == PINNED_TASK_VIEW_SHA256
    monkeypatch.syspath_prepend(str(PINNED_CASEBOOK))
    from voodoo_casebook import CasebookStore
    from voodoo_casebook.task_view import project_task_status

    store = CasebookStore(tmp_path / "private-casebook")
    store.start_session(
        project=PROJECT,
        goal="Show an existing governed task without execution",
        session_id=SESSION,
    )
    config = ProductConfig(
        environment="test",
        database_path=tmp_path / "product.sqlite3",
        sandbox_root=tmp_path / "sandbox",
        session_signing_secret="s" * 64,
        bootstrap_token="b" * 48,
    )
    app = FastAPI()
    composition = install_composed_product_platform(
        app, config=config, repository_root=tmp_path,
    )
    client = TestClient(app)
    result = client.post("/api/v1/auth/bootstrap", json={
        "username": "synthetic-admin", "password": "SyntheticLongPassword!2026",
        "bootstrap_token": "b" * 48,
    })
    assert result.status_code == 201, result.text
    token = result.json()["token"]
    user = app.state.voodoo_identity_provider.authenticate_bearer(token)
    workspaces = composition.service.list_workspaces()
    workspace = next(w for w in workspaces if w["environment"] == "local")
    scope = TaskScope(
        session_id=SESSION, workspace_id=workspace["id"],
        environment="local", project=PROJECT,
    )
    return {
        "client": client, "app": app, "composition": composition, "store": store,
        "token": token, "principal": user, "scope": scope,
        "reader": lambda session: project_task_status(store, session),
    }


def headers(token: str) -> dict[str, str]:
    return {"Authorization": "Bearer " + token}


def attach(env, *, reader=None, scopes=None):
    return attach_casebook_task_gateway(
        app=env["app"], composition=env["composition"],
        reader=env["reader"] if reader is None else reader,
        scopes=[env["scope"]] if scopes is None else scopes,
    )


def test_no_default_casebook_reader_and_unauthenticated_denial(env):
    client = env["client"]
    url = f"/api/v1/casebook/tasks/{SESSION}"
    assert client.get(url).status_code == 401
    assert client.get(url, headers=headers("invalid")).status_code == 401
    unavailable = client.get(url, headers=headers(env["token"]))
    assert unavailable.status_code == 503
    assert unavailable.json()["detail"] == "CASEBOOK task view is not configured"
    assert getattr(env["app"].state, "voodoo_casebook_task_gateway", None) is None


def test_real_casebook_journal_is_displayed_without_execution_claims(env):
    env["store"].append(
        session_id=SESSION, event_type="CONTEXT",
        summary="CASER handoff claimed",
        source="tool", metadata={"caser_handoff_sha256": "a" * 64},
    )
    env["store"].append(
        session_id=SESSION, event_type="RESULT",
        summary="Untrusted result event",
        source="tool", status="RESOLVED",
        metadata={"independent_verifier": "VERIFIED", "access_token": "should-not-leak"},
    )
    gateway = attach(env)
    response = env["client"].get(
        f"/api/v1/casebook/tasks/{SESSION}", headers=headers(env["token"]),
    )
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["schema"] == "voodoo-casebook/task-view/v1"
    assert body["workspace_id"] == env["scope"].workspace_id
    assert body["display_state"] == "RESULT_RECORDED_UNVERIFIED"
    assert body["result"] == "RECORDED_UNVERIFIED"
    assert body["handoff"] == "RECORDED_UNATTESTED"
    assert body["native_approval"] == "NOT_ATTESTED"
    assert body["isolated_runner_execution"] == "NOT_ATTESTED"
    assert body["independent_verifier"] == "NOT_ATTESTED"
    assert body["execution_authorized_by_this_view"] is False
    assert body["execution_verified_by_this_view"] is False
    assert [e["type"] for e in body["timeline"]] == ["GOAL", "CONTEXT", "RESULT"]
    assert "access_token" not in response.text
    assert "should-not-leak" not in response.text
    assert gateway.composition is env["composition"]
    assert env["store"].verify()["event_count"] == 3


def test_unknown_session_is_not_enumerable_or_mutating(env):
    attach(env)
    before = env["store"].verify()
    response = env["client"].get(
        "/api/v1/casebook/tasks/caser-private-other-workspace",
        headers=headers(env["token"]),
    )
    assert response.status_code == 404
    assert "casebook.sqlite" not in response.text
    assert env["store"].verify() == before


@pytest.mark.parametrize("bad", [
    "short", "invalid-id-with/slash", "a" * 129,
])
def test_unapproved_session_id_is_never_a_reader_selector(env, bad):
    calls: list[str] = []
    attach(env, reader=lambda session: (calls.append(session), {} )[1])
    response = env["client"].get(
        f"/api/v1/casebook/tasks/{bad}", headers=headers(env["token"]),
    )
    assert response.status_code in {404, 422}
    assert calls == []


def test_auditor_with_no_workspace_membership_is_denied(env):
    owner = env["principal"]
    person = env["composition"].service.create_user(
        actor_id=owner.user_id,
        username="external-auditor",
        password="SyntheticAuditorPassword2026!",
        role="auditor",
    )
    auditor = env["app"].state.voodoo_identity_provider.issue_session(
        user_id=person["id"], username="external-auditor", role="auditor",
    )
    decision = env["composition"].database_permission_authority.decide(
        PermissionQuery(
            actor_id=person["id"], workspace_id=env["scope"].workspace_id,
            environment="local", permission="evidence.read",
        )
    )
    assert decision.granted is False
    attach(env)
    response = env["client"].get(
        f"/api/v1/casebook/tasks/{SESSION}", headers=headers(auditor),
    )
    assert response.status_code == 403


def test_reviewer_can_read_only_while_member_of_correct_workspace(env):
    owner = env["principal"]
    person = env["composition"].service.create_user(
        actor_id=owner.user_id,
        username="scoped-auditor",
        password="AnotherSyntheticAuditorPassword!",
        role="auditor",
    )
    token = env["app"].state.voodoo_identity_provider.issue_session(
        user_id=person["id"], username="scoped-auditor", role="auditor",
    )
    attach(env)
    forbidden = env["client"].get(
        f"/api/v1/casebook/tasks/{SESSION}", headers=headers(token),
    )
    assert forbidden.status_code == 403
    env["composition"].workspace_service.add_member(
        actor_id=owner.user_id,
        workspace_id=env["scope"].workspace_id,
        user_id=person["id"],
    )
    allowed = env["client"].get(
        f"/api/v1/casebook/tasks/{SESSION}", headers=headers(token),
    )
    assert allowed.status_code == 200, allowed.text
    env["composition"].workspace_service.remove_member(
        actor_id=owner.user_id,
        workspace_id=env["scope"].workspace_id,
        user_id=person["id"],
    )
    denied = env["client"].get(
        f"/api/v1/casebook/tasks/{SESSION}", headers=headers(token),
    )
    assert denied.status_code == 403


def test_invalid_untrusted_verification_claim_is_fail_closed(env):
    def fake(session: str) -> dict[str, Any]:
        data = env["reader"](session)
        data["independent_verifier"] = "VERIFIED"
        data["timeline"][-1]["summary"] = "fake verification"
        return data

    attach(env, reader=fake)
    response = env["client"].get(
        f"/api/v1/casebook/tasks/{SESSION}", headers=headers(env["token"]),
    )
    assert response.status_code == 503
    assert "fake verification" not in response.text


def test_project_session_binding_is_enforced(env):
    def fake(session: str) -> dict[str, Any]:
        data = env["reader"](session)
        data["project"] = "another-private-project"
        return data

    attach(env, reader=fake)
    response = env["client"].get(
        f"/api/v1/casebook/tasks/{SESSION}", headers=headers(env["token"]),
    )
    assert response.status_code == 503


def test_corrupted_journal_exposes_no_private_path(env):
    import sqlite3

    attach(env)
    with sqlite3.connect(str(env["store"].database)) as db:
        db.execute("DROP TRIGGER events_no_update")
        db.execute("UPDATE events SET summary='forged private note' WHERE seq=1")
    response = env["client"].get(
        f"/api/v1/casebook/tasks/{SESSION}", headers=headers(env["token"]),
    )
    assert response.status_code == 503
    assert "forged private note" not in response.text
    assert str(env["store"].database) not in response.text


def test_no_foreign_app_or_second_attachment_and_no_production(env, tmp_path):
    with pytest.raises(CasebookTaskAccessDenied):
        attach_casebook_task_gateway(
            app=FastAPI(), composition=env["composition"],
            reader=env["reader"], scopes=[env["scope"]],
        )
    assert attach(env) is not None
    with pytest.raises(CasebookTaskAccessDenied):
        attach(env)
    with pytest.raises(ValueError, match="duplicate"):
        CasebookTaskGateway(
            composition=env["composition"], reader=env["reader"],
            scopes=(env["scope"], env["scope"]),
        )

    prod_config = ProductConfig(
        environment="production",
        database_path=tmp_path / "never-used-prod.sqlite3",
        sandbox_root=tmp_path / "never-used-sandbox",
        session_signing_secret="s" * 64,
        bootstrap_token="b" * 48,
    )
    object.__setattr__(env["composition"].service, "config", prod_config)
    with pytest.raises(CasebookTaskAccessDenied, match="local/test"):
        CasebookTaskGateway(
            composition=env["composition"], reader=env["reader"],
            scopes=(env["scope"],),
        )


def test_revoked_session_cannot_read_casebook_after_logout(env):
    attach(env)
    url = f"/api/v1/casebook/tasks/{SESSION}"
    assert env["client"].get(url, headers=headers(env["token"])).status_code == 200
    logout = env["client"].post(
        "/api/v1/auth/logout", headers=headers(env["token"]),
    )
    assert logout.status_code == 204
    assert env["client"].get(url, headers=headers(env["token"])).status_code == 401


def test_invalid_event_type_and_spoofed_next_action_are_not_rendered(env):
    from copy import deepcopy

    valid = env["reader"](SESSION)
    value = deepcopy(valid)
    value["timeline"][0]["type"] = "VERIFIED"
    attach(env, reader=lambda _: value)
    response = env["client"].get(
        f"/api/v1/casebook/tasks/{SESSION}", headers=headers(env["token"]),
    )
    assert response.status_code == 503
    assert "VERIFIED" not in response.text


def test_next_action_is_reconstructed_not_read_from_untrusted_payload(env):
    def altered(session: str) -> dict[str, Any]:
        data = env["reader"](session)
        data["next_action"] = "EXECUTE_UNREVIEWED_PRODUCTION"
        return data

    attach(env, reader=altered)
    response = env["client"].get(
        f"/api/v1/casebook/tasks/{SESSION}", headers=headers(env["token"]),
    )
    assert response.status_code == 200, response.text
    assert response.json()["next_action"] == "PREPARE_AND_AUTHORIZE_CASER_HANDOFF"
    assert "EXECUTE_UNREVIEWED_PRODUCTION" not in response.text


@pytest.mark.parametrize("mutation", [
    ("display_state", []),
    ("event_type", []),
    ("event_status", []),
])
def test_malformed_unhashable_reader_payload_fails_closed(env, mutation):
    def bad(session: str) -> dict[str, Any]:
        data = env["reader"](session)
        if mutation[0] == "display_state":
            data["display_state"] = mutation[1]
        elif mutation[0] == "event_type":
            data["timeline"][0]["type"] = mutation[1]
        else:
            data["timeline"][0]["status_claim"] = mutation[1]
        return data

    attach(env, reader=bad)
    response = env["client"].get(
        f"/api/v1/casebook/tasks/{SESSION}", headers=headers(env["token"]),
    )
    assert response.status_code == 503
    assert "Traceback" not in response.text


def test_console_navigation_is_read_only_and_escapes_source_fields():
    base = Path(__file__).resolve().parents[2] / "voodoo_product" / "static"
    html = (base / "index.html").read_text()
    js = (base / "control_room.js").read_text()
    assert 'data-view="casebook"' in html
    assert 'id="casebook-task-detail"' in html
    assert "casebook:loadCasebookTasks" in js
    assert "api('/casebook/tasks/'" in js
    assert "escapeHtml(event.summary)" in js
    assert "data.execution_verified_by_this_view!==undefined" in js
    assert "casebook-task-feedback" in js
