from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI

from voodoo_product import g8_read_runtime as g8_module
from voodoo_product.composition import install_composed_product_platform
from voodoo_product.config import ProductConfig
from voodoo_product.g8_product_activation import (
    G8_ACTIVATION_ENV,
    resolve_g8_read_runtime_factory,
)
from voodoo_product.github_read_provider import (
    GITHUB_READ_REF_CAPABILITY,
    GITHUB_READ_REF_REQUEST_ADAPTER,
    GitHubReadRefTargetBinder,
)
from voodoo_product.operation_passport import OperationPassportService
from voodoo_product.service import ProductService
from voodoo_product.terminal_profile import READ_ONLY_TERMINAL_PROFILE
from voodoo_product.verification_result import (
    NOT_VERIFIED,
    OBSERVED_STATE_MISMATCH,
    VerificationResult,
)
from voodoo_product.verification_result_persistence import (
    VerificationResultPersistenceConflict,
    VerificationResultPersistenceDenied,
)


def config(tmp_path: Path, *, environment: str = "staging", backend: str = "sqlite") -> ProductConfig:
    return ProductConfig(
        environment=environment,
        database_path=tmp_path / f"{environment}.sqlite3",
        sandbox_root=tmp_path / f"{environment}-sandboxes",
        session_signing_secret="s" * 64,
        bootstrap_token="b" * 48,
        database_backend=backend,
    )


