"""Security, contract, and negative tests for the optional R1 map API."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from voodoo_product.api import install_product_platform
from voodoo_product.config import ProductConfig
from voodoo_product.project_control_map import (
    ProjectControlMapUnavailable,
    project_control_map_projection,
)


def sample_snapshot(*, age_days: int = 0) -> dict:
    observed = (datetime.now(UTC) - timedelta(days=age_days)).isoformat()
    sha_a = "a" * 40
    sha_b = "b" * 40
    return {
        "schema": "ProjectControlMapSnapshot/v1",
        "observed_at_utc": observed,
        "truth_policy": {
            "read_only": True,
            "project_authority_effect": "NONE",
            "automatic_git_merge": False,
            "automatic_priority_change": False,
            "unknown_is_pass": False,
            "provider_effects": "NOT_AUTHORIZED",
        },
        "finishgate": {
            "status": "IN_PROGRESS",
            "delivery": "PROJECT-CONTROL-MAP-R1",
        },
        "projects": [
            {
                "id": "voodoo-one",
                "name": "VOODOO One",
                "kind": "product_trust_control_plane",
                "canonical_repo": "eimyroot/Voodoo-One",
                "local_path": "/secret/private/workspace",
                "internal_secret": "this-must-never-leak",
                "observed_status": "UNKNOWN",
                "git": {
                    "local_branch": "review/staged",
                    "local_head": sha_a,
                    "remote_main_head_observed": sha_b,
                    "local_worktree": "CLEAN",
                },
            },
            {
                "id": "mrc",
                "name": "MRC",
                "kind": "phone_first_rescue",
                "canonical_repo": "eimyroot/MRC",
                "observed_status": "LIVE_HTTPS_OBSERVED",
                "git": {
                    "local_branch": "main",
                    "local_head": sha_b,
                    "remote_main_head_observed": sha_b,
                    "local_worktree": "CLEAN",
                },
            },
        ],
        "subworkstreams": [{"id": "architecture-lab", "parent_project_id": "voodoo-one"}],
        "relationships": [
            {
                "from": "architecture-lab",
                "to": "voodoo-one",
                "kind": "nested_experiment",
                "status": "NONPROMOTED",
            }
        ],
        "known_gaps": ["MRC mobile-data verification deferred"],
    }


def write_pinned(tmp_path: Path, data: dict | bytes):
    file = tmp_path / "map.json"
    raw = data if isinstance(data, bytes) else (json.dumps(data) + "\n").encode()
    file.write_bytes(raw)
    return file, hashlib.sha256(raw).hexdigest()


def build_client(tmp_path: Path, path: Path | None = None, sha: str = "") -> TestClient:
    cfg = ProductConfig(
        environment="test",
        database_path=tmp_path / "product.sqlite3",
        sandbox_root=tmp_path / "sandboxes",
        session_signing_secret="s" * 64,
        bootstrap_token="b" * 48,
        project_control_map_snapshot_path=path,
        project_control_map_snapshot_sha256=sha,
    )
    app = FastAPI()
    install_product_platform(app, config=cfg, repository_root=tmp_path)
    return TestClient(app)


def token(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/bootstrap",
        json={
            "username": "admin",
            "password": "VeryStrongAdminPassword1!",
            "bootstrap_token": "b" * 48,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["token"]


def test_not_configured_stays_unavailable_and_requires_auth(tmp_path: Path):
    client = build_client(tmp_path)
    assert client.get("/api/v1/project-control-map").status_code == 401
    t = token(client)
    result = client.get("/api/v1/project-control-map", headers={"Authorization": "Bearer " + t})
    assert result.status_code == 503
    assert "path" not in result.text.lower()
    assert "secret" not in result.text.lower()
    assert client.get("/api/v1/project-control-map", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_config_rejects_unpinned_or_relative_evidence(tmp_path: Path):
    file = tmp_path / "test.json"
    with pytest.raises(ValueError, match="pinned SHA"):
        build_client(tmp_path, file)
    with pytest.raises(ValueError, match="absolute"):
        build_client(tmp_path, Path("relative.json"), "a" * 64)
    with pytest.raises(ValueError, match="requires a snapshot"):
        build_client(tmp_path, None, "a" * 64)


def test_pinned_snapshot_is_rendered_with_no_local_paths_or_secrets(tmp_path: Path):
    file, sha = write_pinned(tmp_path, sample_snapshot())
    client = build_client(tmp_path, file, sha)
    t = token(client)
    response = client.get("/api/v1/project-control-map", headers={"Authorization": "Bearer " + t})
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    d = response.json()
    assert d["schema"] == "ProjectControlMapProjection/v1"
    assert d["mode"] == "READ_ONLY"
    assert d["authority_effect"] == "NONE"
    assert d["freshness"] == "CURRENT_SNAPSHOT"
    assert len(d["projects"]) == 2
    assert len(d["relationships"]) == 1
    assert d["projects"][0]["status"] == "UNKNOWN"
    assert d["projects"][0]["head_comparison"] == "DIFFERENT_HEADS"
    assert "/secret/private" not in response.text
    assert "this-must-never-leak" not in response.text


def test_stale_observation_does_not_imply_live_verification(tmp_path: Path):
    file, sha = write_pinned(tmp_path, sample_snapshot(age_days=3))
    d = project_control_map_projection(file, sha)
    assert d["freshness"] == "STALE_SNAPSHOT"
    assert all(p["freshness"] == "STALE_SNAPSHOT" for p in d["projects"])


def test_integrity_mismatch_never_exposes_data(tmp_path: Path):
    file, sha = write_pinned(tmp_path, sample_snapshot())
    file.write_text('{"schema":"changed","secret":"never-expose"}')
    client = build_client(tmp_path, file, sha)
    t = token(client)
    response = client.get("/api/v1/project-control-map", headers={"Authorization": "Bearer " + t})
    assert response.status_code == 503
    assert "never-expose" not in response.text


@pytest.mark.parametrize("change", [
    ("truth_policy", "read_only", False),
    ("truth_policy", "automatic_git_merge", True),
    ("truth_policy", "unknown_is_pass", True),
    ("truth_policy", "project_authority_effect", "WRITE"),
    ("truth_policy", "provider_effects", "ALLOWED"),
    ("finishgate", "delivery", "OTHER_PROJECT"),
])
def test_invalid_scope_claims_fail_closed(tmp_path: Path, change):
    data = sample_snapshot()
    group, key, value = change
    data[group][key] = value
    file, sha = write_pinned(tmp_path, data)
    with pytest.raises(ProjectControlMapUnavailable):
        project_control_map_projection(file, sha)


def test_reject_orphaned_edge_and_duplicate_id(tmp_path: Path):
    data = sample_snapshot()
    data["relationships"][0]["to"] = "nonexistent"
    file, sha = write_pinned(tmp_path, data)
    with pytest.raises(ProjectControlMapUnavailable):
        project_control_map_projection(file, sha)
    data = sample_snapshot()
    data["projects"].append(data["projects"][0].copy())
    file, sha = write_pinned(tmp_path, data)
    with pytest.raises(ProjectControlMapUnavailable):
        project_control_map_projection(file, sha)


def test_reject_bad_timestamp_sha_and_repo(tmp_path: Path):
    cases = [
        ("observed_at_utc", "2099-01-01T00:00:00Z"),
        ("observed_at_utc", "not-a-date"),
    ]
    for field, value in cases:
        data = sample_snapshot()
        data[field] = value
        file, sha = write_pinned(tmp_path, data)
        with pytest.raises(ProjectControlMapUnavailable):
            project_control_map_projection(file, sha)
    data = sample_snapshot()
    data["projects"][0]["git"]["local_head"] = "bad-sha"
    file, sha = write_pinned(tmp_path, data)
    with pytest.raises(ProjectControlMapUnavailable):
        project_control_map_projection(file, sha)
    data = sample_snapshot()
    data["projects"][0]["canonical_repo"] = "../path-injection"
    file, sha = write_pinned(tmp_path, data)
    with pytest.raises(ProjectControlMapUnavailable):
        project_control_map_projection(file, sha)


def test_reject_invalid_encoding_and_symlink(tmp_path: Path):
    file, sha = write_pinned(tmp_path, b"\xff\xfe")
    with pytest.raises(ProjectControlMapUnavailable):
        project_control_map_projection(file, sha)
    target, sha = write_pinned(tmp_path, sample_snapshot())
    link = tmp_path / "alias.json"
    link.symlink_to(target)
    with pytest.raises(ProjectControlMapUnavailable):
        project_control_map_projection(link, sha)


def test_reject_oversized_evidence(tmp_path: Path):
    file, sha = write_pinned(tmp_path, b" " * 262_145)
    with pytest.raises(ProjectControlMapUnavailable):
        project_control_map_projection(file, sha)


def test_ui_and_legacy_control_room_contract(tmp_path: Path):
    client = build_client(tmp_path)
    t = token(client)
    schema = client.get("/openapi.json").json()
    assert "/api/v1/project-control-map" in schema["paths"]
    assert "/api/v1/control-room" in schema["paths"]
    html = client.get("/console").text
    js = client.get("/console/assets/control_room.js").text
    assert 'data-view="projectmap"' in html
    assert 'id="view-projectmap"' in html
    assert "loadProjectMap" in js
    assert "escapeHtml(p.name)" in js
    assert "UNAVAILABLE / UNVERIFIED" in js
    assert "runCanonicalRead" in js
    legacy = client.get("/api/v1/control-room", headers={"Authorization": "Bearer " + t})
    assert legacy.status_code == 200
    assert "project_control_map" not in legacy.json()


def test_unstructured_evidence_fields_never_leak_into_api(tmp_path: Path):
    data = sample_snapshot()
    data["known_gaps"] = [
        "/Users/example/private/credentials.json",
        "Bearer synthetic_secret_that_must_not_be_public",
    ]
    file, sha = write_pinned(tmp_path, data)
    client = build_client(tmp_path, file, sha)
    token_value = token(client)
    response = client.get(
        "/api/v1/project-control-map",
        headers={"Authorization": "Bearer " + token_value},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "ADDITIONAL_UNSTRUCTURED_EVIDENCE_NOT_PUBLISHED" in payload["known_gaps"]
    assert "/Users/" not in response.text
    assert "synthetic_secret_that_must_not_be_public" not in response.text


@pytest.mark.parametrize(("field", "value"), [
    ("observed_status", "Bearer a-synthetic-password"),
    ("observed_status", "/Users/example/private"),
    ("observed_status", "<script>alert(1)</script>"),
])
def test_unstructured_project_status_fails_closed(tmp_path: Path, field: str, value: str):
    data = sample_snapshot()
    data["projects"][0][field] = value
    file, sha = write_pinned(tmp_path, data)
    with pytest.raises(ProjectControlMapUnavailable):
        project_control_map_projection(file, sha)


def test_unstructured_relation_status_fails_closed(tmp_path: Path):
    data = sample_snapshot()
    data["relationships"][0]["status"] = "/Users/example/private"
    file, sha = write_pinned(tmp_path, data)
    with pytest.raises(ProjectControlMapUnavailable):
        project_control_map_projection(file, sha)


@pytest.mark.parametrize(("field", "payload"), [
    ("name", "/Users/example/internal"),
    ("name", "Bearer synthetic_secret_material"),
    ("kind", "/home/other/private"),
    ("kind", "api_key=synthetic_secret_material"),
])
def test_public_project_fields_reject_sensitive_content(
    tmp_path: Path, field: str, payload: str
):
    data = sample_snapshot()
    data["projects"][0][field] = payload
    file, sha = write_pinned(tmp_path, data)
    with pytest.raises(ProjectControlMapUnavailable):
        project_control_map_projection(file, sha)


@pytest.mark.parametrize(("field", "payload"), [
    ("local_branch", "feature/password=synthetic"),
    ("local_branch", "/Users/example/secrets"),
])
def test_public_git_branch_rejects_sensitive_content(
    tmp_path: Path, field: str, payload: str
):
    data = sample_snapshot()
    data["projects"][0]["git"][field] = payload
    file, sha = write_pinned(tmp_path, data)
    with pytest.raises(ProjectControlMapUnavailable):
        project_control_map_projection(file, sha)


def test_public_relationship_kind_rejects_sensitive_content(tmp_path: Path):
    data = sample_snapshot()
    data["relationships"][0]["kind"] = "token=synthetic_secret"
    file, sha = write_pinned(tmp_path, data)
    with pytest.raises(ProjectControlMapUnavailable):
        project_control_map_projection(file, sha)
