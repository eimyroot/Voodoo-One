from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from voodoo_product.canonical_operation_http import create_canonical_operation_router
from voodoo_product.security import Principal
from voodoo_product.terminal_profile import READ_ONLY_TERMINAL_PROFILE

D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64
D4 = "4" * 64
D5 = "5" * 64
D6 = "6" * 64
SECRET_MARKER = "provider-target-secret-marker"


class FakeIdentityProvider:
    def authenticate_bearer(self, token: str) -> Principal:
        if token == "operator-token":
            return Principal(user_id="usr-operator", username="operator", role="operator")
        if token == "developer-token":
            return Principal(user_id="usr-developer", username="developer", role="developer")
        if token == "viewer-token":
            return Principal(user_id="usr-viewer", username="viewer", role="viewer")
        raise PermissionError(f"invalid session contains {SECRET_MARKER}")


class FakePassport:
    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "vone.operation-passport/v1",
            "execution_id": "exec-1",
            "lifecycle_stage": "EXECUTION_COMPLETED",
            "operation": {"capability": "github.read-ref/v1"},
            "authority": {"snapshot": {"snapshot_digest": D1}},
            "dispatch": {"outbox": {"entry_digest": D2}},
            "runtime": {"status": "COMPLETED"},
            "verification": {
                "status": "NOT_PERSISTED",
                "verdict": "UNKNOWN",
                "result_digest": None,
                "independent_verification_exposed": False,
                "reason": "No durable VerificationResult/v1 is stored for this execution.",
            },
            "integrity": {
                "canonical_json_validated": True,
                "lineage_bindings_validated": True,
                "independent_verification_validated": False,
            },
        }


class FakePassportService:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[str] = []

    def get(self, execution_id: str) -> FakePassport:
        self.calls.append(execution_id)
        if self.error is not None:
            raise self.error
        return FakePassport()


class FakeRuntime:
    def __init__(self, *, verdict: str = "NOT_VERIFIED", error: Exception | None = None) -> None:
        self.read_terminal = object()
        self.verdict = verdict
        self.error = error
        self.calls: list[dict[str, str]] = []

    def run_read_only(self, **kwargs: str) -> object:
        self.calls.append(dict(kwargs))
        if self.error is not None:
            raise self.error
        prepared = SimpleNamespace(
            request_id=kwargs["request_id"],
            execution_id="exec-1",
            capability="github.read-ref/v1",
            environment="staging",
            target_digest=D1,
            terminal_profile=READ_ONLY_TERMINAL_PROFILE,
            execution_epoch=3,
            lease_digest=D2,
            execution_capsule_digest=D3,
        )
        verification = SimpleNamespace(
            verdict=self.verdict,
            reason="OBSERVED_STATE_MISMATCH" if self.verdict == "NOT_VERIFIED" else "OBSERVED_STATE_MATCH",
            verification_strength_class="INDEPENDENT_PROVIDER_READBACK",
            result_digest=D4,
            observed_post_state_digest=D5,
            verifier_identity_digest=D6,
            checked_at="2026-08-23T06:00:00.000+00:00",
        )
        return SimpleNamespace(
            prepared=prepared,
            runner_observation=SimpleNamespace(observation_digest="a" * 64),
            verification_result=verification,
        )


def client(
    runtime: object | None,
    *,
    passport_service: object | None = None,
) -> TestClient:
    app = FastAPI()
    app.include_router(
        create_canonical_operation_router(
            identity_provider=FakeIdentityProvider(),  # type: ignore[arg-type]
            runtime=runtime,  # type: ignore[arg-type]
            operation_passport_service=(
                passport_service or FakePassportService()
            ),  # type: ignore[arg-type]
        )
    )
    return TestClient(app)


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def read_headers(token: str = "operator-token") -> dict[str, str]:
    return {**auth(token), "Idempotency-Key": "canonical-read-1"}


def read_body(**extra: object) -> dict[str, object]:
    return {"correlation_id": "corr-canonical-1", **extra}


def test_status_requires_authentication_and_reports_no_write_surface() -> None:
    runtime = FakeRuntime()
    api = client(runtime)

    assert api.get("/api/v1/operations/status").status_code == 401
    response = api.get("/api/v1/operations/status", headers=auth("viewer-token"))

    assert response.status_code == 200
    assert response.json() == {
        "schema": "vone.canonical-operation-api-status/v1",
        "configured": True,
        "read_terminal_configured": True,
        "write_routes_exposed": False,
        "provider_write_effects_exposed": False,
    }


def test_authentication_error_does_not_leak_identity_provider_detail() -> None:
    api = client(FakeRuntime())

    response = api.get("/api/v1/operations/status", headers=auth("bad-token"))

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid authentication token"
    assert SECRET_MARKER not in response.text


