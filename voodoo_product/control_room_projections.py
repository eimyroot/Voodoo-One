"""Read-only Control Room presentation projections.

These helpers intentionally accept already-authorized rows only. They do not
query persistence, make policy decisions, or infer verification or effect state.
The ProductService facade retains the existing caller-facing method signatures.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .operation_passport import OperationPassport


def execution_presentation_timestamp(execution: dict[str, Any]) -> Any:
    """Use persisted execution times without changing existing presentation rows."""
    if "updated_at" in execution:
        return execution["updated_at"]
    return execution["completed_at"] or execution["started_at"]


def summarize_runs(
    change_requests: list[dict[str, Any]],
    executions: list[dict[str, Any]],
    *,
    limit: int,
    canonical_passports: list[OperationPassport] | None = None,
) -> dict[str, Any]:
    recent = [
        {
            "id": item["id"],
            "title": item["title"],
            "status": item["status"],
            "risk": item["risk"],
            "environment": item["environment"],
            "adapter": item["adapter"],
            "updated_at": execution_presentation_timestamp(item),
            "receipt_id": item.get("receipt_id"),
            "request_id": item.get("request_id"),
        }
        for item in executions
    ]
    # Canonical durable state wins for the same execution ID. Never turn
    # runtime COMPLETED into SUCCEEDED or VERIFIED.
    if canonical_passports:
        by_id = {row["id"]: row for row in recent}
        requests_by_id = {
            row["id"]: row for row in change_requests if row.get("id")
        }
        for passport in canonical_passports:
            operation = passport.operation
            request_id = operation["request_id"]
            request = requests_by_id.get(request_id, {})
            bound = (
                request.get("workspace_id") == operation["workspace_id"]
                and request.get("environment") == operation["environment"]
            )
            verification = passport.verification
            verdict = (
                verification.get("verdict") or "UNKNOWN"
                if passport.integrity.get("independent_verification_validated") is True
                and verification.get("status") == "PERSISTED"
                and verification.get("independent_verification_exposed") is True
                else "UNKNOWN"
            )
            by_id[passport.execution_id] = {
                "id": passport.execution_id,
                "title": (request.get("title") if bound else None)
                or operation["capability"],
                "status": passport.runtime["status"],
                "risk": (request.get("risk") if bound else None) or "UNKNOWN",
                "environment": operation["environment"],
                "adapter": operation["capability"],
                "updated_at": passport.runtime.get("updated_at")
                or passport.runtime.get("completed_at")
                or passport.authority.get("snapshot", {}).get("authorized_at"),
                "receipt_id": None,
                "request_id": request_id,
                "source": "OPERATION_PASSPORT",
                "lifecycle_stage": passport.lifecycle_stage,
                "verification_status": verdict,
            }
        recent = sorted(
            by_id.values(),
            key=lambda row: (row["updated_at"] or "", row["id"]),
            reverse=True,
        )
    draft_or_review = sum(
        1 for item in change_requests if item["status"] in {"DRAFT", "REVIEW_REQUIRED"}
    )
    return {
        "recent": recent[:limit],
        "queue_depth": draft_or_review,
        "active_count": sum(
            1 for item in recent if item["status"] in {"RUNNING", "ACTIVE"}
        ),
        "completed_count": sum(
            1 for item in recent if item["status"] in {"SUCCEEDED", "COMPLETED"}
        ),
        "failed_count": sum(1 for item in recent if item["status"] == "FAILED"),
    }


def summarize_agent_participation(
    passports: list[OperationPassport],
    *,
    limit: int,
) -> dict[str, Any]:
    """Project bounded operation roles; never infer instance identity or presence."""
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit must be an integer between 1 and 100")
    recent: list[dict[str, Any]] = []
    for passport in passports[:limit]:
        if (
            passport.integrity.get("canonical_json_validated") is not True
            or passport.integrity.get("lineage_bindings_validated") is not True
        ):
            raise ValueError("agent participation requires a validated Passport")
        verification = passport.verification
        persisted = (
            passport.integrity.get("independent_verification_validated") is True
            and verification.get("status") == "PERSISTED"
            and verification.get("independent_verification_exposed") is True
            and verification.get("verdict") in {"VERIFIED", "NOT_VERIFIED"}
        )
        recent.append({
            "execution_id": passport.execution_id,
            "lifecycle_stage": passport.lifecycle_stage,
            "capability": passport.operation["capability"],
            "runner_class": passport.runtime.get("runner_class"),
            "runtime_status": passport.runtime["status"],
            "verification_status": verification["verdict"] if persisted else "UNKNOWN",
            "result_digest": verification["result_digest"] if persisted else None,
            "verification_strength": verification["verification_strength_class"] if persisted else None,
            "checked_at": verification["checked_at"] if persisted else None,
        })
    return {
        "schema": "vone.agent-participation/v1",
        "source": "OPERATION_PASSPORT",
        "instance_presence": "UNKNOWN",
        "window_limit": limit,
        "recent": recent,
    }


def summarize_plans(
    change_requests: list[dict[str, Any]],
    approvals: list[dict[str, Any]],
    *,
    limit: int,
) -> dict[str, Any]:
    # Keep indexed lookup for normal SQLite rows; on malformed internal rows,
    # preserve the original lazy first-match scan and its error behavior.
    first_approval_by_request: dict[str, dict[str, Any]] = {}
    indexed = True
    for approval in approvals:
        try:
            first_approval_by_request.setdefault(approval["request_id"], approval)
        except (KeyError, TypeError):
            indexed = False
            break

    items: list[dict[str, Any]] = []
    for request in change_requests[:limit]:
        if indexed:
            try:
                approval = first_approval_by_request.get(request["id"])
            except TypeError:
                approval = next(
                    (item for item in approvals if item["request_id"] == request["id"]),
                    None,
                )
        else:
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


def summarize_learning_intelligence(
    change_requests: list[dict[str, Any]],
    executions: list[dict[str, Any]],
) -> dict[str, Any]:
    total_requests = len(change_requests)
    total_executions = len(executions)
    succeeded = sum(1 for item in executions if item["status"] == "SUCCEEDED")
    failed = sum(1 for item in executions if item["status"] == "FAILED")
    completed = succeeded + failed
    return {
        "completed_sample": completed,
        "signals": [
            {
                "name": "Execution success rate",
                "value": f"{round((succeeded / completed) * 100)}%"
                if completed
                else "UNKNOWN",
                "status": "OBSERVED" if completed else "UNKNOWN",
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
