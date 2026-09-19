from __future__ import annotations

import hashlib
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from .approval_policy import CURRENT_APPROVAL_POLICY_VERSION, current_required_approvals
from .authoritative_grant import AuthoritativeGrantIssuer
from .authorization_snapshot_creator import (
    AuthoritativeSnapshotCreator,
    ImmutableCapabilitySelectionAuthority,
)
from .authorization_snapshot_store import AuthorizationSnapshotStore
from .canonical_operation_runtime import CanonicalOperationRuntime
from .canonical_pipeline import CanonicalOperationPipeline
from .canonical_read_terminal import VerifierRuntimeProfile
from .capability_registry import (
    CapabilityActivation,
    CapabilityDefinition,
    ImmutableCapabilityRegistry,
)
from .config import ProductConfig
from .credential_broker import CredentialBrokerPolicy
from .dispatch_inbox_persistence import DurableDispatchInboxService
from .dispatch_outbox_persistence import DurableDispatchOutboxService
from .durable_coordinator import NativeDurableCoordinator
from .durable_current_fence import DurableCurrentExecutionFence
from .evidence_primitives import canonical_json
from .execution_capsule import (
    AuthoritativeExecutionBindingAuthority,
    CapsuleActivation,
    ExecutionCapsule,
    ImmutableExecutionCapsuleRegistry,
)
from .execution_conformance import (
    ExecutionConformanceAuthority,
    HandlerConformanceEvidence,
    ImmutableHandlerConformanceRegistry,
)
from .execution_contract import ExecutionTarget
from .execution_lease_persistence import DurableExecutionLeaseService
from .g8_read_runtime import G8BoundGitHubReadTransport, G8ReadRuntimePack
from .github_actions_runtime import GitHubActionsIsolatedRuntimeProvider
from .github_read_provider import (
    GITHUB_READ_REF_BINDER_ID,
    GITHUB_READ_REF_CAPABILITY,
    GITHUB_READ_REF_REQUEST_ADAPTER,
    GITHUB_REF_TARGET_KIND,
    GitHubReadRefTargetBinder,
)
from .grant_consumption import DurableGrantService
from .permission_authority import DatabasePermissionAuthority
from .policy_authority import ImmutablePolicyAuthority, PolicyRevision
from .precondition_witness import (
    READ_THEN_COMPARE,
    ImmutablePreconditionRequirementRegistry,
    PreconditionExpectationBinderRegistry,
    PreconditionGuard,
    PreconditionObserverRegistry,
    PreconditionRequirement,
)
from .service import ProductService
from .target_binding import TargetBinderRegistry
from .terminal_profile import (
    READ_ONLY_TERMINAL_PROFILE,
    CapabilityTerminalProfileBinding,
    ImmutableCapabilityTerminalProfileRegistry,
)
from .trusted_clock import TrustedClockAuthority
from .verifier_credential import VerifierCredentialPolicy

CanonicalRuntimeFactory = Callable[[ProductService, DatabasePermissionAuthority], CanonicalOperationRuntime]

G8_ACTIVATION_ENV: Final = "VOODOO_G8_READ_RUNTIME"
G8_DISABLED: Final = "disabled"
G8_ENABLED: Final = "enabled"
G8_ALLOWED_ENVIRONMENTS: Final = frozenset({"local", "development", "staging"})
G8_RUNNER_CLASS: Final = "github-actions.docker-isolated/v1"
G8_RUNNER_CREDENTIAL_CLASS: Final = "github.runner-read/scoped-v1"
G8_VERIFIER_CREDENTIAL_CLASS: Final = "github.verifier-read/scoped-v1"
G8_PRECONDITION_STATE_SCHEMA: Final = "vone.github-read-target-binding/v1"
G8_PRECONDITION_BINDER_ID: Final = "github-read-target-expectation/g8-r1"
G8_PRECONDITION_OBSERVER_ID: Final = "github-read-target-observer/g8-r1"


