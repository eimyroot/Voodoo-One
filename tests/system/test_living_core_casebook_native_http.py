"""Regression: merged native Control Room serves Living Core and CASEBOOK together.

A disposable product database and the real application composition are used.
No actual CASEBOOK evidence source, owner identity, G8 or production service
is connected. Loading the UI must never activate CASEBOOK automatically.
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from voodoo_product.composition import install_composed_product_platform
from voodoo_product.config import ProductConfig


def test_native_console_contains_living_core_casebook_and_existing_controls(
    tmp_path: Path,
) -> None:
    app = FastAPI()
    config = ProductConfig(
        environment="test",
        database_path=tmp_path / "voodoo-test.sqlite3",
        sandbox_root=tmp_path / "empty-sandbox",
        session_signing_secret="s" * 64,
        bootstrap_token="b" * 48,
    )
    install_composed_product_platform(
        app, config=config, repository_root=tmp_path,
    )

    with TestClient(app) as client:
        page = client.get("/console")
        assert page.status_code == 200
        html = page.text
        assert "VOODOO One · Living Core" in html
        assert 'id="living-core-title"' in html
        assert 'id="view-casebook"' in html
        assert 'data-view="casebook"' in html
        assert 'id="casebook-task-form"' in html
        assert 'id="casebook-task-timeline"' in html
        assert 'data-view="plans"' in html
        assert 'data-view="verifier"' in html
        assert 'data-view="projectmap"' in html
        assert 'data-view="governance"' in html

        ids = re.findall(r'\bid="([^"]+)"', html)
        assert len(ids) == len(set(ids)), "duplicate IDs break native JS bindings"
        assert html.index("assets/control_room.js") < html.index("assets/living_core.js")

        for asset, marker in (
            ("living_core.js", "voodooLivingCore"),
            ("living_core.css", "prefers-reduced-motion"),
            ("control_room.js", "loadCasebookTask"),
        ):
            resp = client.get("/console/assets/" + asset)
            assert resp.status_code == 200, (asset, resp.status_code)
            assert marker in resp.text

        # UI discoverability is not a source attachment or an execution grant.
        assert getattr(app.state, "voodoo_casebook_task_gateway", None) is None
        assert client.get(
            "/api/v1/casebook/tasks/caser-example-session"
        ).status_code == 401
