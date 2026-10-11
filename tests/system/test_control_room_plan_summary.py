from __future__ import annotations

from voodoo_product.service import CONTROL_ROOM_LIMIT, ProductService


def _request(identifier: str) -> dict[str, object]:
    return {
        "id": identifier,
        "title": f"Plan {identifier}",
        "status": "REVIEW_REQUIRED",
        "risk": "R1",
        "environment": "staging",
        "requested_by_username": "operator",
        "updated_at": "2026-10-10T00:00:00+00:00",
    }


def _reference_summary(
    requests: list[dict[str, object]], approvals: list[dict[str, object]]
) -> dict[str, object]:
    """Reference behavior of the original first-match linear scan."""
    items = []
    for request in requests[:CONTROL_ROOM_LIMIT]:
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


def test_plan_summary_preserves_first_matching_approval_and_defaults() -> None:
    requests = [_request("req-2"), _request("req-1"), _request("req-3")]
    requests[2]["approval_count"] = 2
    approvals = [
        {"request_id": "req-1", "required_count": 3},
        {"request_id": "req-1", "required_count": 9},
        {"request_id": "different", "required_count": 4},
        {"request_id": "req-3"},
    ]

    actual = ProductService._summarize_plans(None, requests, approvals)

    assert actual == _reference_summary(requests, approvals)
    assert [item["request_id"] for item in actual["items"]] == [
        "req-2", "req-1", "req-3"
    ]
    assert [item["approval_required"] for item in actual["items"]] == [1, 3, 1]
    assert actual["pending_approvals"] == 4


def test_plan_summary_limits_output_without_truncating_pending_count() -> None:
    requests = [_request(f"req-{index}") for index in range(30)]
    approvals = [
        {"request_id": f"req-{index}", "required_count": (index % 4) + 1}
        for index in range(30)
    ]

    actual = ProductService._summarize_plans(None, requests, approvals)

    assert actual == _reference_summary(requests, approvals)
    assert len(actual["items"]) == CONTROL_ROOM_LIMIT
    assert actual["pending_approvals"] == 30


def test_plan_summary_matches_reference_across_deterministic_cases() -> None:
    for case in range(40):
        requests = [_request(f"req-{i}") for i in range((case * 7) % 24)]
        approvals = [
            {
                "request_id": f"req-{(index * 13 + case * 17) % 35}",
                "required_count": (index + case) % 5 + 1,
            }
            for index in range((case * 19) % 75)
        ]
        assert ProductService._summarize_plans(None, requests, approvals) == (
            _reference_summary(requests, approvals)
        )
