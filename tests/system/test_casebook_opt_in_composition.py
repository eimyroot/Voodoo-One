"""Native VOODOO One startup CASEBOOK read binding: fail-closed and opt-in.

All stores are disposable; actual owner CASEBOOK data is never read.
Tests requiring a separately pinned CASEBOOK code candidate skip when absent.
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from voodoo_product import casebook_pinned_task_reader as source_gate
from voodoo_product.composition import install_composed_product_platform
from voodoo_product.config import CasebookReadBinding, ProductConfig

SESSION = "caser-native-integration-001"
PROJECT = "synthetic/CyberCaser"
PINNED_SOURCE = source_gate.EVIDENCE_SHELF / "VOODOO-CASEBOOK" / "TASK_TIMELINE_CANDIDATE_20261123"
CASEBOOK_ENV = {
    "VOODOO_CASEBOOK_READ_SOURCE_ROOT": "/absolute/code-root",
    "VOODOO_CASEBOOK_READ_DATA_ROOT": "/absolute/private-root",
    "VOODOO_CASEBOOK_READ_WORKSPACE_ID": "wrk_12345678901",
    "VOODOO_CASEBOOK_READ_SESSION_ID": SESSION,
    "VOODOO_CASEBOOK_READ_PROJECT": PROJECT,
}


def product_config(root: Path, *, binding=None, environment="local") -> ProductConfig:
    return ProductConfig(
        environment=environment,
        database_path=root / "product.sqlite3",
        sandbox_root=root / "unused-sandbox",
        session_signing_secret="s" * 64,
        bootstrap_token="b" * 48,
        casebook_read_binding=binding,
    )


def test_casebook_is_disabled_by_default_in_native_composition(tmp_path: Path):
    app = FastAPI()
    install_composed_product_platform(
        app, config=product_config(tmp_path), repository_root=tmp_path,
    )
    assert getattr(app.state, "voodoo_casebook_task_gateway", None) is None
    with TestClient(app) as client:
        assert client.get("/api/v1/casebook/tasks/" + SESSION).status_code == 401


def test_explicit_casebook_env_binding_requires_all_fields(monkeypatch):
    for key in CASEBOOK_ENV:
        monkeypatch.delenv(key, raising=False)
    # Use the public ProductConfig.from_env parser without external secrets.
    import voodoo_product.config as config_mod

    assert config_mod._casebook_read_binding_from_env() is None
    monkeypatch.setenv("VOODOO_CASEBOOK_READ_SOURCE_ROOT", "/somewhere")
    with pytest.raises(ValueError, match="all five"):
        config_mod._casebook_read_binding_from_env()
    for key, value in CASEBOOK_ENV.items():
        monkeypatch.setenv(key, value)
    result = config_mod._casebook_read_binding_from_env()
    assert result is not None
    assert result.session_id == SESSION
    assert result.project == PROJECT
    assert result.workspace_id == "wrk_12345678901"


def test_casebook_binding_is_local_only_and_effects_disabled(tmp_path: Path):
    binding = CasebookReadBinding(
        source_root=tmp_path / "code", data_root=tmp_path / "private",
        workspace_id="wrk_12345678901", session_id=SESSION, project=PROJECT,
    )
    with pytest.raises(ValueError, match="local-only"):
        product_config(tmp_path, binding=binding, environment="production")
    with pytest.raises(ValueError, match="local-only"):
        product_config(tmp_path, binding=binding, environment="test")
    with pytest.raises(ValueError, match="exact source"):
        CasebookReadBinding(
            source_root=Path("relative"), data_root=tmp_path / "private",
            workspace_id="wrk_12345678901", session_id=SESSION, project=PROJECT,
        )


def _prepared_native_product(tmp_path: Path):
    """Create one disposable local native account/workspace without CASEBOOK."""
    app = FastAPI()
    product = install_composed_product_platform(
        app, config=product_config(tmp_path), repository_root=tmp_path,
    )
    with TestClient(app) as client:
        result = client.post("/api/v1/auth/bootstrap", json={
            "username": "synthetic-owner",
            "password": "LongSyntheticPasswordForTesting!",
            "bootstrap_token": "b" * 48,
        })
        assert result.status_code == 201, result.text
    workspace = next(w for w in product.service.list_workspaces()
                     if w["environment"] == "local")
    return workspace["id"]


def test_wrong_native_workspace_fails_at_startup(tmp_path: Path):
    _prepared_native_product(tmp_path)
    binding = CasebookReadBinding(
        source_root=tmp_path / "unreviewed-source",
        data_root=tmp_path / "never-touch-data",
        workspace_id="wrk_unknown_access", session_id=SESSION, project=PROJECT,
    )
    with pytest.raises(RuntimeError, match="workspace binding"):
        install_composed_product_platform(
            FastAPI(), config=product_config(tmp_path, binding=binding),
            repository_root=tmp_path,
        )
    assert not (tmp_path / "never-touch-data").exists()


@pytest.fixture
def approved_source(tmp_path: Path):
    source = PINNED_SOURCE / "voodoo_casebook"
    if not source.is_dir():
        pytest.skip("pinned CASEBOOK candidate absent; native read E2E unavailable")
    root = tmp_path / "reviewed-source"
    target = root / "voodoo_casebook"
    target.mkdir(parents=True, mode=0o700)
    for name, digest in source_gate.PINNED_PACKAGE_DIGESTS.items():
        candidate = source / name
        assert hashlib.sha256(candidate.read_bytes()).hexdigest() == digest
        shutil.copyfile(candidate, target / name)
    return root


def test_actual_native_composition_reads_only_bound_real_sqlite_journal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, approved_source: Path,
):
    monkeypatch.setattr(source_gate, "EVIDENCE_SHELF", tmp_path)
    workspace_id = _prepared_native_product(tmp_path)
    # Separate, SHA-pinned code supplies CASEBOOK's actual SQLite journal.
    monkeypatch.syspath_prepend(str(approved_source))
    from voodoo_casebook import CasebookStore

    evidence = tmp_path / "private-casebook"
    store = CasebookStore(evidence)
    store.start_session(
        project=PROJECT, goal="Review exact V-One task scope", session_id=SESSION,
    )
    store.append(
        session_id=SESSION, event_type="RESULT", source="tool",
        summary="unverified recorded result", status="RESOLVED",
    )
    before = hashlib.sha256(store.database.read_bytes()).hexdigest()
    binding = CasebookReadBinding(
        source_root=approved_source, data_root=evidence,
        workspace_id=workspace_id, session_id=SESSION, project=PROJECT,
    )
    app = FastAPI()
    product = install_composed_product_platform(
        app, config=product_config(tmp_path, binding=binding),
        repository_root=tmp_path,
    )
    assert getattr(app.state, "voodoo_casebook_task_gateway", None) is not None
    assert product.database_permission_authority is not None

    with TestClient(app) as client:
        result = client.post("/api/v1/auth/login", json={
            "username": "synthetic-owner",
            "password": "LongSyntheticPasswordForTesting!",
        })
        assert result.status_code == 200, result.text
        token = result.json()["token"]
        uri = "/api/v1/casebook/tasks/" + SESSION
        assert client.get(uri).status_code == 401
        response = client.get(uri, headers={"Authorization": "Bearer " + token})
        assert response.status_code == 200, response.text
        assert response.json()["display_state"] == "RESULT_RECORDED_UNVERIFIED"
        assert response.json()["execution_verified_by_this_view"] is False
        assert response.json()["independent_verifier"] == "NOT_ATTESTED"
        assert client.get(
            "/api/v1/casebook/tasks/caser-other-project",
            headers={"Authorization": "Bearer " + token},
        ).status_code == 404
    assert hashlib.sha256(store.database.read_bytes()).hexdigest() == before


def test_unreviewed_source_fails_closed_on_native_startup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, approved_source: Path,
):
    monkeypatch.setattr(source_gate, "EVIDENCE_SHELF", tmp_path)
    workspace_id = _prepared_native_product(tmp_path)
    evidence = tmp_path / "private-casebook"
    evidence.mkdir(mode=0o700)
    modified = approved_source / "voodoo_casebook" / "task_view.py"
    modified.write_bytes(modified.read_bytes() + b"\n# unreviewed\n")
    binding = CasebookReadBinding(
        source_root=approved_source, data_root=evidence,
        workspace_id=workspace_id, session_id=SESSION, project=PROJECT,
    )
    with pytest.raises(RuntimeError, match="SHA-256"):
        install_composed_product_platform(
            FastAPI(), config=product_config(tmp_path, binding=binding),
            repository_root=tmp_path,
        )
