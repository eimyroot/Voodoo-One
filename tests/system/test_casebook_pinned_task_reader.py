"""Source-pin negative and real SQLite test for nonproduction CASEBOOK reader.

All executable source files come from the reviewed immutable CASEBOOK branch,
are SHA-256 checked, and are copied to ephemeral pytest-private fixtures.
No owner CASEBOOK session, live identity, G8, network or deploy is accessed.
"""
from __future__ import annotations

import hashlib
import os
import pwd
import shutil
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from voodoo_product.casebook_pinned_task_reader import (
    PINNED_PACKAGE_DIGESTS,
    PinnedCasebookTaskReader,
)
from voodoo_product.casebook_task_gateway import (
    CasebookTaskAccessDenied,
    CasebookTaskGateway,
    CasebookTaskUnavailable,
    TaskScope,
    attach_casebook_task_gateway,
)
from voodoo_product.composition import install_composed_product_platform
from voodoo_product.config import ProductConfig

SOURCE = (Path(pwd.getpwuid(os.getuid()).pw_dir) / "0_EVIDENCE" / "VOODOO-CASEBOOK" / "TASK_TIMELINE_CANDIDATE_20261123")
SESSION = "caser-pinned-real-001"
PROJECT = "synthetic/CyberCaser"


@pytest.fixture
def clone_source(tmp_path: Path) -> Path:
    source = SOURCE / "voodoo_casebook"
    if not source.is_dir():
        pytest.skip("pinned CASEBOOK source unavailable")
    root = tmp_path / "immutable-review-code"
    folder = root / "voodoo_casebook"
    folder.mkdir(parents=True, mode=0o700)
    for name, sha in PINNED_PACKAGE_DIGESTS.items():
        source_file = source / name
        assert hashlib.sha256(source_file.read_bytes()).hexdigest() == sha
        shutil.copyfile(source_file, folder / name)
    return root


@pytest.fixture
def synthetic_journal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.syspath_prepend(str(SOURCE))
    from voodoo_casebook import CasebookStore

    root = tmp_path / "owner-private-synthetic-casebook"
    store = CasebookStore(root)
    store.start_session(project=PROJECT, goal="Display one governed local task", session_id=SESSION)
    store.append(
        session_id=SESSION, event_type="RESULT", source="tool", status="RESOLVED",
        summary="Recorded claim, not externally verified",
    )
    return root


def test_pinned_reader_projects_real_sqlite_and_does_not_modify_journal(
    clone_source: Path, synthetic_journal: Path
):
    reader = PinnedCasebookTaskReader(source_root=clone_source, data_root=synthetic_journal)
    db = synthetic_journal / "casebook.sqlite3"
    before = db.stat().st_mtime_ns
    actual = reader(SESSION)
    assert actual["display_state"] == "RESULT_RECORDED_UNVERIFIED"
    assert actual["native_approval"] == "NOT_ATTESTED"
    assert actual["isolated_runner_execution"] == "NOT_ATTESTED"
    assert actual["independent_verifier"] == "NOT_ATTESTED"
    assert [x["type"] for x in actual["timeline"]] == ["GOAL", "RESULT"]
    assert db.stat().st_mtime_ns == before
    assert not list(clone_source.rglob("__pycache__"))


@pytest.mark.parametrize("filename", ["__init__.py", "core.py", "task_view.py"])
def test_tampered_code_is_denied_before_any_import_or_journal_access(
    clone_source: Path, synthetic_journal: Path, filename: str
):
    altered = clone_source / "voodoo_casebook" / filename
    altered.write_bytes(altered.read_bytes() + b"\n# unreviewed source change\n")
    with pytest.raises(CasebookTaskUnavailable, match="SHA-256"):
        PinnedCasebookTaskReader(source_root=clone_source, data_root=synthetic_journal)
    assert not list(clone_source.rglob("__pycache__"))


def test_source_change_after_attachment_denied_before_any_read(
    clone_source: Path, synthetic_journal: Path
):
    reader = PinnedCasebookTaskReader(source_root=clone_source, data_root=synthetic_journal)
    altered = clone_source / "voodoo_casebook" / "core.py"
    altered.write_bytes(altered.read_bytes() + b"\n# drift after attachment\n")
    with pytest.raises(CasebookTaskUnavailable, match="SHA-256"):
        reader(SESSION)


def test_absent_private_root_denied_without_creating_it(
    clone_source: Path, tmp_path: Path
):
    root = tmp_path / "never-present"
    with pytest.raises(CasebookTaskUnavailable, match="not present"):
        PinnedCasebookTaskReader(source_root=clone_source, data_root=root)
    assert not root.exists()


def test_unsafe_private_root_mode_denied(
    clone_source: Path, synthetic_journal: Path
):
    synthetic_journal.chmod(0o755)
    with pytest.raises(CasebookTaskUnavailable, match="owner-private"):
        PinnedCasebookTaskReader(
            source_root=clone_source, data_root=synthetic_journal,
        )


