from __future__ import annotations

from pathlib import Path

import pytest

from scripts.check_requirements_lock_drift import (
    RequirementLockDriftError,
    check_pair,
    evaluate,
)


def write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_current_repository_requirement_locks_match_direct_pins() -> None:
    report = evaluate()

    assert report["ok"] is True
    assert report["checks"]["product"]["mismatched"] == []
    assert report["checks"]["development"]["mismatched"] == []


def test_check_pair_supports_recursive_manifest_and_extras(tmp_path: Path) -> None:
    write(
        tmp_path / "requirements-product.txt",
        "fastapi==1.2.3\nuvicorn[standard]==4.5.6\n",
    )
    manifest = write(
        tmp_path / "requirements-dev.in",
        "-r requirements-product.txt\npytest==9.9.9\n",
    )
    lock = write(
        tmp_path / "requirements-dev.lock",
        "fastapi==1.2.3 \\\n"
        "    --hash=sha256:" + "a" * 64 + "\n"
        "pytest==9.9.9 \\\n"
        "    --hash=sha256:" + "b" * 64 + "\n"
        "uvicorn[standard]==4.5.6 \\\n"
        "    --hash=sha256:" + "c" * 64 + "\n",
    )

    report = check_pair(manifest=manifest, lock=lock, root=tmp_path)

    assert report["ok"] is True
    assert report["required_pin_count"] == 3


def test_check_pair_detects_manifest_lock_version_drift(tmp_path: Path) -> None:
    manifest = write(tmp_path / "requirements-product.txt", "fastapi==1.2.3\n")
    lock = write(tmp_path / "requirements-product.lock", "fastapi==1.2.2\n")

    report = check_pair(manifest=manifest, lock=lock, root=tmp_path)

    assert report["ok"] is False
    assert report["mismatched"] == [
        {
            "requirement": "fastapi",
            "manifest_version": "1.2.3",
            "lock_version": "1.2.2",
        }
    ]


def test_check_pair_detects_missing_direct_requirement(tmp_path: Path) -> None:
    manifest = write(
        tmp_path / "requirements-product.txt",
        "fastapi==1.2.3\npydantic==4.5.6\n",
    )
    lock = write(tmp_path / "requirements-product.lock", "fastapi==1.2.3\n")

    report = check_pair(manifest=manifest, lock=lock, root=tmp_path)

    assert report["ok"] is False
    assert report["missing"] == ["pydantic"]


def test_manifest_include_cannot_escape_repository_root(tmp_path: Path) -> None:
    outside = write(tmp_path.parent / "outside-requirements.txt", "unsafe==1.0\n")
    manifest = write(
        tmp_path / "requirements-dev.in",
        f"-r ../{outside.name}\npytest==9.9.9\n",
    )
    lock = write(tmp_path / "requirements-dev.lock", "pytest==9.9.9\n")

    with pytest.raises(RequirementLockDriftError, match="escapes repository root"):
        check_pair(manifest=manifest, lock=lock, root=tmp_path)


def test_unsupported_manifest_syntax_fails_closed(tmp_path: Path) -> None:
    manifest = write(
        tmp_path / "requirements-product.txt",
        "fastapi>=1.2.3\n",
    )
    lock = write(tmp_path / "requirements-product.lock", "fastapi==1.2.3\n")

    with pytest.raises(RequirementLockDriftError, match="unsupported requirement syntax"):
        check_pair(manifest=manifest, lock=lock, root=tmp_path)
