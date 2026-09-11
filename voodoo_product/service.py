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
        return {
            "overview": overview,
            "runs": self._summarize_runs(change_requests, executions),
            "plans": self._summarize_plans(change_requests, approvals),
            "capability_registry": self._capability_registry(canonical_runtime_enabled),
            "evidence_timeline": self._evidence_timeline(
                change_requests=change_requests,
                executions=executions,
                receipts=receipts,
                audits=audits,
            ),
            "policy_gates": self._policy_gates(
                overview=overview,
                canonical_runtime_enabled=canonical_runtime_enabled,
            ),
            "verifier_center": self._verifier_center(receipts=receipts, executions=executions),
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

    def _evidence_timeline(
        self,
        *,
        change_requests: list[dict[str, Any]],
        executions: list[dict[str, Any]],
        receipts: list[dict[str, Any]],
        audits: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for event in audits[:6]:
            items.append(
                {
                    "kind": "AUDIT_EVENT",
                    "id": event["id"],
                    "title": event["action"],
                    "status": "RECORDED",
                    "timestamp": event["created_at"],
                    "detail": event["target_type"],
                }
            )
        for receipt in receipts[:3]:
            items.append(
                {
                    "kind": "RECEIPT",
                    "id": receipt["id"],
                    "title": receipt["execution_id"],
                    "status": "RECORDED",
                    "timestamp": receipt["created_at"],
                    "detail": receipt["receipt_hash"],
                }
            )
        for execution in executions[:3]:
            items.append(
                {
                    "kind": "EXECUTION",
                    "id": execution["id"],
                    "title": execution["title"],
                    "status": execution["status"],
                    "timestamp": execution["updated_at"],
                    "detail": execution["adapter"],
                }
            )
        for request in change_requests[:3]:
            items.append(
                {
                    "kind": "PLAN",
                    "id": request["id"],
                    "title": request["title"],
                    "status": request["status"],
                    "timestamp": request["updated_at"],
                    "detail": request["risk"],
                }
            )
        items.sort(key=lambda item: item["timestamp"], reverse=True)
        return items[:CONTROL_ROOM_LIMIT]

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
    ) -> dict[str, Any]:
        recent_checks = []
        execution_index = {item["id"]: item for item in executions}
        for receipt in receipts[:CONTROL_ROOM_LIMIT]:
            execution = execution_index.get(receipt["execution_id"], {})
            recent_checks.append(
                {
                    "receipt_id": receipt["id"],
                    "execution_id": receipt["execution_id"],
                    "execution_status": execution.get("status", "UNKNOWN"),
                    "verification_status": "UNKNOWN",
                    "created_at": receipt["created_at"],
                }
            )
        return {
            "separation_rule": "ExecutionReceipt != VerificationResult",
            "recent_checks": recent_checks,
            "independent_verification_exposed": False,
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
