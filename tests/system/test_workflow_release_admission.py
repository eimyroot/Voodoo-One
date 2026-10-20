"""Fail-closed admission of the actual workflow console release source tree."""
from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.product_readiness_gate import WORKFLOW_UI_REQUIRED, workflow_ui_source_admission


def git(path: Path, *args: str) -> None:
    done = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "-c", "user.name=QA",
         "-c", "user.email=qa@example.invalid", *args],
        cwd=path, check=False, text=True, capture_output=True,
    )
    assert done.returncode == 0, done.stderr


def test_workflow_ui_admission_rejects_missing_git_head(tmp_path: Path) -> None:
    result = workflow_ui_source_admission(tmp_path)
    assert result["ok"] is False
    assert result["reason"] == "GIT_HEAD_NOT_AVAILABLE"


def test_workflow_ui_admission_requires_committed_tree_not_untracked_or_staged(tmp_path: Path) -> None:
    git(tmp_path, "init", "-q")
    (tmp_path / "README.md").write_text("QA\n")
    git(tmp_path, "add", "README.md")
    git(tmp_path, "commit", "-qm", "initial checkpoint")
    for rel in WORKFLOW_UI_REQUIRED:
        file = tmp_path / rel
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("test source\n")
    assert workflow_ui_source_admission(tmp_path)["ok"] is False
    git(tmp_path, "add", "--", *WORKFLOW_UI_REQUIRED)
    # Merely staging files does not make them part of the exact release HEAD.
    assert workflow_ui_source_admission(tmp_path)["ok"] is False
    git(tmp_path, "commit", "-qm", "admit workflow sources")
    admitted = workflow_ui_source_admission(tmp_path)
    assert admitted["ok"] is True
    assert admitted["missing_in_head"] == []
    # Tracked files edited after the release HEAD cannot silently pass readiness.
    (tmp_path / WORKFLOW_UI_REQUIRED[1]).write_text("new uncommitted content\\n")
    drift = workflow_ui_source_admission(tmp_path)
    assert drift["ok"] is False
    assert drift["reason"] == "UI_SOURCE_DIFFERS_FROM_HEAD"


def test_workflow_ui_admission_blocks_when_one_file_missing_from_head(tmp_path: Path) -> None:
    git(tmp_path, "init", "-q")
    rel = WORKFLOW_UI_REQUIRED[0]
    first = tmp_path / rel
    first.parent.mkdir(parents=True)
    first.write_text("checked in\n")
    git(tmp_path, "add", rel)
    git(tmp_path, "commit", "-qm", "partial ui")
    observed = workflow_ui_source_admission(tmp_path)
    assert observed["ok"] is False
    assert len(observed["missing_in_head"]) == len(WORKFLOW_UI_REQUIRED) - 1
