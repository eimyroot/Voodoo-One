from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

from scripts.verify_architecture_atlas import DEFAULT_MANIFEST, ROOT, verify_manifest


def _manifest() -> dict[str, object]:
    value = yaml.safe_load(DEFAULT_MANIFEST.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _write_manifest(tmp_path: Path, value: dict[str, object]) -> Path:
    path = tmp_path / "architecture-manifest.yaml"
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    return path


def test_current_architecture_manifest_matches_repository() -> None:
    result = verify_manifest()
    assert result["ok"] is True
    assert result["errors"] == []


def test_architecture_manifest_rejects_invalid_status(tmp_path: Path) -> None:
    value = deepcopy(_manifest())
    nodes = value["nodes"]
    assert isinstance(nodes, list)
    assert isinstance(nodes[0], dict)
    nodes[0]["status"] = "MAGICALLY_DONE"

    result = verify_manifest(_write_manifest(tmp_path, value), root=ROOT)
    assert result["ok"] is False
    assert any("invalid status" in error for error in result["errors"])


def test_architecture_manifest_rejects_missing_source_path(tmp_path: Path) -> None:
    value = deepcopy(_manifest())
    nodes = value["nodes"]
    assert isinstance(nodes, list)
    assert isinstance(nodes[0], dict)
    nodes[0]["source_paths"] = ["voodoo_product/definitely_missing.py"]

    result = verify_manifest(_write_manifest(tmp_path, value), root=ROOT)
    assert result["ok"] is False
    assert any("source path is missing" in error for error in result["errors"])


def test_architecture_manifest_rejects_route_drift(tmp_path: Path) -> None:
    value = deepcopy(_manifest())
    contract = value["objective_contract"]
    assert isinstance(contract, dict)
    routes = contract["routes"]
    assert isinstance(routes, list)
    assert isinstance(routes[0], dict)
    routes[0]["path"] = "/api/v1/missing"

    result = verify_manifest(_write_manifest(tmp_path, value), root=ROOT)
    assert result["ok"] is False
    assert any("declared route is missing" in error for error in result["errors"])

def test_architecture_manifest_rejects_migration_inventory_drift(tmp_path: Path) -> None:
    value = deepcopy(_manifest())
    contract = value["objective_contract"]
    assert isinstance(contract, dict)
    migrations = contract["sqlite_migrations"]
    assert isinstance(migrations, list)
    contract["sqlite_migrations"] = migrations[:-1]

    result = verify_manifest(_write_manifest(tmp_path, value), root=ROOT)
    assert result["ok"] is False
    assert any("migration inventory differs" in error for error in result["errors"])