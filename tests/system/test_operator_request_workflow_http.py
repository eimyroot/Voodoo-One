"""HTTP surface checks for the operator-first Requests workflow."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from voodoo_product.api import install_product_platform
from voodoo_product.config import ProductConfig


def test_requests_workflow_assets_and_fail_closed_surface(tmp_path: Path) -> None:
    app = FastAPI()
    config = ProductConfig(
        environment="test",
        database_path=tmp_path / "requests.sqlite3",
        sandbox_root=tmp_path / "sandbox",
        session_signing_secret="s" * 64,
        bootstrap_token="b" * 48,
        production_effects_enabled=False,
    )
    install_product_platform(app, config=config, repository_root=tmp_path)

    with TestClient(app) as client:
        page = client.get("/console")
        assert page.status_code == 200
        assert '>Požadavky</button>' in page.text
        assert '<button data-view="registry" class="nav">' not in page.text
        assert 'id="request-capability-context"' in page.text
        assert 'id="change-review-button"' in page.text
        assert 'id="change-create-button" disabled' in page.text
        assert "/console/assets/request_workflow.css" in page.text

        style = client.get("/console/assets/request_workflow.css")
        assert style.status_code == 200
        assert ".request-review" in style.text
        assert ".approval-facts" in style.text

        # UI availability never grants request creation or approval authority.
        assert client.post("/api/v1/change-requests", json={}).status_code == 401
        assert client.get("/api/v1/approvals?pending_only=true").status_code == 401
