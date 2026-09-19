from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import FastAPI

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ADMIN_USERNAME = "g8-admin"
OPERATOR_USERNAME = "g8-operator"
ADMIN_CREDENTIAL_ENV = "VONE_G8_ACCEPTANCE_ADMIN_PASSWORD"
OPERATOR_CREDENTIAL_ENV = "VONE_G8_ACCEPTANCE_OPERATOR_PASSWORD"
TARGET_REPOSITORY_ENV = "VONE_G8_TARGET_REPOSITORY"
TARGET_REF_ENV = "VONE_G8_TARGET_REF"
BASE_URL_ENV = "VONE_G8_BASE_URL"


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"required environment variable is missing: {name}")
    return value.strip()


def _config() -> Any:
    from voodoo_product.config import ProductConfig

    return ProductConfig.from_env()


def _json_response(response: Any) -> Any:
    raw = response.read().decode("utf-8")
    return json.loads(raw) if raw else None


def _http_json(
    method: str,
    path: str,
    *,
    token: str | None = None,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    base_url = _required_env(BASE_URL_ENV).rstrip("/")
    if not base_url.startswith("http://127.0.0.1:"):
        raise RuntimeError("acceptance HTTP base URL must be loopback")
    request_headers = {"Accept": "application/json"}
    if token is not None:
        request_headers["Authorization"] = f"Bearer {token}"
    if headers:
        request_headers.update(headers)
    data = None
    if body is not None:
        data = json.dumps(body, sort_keys=True).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(  # noqa: S310 -- loopback checked above
        f"{base_url}{path}",
        data=data,
        headers=request_headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 -- loopback checked above
            return _json_response(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {path}: {detail}") from exc


def _login(username: str, password: str) -> str:
    result = _http_json(
        "POST",
        "/api/v1/auth/login",
        body={"username": username, "password": password},
    )
    token = result.get("token") if isinstance(result, dict) else None
    if not isinstance(token, str) or not token:
        raise RuntimeError("login did not return a bearer token")
    return token


def _fixture() -> dict[str, Any]:
    from voodoo_product.service import ProductService

    config = _config()
    service = ProductService(config)
    if service.has_users():
        raise RuntimeError("acceptance fixture requires a fresh product database")
    bootstrap = service.bootstrap_admin(
        username=ADMIN_USERNAME,
        password=_required_env(ADMIN_CREDENTIAL_ENV),
        token=config.bootstrap_token,
    )
    operator = service.create_user(
        actor_id=bootstrap["user_id"],
        username=OPERATOR_USERNAME,
        password=_required_env(OPERATOR_CREDENTIAL_ENV),
        role="operator",
    )
    service.workspace_service.add_member(
        actor_id=bootstrap["user_id"],
        workspace_id=bootstrap["workspace_id"],
        user_id=operator["id"],
    )
    return {
        "status": "PASS",
        "workspace_id": bootstrap["workspace_id"],
        "admin_user_id": bootstrap["user_id"],
        "operator_user_id": operator["id"],
    }


def _approved_request(*, title: str) -> tuple[str, str]:
    admin_token = _login(ADMIN_USERNAME, _required_env(ADMIN_CREDENTIAL_ENV))
    operator_token = _login(OPERATOR_USERNAME, _required_env(OPERATOR_CREDENTIAL_ENV))
    workspaces = _http_json("GET", "/api/v1/workspaces", token=admin_token)
    if not isinstance(workspaces, list) or len(workspaces) != 1:
        raise RuntimeError("acceptance fixture must expose exactly one workspace")
    workspace_id = workspaces[0].get("id")
    if not isinstance(workspace_id, str):
        raise RuntimeError("workspace id is invalid")
    request_value = _http_json(
        "POST",
        "/api/v1/change-requests",
        token=admin_token,
        body={
            "workspace_id": workspace_id,
            "title": title,
            "description": "G8 exact-head live READ acceptance",
            "risk": "R1",
            "environment": "staging",
            "adapter": "github-read-ref",
            "payload": {
                "repository": _required_env(TARGET_REPOSITORY_ENV),
                "ref": _required_env(TARGET_REF_ENV),
            },
        },
    )
    request_id = request_value.get("id") if isinstance(request_value, dict) else None
    if not isinstance(request_id, str):
        raise RuntimeError("change request id is invalid")
    _http_json("POST", f"/api/v1/change-requests/{request_id}/submit", token=admin_token)
    _http_json(
        "POST",
        f"/api/v1/change-requests/{request_id}/decision",
        token=operator_token,
        body={
            "decision": "APPROVED",
            "reason": "G8 live acceptance independent approval",
        },
    )
    return request_id, operator_token


def _assert_verified_response(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeError("canonical READ response is invalid")
    verification = value.get("verification")
    execution = value.get("execution")
    if not isinstance(verification, dict) or not isinstance(execution, dict):
        raise RuntimeError("canonical READ response is incomplete")
    if verification.get("verdict") != "VERIFIED":
        raise RuntimeError("canonical READ did not produce VERIFIED result")
    if verification.get("strength_class") != "INDEPENDENT_PROVIDER_READBACK":
        raise RuntimeError("canonical READ verification strength is not independent readback")
    if execution.get("status") != "SUCCEEDED":
        raise RuntimeError("canonical READ execution did not succeed")
    return value


def _http_e2e() -> dict[str, Any]:
    request_id, operator_token = _approved_request(title="G8 HTTP exact-head READ")
    response = _http_json(
        "POST",
        f"/api/v1/operations/{request_id}/read",
        token=operator_token,
        headers={"Idempotency-Key": "g8-http-e2e-001"},
        body={"correlation_id": "g8-http-e2e-001"},
    )
    verified = _assert_verified_response(response)
    return {
        "status": "PASS",
        "request_id": request_id,
        "operation": verified["operation"],
        "execution": verified["execution"],
        "verification": verified["verification"],
    }


def _http_create_approved() -> dict[str, Any]:
    request_id, _ = _approved_request(title="G8 restart exact-head READ")
    return {"status": "PASS", "request_id": request_id}


def _composition() -> Any:
    from voodoo_product.composition import install_composed_product_platform
    from voodoo_product.g8_product_activation import resolve_g8_read_runtime_factory

    config = _config()
    factory = resolve_g8_read_runtime_factory(config)
    if factory is None:
        raise RuntimeError("G8 runtime is not enabled")
    return install_composed_product_platform(
        FastAPI(),
        config=config,
        repository_root=Path.cwd(),
        canonical_runtime_factory=factory,
    )


def _operator_id(service: Any) -> str:
    user = service.authenticate(
        username=OPERATOR_USERNAME,
        password=_required_env(OPERATOR_CREDENTIAL_ENV),
    )
    user_id = user.get("id") if isinstance(user, dict) else None
    if not isinstance(user_id, str):
        raise RuntimeError("operator identity is invalid")
    return user_id


def _prepare_active(request_id: str) -> dict[str, Any]:
    from voodoo_product.canonical_read_terminal import READ_ONLY_TERMINAL_PROFILE
    from voodoo_product.github_read_provider import GITHUB_READ_REF_CAPABILITY

    composition = _composition()
    runtime = composition.canonical_operation_runtime
    if runtime is None:
        raise RuntimeError("canonical runtime is unavailable")
    prepared = runtime.pipeline.prepare(
        actor_id=_operator_id(composition.service),
        request_id=request_id,
        idempotency_key=f"g8-restart-{request_id}",
        correlation_id="g8-restart-active",
        required_terminal_profile=READ_ONLY_TERMINAL_PROFILE,
        required_capability=GITHUB_READ_REF_CAPABILITY,
    )
    return {
        "status": "ACTIVE",
        "request_id": prepared.request_id,
        "execution_id": prepared.execution_id,
        "execution_epoch": prepared.execution_epoch,
        "lease_id": prepared.lease_id,
        "lease_digest": prepared.lease_digest,
        "grant_digest": prepared.grant_digest,
        "outbox_entry_digest": prepared.outbox_entry_digest,
        "admission_digest": prepared.admission_digest,
    }


def _resume(execution_id: str) -> dict[str, Any]:
    composition = _composition()
    runtime = composition.canonical_operation_runtime
    if runtime is None:
        raise RuntimeError("canonical runtime is unavailable")
    result = runtime.run_resumed_read_only(
        actor_id=_operator_id(composition.service),
        execution_id=execution_id,
    )
    if result.prepared.execution_id != execution_id:
        raise RuntimeError("resume returned a different execution id")
    verification = result.verification_result
    if verification.verdict != "VERIFIED":
        raise RuntimeError("resumed execution was not independently verified")
    if verification.verification_strength_class != "INDEPENDENT_PROVIDER_READBACK":
        raise RuntimeError("resumed verification strength is not independent readback")
    if result.runner_observation.commit_sha != result.verifier_observation.commit_sha:
        raise RuntimeError("Runner and Verifier observed different GitHub refs")
    expected_sha = _required_env("VONE_G8_EXPECTED_TARGET_SHA")
    if result.runner_observation.commit_sha != expected_sha:
        raise RuntimeError("resumed provider observation does not match expected candidate SHA")
    return {
        "status": "VERIFIED",
        "execution_id": execution_id,
        "execution_epoch": result.prepared.execution_epoch,
        "runner_commit_sha": result.runner_observation.commit_sha,
        "verifier_commit_sha": result.verifier_observation.commit_sha,
        "verification_result_digest": verification.result_digest,
        "verification_strength_class": verification.verification_strength_class,
        "verification_reason": verification.reason,
    }


def _lineage(execution_id: str) -> dict[str, Any]:
    database_path = _config().database_path
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        queries = {
            "authorization_snapshots": "SELECT COUNT(*) AS count FROM authorization_snapshots WHERE execution_id = ?",
            "execution_grants_v2": "SELECT COUNT(*) AS count FROM execution_grants_v2 WHERE execution_id = ?",
            "grant_consumptions_v1": "SELECT COUNT(*) AS count FROM grant_consumptions_v1 WHERE execution_id = ?",
            "dispatch_outbox_v1": "SELECT COUNT(*) AS count FROM dispatch_outbox_v1 WHERE execution_id = ?",
            "dispatch_inbox_v1": "SELECT COUNT(*) AS count FROM dispatch_inbox_v1 WHERE execution_id = ?",
            "execution_leases_v1": "SELECT COUNT(*) AS count FROM execution_leases_v1 WHERE execution_id = ?",
            "execution_epoch_state_v1": "SELECT COUNT(*) AS count FROM execution_epoch_state_v1 WHERE execution_id = ?",
        }
        counts: dict[str, int] = {}
        for table, query in queries.items():
            row = connection.execute(query, (execution_id,)).fetchone()
            counts[table] = int(row["count"])
        epoch = connection.execute(
            "SELECT current_epoch, current_lease_id, current_lease_digest, status "
            "FROM execution_epoch_state_v1 WHERE execution_id = ?",
            (execution_id,),
        ).fetchone()
        if epoch is None:
            raise RuntimeError("execution epoch state is missing")
        return {
            "execution_id": execution_id,
            "counts": counts,
            "current_epoch": int(epoch["current_epoch"]),
            "current_lease_id": str(epoch["current_lease_id"]),
            "current_lease_digest": str(epoch["current_lease_digest"]),
            "status": str(epoch["status"]),
        }
    finally:
        connection.close()


def _assert_lineage(execution_id: str, expected_status: str) -> dict[str, Any]:
    snapshot = _lineage(execution_id)
    for table, count in snapshot["counts"].items():
        if count != 1:
            raise RuntimeError(f"duplicate or missing durable lineage in {table}: {count}")
    if snapshot["status"] != expected_status:
        raise RuntimeError(
            f"execution status mismatch: expected {expected_status}, got {snapshot['status']}"
        )
    return snapshot


def _emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, sort_keys=True, separators=(",", ":")))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="G8 exact-head live product acceptance driver")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("fixture")
    subparsers.add_parser("http-e2e")
    subparsers.add_parser("http-create-approved")
    prepare = subparsers.add_parser("prepare-active")
    prepare.add_argument("--request-id", required=True)
    prepare.add_argument("--hold-seconds", type=int, default=0)
    resume = subparsers.add_parser("resume")
    resume.add_argument("--execution-id", required=True)
    lineage = subparsers.add_parser("assert-lineage")
    lineage.add_argument("--execution-id", required=True)
    lineage.add_argument("--status", choices=("ACTIVE", "COMPLETED"), required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "fixture":
        _emit(_fixture())
    elif args.command == "http-e2e":
        _emit(_http_e2e())
    elif args.command == "http-create-approved":
        _emit(_http_create_approved())
    elif args.command == "prepare-active":
        if args.hold_seconds < 0 or args.hold_seconds > 1800:
            raise ValueError("hold-seconds must be between 0 and 1800")
        _emit(_prepare_active(args.request_id))
        sys.stdout.flush()
        if args.hold_seconds:
            time.sleep(args.hold_seconds)
    elif args.command == "resume":
        _emit(_resume(args.execution_id))
    elif args.command == "assert-lineage":
        _emit(_assert_lineage(args.execution_id, args.status))
    else:
        raise RuntimeError("unsupported acceptance command")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
