from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs" / "architecture" / "atlas" / "architecture-manifest.yaml"
ALLOWED_STATUSES = {
    "VERIFIED",
    "IMPLEMENTED BUT NOT VERIFIED",
    "IN PROGRESS",
    "NEXT",
    "BLOCKED",
    "LATER",
}
HTTP_METHODS = {"delete", "get", "patch", "post", "put"}
MIGRATION_PATTERN = re.compile(r"^[0-9]{4}_[a-z0-9_]+\.sql$")


def _load_manifest(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("architecture manifest must be a mapping")
    return value

def _router_prefix(tree: ast.AST) -> str:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        call = node.value
        if not isinstance(call.func, ast.Name) or call.func.id != "APIRouter":
            continue
        if not any(isinstance(target, ast.Name) and target.id == "router" for target in node.targets):
            continue
        for keyword in call.keywords:
            if (
                keyword.arg == "prefix"
                and isinstance(keyword.value, ast.Constant)
                and isinstance(keyword.value.value, str)
            ):
                return keyword.value.value
    return ""


def _routes(path: Path) -> set[tuple[str, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    prefix = _router_prefix(tree)
    found: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not decorator.args:
                continue
            function = decorator.func
            if not isinstance(function, ast.Attribute) or function.attr not in HTTP_METHODS:
                continue
            if not isinstance(function.value, ast.Name) or function.value.id != "router":
                continue
            route_arg = decorator.args[0]
            if isinstance(route_arg, ast.Constant) and isinstance(route_arg.value, str):
                found.add((function.attr.upper(), f"{prefix}{route_arg.value}"))
    return found


def verify_manifest(path: Path = DEFAULT_MANIFEST, *, root: Path = ROOT) -> dict[str, Any]:
    manifest = _load_manifest(path)
    errors: list[str] = []
    if manifest.get("schema") != "johny-architecture-atlas/v1":
        errors.append("unsupported or missing architecture manifest schema")
    if set(manifest.get("status_values", [])) != ALLOWED_STATUSES:
        errors.append("status_values do not match the canonical Atlas statuses")

    nodes = manifest.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        errors.append("nodes must be a non-empty list")
        nodes = []
    for node in nodes:
        if not isinstance(node, dict):
            errors.append("node entry must be a mapping")
            continue
        node_id = str(node.get("id", "<missing>"))
        if node.get("status") not in ALLOWED_STATUSES:
            errors.append(f"node {node_id} has invalid status")
        for raw_path in node.get("source_paths", []):
            candidate = root / str(raw_path)
            if not candidate.exists():
                errors.append(f"node {node_id} source path is missing: {raw_path}")
    contract = manifest.get("objective_contract", {})
    if not isinstance(contract, dict):
        errors.append("objective_contract must be a mapping")
        contract = {}

    route_cache: dict[str, set[tuple[str, str]]] = {}
    for route in contract.get("routes", []):
        if not isinstance(route, dict):
            errors.append("route contract entry must be a mapping")
            continue
        source = str(route.get("source", ""))
        method = str(route.get("method", "")).upper()
        route_path = str(route.get("path", ""))
        source_path = root / source
        if source not in route_cache and source_path.is_file():
            route_cache[source] = _routes(source_path)
        if (method, route_path) not in route_cache.get(source, set()):
            errors.append(f"declared route is missing: {method} {route_path} in {source}")

    migration_dir = root / "voodoo_product" / "migrations" / "sqlite"
    actual_migrations = sorted(
        item.name for item in migration_dir.iterdir() if item.is_file() and MIGRATION_PATTERN.match(item.name)
    )
    expected_migrations = contract.get("sqlite_migrations", [])
    if actual_migrations != expected_migrations:
        errors.append("sqlite migration inventory differs from architecture manifest")

    for workflow in contract.get("workflows", []):
        if not (root / str(workflow)).is_file():
            errors.append(f"declared workflow is missing: {workflow}")

    try:
        manifest_display = str(path.relative_to(root))
    except ValueError:
        manifest_display = str(path)
    return {"ok": not errors, "errors": errors, "manifest": manifest_display}


def main() -> int:
    result = verify_manifest()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())