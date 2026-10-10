"""Read-only Control Room presentation projections.

These helpers intentionally accept already-authorized rows only. They do not
query persistence, make policy decisions, or infer verification or effect state.
The ProductService facade retains the existing caller-facing method signatures.
"""

from __future__ import annotations

from typing import Any


def summarize_runs(
    change_requests: list[dict[str, Any]],
    executions: list[dict[str, Any]],
    *,
    limit: int,
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
        for item in executions[:limit]
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


def summarize_plans(
    change_requests: list[dict[str, Any]],
    approvals: list[dict[str, Any]],
    *,
    limit: int,
) -> dict[str, Any]:
    # Preserve source-order, first-match precedence for duplicate approvals.
    first_approval_by_request: dict[str, dict[str, Any]] = {}
    for approval in approvals:
        first_approval_by_request.setdefault(approval["request_id"], approval)

    items: list[dict[str, Any]] = []
    for request in change_requests[:limit]:
        approval = first_approval_by_request.get(request["id"])
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
