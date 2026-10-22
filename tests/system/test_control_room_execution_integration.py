from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from voodoo_product.composition import install_composed_product_platform
from voodoo_product.config import ProductConfig
from voodoo_product.control_room_projections import summarize_runs


@pytest.mark.parametrize(
    ("timestamps", "expected"),
    [
        ({"started_at": "start", "completed_at": None}, "start"),
        ({"started_at": "start", "completed_at": "finish"}, "finish"),
        ({"updated_at": "existing"}, "existing"),
        ({"updated_at": None}, None),
    ],
)
def test_run_projection_preserves_timestamp_contract(timestamps, expected):
    row = {
        "id": "exec-1", "title": "Actual execution", "status": "SUCCEEDED",
        "risk": "R1", "environment": "local", "adapter": "echo", **timestamps,
    }
    assert summarize_runs([], [row], limit=20)["recent"][0]["updated_at"] == expected


def test_control_room_http_accepts_real_persisted_execution(tmp_path: Path):
    config = ProductConfig(
        environment="test", database_path=tmp_path / "product.sqlite3",
        sandbox_root=tmp_path / "sandbox", session_signing_secret="s" * 64,
        bootstrap_token="b" * 48,
    )
    app = FastAPI()
    composition = install_composed_product_platform(app, config=config, repository_root=tmp_path)
    service = composition.service
    admin = service.bootstrap_admin(
        username="admin", password="Synthetic-Admin-Password-2026!", token="b" * 48,
    )
    operator = service.create_user(
        actor_id=admin["user_id"], username="operator",
        password="Synthetic-Operator-Password-2026!", role="operator",
    )
    request = service.create_change_request(
        actor_id=admin["user_id"], workspace_id=admin["workspace_id"],
        title="Real execution projection", description="", risk="R1",
        environment="local", adapter="echo", payload={"synthetic": True},
    )
    service.submit_change_request(actor_id=admin["user_id"], request_id=request["id"])
    service.approve_change_request(
        actor_id=operator["id"], request_id=request["id"],
        decision="APPROVED", reason="independent synthetic review",
    )
    execution = service.execute_change_request(
        actor_id=operator["id"], request_id=request["id"],
        idempotency_key="synthetic-real-execution", repository_root=tmp_path,
    )
    assert "updated_at" not in service.list_executions()[0]
    with TestClient(app) as client:
        login = client.post("/api/v1/auth/login", json={
            "username": "admin", "password": "Synthetic-Admin-Password-2026!",
        })
        response = client.get("/api/v1/control-room", headers={
            "Authorization": "Bearer " + login.json()["token"],
        })
    assert response.status_code == 200
    row = response.json()["runs"]["recent"][0]
    assert row["id"] == execution["id"]
    assert row["updated_at"] == execution["completed_at"]
    assert response.json()["verifier_center"]["recent_checks"][0]["verification_status"] == "UNKNOWN"
    assert service.verify_receipt_chain()["valid"]
    assert service.verify_audit_chain()["valid"]
