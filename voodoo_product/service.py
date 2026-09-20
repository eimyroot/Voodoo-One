from __future__ import annotations

import secrets
import time
from pathlib import Path
from typing import Any

from .adapters import execute_adapter
from .audit import AuditLedger
from .auth_rate_limit import AuthenticationRateLimitService, AuthRateLimitExceeded
from .bootstrap import BootstrapService
from .change_request import ChangeRequestService
from .config import ProductConfig
from .credential_authentication import CredentialAuthenticationService
from .db import create_product_database
from .evidence_primitives import canonical_json, chained_hash, new_id, utc_now
from .execution import ExecutionService, timestamp_after, timestamp_expired
from .operation_passport import OperationPassport, OperationPassportService
from .operational_safety import OperationalSafetyService
from .persistence import DatabaseConnection, DatabaseRow, ProductDatabaseAdapter
from .platform_status import PlatformStatusService
from .receipt import ReceiptLedger
from .security import hash_password, session_reference, verify_password
from .session_lifecycle import SessionLifecycleService
from .user_account import UserAccountService
from .workspace import WorkspaceService

__all__ = [
    "AuthRateLimitExceeded",
    "ProductService",
    "canonical_json",
    "chained_hash",
    "new_id",
    "utc_now",
]

VALID_ROLES = {
    "viewer",
    "developer",
    "operator",
    "security_reviewer",
    "auditor",
    "administrator",
}
VALID_RISKS = {"R0", "R1", "R2", "R3", "R4"}
VALID_ENVIRONMENTS = {"local", "development", "staging", "production"}
VALID_ADAPTERS = {"echo", "write_artifact", "run_validation"}
MAX_CHANGE_PAYLOAD_BYTES = 65_536
CONTROL_ROOM_LIMIT = 12


