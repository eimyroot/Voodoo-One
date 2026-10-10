from __future__ import annotations

from voodoo_product.service import CONTROL_ROOM_LIMIT, ProductService


def _run(identifier: int, status: str) -> dict[str, object]:
    return {
        "id": f"exec-{identifier}",
        "title": f"Execution {identifier}",
        "status": status,
        "risk": "R1",
        "environment": "staging",
        "adapter": "echo",
        "updated_at": "2026-10-10T00:00:00+00:00",
    }


def test_run_summary_preserves_visible_limit_and_counts_all_supplied_rows() -> None:
    requests = [
        {"status": "DRAFT"},
        {"status": "REVIEW_REQUIRED"},
        {"status": "APPROVED"},
        {"status": "REVIEW_REQUIRED"},
    ]
    executions = [
        _run(i, ("RUNNING", "SUCCEEDED", "FAILED", "INTERRUPTED")[i % 4])
        for i in range(CONTROL_ROOM_LIMIT + 4)
    ]
    executions[0]["receipt_id"] = "receipt-1"

    summary = ProductService._summarize_runs(None, requests, executions)

    assert len(summary["recent"]) == CONTROL_ROOM_LIMIT
    assert summary["recent"][0] == {
        "id": "exec-0",
        "title": "Execution 0",
        "status": "RUNNING",
        "risk": "R1",
        "environment": "staging",
        "adapter": "echo",
        "updated_at": "2026-10-10T00:00:00+00:00",
        "receipt_id": "receipt-1",
    }
    assert summary["recent"][1]["receipt_id"] is None
    assert summary["queue_depth"] == 3
    assert summary["active_count"] == 4
    assert summary["completed_count"] == 4
    assert summary["failed_count"] == 4


def test_run_summary_empty_input_retains_exact_contract() -> None:
    assert ProductService._summarize_runs(None, [], []) == {
        "recent": [],
        "queue_depth": 0,
        "active_count": 0,
        "completed_count": 0,
        "failed_count": 0,
    }


def test_learning_projection_preserves_unknown_and_observed_states() -> None:
    empty = ProductService._learning_intelligence(
        None, change_requests=[], executions=[]
    )
    assert empty == {
        "signals": [
            {"name": "Execution success rate", "value": "UNKNOWN", "status": "UNKNOWN"},
            {"name": "Failure pressure", "value": "0", "status": "UNKNOWN"},
            {"name": "Approval queue", "value": "0", "status": "UNKNOWN"},
        ],
        "scoring_router": "NOT_EXPOSED",
    }

    observed = ProductService._learning_intelligence(
        None,
        change_requests=[
            {"status": "REVIEW_REQUIRED"},
            {"status": "DRAFT"},
            {"status": "REVIEW_REQUIRED"},
        ],
        executions=[
            {"status": "SUCCEEDED"},
            {"status": "FAILED"},
            {"status": "RUNNING"},
        ],
    )
    assert observed == {
        "signals": [
            {"name": "Execution success rate", "value": "33%", "status": "OBSERVED"},
            {"name": "Failure pressure", "value": "1", "status": "OBSERVED"},
            {"name": "Approval queue", "value": "2", "status": "OBSERVED"},
        ],
        "scoring_router": "NOT_EXPOSED",
    }


def test_learning_projection_preserves_half_to_even_rounding() -> None:
    executions = [{"status": "SUCCEEDED"}] * 5 + [{"status": "FAILED"}] * 3
    projection = ProductService._learning_intelligence(
        None, change_requests=[], executions=executions
    )
    assert projection["signals"][0]["value"] == "62%"