def _digest(value: object) -> str:
    raw = value if isinstance(value, str) else canonical_json(value)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _file_digest(path: Path) -> str:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise RuntimeError("G8 runtime source artifact is unavailable") from exc
    return hashlib.sha256(data).hexdigest()


def _require_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or "\x00" in value:
        raise RuntimeError(f"{field} is invalid")
    return value


def _require_digest(value: object, *, field: str) -> str:
    text = _require_text(value, field=field)
    if len(text) != 64 or text.casefold() != text or any(c not in "0123456789abcdef" for c in text):
        raise RuntimeError(f"{field} must be a lowercase SHA-256 digest")
    return text


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None:
        raise RuntimeError(f"required G8 setting is missing: {name}")
    return _require_text(value.strip(), field=name)


def _required_digest_env(name: str) -> str:
    return _require_digest(_required_env(name), field=name)


def _required_nonnegative_int_env(name: str) -> int:
    raw = _required_env(name)
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a non-negative integer") from exc
    if value < 0 or str(value) != raw:
        raise RuntimeError(f"{name} must be a canonical non-negative integer")
    return value


@dataclass(frozen=True, slots=True, repr=False)
class _G8ActivationSettings:
    environment: str
    runner_token: str
    verifier_token: str
    runner_provider_instance_id: str
    verifier_provider_instance_id: str
    runner_rootfs_digest: str
    runner_resource_digest: str
    runner_network_digest: str
    verifier_rootfs_digest: str
    verifier_resource_digest: str
    verifier_network_digest: str
    dependency_lock_digest: str
    sbom_digest: str
    revocation_epoch: int


class _ConfiguredRevocationEpochAuthority:
    """Startup-configured global epoch; changing it requires a process restart."""

    def __init__(self, epoch: int) -> None:
        if type(epoch) is not int or epoch < 0:
            raise ValueError("revocation epoch must be non-negative")
        self._epoch = epoch

    def current_epoch(
        self,
        connection: object,
        *,
        workspace_id: str,
        environment: str,
        capability_definition_identity: str,
    ) -> int:
        del connection
        _require_text(workspace_id, field="workspace_id")
        if environment not in G8_ALLOWED_ENVIRONMENTS:
            raise PermissionError("G8 revocation authority environment is not allowed")
        _require_digest(
            capability_definition_identity,
            field="capability_definition_identity",
        )
        return self._epoch


class _ReadTargetExpectationBinder:
    binder_id = G8_PRECONDITION_BINDER_ID
    target_kind = GITHUB_REF_TARGET_KIND
    state_schema = G8_PRECONDITION_STATE_SCHEMA

    def bind_expected(self, *, target: ExecutionTarget) -> Mapping[str, Any]:
        return _target_state(target)


class _ReadTargetObserver:
    observer_id = G8_PRECONDITION_OBSERVER_ID
    target_kind = GITHUB_REF_TARGET_KIND
    state_schema = G8_PRECONDITION_STATE_SCHEMA
    source_identity = "v-one.control-plane-authorized-target/g8-r1"

    def observe(self, *, target: ExecutionTarget) -> Mapping[str, Any]:
        return _target_state(target)


def _target_state(target: ExecutionTarget) -> dict[str, str]:
    if not isinstance(target, ExecutionTarget) or target.target_kind != GITHUB_REF_TARGET_KIND:
        raise ValueError("G8 target precondition requires git_ref ExecutionTarget")
    claims = target.target_claims
    if set(claims) != {"repository", "ref"}:
        raise ValueError("G8 target claims are invalid")
    repository = claims["repository"]
    ref = claims["ref"]
    if not isinstance(repository, str) or not isinstance(ref, str):
        raise ValueError("G8 target claims must be strings")
    return {"repository": repository, "ref": ref}