def row_dict(row: DatabaseRow | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


class ProductService:
    def __init__(
        self,
        config: ProductConfig,
        *,
        database: ProductDatabaseAdapter | None = None,
        authentication_rate_limit_service: AuthenticationRateLimitService | None = None,
        credential_authentication_service: CredentialAuthenticationService | None = None,
        bootstrap_service: BootstrapService | None = None,
        audit_ledger: AuditLedger | None = None,
        user_account_service: UserAccountService | None = None,
        session_lifecycle_service: SessionLifecycleService | None = None,
        workspace_service: WorkspaceService | None = None,
        change_request_service: ChangeRequestService | None = None,
        receipt_ledger: ReceiptLedger | None = None,
        operational_safety_service: OperationalSafetyService | None = None,
        execution_service: ExecutionService | None = None,
        platform_status_service: PlatformStatusService | None = None,
    ) -> None:
        self.config = config
        self.db = (
            database
            if database is not None
            else create_product_database(
                backend=self.config.database_backend,
                path=self.config.database_path,
            )
        )
        self.db.initialize()
        resolved_authentication_rate_limit_service = (
            authentication_rate_limit_service
            or AuthenticationRateLimitService(
                database=self.db,
                config=self.config,
                clock=lambda: time.time(),
            )
        )
        if resolved_authentication_rate_limit_service.db is not self.db:
            raise ValueError(
                "authentication rate-limit service must use the product service database"
            )
        if resolved_authentication_rate_limit_service.config is not self.config:
            raise ValueError(
                "authentication rate-limit service must use the product service configuration"
            )
        self.authentication_rate_limit_service = resolved_authentication_rate_limit_service
        resolved_credential_authentication_service = (
            credential_authentication_service
            or CredentialAuthenticationService(
                database=self.db,
                password_hasher=lambda password: hash_password(password),
                password_verifier=lambda password, encoded: verify_password(
                    password,
                    encoded,
                ),
            )
        )
        if resolved_credential_authentication_service.db is not self.db:
            raise ValueError(
                "credential authentication service must use the product service database"
            )
        self.credential_authentication_service = resolved_credential_authentication_service
        resolved_audit_ledger = audit_ledger or AuditLedger(self.db)
        if resolved_audit_ledger.db is not self.db:
            raise ValueError("audit ledger must use the product service database")
        self.audit_ledger = resolved_audit_ledger
        resolved_bootstrap_service = bootstrap_service or BootstrapService(
            database=self.db,
            config=self.config,
            audit_ledger=self.audit_ledger,
            id_factory=lambda prefix: new_id(prefix),
            clock=lambda: utc_now(),
            password_hasher=lambda password: hash_password(password),
            token_comparator=lambda supplied, expected: secrets.compare_digest(
                supplied,
                expected,
            ),
        )
        if resolved_bootstrap_service.db is not self.db:
            raise ValueError("bootstrap service must use the product service database")
        if resolved_bootstrap_service.config is not self.config:
            raise ValueError("bootstrap service must use the product service configuration")
        if resolved_bootstrap_service.audit_ledger is not self.audit_ledger:
            raise ValueError("bootstrap service must use the product service audit ledger")
        self.bootstrap_service = resolved_bootstrap_service
        resolved_user_account_service = user_account_service or UserAccountService(
            database=self.db,
            audit_ledger=self.audit_ledger,
            id_factory=lambda prefix: new_id(prefix),
            clock=lambda: utc_now(),
            password_hasher=lambda password: hash_password(password),
        )
        if resolved_user_account_service.db is not self.db:
            raise ValueError(
                "user account service must use the product service database"
            )
        if resolved_user_account_service.audit_ledger is not self.audit_ledger:
            raise ValueError(
                "user account service must use the product service audit ledger"
            )
        self.user_account_service = resolved_user_account_service
        resolved_session_lifecycle_service = (
            session_lifecycle_service
            or SessionLifecycleService(
                database=self.db,
                audit_ledger=self.audit_ledger,
                session_reference_factory=lambda session_id: session_reference(
                    secret=self.config.session_signing_secret,
                    session_id=session_id,
                ),
                clock=lambda: time.time(),
            )
        )
        if resolved_session_lifecycle_service.db is not self.db:
            raise ValueError(
                "session lifecycle service must use the product service database"
            )
        if resolved_session_lifecycle_service.audit_ledger is not self.audit_ledger:
            raise ValueError(
                "session lifecycle service must use the product service audit ledger"
            )
        self.session_lifecycle_service = resolved_session_lifecycle_service
        resolved_workspace_service = workspace_service or WorkspaceService(
            database=self.db,
            audit_ledger=self.audit_ledger,
            id_factory=lambda prefix: new_id(prefix),
            clock=lambda: utc_now(),
        )
        if resolved_workspace_service.db is not self.db:
            raise ValueError(
                "workspace service must use the product service database"
            )
        if resolved_workspace_service.audit_ledger is not self.audit_ledger:
            raise ValueError(
                "workspace service must use the product service audit ledger"
            )
        self.workspace_service = resolved_workspace_service
        resolved_change_request_service = (
            change_request_service
            or ChangeRequestService(
                database=self.db,
                audit_ledger=self.audit_ledger,
                id_factory=lambda prefix: new_id(prefix),
                clock=lambda: utc_now(),
                approval_policy_compatibility_enabled=(
                    self.config.approval_policy_compatibility_enabled
                ),
            )
        )
        if resolved_change_request_service.db is not self.db:
            raise ValueError(
                "change request service must use the product service database"
            )
        if resolved_change_request_service.audit_ledger is not self.audit_ledger:
            raise ValueError(
                "change request service must use the product service audit ledger"
            )
        if (
            resolved_change_request_service.approval_policy_compatibility_enabled
            is not self.config.approval_policy_compatibility_enabled
        ):
            raise ValueError(
                "change request service must use the product approval-policy configuration"
            )
        self.change_request_service = resolved_change_request_service
        resolved_operational_safety_service = (
            operational_safety_service
            or OperationalSafetyService(
                database=self.db,
                audit_ledger=self.audit_ledger,
                clock=lambda: utc_now(),
            )
        )
        if resolved_operational_safety_service.db is not self.db:
            raise ValueError(
                "operational safety service must use the product service database"
            )
        if resolved_operational_safety_service.audit_ledger is not self.audit_ledger:
            raise ValueError(
                "operational safety service must use the product service audit ledger"
            )
        self.operational_safety_service = resolved_operational_safety_service
        resolved_receipt_ledger = receipt_ledger or ReceiptLedger(self.db)
        if resolved_receipt_ledger.db is not self.db:
            raise ValueError("receipt ledger must use the product service database")
        self.receipt_ledger = resolved_receipt_ledger
        resolved_execution_service = execution_service or ExecutionService(
            database=self.db,
            config=self.config,
            audit_ledger=self.audit_ledger,
            receipt_ledger=self.receipt_ledger,
            operational_safety_service=self.operational_safety_service,
            adapter_executor=lambda adapter, payload, *, context: execute_adapter(
                adapter,
                payload,
                context=context,
            ),
            id_factory=lambda prefix: new_id(prefix),
            clock=lambda: utc_now(),
            lease_deadline=lambda value, seconds: timestamp_after(value, seconds),
            lease_expired=lambda value, *, now: timestamp_expired(value, now=now),
        )
        if resolved_execution_service.db is not self.db:
            raise ValueError("execution service must use the product service database")
        if resolved_execution_service.config is not self.config:
            raise ValueError("execution service must use the product service configuration")
        if resolved_execution_service.audit_ledger is not self.audit_ledger:
            raise ValueError("execution service must use the product service audit ledger")
        if resolved_execution_service.receipt_ledger is not self.receipt_ledger:
            raise ValueError("execution service must use the product service receipt ledger")
        if (
            resolved_execution_service.operational_safety_service
            is not self.operational_safety_service
        ):
            raise ValueError(
                "execution service must use the product operational safety service"
            )
        self.execution_service = resolved_execution_service
        resolved_platform_status_service = platform_status_service or PlatformStatusService(
            database=self.db,
            config=self.config,
            audit_ledger=self.audit_ledger,
            receipt_ledger=self.receipt_ledger,
            operational_safety_service=self.operational_safety_service,
        )
        if resolved_platform_status_service.db is not self.db:
            raise ValueError("platform status service must use the product service database")
        if resolved_platform_status_service.config is not self.config:
            raise ValueError("platform status service must use the product service configuration")
        if resolved_platform_status_service.audit_ledger is not self.audit_ledger:
            raise ValueError("platform status service must use the product service audit ledger")
        if resolved_platform_status_service.receipt_ledger is not self.receipt_ledger:
            raise ValueError("platform status service must use the product service receipt ledger")
        if (
            resolved_platform_status_service.operational_safety_service
            is not self.operational_safety_service
        ):
            raise ValueError(
                "platform status service must use the product operational safety service"
            )
        self.platform_status_service = resolved_platform_status_service
        self.config.sandbox_root.mkdir(parents=True, exist_ok=True)

    def has_users(self) -> bool:
        return self.bootstrap_service.has_users()

    def bootstrap_admin(self, *, username: str, password: str, token: str) -> dict[str, Any]:
        return self.bootstrap_service.bootstrap_admin(
            username=username,
            password=password,
            token=token,
        )

    def enforce_login_rate_limit(self, *, username: str, source: str) -> None:
        self.authentication_rate_limit_service.enforce_login_rate_limit(
            username=username,
            source=source,
        )

    def record_login_failure(self, *, username: str, source: str) -> None:
        self.authentication_rate_limit_service.record_login_failure(
            username=username,
            source=source,
        )

    def clear_login_rate_limit(self, *, username: str, source: str) -> None:
        self.authentication_rate_limit_service.clear_login_rate_limit(
            username=username,
            source=source,
        )

    def enforce_bootstrap_rate_limit(self, *, source: str) -> None:
        self.authentication_rate_limit_service.enforce_bootstrap_rate_limit(source=source)

    def record_bootstrap_failure(self, *, source: str) -> None:
        self.authentication_rate_limit_service.record_bootstrap_failure(source=source)

    def clear_bootstrap_rate_limit(self, *, source: str) -> None:
        self.authentication_rate_limit_service.clear_bootstrap_rate_limit(source=source)

    def authenticate(self, *, username: str, password: str) -> dict[str, Any]:
        return self.credential_authentication_service.authenticate(
            username=username,
            password=password,
        )

    def get_active_user(self, user_id: str) -> dict[str, Any]:
        return self.user_account_service.get_active_user(user_id)

    def register_session(
        self,
        *,
        session_id: str,
        user_id: str,
        issued_at: int,
        expires_at: int,
    ) -> None:
        self.session_lifecycle_service.register_session(
            session_id=session_id,
            user_id=user_id,
            issued_at=issued_at,
            expires_at=expires_at,
        )

    def require_active_session(
        self,
        *,
        session_id: str,
        user_id: str,
        issued_at: int,
        expires_at: int,
    ) -> None:
        self.session_lifecycle_service.require_active_session(
            session_id=session_id,
            user_id=user_id,
            issued_at=issued_at,
            expires_at=expires_at,
        )

    def revoke_session(
        self,
        *,
        session_id: str,
        user_id: str,
        actor_id: str,
        reason: str,
    ) -> None:
        self.session_lifecycle_service.revoke_session(
            session_id=session_id,
            user_id=user_id,
            actor_id=actor_id,
            reason=reason,
        )

    def revoke_all_sessions(
        self, *, user_id: str, actor_id: str, reason: str
    ) -> dict[str, object]:
        revoked_count = self.session_lifecycle_service.revoke_all_sessions(
            user_id=user_id,
            actor_id=actor_id,
            reason=reason,
        )
        return {"user_id": user_id, "revoked_count": revoked_count}

    def create_user(
        self, *, actor_id: str, username: str, password: str, role: str
    ) -> dict[str, Any]:
        return self.user_account_service.create_user(
            actor_id=actor_id,
            username=username,
            password=password,
            role=role,
        )

    def list_workspaces(self) -> list[dict[str, Any]]:
        return self.workspace_service.list_workspaces()

    def create_workspace(self, *, actor_id: str, name: str, environment: str) -> dict[str, Any]:
        return self.workspace_service.create_workspace(
            actor_id=actor_id,
            name=name,
            environment=environment,
        )

    def create_change_request(
        self,
        *,
        actor_id: str,
        workspace_id: str,
        title: str,
        description: str,
        risk: str,
        environment: str,
        adapter: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self.change_request_service.create_change_request(
            actor_id=actor_id,
            workspace_id=workspace_id,
            title=title,
            description=description,
            risk=risk,
            environment=environment,
            adapter=adapter,
            payload=payload,
        )

    def list_change_requests(self, *, limit: int = 100) -> list[dict[str, Any]]:
        return self.change_request_service.list_change_requests(limit=limit)

    def get_change_request(self, request_id: str) -> dict[str, Any]:
        return self.change_request_service.get_change_request(request_id)

    def submit_change_request(self, *, actor_id: str, request_id: str) -> dict[str, Any]:
        return self.change_request_service.submit_change_request(
            actor_id=actor_id,
            request_id=request_id,
        )

    def approve_change_request(
        self,
        *,
        actor_id: str,
        request_id: str,
        decision: str,
        reason: str,
    ) -> dict[str, Any]:
        return self.change_request_service.approve_change_request(
            actor_id=actor_id,
            request_id=request_id,
            decision=decision,
            reason=reason,
        )

    def list_approvals(self, *, pending_only: bool = False) -> list[dict[str, Any]]:
        return self.change_request_service.list_approvals(pending_only=pending_only)

    def execute_change_request(
        self,
        *,
        actor_id: str,
        request_id: str,
        idempotency_key: str | None,
        repository_root: Path,
    ) -> dict[str, Any]:
        return self.execution_service.execute_change_request(
            actor_id=actor_id,
            request_id=request_id,
            idempotency_key=idempotency_key,
            repository_root=repository_root,
        )

    def recover_execution(
        self,
        *,
        actor_id: str,
        execution_id: str,
        reason: str,
    ) -> dict[str, Any]:
        return self.execution_service.recover_execution(
            actor_id=actor_id,
            execution_id=execution_id,
            reason=reason,
        )

    def list_executions(self, *, limit: int = 100) -> list[dict[str, Any]]:
        return self.execution_service.list_executions(limit=limit)

    def get_execution(self, execution_id: str) -> dict[str, Any]:
        return self.execution_service.get_execution(execution_id)

    def list_receipts(self, *, limit: int = 100) -> list[dict[str, Any]]:
        return self.receipt_ledger.list_receipts(limit=limit)

    def verify_receipt_chain(self) -> dict[str, Any]:
        return self.receipt_ledger.verify()

    def list_audit_events(self, *, limit: int = 200) -> list[dict[str, Any]]:
        return self.audit_ledger.list_events(limit=limit)

    def verify_audit_chain(self) -> dict[str, Any]:
        return self.audit_ledger.verify()

    def command_center(self) -> dict[str, Any]:
        return self.platform_status_service.command_center()

    def control_room(self, *, canonical_runtime_enabled: bool = False) -> dict[str, Any]:
        overview = self.command_center()
        change_requests = self.list_change_requests(limit=CONTROL_ROOM_LIMIT)
        approvals = self.list_approvals(pending_only=True)
        executions = self.list_executions(limit=CONTROL_ROOM_LIMIT)
        receipts = self.list_receipts(limit=CONTROL_ROOM_LIMIT)
        audits = self.list_audit_events(limit=CONTROL_ROOM_LIMIT)
        passport_service = OperationPassportService(database=self.db)
        canonical_passports = passport_service.list_recent(limit=CONTROL_ROOM_LIMIT)
        verification_passports = passport_service.list_recent_verified(
            limit=CONTROL_ROOM_LIMIT
        )
        return {
            "overview": overview,
            "runs": self._summarize_runs(change_requests, executions),
            "plans": self._summarize_plans(change_requests, approvals),
            "architecture": self._architecture_projection(canonical_runtime_enabled),
            "capability_registry": self._capability_registry(canonical_runtime_enabled),
            "evidence_timeline": self._evidence_timeline(
                change_requests=change_requests,
                executions=executions,
                receipts=receipts,
                audits=audits,
                canonical_passports=canonical_passports,
            ),
            "policy_gates": self._policy_gates(
                overview=overview,
                canonical_runtime_enabled=canonical_runtime_enabled,
            ),
            "verifier_center": self._verifier_center(
                receipts=receipts,
                executions=executions,
                verification_passports=verification_passports,
            ),
            "runtime_health": self._runtime_health(
                health=self.health(),
                canonical_runtime_enabled=canonical_runtime_enabled,
            ),
            "learning_intelligence": self._learning_intelligence(
                change_requests=change_requests,
                executions=executions,
            ),
            "governance": self._governance_projection(overview=overview),
        }

    def set_emergency_stop(self, *, actor_id: str, active: bool, reason: str) -> dict[str, Any]:
        return self.operational_safety_service.set_emergency_stop(
            actor_id=actor_id,
            active=active,
            reason=reason,
        )

    def health(self) -> dict[str, Any]:
        return self.platform_status_service.health()

    def _summarize_runs(
        self,
        change_requests: list[dict[str, Any]],
        executions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        recent = [
            {
                "id": item["id"],
                "title": item["title"],
                "status": item["status"],
                "risk": item["risk"],
                "environment": item["environment"],
                "adapter": item["adapter"],
                "updated_at": item["updated_at"],
                "receipt_id": item.get("receipt_id"),
            }
            for item in executions[:CONTROL_ROOM_LIMIT]
        ]
        draft_or_review = sum(
            1 for item in change_requests if item["status"] in {"DRAFT", "REVIEW_REQUIRED"}
        )
        return {
            "recent": recent,
            "queue_depth": draft_or_review,
            "active_count": sum(1 for item in executions if item["status"] == "RUNNING"),
            "completed_count": sum(1 for item in executions if item["status"] == "SUCCEEDED"),
            "failed_count": sum(1 for item in executions if item["status"] == "FAILED"),
        }

    def _summarize_plans(
        self,
        change_requests: list[dict[str, Any]],
        approvals: list[dict[str, Any]],
    ) -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        for request in change_requests[:CONTROL_ROOM_LIMIT]:
            approval = next(
                (item for item in approvals if item["request_id"] == request["id"]),
                None,
            )
            items.append(
                {
                    "request_id": request["id"],
                    "title": request["title"],
                    "status": request["status"],
                    "risk": request["risk"],
                    "environment": request["environment"],
                    "requested_by": request["requested_by_username"],
                    "approval_count": request.get("approval_count", 0),
                    "approval_required": approval.get("required_count", 1) if approval else 1,
                    "updated_at": request["updated_at"],
                }
            )
        return {"items": items, "pending_approvals": len(approvals)}

    @staticmethod
    def _architecture_projection(canonical_runtime_enabled: bool) -> dict[str, Any]:
        canonical_status = "ENABLED" if canonical_runtime_enabled else "DISABLED"
        return {
            "projection": "AS_IS_RUNTIME",
            "source": "product_service.control_room",
            "flows": [
                {
                    "id": "legacy_governed_execution",
                    "label": "Governed adapter execution",
                    "status": "ACTIVE",
                    "nodes": [
                        {"id": "change_request", "label": "Change Request", "status": "ACTIVE", "source": "change_request_service"},
                        {"id": "approval", "label": "Approval", "status": "ACTIVE", "source": "change_request_service"},
                        {"id": "execution_service", "label": "Execution Service", "status": "ACTIVE", "source": "execution_service"},
                        {"id": "receipt_audit", "label": "Receipt + Audit", "status": "ACTIVE", "source": "receipt_ledger + audit_ledger"},
                    ],
                },
                {
                    "id": "canonical_read",
                    "label": "Canonical READ",
                    "status": canonical_status,
                    "nodes": [
                        {"id": "canonical_api", "label": "Canonical READ API", "status": "EXPOSED", "source": "canonical_operation_http"},
                        {"id": "authority_pipeline", "label": "Authority + Dispatch", "status": canonical_status, "source": "canonical_operation_runtime"},
                        {"id": "read_runner", "label": "READ Runner", "status": canonical_status, "source": "canonical_read_terminal"},
                        {"id": "independent_verifier", "label": "Independent Verifier", "status": canonical_status, "source": "canonical_read_terminal"},
                        {"id": "operation_passport", "label": "Operation Passport", "status": "EXPOSED", "source": "operation_passport_service", "note": "schema-v15 durable VerificationResult/v1 is exposed when present; absence remains UNKNOWN / NOT_PERSISTED"},
                    ],
                },
            ],
        }

    def _capability_registry(self, canonical_runtime_enabled: bool) -> dict[str, Any]:
        adapters = [
            {
                "id": "echo",
                "surface": "adapter",
                "effect": "INERT",
                "verification": "NOT_REQUIRED",
                "environments": ["local", "development", "staging", "production"],
                "runtime_status": "ACTIVE",
                "source": "runtime_allowlist",
            },
            {
                "id": "write_artifact",
                "surface": "adapter",
                "effect": "FILESYSTEM_WRITE",
                "verification": "RECEIPT_ONLY",
                "environments": ["local", "development", "staging", "production"],
                "runtime_status": "ACTIVE",
                "source": "runtime_allowlist",
            },
            {
                "id": "run_validation",
                "surface": "adapter",
                "effect": "LOCAL_PROCESS",
                "verification": "EXIT_CODE_AND_OUTPUT",
                "environments": ["local", "development", "staging", "production"],
                "runtime_status": "ACTIVE",
                "source": "runtime_allowlist",
            },
            {
                "id": "github.read-ref/v1",
                "surface": "canonical_operation",
                "effect": "READ_ONLY",
                "verification": "INDEPENDENT_VERIFIER",
                "environments": ["local", "development", "staging"],
                "runtime_status": "ENABLED" if canonical_runtime_enabled else "DISABLED",
                "source": "canonical_router",
            },
        ]
        return {
            "items": adapters,
            "fail_closed_default": True,
            "production_effects_enabled": self.config.production_effects_enabled,
        }

    @staticmethod
    def _canonical_evidence_items(
        passports: list[OperationPassport],
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []

        def append(
            *,
            execution_id: str,
            request_id: object,
            title: str,
            stage: str,
            status: str,
            timestamp: object,
            reference: object,
            detail: str,
        ) -> None:
            if not isinstance(timestamp, str) or not timestamp:
                return
            items.append(
                {
                    "kind": stage,
                    "id": f"canonical:{execution_id}:{stage.casefold()}",
                    "title": title,
                    "status": status,
                    "timestamp": timestamp,
                    "detail": detail,
                    "source": "OPERATION_PASSPORT",
                    "execution_id": execution_id,
                    "request_id": request_id,
                    "reference": reference,
                }
            )

        for passport in passports:
            execution_id = passport.execution_id
            operation = passport.operation
            request_id = operation["request_id"]
            authority = passport.authority
            snapshot = authority["snapshot"]
            grant = authority["grant"]
            consumption = authority["consumption"]
            outbox = passport.dispatch["outbox"]
            runtime = passport.runtime
            verification = passport.verification
            title = f"{execution_id} · {operation['capability']}"

            append(
                execution_id=execution_id,
                request_id=request_id,
                title=title,
                stage="CANONICAL_AUTHORIZATION",
                status="AUTHORIZED",
                timestamp=snapshot["authorized_at"],
                reference=snapshot["snapshot_digest"],
                detail=f"AuthorizationSnapshot {snapshot['snapshot_digest']}",
            )
            if grant is not None:
                append(
                    execution_id=execution_id,
                    request_id=request_id,
                    title=title,
                    stage="CANONICAL_GRANT",
                    status="ISSUED",
                    timestamp=grant["issued_at"],
                    reference=grant["grant_digest"],
                    detail=f"ExecutionGrant/v2 {grant['grant_digest']}",
                )
            if consumption is not None:
                append(
                    execution_id=execution_id,
                    request_id=request_id,
                    title=title,
                    stage="CANONICAL_GRANT_CONSUMPTION",
                    status="CONSUMED",
                    timestamp=consumption["consumed_at"],
                    reference=consumption["consumption_digest"],
                    detail=f"GrantConsumptionWitness/v1 {consumption['consumption_digest']}",
                )
            if outbox is not None:
                append(
                    execution_id=execution_id,
                    request_id=request_id,
                    title=title,
                    stage="CANONICAL_DISPATCH",
                    status="ENQUEUED",
                    timestamp=outbox["created_at"],
                    reference=outbox["entry_digest"],
                    detail=f"DispatchOutboxEntry/v1 {outbox['entry_digest']}",
                )

            runtime_timestamp = runtime["completed_at"] or runtime["updated_at"]
            runtime_reference = (
                runtime["completion_digest"] or runtime["execution_capsule_digest"]
            )
            verification_state = (
                f"{verification['status']} / {verification['verdict']}"
            )
            append(
                execution_id=execution_id,
                request_id=request_id,
                title=title,
                stage="CANONICAL_RUNTIME",
                status=str(runtime["status"]),
                timestamp=runtime_timestamp,
                reference=runtime_reference,
                detail=(
                    f"Runtime {runtime['status']} · verification {verification_state}"
                ),
            )

            if verification["independent_verification_exposed"]:
                append(
                    execution_id=execution_id,
                    request_id=request_id,
                    title=title,
                    stage="CANONICAL_VERIFICATION",
                    status=str(verification["verdict"]),
                    timestamp=verification["checked_at"],
                    reference=verification["result_digest"],
                    detail=(
                        "VerificationResult/v1 "
                        f"{verification['result_digest']} · "
                        f"{verification['verification_strength_class']}"
                    ),
                )

        items.sort(key=lambda item: (item["timestamp"], item["id"]), reverse=True)
        return items

    @classmethod
    def _evidence_timeline(
        cls,
        *,
        change_requests: list[dict[str, Any]],
        executions: list[dict[str, Any]],
        receipts: list[dict[str, Any]],
        audits: list[dict[str, Any]],
        canonical_passports: list[OperationPassport],
    ) -> list[dict[str, Any]]:
        legacy_items: list[dict[str, Any]] = []
        for event in audits[:6]:
            legacy_items.append(
                {
                    "kind": "AUDIT_EVENT",
                    "id": event["id"],
                    "title": event["action"],
                    "status": "RECORDED",
                    "timestamp": event["created_at"],
                    "detail": event["target_type"],
                    "source": "AUDIT_LEDGER",
                    "execution_id": None,
                    "request_id": None,
                    "reference": event["id"],
                }
            )
        for receipt in receipts[:3]:
            legacy_items.append(
                {
                    "kind": "RECEIPT",
                    "id": receipt["id"],
                    "title": receipt["execution_id"],
                    "status": "RECORDED",
                    "timestamp": receipt["created_at"],
                    "detail": receipt["receipt_hash"],
                    "source": "RECEIPT_LEDGER",
                    "execution_id": receipt["execution_id"],
                    "request_id": None,
                    "reference": receipt["receipt_hash"],
                }
            )
        for execution in executions[:3]:
            legacy_items.append(
                {
                    "kind": "EXECUTION",
                    "id": execution["id"],
                    "title": execution["title"],
                    "status": execution["status"],
                    "timestamp": execution["updated_at"],
                    "detail": execution["adapter"],
                    "source": "LEGACY_EXECUTION",
                    "execution_id": execution["id"],
                    "request_id": None,
                    "reference": execution.get("receipt_id"),
                }
            )
        for request in change_requests[:3]:
            legacy_items.append(
                {
                    "kind": "PLAN",
                    "id": request["id"],
                    "title": request["title"],
                    "status": request["status"],
                    "timestamp": request["updated_at"],
                    "detail": request["risk"],
                    "source": "CHANGE_REQUEST",
                    "execution_id": None,
                    "request_id": request["id"],
                    "reference": request["id"],
                }
            )

        canonical_items = cls._canonical_evidence_items(canonical_passports)
        legacy_items.sort(
            key=lambda item: (item["timestamp"], item["id"]),
            reverse=True,
        )
        canonical_quota = CONTROL_ROOM_LIMIT // 2
        legacy_quota = CONTROL_ROOM_LIMIT - canonical_quota
        selected = canonical_items[:canonical_quota] + legacy_items[:legacy_quota]
        if len(selected) < CONTROL_ROOM_LIMIT:
            overflow = canonical_items[canonical_quota:] + legacy_items[legacy_quota:]
            overflow.sort(
                key=lambda item: (item["timestamp"], item["id"]),
                reverse=True,
            )
            selected.extend(overflow[: CONTROL_ROOM_LIMIT - len(selected)])
        selected.sort(
            key=lambda item: (item["timestamp"], item["id"]),
            reverse=True,
        )
        return selected[:CONTROL_ROOM_LIMIT]

    def _policy_gates(
        self,
        *,
        overview: dict[str, Any],
        canonical_runtime_enabled: bool,
    ) -> list[dict[str, Any]]:
        gates = [
            ("UNKNOWN != PASS", "ENFORCED", "truth_invariant"),
            ("MISSING != PASS", "ENFORCED", "truth_invariant"),
            ("UNVERIFIED != PASS", "ENFORCED", "truth_invariant"),
            (
                "Production effects",
                "ENABLED" if overview["production_effects_enabled"] else "DISABLED",
                "runtime",
            ),
            ("Emergency stop", "ACTIVE" if overview["emergency_stop"] else "INACTIVE", "runtime"),
            (
                "Receipt chain",
                "PASS" if overview["receipt_integrity"]["valid"] else "FAIL",
                "evidence",
            ),
            (
                "Audit chain",
                "PASS" if overview["audit_integrity"]["valid"] else "FAIL",
                "evidence",
            ),
            (
                "Canonical read runtime",
                "ENABLED" if canonical_runtime_enabled else "DISABLED",
                "runtime",
            ),
        ]
        return [{"name": name, "status": status, "source": source} for name, status, source in gates]

    def _verifier_center(
        self,
        *,
        receipts: list[dict[str, Any]],
        executions: list[dict[str, Any]],
        verification_passports: list[OperationPassport],
    ) -> dict[str, Any]:
        recent_checks: list[dict[str, Any]] = []
        canonical_execution_ids: set[str] = set()
        for passport in verification_passports:
            verification = passport.verification
            canonical_execution_ids.add(passport.execution_id)
            recent_checks.append(
                {
                    "source": "VERIFICATION_RESULT_V1",
                    "receipt_id": None,
                    "execution_id": passport.execution_id,
                    "execution_status": passport.runtime["status"],
                    "verification_status": verification["verdict"],
                    "verification_strength": verification["verification_strength_class"],
                    "result_digest": verification["result_digest"],
                    "checked_at": verification["checked_at"],
                    "created_at": verification["checked_at"],
                }
            )

        execution_index = {item["id"]: item for item in executions}
        for receipt in receipts[:CONTROL_ROOM_LIMIT]:
            if receipt["execution_id"] in canonical_execution_ids:
                continue
            execution = execution_index.get(receipt["execution_id"], {})
            recent_checks.append(
                {
                    "source": "LEGACY_RECEIPT",
                    "receipt_id": receipt["id"],
                    "execution_id": receipt["execution_id"],
                    "execution_status": execution.get("status", "UNKNOWN"),
                    "verification_status": "UNKNOWN",
                    "verification_strength": None,
                    "result_digest": None,
                    "checked_at": None,
                    "created_at": receipt["created_at"],
                }
            )
        recent_checks.sort(key=lambda item: item["created_at"], reverse=True)
        return {
            "separation_rule": "ExecutionReceipt != VerificationResult",
            "recent_checks": recent_checks[:CONTROL_ROOM_LIMIT],
            "independent_verification_exposed": bool(verification_passports),
            "canonical_result_count": len(verification_passports),
        }

    def _runtime_health(
        self,
        *,
        health: dict[str, Any],
        canonical_runtime_enabled: bool,
    ) -> list[dict[str, Any]]:
        return [
            {"name": "API", "status": health["status"], "detail": "FastAPI product surface"},
            {"name": "Database", "status": health["database"], "detail": health["database_backend"]},
            {
                "name": "Evidence",
                "status": health.get("evidence_integrity", "UNKNOWN"),
                "detail": "liveness projection",
            },
            {
                "name": "Identity",
                "status": self.config.identity_provider.upper(),
                "detail": "configured provider",
            },
            {
                "name": "Canonical runtime",
                "status": "ENABLED" if canonical_runtime_enabled else "DISABLED",
                "detail": "read path activation",
            },
        ]

    def _learning_intelligence(
        self,
        *,
        change_requests: list[dict[str, Any]],
        executions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        total_requests = len(change_requests)
        total_executions = len(executions)
        succeeded = sum(1 for item in executions if item["status"] == "SUCCEEDED")
        failed = sum(1 for item in executions if item["status"] == "FAILED")
        return {
            "signals": [
                {
                    "name": "Execution success rate",
                    "value": f"{round((succeeded / total_executions) * 100)}%"
                    if total_executions
                    else "UNKNOWN",
                    "status": "OBSERVED" if total_executions else "UNKNOWN",
                },
                {
                    "name": "Failure pressure",
                    "value": str(failed),
                    "status": "OBSERVED" if total_executions else "UNKNOWN",
                },
                {
                    "name": "Approval queue",
                    "value": str(
                        sum(1 for item in change_requests if item["status"] == "REVIEW_REQUIRED")
                    ),
                    "status": "OBSERVED" if total_requests else "UNKNOWN",
                },
            ],
            "scoring_router": "NOT_EXPOSED",
        }

    def _governance_projection(self, *, overview: dict[str, Any]) -> dict[str, Any]:
        return {
            "environment": overview["environment"],
            "trusted_hosts": list(self.config.trusted_hosts),
            "cors_origins": list(self.config.cors_origins),
            "identity_provider": self.config.identity_provider,
            "production_effects_enabled": self.config.production_effects_enabled,
            "approval_policy_compatibility_enabled": (
                self.config.approval_policy_compatibility_enabled
            ),
        }

    def _append_audit(
        self,
        connection: DatabaseConnection,
        *,
        actor_id: str,
        action: str,
        target_type: str,
        target_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self.audit_ledger.append(
            connection,
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            payload=payload,
        )

    def _append_receipt(
        self,
        connection: DatabaseConnection,
        *,
        execution_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self.receipt_ledger.append(
            connection,
            execution_id=execution_id,
            payload=payload,
        )
