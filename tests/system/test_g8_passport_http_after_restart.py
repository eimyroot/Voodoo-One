from __future__ import annotations

import copy

import pytest

from scripts import g8_live_product_acceptance as g8

EXECUTION_ID = "exec_test123"
VERIFICATION_DIGEST = "b" * 64


def valid_passport() -> dict[str, object]:
    return {
        "schema": "vone.operation-passport/v1",
        "execution_id": EXECUTION_ID,
        "lifecycle_stage": "EXECUTION_COMPLETED",
        "operation": {"capability": "github.read-ref/v1", "environment": "staging"},
        "runtime": {"status": "COMPLETED"},
        "verification": {
            "status": "PERSISTED",
            "verdict": "VERIFIED",
            "independent_verification_exposed": True,
            "verification_strength_class": "INDEPENDENT_PROVIDER_READBACK",
            "result_digest": VERIFICATION_DIGEST,
        },
        "integrity": {
            "lineage_bindings_validated": True,
            "independent_verification_validated": True,
        },
    }


def setup_client(monkeypatch: pytest.MonkeyPatch, passport: object) -> list[tuple[str, str]]:
    calls: list[tuple[str, str]] = []
    monkeypatch.setenv(g8.OPERATOR_CREDENTIAL_ENV, "fixture-password-local-only")

    def login(username: str, password: str) -> str:
        assert username == g8.OPERATOR_USERNAME
        assert password == "fixture-password-local-only"
        return "fixture-bearer-local-only"

    def http(method: str, path: str, *, token: str | None = None) -> object:
        assert token == "fixture-bearer-local-only"
        calls.append((method, path))
        return copy.deepcopy(passport)

    monkeypatch.setattr(g8, "_login", login)
    monkeypatch.setattr(g8, "_http_json", http)
    return calls


def test_authenticated_passport_http_after_restart_requires_exact_durable_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = setup_client(monkeypatch, valid_passport())
    result = g8._assert_passport_http_after_restart(EXECUTION_ID, VERIFICATION_DIGEST)

    assert result == {
        "status": "PASS",
        "schema": "vone.operation-passport/v1",
        "execution_id": EXECUTION_ID,
        "lifecycle_stage": "EXECUTION_COMPLETED",
        "verification_result_digest": VERIFICATION_DIGEST,
        "verification_strength_class": "INDEPENDENT_PROVIDER_READBACK",
        "lineage_bindings_validated": True,
        "independent_verification_validated": True,
    }
    assert calls == [
        ("GET", f"/api/v1/operations/{EXECUTION_ID}/passport"),
    ]


@pytest.mark.parametrize(
    ("path", "bad_value"),
    [
        (("schema",), "vone.other-schema/v1"),
        (("execution_id",), "exec_other"),
        (("lifecycle_stage",), "EXECUTION_ACTIVE"),
        (("operation", "capability"), "github.create-ref/v1"),
        (("operation", "environment"), "production"),
        (("runtime", "status"), "ACTIVE"),
        (("verification", "status"), "NOT_PERSISTED"),
        (("verification", "verdict"), "UNKNOWN"),
        (("verification", "independent_verification_exposed"), False),
        (("verification", "verification_strength_class"), "SELF_REPORTED"),
        (("verification", "result_digest"), "c" * 64),
        (("integrity", "lineage_bindings_validated"), False),
        (("integrity", "independent_verification_validated"), False),
    ],
)
def test_passport_http_rejects_mismatched_or_incomplete_evidence(
    monkeypatch: pytest.MonkeyPatch, path: tuple[str, ...], bad_value: object
) -> None:
    bad = valid_passport()
    target: dict[str, object] = bad
    for part in path[:-1]:
        target = target[part]  # type: ignore[assignment]
    target[path[-1]] = bad_value
    setup_client(monkeypatch, bad)
    with pytest.raises(RuntimeError):
        g8._assert_passport_http_after_restart(EXECUTION_ID, VERIFICATION_DIGEST)


@pytest.mark.parametrize(
    ("execution_id", "digest"),
    [
        ("../etc/passwd", VERIFICATION_DIGEST),
        ("exec/slash", VERIFICATION_DIGEST),
        ("x", VERIFICATION_DIGEST),
        (EXECUTION_ID, "broken-digest"),
        (EXECUTION_ID, "B" * 64),
    ],
)
def test_invalid_passport_assertion_input_fails_before_login(
    monkeypatch: pytest.MonkeyPatch, execution_id: str, digest: str
) -> None:
    def forbidden_login(*_: object) -> str:
        raise AssertionError("login must never be invoked for invalid input")

    monkeypatch.setattr(g8, "_login", forbidden_login)
    with pytest.raises(RuntimeError):
        g8._assert_passport_http_after_restart(execution_id, digest)


@pytest.mark.parametrize("bad_body", [None, [], {}, {"verification": {}}])
def test_missing_passport_sections_fail_closed(
    monkeypatch: pytest.MonkeyPatch, bad_body: object
) -> None:
    setup_client(monkeypatch, bad_body)
    with pytest.raises(RuntimeError):
        g8._assert_passport_http_after_restart(EXECUTION_ID, VERIFICATION_DIGEST)


def test_unauthorized_passport_get_never_returns_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup_client(monkeypatch, valid_passport())

    def denied(*_: object, **__: object) -> object:
        raise RuntimeError("HTTP 401")

    monkeypatch.setattr(g8, "_http_json", denied)
    with pytest.raises(RuntimeError, match="HTTP 401"):
        g8._assert_passport_http_after_restart(EXECUTION_ID, VERIFICATION_DIGEST)