def _load_settings(config: ProductConfig) -> _G8ActivationSettings | None:
    mode = os.getenv(G8_ACTIVATION_ENV, G8_DISABLED).strip().lower()
    if mode == G8_DISABLED:
        return None
    if mode != G8_ENABLED:
        raise RuntimeError(f"{G8_ACTIVATION_ENV} must be disabled or enabled")
    if config.environment not in G8_ALLOWED_ENVIRONMENTS:
        raise PermissionError("G8 READ runtime may only activate in local/development/staging")
    if config.production_effects_enabled:
        raise PermissionError("G8 READ activation requires production effects disabled")
    if config.database_backend != "sqlite":
        raise PermissionError("G8 READ activation currently requires released SQLite persistence")

    runner_token = _required_env("VOODOO_G8_RUNNER_GITHUB_TOKEN")
    verifier_token = _required_env("VOODOO_G8_VERIFIER_GITHUB_TOKEN")
    if hashlib.sha256(runner_token.encode()).digest() == hashlib.sha256(verifier_token.encode()).digest():
        raise PermissionError("G8 Runner and Verifier credential material must be distinct")
    runner_instance = _required_env("VOODOO_G8_RUNNER_PROVIDER_INSTANCE_ID")
    verifier_instance = _required_env("VOODOO_G8_VERIFIER_PROVIDER_INSTANCE_ID")
    if runner_instance == verifier_instance:
        raise PermissionError("G8 Runner and Verifier provider instances must be distinct")

    return _G8ActivationSettings(
        environment=config.environment,
        runner_token=runner_token,
        verifier_token=verifier_token,
        runner_provider_instance_id=runner_instance,
        verifier_provider_instance_id=verifier_instance,
        runner_rootfs_digest=_required_digest_env("VOODOO_G8_RUNNER_ROOTFS_DIGEST"),
        runner_resource_digest=_required_digest_env("VOODOO_G8_RUNNER_RESOURCE_LIMIT_PROFILE_DIGEST"),
        runner_network_digest=_required_digest_env("VOODOO_G8_RUNNER_NETWORK_POLICY_DIGEST"),
        verifier_rootfs_digest=_required_digest_env("VOODOO_G8_VERIFIER_ROOTFS_DIGEST"),
        verifier_resource_digest=_required_digest_env("VOODOO_G8_VERIFIER_RESOURCE_LIMIT_PROFILE_DIGEST"),
        verifier_network_digest=_required_digest_env("VOODOO_G8_VERIFIER_NETWORK_POLICY_DIGEST"),
        dependency_lock_digest=_required_digest_env("VOODOO_G8_DEPENDENCY_LOCK_DIGEST"),
        sbom_digest=_required_digest_env("VOODOO_G8_SBOM_DIGEST"),
        revocation_epoch=_required_nonnegative_int_env("VOODOO_G8_REVOCATION_EPOCH"),
    )


def resolve_g8_read_runtime_factory(config: ProductConfig) -> CanonicalRuntimeFactory | None:
    """Return no runtime by default; build G8 only after explicit bounded configuration."""

    settings = _load_settings(config)
    if settings is None:
        return None

    def factory(
        service: ProductService,
        permission_authority: DatabasePermissionAuthority,
    ) -> CanonicalOperationRuntime:
        return _build_runtime(
            service=service,
            permission_authority=permission_authority,
            settings=settings,
        )

    return factory


