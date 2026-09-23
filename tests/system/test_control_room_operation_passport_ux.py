from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_runs_exposes_read_only_operation_passport_drilldown() -> None:
    html = _read("voodoo_product/static/index.html")
    javascript = _read("voodoo_product/static/control_room.js")

    assert 'id="operation-passport-panel"' in html
    assert 'id="operation-passport-content"' in html
    assert 'id="close-passport-button"' in html
    assert "data-passport-execution-id" in javascript
    assert "api(`/operations/${encodeURIComponent(executionId)}/passport`)" in javascript
    assert "$('runs-table').addEventListener('click'" in javascript

    start = javascript.index("async function loadOperationPassport")
    end = javascript.index("$('runs-table').addEventListener", start)
    passport_loader = javascript[start:end]
    assert "method:" not in passport_loader
    assert "/read" not in passport_loader


def test_passport_ux_preserves_verification_truth_boundaries() -> None:
    javascript = _read("voodoo_product/static/control_room.js")

    assert "verification.verdict||'UNKNOWN'" in javascript
    assert "verification.independent_verification_exposed" in javascript
    assert "integrity.independent_verification_validated" in javascript
    assert "NOT_VALIDATED" in javascript
    assert "Absence canonical lineage" in javascript
    assert "err.statusCode===404" in javascript
    assert "konflikt canonical lineage se nesmí interpretovat jako prostá absence" in javascript
    assert "JSON.stringify(data,null,2)" in javascript
    assert "$('passport-raw-json').textContent" in javascript

def test_passport_ux_renders_canonical_evidence_timeline_from_passport_only() -> None:
    javascript = _read("voodoo_product/static/control_room.js")

    assert "function passportEvidenceTimeline" in javascript
    assert "Canonical evidence timeline" in javascript
    assert "Derived only from validated Operation Passport facts" in javascript
    assert "snapshot.authorized_at" in javascript
    assert "grant.issued_at" in javascript
    assert "consumption.consumed_at" in javascript
    assert "outbox.created_at" in javascript
    assert "runtime.completed_at||runtime.updated_at" in javascript
    assert "verification.checked_at" in javascript
    assert "verification.result_digest" in javascript
    assert "'NOT_PERSISTED','UNKNOWN'" in javascript
    assert "Verification strength" in javascript
    assert "Checked at" in javascript

    start = javascript.index("function passportEvidenceTimeline")
    end = javascript.index("function renderOperationPassport", start)
    timeline = javascript[start:end]
    assert "controlRoom(" not in timeline
    assert "api(" not in timeline
    assert "fetch(" not in timeline