def test_symlinked_source_or_private_root_is_denied(
    clone_source: Path, synthetic_journal: Path, tmp_path: Path
):
    alias = tmp_path / "unsafe-alias"
    alias.symlink_to(clone_source, target_is_directory=True)
    with pytest.raises(CasebookTaskUnavailable, match="canonical"):
        PinnedCasebookTaskReader(source_root=alias, data_root=synthetic_journal)
    alias.unlink()
    alias.symlink_to(synthetic_journal, target_is_directory=True)
    with pytest.raises(CasebookTaskUnavailable, match="canonical"):
        PinnedCasebookTaskReader(source_root=clone_source, data_root=alias)


def build_native_app(tmp_path: Path, *, environment="test"):
    app = FastAPI()
    config = ProductConfig(
        environment=environment,
        database_path=tmp_path / "product.sqlite3",
        sandbox_root=tmp_path / "sandboxes",
        session_signing_secret="s" * 64,
        bootstrap_token="b" * 48,
    )
    composition = install_composed_product_platform(
        app, config=config, repository_root=tmp_path,
    )
    client = TestClient(app)
    bootstrap = client.post("/api/v1/auth/bootstrap", json={
        "username": "synthetic-admin",
        "password": "SyntheticLongPassword!2026",
        "bootstrap_token": "b" * 48,
    })
    assert bootstrap.status_code == 201, bootstrap.text
    token = bootstrap.json()["token"]
    workspace = next(
        row for row in composition.service.list_workspaces()
        if row["environment"] == "local"
    )
    scope = TaskScope(
        session_id=SESSION, workspace_id=workspace["id"],
        environment="local", project=PROJECT,
    )
    return app, composition, client, token, scope


def test_scoped_http_reads_pinned_real_casebook_journal(
    clone_source: Path, synthetic_journal: Path, tmp_path: Path
):
    app, composition, client, token, scope = build_native_app(tmp_path)
    reader = PinnedCasebookTaskReader(source_root=clone_source, data_root=synthetic_journal)
    attach_casebook_task_gateway(
        app=app, composition=composition, reader=reader, scopes=[scope],
    )
    response = client.get(
        f"/api/v1/casebook/tasks/{SESSION}",
        headers={"Authorization": "Bearer " + token},
    )
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["display_state"] == "RESULT_RECORDED_UNVERIFIED"
    assert response.json()["independent_verifier"] == "NOT_ATTESTED"


def test_local_product_accepts_only_pinned_scoped_read_source(
    clone_source: Path,
    synthetic_journal: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    # Relocate the evidence shelf **only for disposable test data**.
    # No owner data or persistent policy is changed by this fixture.
    import voodoo_product.casebook_pinned_task_reader as reader_module

    monkeypatch.setattr(reader_module, "EVIDENCE_SHELF", tmp_path)
    app, composition, client, token, scope = build_native_app(
        tmp_path, environment="local",
    )
    reader = PinnedCasebookTaskReader(
        source_root=clone_source, data_root=synthetic_journal,
    )
    attach_casebook_task_gateway(
        app=app, composition=composition, reader=reader, scopes=[scope],
    )
    url = f"/api/v1/casebook/tasks/{SESSION}"
    denied = client.get(url)
    assert denied.status_code == 401
    allowed = client.get(
        url, headers={"Authorization": "Bearer " + token},
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["display_state"] == "RESULT_RECORDED_UNVERIFIED"
    assert allowed.json()["independent_verifier"] == "NOT_ATTESTED"
    logout = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": "Bearer " + token},
    )
    assert logout.status_code == 204
    assert client.get(url, headers={"Authorization": "Bearer " + token}).status_code == 401


def test_sqlite_exception_is_generic_http_unavailable(tmp_path: Path):
    import sqlite3

    app, composition, client, token, scope = build_native_app(tmp_path)
    def raised(_session: str):
        raise sqlite3.DatabaseError("/private/user-journal/casebook.sqlite3 corrupt")
    attach_casebook_task_gateway(
        app=app, composition=composition, reader=raised, scopes=[scope],
    )
    response = client.get(
        f"/api/v1/casebook/tasks/{SESSION}",
        headers={"Authorization": "Bearer " + token},
    )
    assert response.status_code == 503
    assert "/private" not in response.text
    assert "corrupt" not in response.text


def test_local_product_cannot_attach_arbitrary_reader(tmp_path: Path):
    app, composition, client, token, scope = build_native_app(
        tmp_path, environment="local",
    )
    with pytest.raises(CasebookTaskAccessDenied, match="source-pinned"):
        attach_casebook_task_gateway(
            app=app, composition=composition,
            reader=lambda _: {"schema": "untrusted"},
            scopes=[scope],
        )
    assert getattr(app.state, "voodoo_casebook_task_gateway", None) is None
    response = client.get(
        f"/api/v1/casebook/tasks/{SESSION}",
        headers={"Authorization": "Bearer " + token},
    )
    assert response.status_code == 503


def test_local_product_rejects_pinned_reader_outside_evidence_shelf(
    clone_source: Path, synthetic_journal: Path, tmp_path: Path
):
    app, composition, _, _, scope = build_native_app(tmp_path, environment="local")
    reader = PinnedCasebookTaskReader(source_root=clone_source, data_root=synthetic_journal)
    with pytest.raises(CasebookTaskAccessDenied, match="source-pinned"):
        CasebookTaskGateway(
            composition=composition, scopes=(scope,), reader=reader,
        )