def _build_runtime(
    *,
    service: ProductService,
    permission_authority: DatabasePermissionAuthority,
    settings: _G8ActivationSettings,
) -> CanonicalOperationRuntime:
    if service.config.environment != settings.environment:
        raise PermissionError("G8 activation environment changed after startup")
    if service.config.environment not in G8_ALLOWED_ENVIRONMENTS:
        raise PermissionError("G8 runtime environment is not allowed")
    if permission_authority.db is not service.db:
        raise ValueError("G8 activation permission authority must use ProductService database")

    definition = CapabilityDefinition.create(
        capability=GITHUB_READ_REF_CAPABILITY,
        target_kind=GITHUB_REF_TARGET_KIND,
        binder_id=GITHUB_READ_REF_BINDER_ID,
        handler_id="github-ref-read-handler/v1",
        effect_class="READ_ONLY",
        verification_class="INDEPENDENT_READBACK_REQUIRED",
        supported_environments=(settings.environment,),
        required_permissions=("execution.run",),
        production_eligible=False,
    )
    capability_activation = CapabilityActivation.create(
        capability_definition_identity=definition.definition_identity,
        activation_generation=1,
        enabled_environments=(settings.environment,),
    )
    capability_registry = ImmutableCapabilityRegistry(
        definitions=(definition,),
        activations=(capability_activation,),
    )

    handler_digest = _file_digest(Path(__file__).with_name("github_read_provider.py"))
    module_manifest_digest = _digest(
        {
            "module": "voodoo_product.github_read_provider",
            "handler": "GitHubRefReadHandler",
            "module_source_digest": handler_digest,
        }
    )
    verification_contract_identity = _digest("verification-result/v1:github.read-ref/v1")
    capsule = ExecutionCapsule.create(
        capability_definition_identity=definition.definition_identity,
        target_kind=definition.target_kind,
        handler_id=definition.handler_id,
        handler_digest=handler_digest,
        module_manifest_digest=module_manifest_digest,
        artifact_kind="python-module",
        artifact_digest=handler_digest,
        rootfs_digest=settings.runner_rootfs_digest,
        dependency_lock_digest=settings.dependency_lock_digest,
        sbom_digest=settings.sbom_digest,
        network_policy_digest=settings.runner_network_digest,
        resource_limit_profile_digest=settings.runner_resource_digest,
        credential_class=G8_RUNNER_CREDENTIAL_CLASS,
        runner_class=G8_RUNNER_CLASS,
        precondition_enforcement_class=READ_THEN_COMPARE,
        verification_class=definition.verification_class,
        verification_contract_identity=verification_contract_identity,
        capsule_revision="execution-capsule/g8-product-r1",
    )
    capsule_activation = CapsuleActivation.create(
        execution_capsule_digest=capsule.capsule_digest,
        activation_generation=1,
        enabled_environments=(settings.environment,),
        production_eligible=False,
    )
    capsule_registry = ImmutableExecutionCapsuleRegistry(
        capability_registry=capability_registry,
        capsules=(capsule,),
        activations=(capsule_activation,),
    )
    handler_evidence = HandlerConformanceEvidence.create(
        capability_definition_identity=definition.definition_identity,
        execution_capsule_digest=capsule.capsule_digest,
        handler_id=capsule.handler_id,
        handler_digest=capsule.handler_digest,
        runner_class=capsule.runner_class,
        credential_class=capsule.credential_class,
        precondition_enforcement_class=capsule.precondition_enforcement_class,
        verification_contract_identity=capsule.verification_contract_identity,
        atomic_provider_condition_contract_identity=None,
        evidence_revision="handler-conformance/g8-product-r1",
    )
    handler_registry = ImmutableHandlerConformanceRegistry(
        capsule_registry=capsule_registry,
        evidence=(handler_evidence,),
    )
    conformance_authority = ExecutionConformanceAuthority(
        capsule_registry=capsule_registry,
        handler_registry=handler_registry,
        authority_revision="execution-conformance/g8-product-r1",
    )
    binding_authority = AuthoritativeExecutionBindingAuthority(
        registry=capsule_registry,
        authority_revision="execution-binding/g8-product-r1",
    )

    clock = TrustedClockAuthority(
        source_identity="system-utc/g8-product-r1",
        authority_revision="trusted-clock/g8-product-r1",
        allowed_environments=frozenset({settings.environment}),
    )
    revocation = _ConfiguredRevocationEpochAuthority(settings.revocation_epoch)
    policy = PolicyRevision.create(
        policy_version=CURRENT_APPROVAL_POLICY_VERSION,
        policy_package="v-one.approval.current-compatibility",
        approval_validity_seconds=600,
        required_approvals_by_environment={
            environment: current_required_approvals(environment)
            for environment in ("local", "development", "staging", "production")
        },
    )
    snapshot_store = AuthorizationSnapshotStore(
        database=service.db,
        audit_ledger=service.audit_ledger,
    )
    snapshot_creator = AuthoritativeSnapshotCreator(
        database=service.db,
        audit_ledger=service.audit_ledger,
        snapshot_store=snapshot_store,
        permission_authority=permission_authority,
        policy_authority=ImmutablePolicyAuthority((policy,)),
        policy_version=policy.policy_version,
        capability_registry=capability_registry,
        capability_selection_authority=ImmutableCapabilitySelectionAuthority(
            bindings={GITHUB_READ_REF_REQUEST_ADAPTER: definition.capability},
            authority_revision="capability-selection/g8-product-r1",
        ),
        target_binders=TargetBinderRegistry(
            {GITHUB_READ_REF_BINDER_ID: GitHubReadRefTargetBinder()}
        ),
        trusted_clock=clock,
        revocation_authority=revocation,
        operational_safety_service=service.operational_safety_service,
        production_effects_enabled=False,
        authorization_source_revision="snapshot-creator/g8-product-r1",
    )

    requirement = PreconditionRequirement.create(
        capability_definition_identity=definition.definition_identity,
        target_kind=definition.target_kind,
        expectation_binder_id=G8_PRECONDITION_BINDER_ID,
        observer_id=G8_PRECONDITION_OBSERVER_ID,
        state_schema=G8_PRECONDITION_STATE_SCHEMA,
        requirement_revision="precondition/g8-read-target-binding-r1",
        enforcement_class=READ_THEN_COMPARE,
    )
    precondition_guard = PreconditionGuard(
        requirements=ImmutablePreconditionRequirementRegistry((requirement,)),
        expectation_binders=PreconditionExpectationBinderRegistry(
            {G8_PRECONDITION_BINDER_ID: _ReadTargetExpectationBinder()}
        ),
        observers=PreconditionObserverRegistry(
            {G8_PRECONDITION_OBSERVER_ID: _ReadTargetObserver()}
        ),
        trusted_clock=clock,
    )
    grant_issuer = AuthoritativeGrantIssuer(
        database=service.db,
        operational_safety_service=service.operational_safety_service,
        revocation_authority=revocation,
        precondition_guard=precondition_guard,
        execution_binding_authority=binding_authority,
        trusted_clock=clock,
        issuer_identity="v-one.authoritative-grant-issuer/g8-product",
        issuer_revision="authoritative-grant-issuer/g8-product-r1",
        grant_ttl_seconds=120,
    )
    grant_service = DurableGrantService(
        database=service.db,
        grant_issuer=grant_issuer,
        operational_safety_service=service.operational_safety_service,
        revocation_authority=revocation,
        conformance_authority=conformance_authority,
        trusted_clock=clock,
        authority_revision="durable-grant/g8-product-r1",
    )
    outbox_service = DurableDispatchOutboxService(
        grant_service=grant_service,
        outbox_revision="dispatch-outbox/g8-product-r1",
    )
    inbox_service = DurableDispatchInboxService(
        database=service.db,
        admission_revision="dispatch-inbox/g8-product-r1",
    )
    lease_service = DurableExecutionLeaseService(
        database=service.db,
        trusted_clock=clock,
        lease_seconds=service.config.execution_lease_seconds,
        lease_revision="execution-lease/g8-product-r1",
        authority_revision="execution-epoch-authority/g8-product-r1",
    )
    coordinator = NativeDurableCoordinator(
        inbox_service=inbox_service,
        lease_service=lease_service,
    )
    terminal_profile_registry = ImmutableCapabilityTerminalProfileRegistry(
        (
            CapabilityTerminalProfileBinding.create(
                definition=definition,
                terminal_profile=READ_ONLY_TERMINAL_PROFILE,
                binding_revision="terminal-profile/g8-product-r1",
            ),
        )
    )
    pipeline = CanonicalOperationPipeline(
        snapshot_creator=snapshot_creator,
        grant_service=grant_service,
        outbox_service=outbox_service,
        coordinator=coordinator,
        terminal_profile_registry=terminal_profile_registry,
        envelope_revision="dispatch-envelope/g8-product-r1",
    )
    current_fence = DurableCurrentExecutionFence(database=service.db, trusted_clock=clock)

    runner_provider = GitHubActionsIsolatedRuntimeProvider(
        provider_instance_id=settings.runner_provider_instance_id,
        runner_class=G8_RUNNER_CLASS,
        environment=settings.environment,
        rootfs_digest=settings.runner_rootfs_digest,
        resource_limit_profile_digest=settings.runner_resource_digest,
        network_policy_digest=settings.runner_network_digest,
        bootstrap_revision="isolated-runtime-bootstrap/g8-product-r1",
        activation_revision="runner-activation/g8-product-r1",
    )
    runner_policy = CredentialBrokerPolicy.create(
        credential_class=G8_RUNNER_CREDENTIAL_CLASS,
        provider="github",
        audience="api.github.com",
        allowed_capability_definition_identities=(definition.definition_identity,),
        enabled_environments=(settings.environment,),
        policy_revision="credential-broker-policy/g8-product-r1",
    )
    verifier_profile = VerifierRuntimeProfile(
        verifier_class="github-actions.verifier/v1",
        provider="github",
        provider_instance_id=settings.verifier_provider_instance_id,
        credential_class=G8_VERIFIER_CREDENTIAL_CLASS,
        rootfs_digest=settings.verifier_rootfs_digest,
        resource_limit_profile_digest=settings.verifier_resource_digest,
        network_policy_digest=settings.verifier_network_digest,
        identity_revision="verifier-identity/g8-product-r1",
        boundary_revision="verification-boundary/g8-product-r1",
        decision_revision="verifier-credential/g8-product-r1",
        credential_ttl_seconds=60,
    )
    verifier_policy = VerifierCredentialPolicy.create(
        credential_class=G8_VERIFIER_CREDENTIAL_CLASS,
        provider="github",
        audience="api.github.com",
        enabled_environments=(settings.environment,),
        max_ttl_seconds=60,
        policy_revision="verifier-policy/g8-product-r1",
    )
    pack = G8ReadRuntimePack(
        pipeline=pipeline,
        capsule_registry=capsule_registry,
        current_fence=current_fence,
        runner_provider=runner_provider,
        runner_transport=G8BoundGitHubReadTransport(
            token=settings.runner_token,
            credential_class=G8_RUNNER_CREDENTIAL_CLASS,
        ),
        runner_clock=clock,
        runner_credential_policy=runner_policy,
        runner_credential_decision_revision="credential-decision/g8-product-r1",
        runner_identity_revision="runner-identity/g8-product-r1",
        runner_boundary_revision="runner-boundary/g8-product-r1",
        runner_activation_revision="runner-activation/g8-product-r1",
        runner_observation_revision="runner-observation/g8-product-r1",
        verifier_profile=verifier_profile,
        verifier_policy=verifier_policy,
        verifier_transport=G8BoundGitHubReadTransport(
            token=settings.verifier_token,
            credential_class=G8_VERIFIER_CREDENTIAL_CLASS,
        ),
        verifier_clock=TrustedClockAuthority(
            source_identity="system-utc/g8-verifier-product-r1",
            authority_revision="trusted-clock/g8-verifier-product-r1",
            allowed_environments=frozenset({settings.environment}),
        ),
        verifier_observation_revision="verifier-observation/g8-product-r1",
        observed_post_state_revision="observed-post-state/g8-product-r1",
        strength_revision="verification-strength/g8-product-r1",
        result_revision="verification-result/g8-product-r1",
        read_capability_definition_identity=definition.definition_identity,
    )
    return pack.build_runtime(
        service=service,
        permission_authority=permission_authority,
    )
