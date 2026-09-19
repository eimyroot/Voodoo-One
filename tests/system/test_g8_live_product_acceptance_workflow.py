from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "g8-live-product-read.yml"
DRIVER = ROOT / "scripts" / "g8_live_product_acceptance.py"


def test_g8_live_gate_is_manual_main_only_and_read_only() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "pull_request:" not in text
    assert "push:" not in text
    assert "if: github.ref == 'refs/heads/main'" in text
    assert "permissions:\n  contents: read" in text
    assert "contents: write" not in text
    assert "actions: write" not in text
    assert "pull-requests: write" not in text
    assert "packages: write" not in text


def test_g8_live_gate_requires_exact_sha_and_explicit_confirmation() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "expected_sha:" in text
    assert 'test "$GITHUB_SHA" = "$EXPECTED_SHA"' in text
    assert 'test "$(git rev-parse HEAD)" = "$EXPECTED_SHA"' in text
    assert "RUN_G8_LIVE_READ" in text


def test_g8_live_gate_separates_runner_and_verifier_credentials() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "RUNNER_GITHUB_TOKEN: ${{ secrets.VONE_G8_RUNNER_GITHUB_TOKEN }}" in text
    assert "github.token" not in text
    assert "VERIFIER_GITHUB_TOKEN: ${{ secrets.VONE_G8_VERIFIER_GITHUB_TOKEN }}" in text
    assert "VONE_GITHUB_GOVERNANCE_TOKEN" not in text
    assert "VOODOO_G8_RUNNER_GITHUB_TOKEN=$RUNNER_GITHUB_TOKEN" in text
    assert "VOODOO_G8_VERIFIER_GITHUB_TOKEN=$VERIFIER_GITHUB_TOKEN" in text
    assert 'test -n "$RUNNER_GITHUB_TOKEN"' in text
    assert 'test -n "$VERIFIER_GITHUB_TOKEN"' in text
    assert text.count("--ctstate ESTABLISHED,RELATED -j ACCEPT") == 3
    assert "id: sanitize_evidence" in text
    assert "if: always() && steps.sanitize_evidence.outcome == 'success'" in text
    assert "secret material found in evidence file" in text
    assert 'test "$runner_id" != "$verifier_id"' in text


def test_g8_live_gate_preserves_default_deny_runtime_boundary() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    for required in (
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--memory=512m",
        "--cpus=1",
        "--pids-limit=256",
        "DOCKER-USER",
        "G8_NETWORK_NEGATIVE_CHECK=PASS",
    ):
        assert required in text
    for forbidden in ("github-create-ref", "github-delete-ref", "CREATE_REF", "DELETE_REF"):
        assert forbidden not in text


def test_g8_live_gate_proves_http_restart_resume_and_duplicate_lineage() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    for required in (
        "http-e2e",
        "http-create-approved",
        "prepare-active",
        "--hold-seconds 600",
        "g8-prepare.pid",
        'kill -9 "$(cat /tmp/g8-prepare.pid)"',
        "active-interruption.json",
        "assert-lineage --execution-id",
        "--status ACTIVE",
        "resume --execution-id",
        "--status COMPLETED",
        'assert active["counts"] == completed["counts"]',
        'assert active["current_lease_id"] == completed["current_lease_id"]',
    ):
        assert required in text


def test_g8_acceptance_driver_has_only_fixed_subcommands() -> None:
    source = DRIVER.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(DRIVER))
    assert "subprocess" not in {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    for command in (
        'subparsers.add_parser("fixture")',
        'subparsers.add_parser("http-e2e")',
        'subparsers.add_parser("http-create-approved")',
        'subparsers.add_parser("prepare-active")',
        'subparsers.add_parser("resume")',
        'subparsers.add_parser("assert-lineage")',
    ):
        assert command in source
    assert "github_create_ref" not in source
    assert "github_delete_ref" not in source
    assert 'prepare.add_argument("--hold-seconds", type=int, default=0)' in source
    assert "time.sleep(args.hold_seconds)" in source
    assert "OperationProof" not in source
    assert "OperationCell" not in source


def test_g8_live_gate_uploads_only_sanitized_evidence() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "secret material found in evidence file" in text
    assert "acceptance-summary.json" in text
    assert "SHA256SUMS.txt" in text
    assert "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a" in text
    assert "deployment_performed\": False" in text
    assert "provider_write_performed\": False" in text