def test_passport_is_read_only_and_available_without_runtime_activation() -> None:
    passport_service = FakePassportService()
    api = client(None, passport_service=passport_service)

    response = api.get(
        "/api/v1/operations/exec-1/passport",
        headers=auth("viewer-token"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema"] == "vone.operation-passport/v1"
    assert payload["execution_id"] == "exec-1"
    assert payload["lifecycle_stage"] == "EXECUTION_COMPLETED"
    assert payload["verification"]["verdict"] == "UNKNOWN"
    assert payload["verification"]["independent_verification_exposed"] is False
    assert passport_service.calls == ["exec-1"]


def test_passport_missing_canonical_execution_is_sanitized() -> None:
    api = client(
        None,
        passport_service=FakePassportService(
            error=LookupError(f"missing internal row {SECRET_MARKER}")
        ),
    )

    response = api.get(
        "/api/v1/operations/exec-404/passport",
        headers=auth("viewer-token"),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "canonical operation resource not found"
    assert SECRET_MARKER not in response.text


def test_read_fails_closed_when_runtime_is_not_configured() -> None:
    api = client(None)

    response = api.post(
        "/api/v1/operations/req-12345/read",
        headers=read_headers(),
        json=read_body(),
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "canonical operation runtime is not configured"


def test_read_requires_execution_permission() -> None:
    api = client(FakeRuntime())

    response = api.post(
        "/api/v1/operations/req-12345/read",
        headers=read_headers("developer-token"),
        json=read_body(),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "permission required: execution.run"


def test_caller_cannot_select_terminal_profile() -> None:
    runtime = FakeRuntime()
    api = client(runtime)

    response = api.post(
        "/api/v1/operations/req-12345/read",
        headers=read_headers(),
        json=read_body(terminal_profile="BOUNDED_MUTATION_VERIFIED"),
    )

    assert response.status_code == 422
    assert runtime.calls == []


def test_read_requires_idempotency_key() -> None:
    runtime = FakeRuntime()
    api = client(runtime)

    response = api.post(
        "/api/v1/operations/req-12345/read",
        headers=auth("operator-token"),
        json=read_body(),
    )

    assert response.status_code == 422
    assert runtime.calls == []


def test_unsafe_request_id_is_rejected_before_runtime() -> None:
    runtime = FakeRuntime()
    api = client(runtime)

    response = api.post(
        "/api/v1/operations/req%20unsafe/read",
        headers=read_headers(),
        json=read_body(),
    )

    assert response.status_code == 422
    assert runtime.calls == []


def test_execution_success_and_independent_verification_remain_separate() -> None:
    runtime = FakeRuntime(verdict="NOT_VERIFIED")
    api = client(runtime)

    response = api.post(
        "/api/v1/operations/req-12345/read",
        headers=read_headers(),
        json=read_body(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema"] == "vone.canonical-operation-read/v1"
    assert payload["operation"]["terminal_profile"] == READ_ONLY_TERMINAL_PROFILE
    assert payload["execution"]["status"] == "SUCCEEDED"
    assert payload["verification"]["verdict"] == "NOT_VERIFIED"
    assert payload["verification"]["reason"] == "OBSERVED_STATE_MISMATCH"
    assert runtime.calls == [
        {
            "actor_id": "usr-operator",
            "request_id": "req-12345",
            "idempotency_key": "canonical-read-1",
            "correlation_id": "corr-canonical-1",
        }
    ]


def test_runtime_permission_failure_is_sanitized_and_not_execution_success() -> None:
    runtime = FakeRuntime(
        error=PermissionError(
            f"CANONICAL_PIPELINE_REQUIRED_CAPABILITY_MISMATCH target={SECRET_MARKER}"
        )
    )
    api = client(runtime)

    response = api.post(
        "/api/v1/operations/req-12345/read",
        headers=read_headers(),
        json=read_body(),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "canonical operation denied"
    assert SECRET_MARKER not in response.text
    assert "REQUIRED_CAPABILITY_MISMATCH" not in response.text


def test_unknown_runtime_error_does_not_leak_internal_detail() -> None:
    runtime = FakeRuntime(error=Exception(f"unexpected provider state: {SECRET_MARKER}"))
    api = client(runtime)

    response = api.post(
        "/api/v1/operations/req-12345/read",
        headers=read_headers(),
        json=read_body(),
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "canonical operation failed"
    assert SECRET_MARKER not in response.text


def test_openapi_exposes_read_only_canonical_operation_surface() -> None:
    api = client(FakeRuntime())
    paths = api.get("/openapi.json").json()["paths"]

    assert "/api/v1/operations/status" in paths
    assert "/api/v1/operations/{execution_id}/passport" in paths
    assert paths["/api/v1/operations/{execution_id}/passport"] == {
        "get": paths["/api/v1/operations/{execution_id}/passport"]["get"]
    }
    assert "/api/v1/operations/{request_id}/read" in paths
    assert all("create-ref" not in path for path in paths)
    assert all("delete" not in path.casefold() for path in paths)
    assert all("rollback" not in path for path in paths)
