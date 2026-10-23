"""Truthful read-only workflow board integration on the existing product console."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from voodoo_product.api import install_product_platform
from voodoo_product.config import ProductConfig


def test_workflow_boards_integrate_without_new_authority(tmp_path: Path) -> None:
    config = ProductConfig(
        environment="test",
        database_path=tmp_path / "boards.sqlite3",
        sandbox_root=tmp_path / "sandbox",
        session_signing_secret="s" * 64,
        bootstrap_token="b" * 48,
        production_effects_enabled=False,
    )
    app = FastAPI()
    install_product_platform(app, config=config, repository_root=tmp_path)
    client = TestClient(app)

    page = client.get("/console")
    assert page.status_code == 200
    for name in ("ecosystem", "lifecycle", "authority", "lineage", "overlays"):
        assert f'data-view="{name}"' in page.text
        assert f'id="view-{name}"' in page.text
    assert "/console/assets/workflow_boards.css" in page.text
    assert "/console/assets/workflow_boards.js" in page.text

    script = client.get("/console/assets/workflow_boards.js")
    style = client.get("/console/assets/workflow_boards.css")
    router = client.get("/console/assets/control_room.js")
    assert script.status_code == 200
    assert style.status_code == 200
    assert router.status_code == 200
    for function in (
        "loadEcosystemBoard", "loadLifecycleBoard", "loadAuthorityBoard",
        "loadLineageBoard", "loadOverlaysBoard",
    ):
        assert function in script.text
        assert function in router.text
    assert "await controlRoom()" in script.text
    assert "method: 'POST'" not in script.text
    assert "fetch(" not in script.text
    assert "Execution" in script.text and "VerificationResult/v1" in script.text
    assert "NOT CONNECTED" in script.text
    assert "UNKNOWN" in script.text
    assert "Agents Online 12" not in script.text

    unauthorized = client.get("/api/v1/control-room")
    assert unauthorized.status_code in (401, 403)
    token = client.post(
        "/api/v1/auth/bootstrap",
        json={
            "username": "admin",
            "password": "VeryStrongAdminPassword1!",
            "bootstrap_token": "b" * 48,
        },
    )
    assert token.status_code == 201
    result = client.get(
        "/api/v1/control-room",
        headers={"Authorization": f"Bearer {token.json()['token']}"},
    )
    assert result.status_code == 200
    payload = result.json()
    assert payload["capability_registry"]["production_effects_enabled"] is False
    assert "evidence_timeline" in payload
    assert "policy_gates" in payload