def enable_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    values = {
        G8_ACTIVATION_ENV: "enabled",
        "VOODOO_G8_RUNNER_GITHUB_TOKEN": "runner-g8-product-test-token",
        "VOODOO_G8_VERIFIER_GITHUB_TOKEN": "verifier-g8-product-test-token",
        "VOODOO_G8_RUNNER_PROVIDER_INSTANCE_ID": "gha:g8:runner:test",
        "VOODOO_G8_VERIFIER_PROVIDER_INSTANCE_ID": "gha:g8:verifier:test",
        "VOODOO_G8_RUNNER_ROOTFS_DIGEST": "1" * 64,
        "VOODOO_G8_RUNNER_RESOURCE_LIMIT_PROFILE_DIGEST": "2" * 64,
        "VOODOO_G8_RUNNER_NETWORK_POLICY_DIGEST": "3" * 64,
        "VOODOO_G8_VERIFIER_ROOTFS_DIGEST": "4" * 64,
        "VOODOO_G8_VERIFIER_RESOURCE_LIMIT_PROFILE_DIGEST": "5" * 64,
        "VOODOO_G8_VERIFIER_NETWORK_POLICY_DIGEST": "6" * 64,
        "VOODOO_G8_DEPENDENCY_LOCK_DIGEST": "7" * 64,
        "VOODOO_G8_SBOM_DIGEST": "8" * 64,
        "VOODOO_G8_REVOCATION_EPOCH": "0",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def fake_principal_observation(monkeypatch: pytest.MonkeyPatch) -> None:
    def observe(token: str) -> str:
        if token.startswith("runner-"):
            return "github-principal/user/101"
        if token.startswith("verifier-"):
            return "github-principal/user/202"
        raise AssertionError("unexpected credential")

    monkeypatch.setattr(g8_module, "_observe_github_credential_principal", observe)


def test_g8_is_disabled_by_default_without_reading_credentials(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(G8_ACTIVATION_ENV, raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "ambient-token-must-not-activate")

    assert resolve_g8_read_runtime_factory(config(tmp_path)) is None


def test_g8_rejects_unknown_activation_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(G8_ACTIVATION_ENV, "maybe")

    with pytest.raises(RuntimeError, match="must be disabled or enabled"):
        resolve_g8_read_runtime_factory(config(tmp_path))


def test_g8_rejects_production_before_reading_credentials(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(G8_ACTIVATION_ENV, "enabled")

    with pytest.raises(PermissionError, match="only activate in local/development/staging"):
        resolve_g8_read_runtime_factory(config(tmp_path, environment="production"))


def test_g8_rejects_non_released_database_backend_before_credentials(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(G8_ACTIVATION_ENV, "enabled")

    with pytest.raises(PermissionError, match="released SQLite persistence"):
        resolve_g8_read_runtime_factory(config(tmp_path, backend="postgresql"))


def test_g8_does_not_accept_ambient_github_token_as_runner_credential(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(G8_ACTIVATION_ENV, "enabled")
    monkeypatch.setenv("GITHUB_TOKEN", "ambient-token-must-not-be-used")

    with pytest.raises(RuntimeError, match="VOODOO_G8_RUNNER_GITHUB_TOKEN"):
        resolve_g8_read_runtime_factory(config(tmp_path))


def test_g8_rejects_collapsed_runner_and_verifier_credentials(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(G8_ACTIVATION_ENV, "enabled")
    monkeypatch.setenv("VOODOO_G8_RUNNER_GITHUB_TOKEN", "same-token")
    monkeypatch.setenv("VOODOO_G8_VERIFIER_GITHUB_TOKEN", "same-token")

    with pytest.raises(PermissionError, match="credential material must be distinct"):
        resolve_g8_read_runtime_factory(config(tmp_path))


def test_g8_rejects_collapsed_provider_instances(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(G8_ACTIVATION_ENV, "enabled")
    monkeypatch.setenv("VOODOO_G8_RUNNER_GITHUB_TOKEN", "runner-token")
    monkeypatch.setenv("VOODOO_G8_VERIFIER_GITHUB_TOKEN", "verifier-token")
    monkeypatch.setenv("VOODOO_G8_RUNNER_PROVIDER_INSTANCE_ID", "same-instance")
    monkeypatch.setenv("VOODOO_G8_VERIFIER_PROVIDER_INSTANCE_ID", "same-instance")

    with pytest.raises(PermissionError, match="provider instances must be distinct"):
        resolve_g8_read_runtime_factory(config(tmp_path))


def test_g8_enabled_factory_builds_on_exact_product_db_and_permission_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_settings(monkeypatch)
    fake_principal_observation(monkeypatch)
    subject = config(tmp_path)
    factory = resolve_g8_read_runtime_factory(subject)
    assert factory is not None

    app = FastAPI()
    composition = install_composed_product_platform(
        app,
        config=subject,
        repository_root=tmp_path,
        canonical_runtime_factory=factory,
    )
    runtime = composition.canonical_operation_runtime
    assert runtime is not None
    assert runtime.pipeline.snapshot_creator.db is composition.service.db
    assert runtime.pipeline.snapshot_creator.permission_authority is composition.database_permission_authority
    assert runtime.pipeline.grant_service.db is composition.service.db
    assert runtime.pipeline.outbox_service.db is composition.service.db
    assert runtime.resume_service is not None
    assert runtime.resume_service.db is composition.service.db
    assert runtime.resume_service.permission_authority is composition.database_permission_authority
    definition = runtime.pipeline.snapshot_creator.capability_registry.definition(GITHUB_READ_REF_CAPABILITY)
    assert definition.effect_class == "READ_ONLY"
    assert definition.production_eligible is False
    profile = runtime.pipeline.terminal_profile_registry.resolve(
        capability_definition_identity=definition.definition_identity,
        capability=definition.capability,
    )
    assert profile.terminal_profile == READ_ONLY_TERMINAL_PROFILE
    assert runtime.read_terminal is not None
    assert not hasattr(runtime, "create_ref")
    assert not hasattr(runtime, "delete_ref")
    assert not hasattr(runtime, "rollback")
    assert composition.service.control_room(canonical_runtime_enabled=True)["policy_gates"][-1] == {
        "name": "Canonical read runtime",
        "status": "ENABLED",
        "source": "runtime",
    }


def test_g8_product_assembly_prepares_one_canonical_read_lineage_without_provider_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_settings(monkeypatch)
    fake_principal_observation(monkeypatch)
    subject = config(tmp_path)
    factory = resolve_g8_read_runtime_factory(subject)
    assert factory is not None
    app = FastAPI()
    composition = install_composed_product_platform(
        app,
        config=subject,
        repository_root=tmp_path,
        canonical_runtime_factory=factory,
    )
    service = composition.service
    runtime = composition.canonical_operation_runtime
    assert runtime is not None

    bootstrap = service.bootstrap_admin(
        username="admin",
        password="VeryStrongAdminPassword1!",
        token="b" * 48,
    )
    reviewer = service.create_user(
        actor_id=bootstrap["user_id"],
        username="reviewer",
        password="VeryStrongReviewerPassword1!",
        role="operator",
    )
    request = service.create_change_request(
        actor_id=bootstrap["user_id"],
        workspace_id=bootstrap["workspace_id"],
        title="Canonical GitHub ref read",
        description="prepare only, no provider effect",
        risk="R0",
        environment="staging",
        adapter=GITHUB_READ_REF_REQUEST_ADAPTER,
        payload={"repository": "eimyroot/Voodoo-One", "ref": "refs/heads/main"},
    )
    service.submit_change_request(actor_id=bootstrap["user_id"], request_id=request["id"])
    service.approve_change_request(
        actor_id=reviewer["id"],
        request_id=request["id"],
        decision="APPROVED",
        reason="bounded read-only G8 preparation",
    )

    prepared = runtime.pipeline.prepare(
        actor_id=bootstrap["user_id"],
        request_id=request["id"],
        idempotency_key="g8-product-pre-effect-1",
        correlation_id="corr-g8-product-pre-effect-1",
    )

    assert prepared.request_id == request["id"]
    assert prepared.capability == GITHUB_READ_REF_CAPABILITY
    assert prepared.terminal_profile == READ_ONLY_TERMINAL_PROFILE
    assert prepared.environment == "staging"
    assert prepared.execution_epoch == 1
    assert prepared.authorization_snapshot_digest == prepared.snapshot.snapshot_digest
    assert prepared.grant_digest == prepared.grant.grant_digest
    assert prepared.execution_capsule_digest == prepared.lease.execution_capsule_digest
    assert prepared.outbox.execution_id == prepared.execution_id
    assert prepared.admission.execution_id == prepared.execution_id
    assert prepared.lease.execution_id == prepared.execution_id
    assert service.list_receipts() == []

    store = runtime.verification_result_store
    assert store is not None
    premature = VerificationResult.create(
        execution_id=prepared.execution_id,
        execution_epoch=prepared.execution_epoch,
        target_digest=prepared.target_digest,
        runner_observation_digest="a" * 64,
        verifier_observation_digest="b" * 64,
        observed_post_state_digest="c" * 64,
        verification_boundary_digest="d" * 64,
        verifier_id="e" * 64,
        verifier_identity_digest="f" * 64,
        verification_strength_digest="1" * 64,
        verification_strength_class="INDEPENDENT_PROVIDER_READBACK",
        verdict=NOT_VERIFIED,
        reason=OBSERVED_STATE_MISMATCH,
        checked_at="2026-09-19T18:00:00.000+00:00",
        result_revision="verification-result/g02-binding-test-r1",
    )
    with pytest.raises(
        VerificationResultPersistenceDenied,
        match="VERIFICATION_RESULT_PERSISTENCE_DENIED",
    ):
        store.store(result=premature)


def test_g8_product_read_terminal_runs_through_activation_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_settings(monkeypatch)
    fake_principal_observation(monkeypatch)
    observed_reads: list[tuple[str, str]] = []

    def provider_read(
        *,
        pin: object,
        token: str,
        repository: str,
        ref: str,
    ) -> str:
        del pin, token
        observed_reads.append((repository, ref))
        return "a" * 40

    monkeypatch.setattr(g8_module, "_provider_read_with_pin", provider_read)

    subject = config(tmp_path)
    factory = resolve_g8_read_runtime_factory(subject)
    assert factory is not None
    app = FastAPI()
    composition = install_composed_product_platform(
        app,
        config=subject,
        repository_root=tmp_path,
        canonical_runtime_factory=factory,
    )
    service = composition.service
    runtime = composition.canonical_operation_runtime
    assert runtime is not None

    bootstrap = service.bootstrap_admin(
        username="admin",
        password="VeryStrongAdminPassword1!",
        token="b" * 48,
    )
    reviewer = service.create_user(
        actor_id=bootstrap["user_id"],
        username="reviewer",
        password="VeryStrongReviewerPassword1!",
        role="operator",
    )
    request = service.create_change_request(
        actor_id=bootstrap["user_id"],
        workspace_id=bootstrap["workspace_id"],
        title="Canonical GitHub ref read",
        description="run through G8 READ terminal",
        risk="R0",
        environment="staging",
        adapter=GITHUB_READ_REF_REQUEST_ADAPTER,
        payload={"repository": "eimyroot/Voodoo-One", "ref": "refs/heads/main"},
    )
    service.submit_change_request(actor_id=bootstrap["user_id"], request_id=request["id"])
    service.approve_change_request(
        actor_id=reviewer["id"],
        request_id=request["id"],
        decision="APPROVED",
        reason="bounded read-only G8 terminal regression",
    )

    result = runtime.run_read_only(
        actor_id=bootstrap["user_id"],
        request_id=request["id"],
        idempotency_key="g8-product-read-terminal-1",
        correlation_id="corr-g8-product-read-terminal-1",
    )

    assert result.prepared.capability == GITHUB_READ_REF_CAPABILITY
    assert result.runner_observation.runtime_activation_digest
    assert result.verifier_observation.commit_sha == result.runner_observation.commit_sha
    assert result.verification_result.verdict == "VERIFIED"
    assert result.durable_completion.lease.execution_id == result.prepared.execution_id

    restarted_passport = OperationPassportService(database=service.db).get(
        result.prepared.execution_id
    ).to_dict()
    assert restarted_passport["verification"]["status"] == "PERSISTED"
    assert restarted_passport["verification"]["verdict"] == result.verification_result.verdict
    assert (
        restarted_passport["verification"]["result_digest"]
        == result.verification_result.result_digest
    )
    assert restarted_passport["integrity"]["independent_verification_validated"] is True

    passport_service = OperationPassportService(database=service.db)
    recent = passport_service.list_recent(limit=3)
    assert [item.execution_id for item in recent] == [result.prepared.execution_id]
    recent_verified = passport_service.list_recent_verified(limit=3)
    assert [item.execution_id for item in recent_verified] == [result.prepared.execution_id]
    control_room = service.control_room(canonical_runtime_enabled=True)
    verifier_center = control_room["verifier_center"]
    assert verifier_center["independent_verification_exposed"] is True
    assert verifier_center["canonical_result_count"] == 1
    check = verifier_center["recent_checks"][0]
    assert check["source"] == "VERIFICATION_RESULT_V1"
    assert check["execution_id"] == result.prepared.execution_id
    assert check["verification_status"] == result.verification_result.verdict
    assert check["verification_strength"] == result.verification_result.verification_strength_class
    assert check["result_digest"] == result.verification_result.result_digest
    assert check["checked_at"] == result.verification_result.checked_at

    timeline = control_room["evidence_timeline"]
    canonical_items = [
        item for item in timeline if item["source"] == "OPERATION_PASSPORT"
    ]
    assert {item["kind"] for item in canonical_items} == {
        "CANONICAL_AUTHORIZATION",
        "CANONICAL_GRANT",
        "CANONICAL_GRANT_CONSUMPTION",
        "CANONICAL_DISPATCH",
        "CANONICAL_RUNTIME",
        "CANONICAL_VERIFICATION",
    }
    assert all(
        item["execution_id"] == result.prepared.execution_id
        for item in canonical_items
    )
    verification_item = next(
        item for item in canonical_items if item["kind"] == "CANONICAL_VERIFICATION"
    )
    assert verification_item["status"] == result.verification_result.verdict
    assert verification_item["reference"] == result.verification_result.result_digest
    assert any(item["source"] != "OPERATION_PASSPORT" for item in timeline)

    store = runtime.verification_result_store
    assert store is not None
    assert store.store(result=result.verification_result) == result.verification_result

    conflicting = VerificationResult.create(
        execution_id=result.verification_result.execution_id,
        execution_epoch=result.verification_result.execution_epoch,
        target_digest=result.verification_result.target_digest,
        runner_observation_digest=result.verification_result.runner_observation_digest,
        verifier_observation_digest="0" * 64,
        observed_post_state_digest="1" * 64,
        verification_boundary_digest=result.verification_result.verification_boundary_digest,
        verifier_id=result.verification_result.verifier_id,
        verifier_identity_digest=result.verification_result.verifier_identity_digest,
        verification_strength_digest=result.verification_result.verification_strength_digest,
        verification_strength_class=result.verification_result.verification_strength_class,
        verdict=NOT_VERIFIED,
        reason=OBSERVED_STATE_MISMATCH,
        checked_at=result.verification_result.checked_at,
        result_revision=result.verification_result.result_revision,
    )
    with pytest.raises(
        VerificationResultPersistenceConflict,
        match="VERIFICATION_RESULT_CONFLICT",
    ):
        store.store(result=conflicting)

    assert observed_reads == [
        ("eimyroot/Voodoo-One", "refs/heads/main"),
        ("eimyroot/Voodoo-One", "refs/heads/main"),
    ]


@pytest.mark.parametrize(
    "mismatch",
    ("target_digest", "execution_epoch", "runner_observation_digest"),
)
def test_verification_result_store_rejects_durable_binding_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mismatch: str,
) -> None:
    enable_settings(monkeypatch)
    fake_principal_observation(monkeypatch)

    def provider_read(
        *,
        pin: object,
        token: str,
        repository: str,
        ref: str,
    ) -> str:
        del pin, token, repository, ref
        return "a" * 40

    monkeypatch.setattr(g8_module, "_provider_read_with_pin", provider_read)

    subject = config(tmp_path)
    factory = resolve_g8_read_runtime_factory(subject)
    assert factory is not None
    composition = install_composed_product_platform(
        FastAPI(),
        config=subject,
        repository_root=tmp_path,
        canonical_runtime_factory=factory,
    )
    service = composition.service
    runtime = composition.canonical_operation_runtime
    assert runtime is not None
    assert runtime.read_terminal is not None
    assert runtime.verification_result_store is not None

    bootstrap = service.bootstrap_admin(
        username="admin",
        password="VeryStrongAdminPassword1!",
        token="b" * 48,
    )
    reviewer = service.create_user(
        actor_id=bootstrap["user_id"],
        username="reviewer",
        password="VeryStrongReviewerPassword1!",
        role="operator",
    )
    request = service.create_change_request(
        actor_id=bootstrap["user_id"],
        workspace_id=bootstrap["workspace_id"],
        title="Verification result durable binding",
        description="exercise fail-closed persistence bindings",
        risk="R0",
        environment="staging",
        adapter=GITHUB_READ_REF_REQUEST_ADAPTER,
        payload={"repository": "eimyroot/Voodoo-One", "ref": "refs/heads/main"},
    )
    service.submit_change_request(actor_id=bootstrap["user_id"], request_id=request["id"])
    service.approve_change_request(
        actor_id=reviewer["id"],
        request_id=request["id"],
        decision="APPROVED",
        reason="bounded persistence binding regression",
    )

    prepared = runtime.pipeline.prepare(
        actor_id=bootstrap["user_id"],
        request_id=request["id"],
        idempotency_key=f"g02-binding-{mismatch}",
        correlation_id=f"corr-g02-binding-{mismatch}",
        required_terminal_profile=READ_ONLY_TERMINAL_PROFILE,
        required_capability=GITHUB_READ_REF_CAPABILITY,
    )
    terminal_result = runtime.read_terminal.run(prepared=prepared)
    valid = terminal_result.verification_result

    invalid = VerificationResult.create(
        execution_id=valid.execution_id,
        execution_epoch=(valid.execution_epoch + 1 if mismatch == "execution_epoch" else valid.execution_epoch),
        target_digest=("0" * 64 if mismatch == "target_digest" else valid.target_digest),
        runner_observation_digest=(
            "0" * 64
            if mismatch == "runner_observation_digest"
            else valid.runner_observation_digest
        ),
        verifier_observation_digest=valid.verifier_observation_digest,
        observed_post_state_digest=valid.observed_post_state_digest,
        verification_boundary_digest=valid.verification_boundary_digest,
        verifier_id=valid.verifier_id,
        verifier_identity_digest=valid.verifier_identity_digest,
        verification_strength_digest=valid.verification_strength_digest,
        verification_strength_class=valid.verification_strength_class,
        verdict=valid.verdict,
        reason=valid.reason,
        checked_at=valid.checked_at,
        result_revision=valid.result_revision,
    )

    with pytest.raises(
        VerificationResultPersistenceDenied,
        match="VERIFICATION_RESULT_PERSISTENCE_DENIED",
    ):
        runtime.verification_result_store.store(result=invalid)

    assert runtime.verification_result_store.get(valid.execution_id) is None


def test_github_read_ref_target_binder_is_exact_and_read_only() -> None:
    binder = GitHubReadRefTargetBinder()
    target = binder.bind(
        approved_payload={"repository": "eimyroot/Voodoo-One", "ref": "refs/heads/main"}
    )

    assert target.target_kind == "git_ref"
    assert target.target_claims == {
        "repository": "eimyroot/Voodoo-One",
        "ref": "refs/heads/main",
    }
    with pytest.raises(ValueError, match="fields are invalid"):
        binder.bind(
            approved_payload={
                "repository": "eimyroot/Voodoo-One",
                "ref": "refs/heads/main",
                "token": "must-not-be-accepted",
            }
        )
    with pytest.raises(ValueError, match="fully-qualified heads or tags ref"):
        binder.bind(approved_payload={"repository": "eimyroot/Voodoo-One", "ref": "main"})


def test_reviewed_github_read_request_cannot_enter_legacy_execution_service(tmp_path: Path) -> None:
    service = ProductService(config(tmp_path, environment="local"))
    bootstrap = service.bootstrap_admin(
        username="admin",
        password="VeryStrongAdminPassword1!",
        token="b" * 48,
    )
    reviewer = service.create_user(
        actor_id=bootstrap["user_id"],
        username="reviewer",
        password="VeryStrongReviewerPassword1!",
        role="operator",
    )
    request = service.create_change_request(
        actor_id=bootstrap["user_id"],
        workspace_id=bootstrap["workspace_id"],
        title="Read canonical GitHub ref",
        description="G8 canonical read request",
        risk="R0",
        environment="local",
        adapter=GITHUB_READ_REF_REQUEST_ADAPTER,
        payload={"repository": "eimyroot/Voodoo-One", "ref": "refs/heads/main"},
    )
    service.submit_change_request(actor_id=bootstrap["user_id"], request_id=request["id"])
    service.approve_change_request(
        actor_id=reviewer["id"],
        request_id=request["id"],
        decision="APPROVED",
        reason="read-only canonical runtime test",
    )

    with pytest.raises(PermissionError, match="requires the canonical operation runtime"):
        service.execute_change_request(
            actor_id=bootstrap["user_id"],
            request_id=request["id"],
            idempotency_key="legacy-g8-read-must-deny",
            repository_root=tmp_path,
        )

    assert service.get_change_request(request["id"])["status"] == "APPROVED"
    assert service.list_executions() == []


def test_activation_module_never_reads_generic_github_token() -> None:
    source = Path("voodoo_product/g8_product_activation.py").read_text(encoding="utf-8")
    assert 'os.getenv("GITHUB_TOKEN")' not in source
    assert "github-create-ref" not in source
    assert "github-delete-ref" not in source
