from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.dependency_graph_snapshot import (
    CORRELATOR,
    DETECTOR_NAME,
    DependencySnapshotError,
    build_snapshot,
    build_verification_spec,
    verify_sbom,
    write_snapshot,
)

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "dependency-graph-refresh.yml"
SHA = "1" * 40
SCANNED = "2026-10-08T17:54:51Z"


def _write_fixture(tmp_path: Path) -> dict[str, Path]:
    product_input = tmp_path / "requirements-product.txt"
    product_input.write_text(
        "fastapi==0.141.1\n"
        "pydantic==2.13.5\n"
        "uvicorn[standard]==0.52.4\n",
        encoding="utf-8",
    )
    product_lock = tmp_path / "requirements-product.lock"
    product_lock.write_text(
        "fastapi==0.141.1 \\\n"
        "pydantic==2.13.5 \\\n"
        "starlette==0.48.0 \\\n"
        "uvicorn==0.52.4 \\\n",
        encoding="utf-8",
    )
    dev_input = tmp_path / "requirements-dev.in"
    dev_input.write_text(
        "-r requirements-product.txt\n"
        "httpx2==2.12.0\n"
        "pip-audit==2.10.1\n"
        "pytest==9.1.1\n"
        "pre-commit==4.6.2\n"
        "ruff==0.16.5\n",
        encoding="utf-8",
    )
    dev_lock = tmp_path / "requirements-dev.lock"
    dev_lock.write_text(
        "fastapi==0.141.1 \\\n"
        "httpcore2==2.12.0 \\\n"
        "httpx2==2.12.0 \\\n"
        "pip-audit==2.10.1 \\\n"
        "pytest==9.1.1 \\\n"
        "pre-commit==4.6.2 \\\n"
        "ruff==0.16.5 \\\n"
        "urllib3==2.8.0 \\\n"
        "virtualenv==21.14.6 \\\n",
        encoding="utf-8",
    )
    return {
        "product_input": product_input,
        "product_lock": product_lock,
        "dev_input": dev_input,
        "dev_lock": dev_lock,
    }


def test_snapshot_is_exact_main_bound_and_preserves_scope_relationships(
    tmp_path: Path,
) -> None:
    paths = _write_fixture(tmp_path)

    snapshot = build_snapshot(
        sha=SHA,
        ref="refs/heads/main",
        scanned=SCANNED,
        **paths,
    )

    assert snapshot["sha"] == SHA
    assert snapshot["ref"] == "refs/heads/main"
    assert snapshot["job"]["correlator"] == CORRELATOR
    assert snapshot["detector"]["name"] == DETECTOR_NAME

    runtime = snapshot["manifests"]["requirements-product.txt"]["resolved"]
    development = snapshot["manifests"]["requirements-dev.in"]["resolved"]

    assert runtime["fastapi"] == {
        "package_url": "pkg:pypi/fastapi@0.141.1",
        "relationship": "direct",
        "scope": "runtime",
    }
    assert runtime["starlette"]["relationship"] == "indirect"
    assert runtime["starlette"]["scope"] == "runtime"
    assert development["httpx2"] == {
        "package_url": "pkg:pypi/httpx2@2.12.0",
        "relationship": "direct",
        "scope": "development",
    }
    assert development["fastapi"]["relationship"] == "indirect"
    assert development["fastapi"]["scope"] == "development"


def test_snapshot_uses_resolved_lock_version_for_direct_dependency(
    tmp_path: Path,
) -> None:
    paths = _write_fixture(tmp_path)
    paths["dev_lock"].write_text(
        paths["dev_lock"].read_text(encoding="utf-8").replace(
            "httpx2==2.12.0",
            "httpx2==2.11.0",
        ),
        encoding="utf-8",
    )

    snapshot = build_snapshot(
        sha=SHA,
        ref="refs/heads/main",
        scanned=SCANNED,
        **paths,
    )

    dependency = snapshot["manifests"]["requirements-dev.in"]["resolved"]["httpx2"]
    assert dependency["package_url"] == "pkg:pypi/httpx2@2.11.0"
    assert dependency["relationship"] == "direct"


def test_snapshot_rejects_unexpected_requirement_include(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    paths["dev_input"].write_text(
        "-r requirements-product.txt\n"
        "-r unexpected.in\n"
        "httpx2==2.12.0\n"
        "pip-audit==2.10.1\n"
        "pytest==9.1.1\n"
        "pre-commit==4.6.2\n"
        "ruff==0.16.5\n",
        encoding="utf-8",
    )

    with pytest.raises(DependencySnapshotError, match="unsupported requirement include"):
        build_snapshot(
            sha=SHA,
            ref="refs/heads/main",
            scanned=SCANNED,
            **paths,
        )


def test_snapshot_bytes_are_deterministic_for_identical_inputs(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    first_snapshot = tmp_path / "first.json"
    first_verification = tmp_path / "first-verification.json"
    second_snapshot = tmp_path / "second.json"
    second_verification = tmp_path / "second-verification.json"

    write_snapshot(
        sha=SHA,
        ref="refs/heads/main",
        scanned=SCANNED,
        snapshot_out=first_snapshot,
        verification_out=first_verification,
        previous_product_lock=None,
        previous_dev_lock=None,
        **paths,
    )
    write_snapshot(
        sha=SHA,
        ref="refs/heads/main",
        scanned=SCANNED,
        snapshot_out=second_snapshot,
        verification_out=second_verification,
        previous_product_lock=None,
        previous_dev_lock=None,
        **paths,
    )

    assert first_snapshot.read_bytes() == second_snapshot.read_bytes()
    assert first_verification.read_bytes() == second_verification.read_bytes()


@pytest.mark.parametrize(
    ("sha", "ref", "message"),
    [
        ("abc", "refs/heads/main", "40-character Git SHA"),
        (SHA, "refs/heads/feature", "refs/heads/main"),
    ],
)
def test_snapshot_rejects_noncanonical_sha_or_ref(
    tmp_path: Path,
    sha: str,
    ref: str,
    message: str,
) -> None:
    paths = _write_fixture(tmp_path)

    with pytest.raises(DependencySnapshotError, match=message):
        build_snapshot(
            sha=sha,
            ref=ref,
            scanned=SCANNED,
            **paths,
        )


def test_verification_spec_tracks_old_versions_as_stale(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    previous_product = tmp_path / "previous-product.lock"
    previous_product.write_text(paths["product_lock"].read_text(encoding="utf-8"), encoding="utf-8")
    previous_dev = tmp_path / "previous-dev.lock"
    previous_dev.write_text(
        "fastapi==0.141.1 \\\n"
        "httpcore2==2.10.0 \\\n"
        "httpx2==2.10.0 \\\n"
        "pip-audit==2.10.1 \\\n"
        "pytest==9.1.1 \\\n"
        "ruff==0.16.5 \\\n"
        "urllib3==2.7.0 \\\n"
        "virtualenv==21.7.0 \\\n",
        encoding="utf-8",
    )
    snapshot = build_snapshot(
        sha=SHA,
        ref="refs/heads/main",
        scanned=SCANNED,
        **paths,
    )
    snapshot_bytes = (
        json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode()

    verification = build_verification_spec(
        snapshot=snapshot,
        snapshot_bytes=snapshot_bytes,
        product_lock=paths["product_lock"],
        dev_lock=paths["dev_lock"],
        previous_product_lock=previous_product,
        previous_dev_lock=previous_dev,
    )

    assert "pkg:pypi/httpx2@2.10.0" in verification["stale_purls"]
    assert "pkg:pypi/urllib3@2.7.0" in verification["stale_purls"]
    assert "pkg:pypi/virtualenv@21.7.0" in verification["stale_purls"]
    assert "pkg:pypi/httpx2@2.12.0" in verification["expected_purls"]


def test_provider_verifier_accepts_expected_purls_and_rejects_stale_versions(
    tmp_path: Path,
) -> None:
    paths = _write_fixture(tmp_path)
    previous_dev = tmp_path / "previous-dev.lock"
    previous_dev.write_text(
        paths["dev_lock"]
        .read_text(encoding="utf-8")
        .replace("httpx2==2.12.0", "httpx2==2.10.0"),
        encoding="utf-8",
    )
    previous_product = tmp_path / "previous-product.lock"
    previous_product.write_text(paths["product_lock"].read_text(encoding="utf-8"), encoding="utf-8")
    snapshot = build_snapshot(
        sha=SHA,
        ref="refs/heads/main",
        scanned=SCANNED,
        **paths,
    )
    snapshot_bytes = (
        json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode()
    verification = build_verification_spec(
        snapshot=snapshot,
        snapshot_bytes=snapshot_bytes,
        product_lock=paths["product_lock"],
        dev_lock=paths["dev_lock"],
        previous_product_lock=previous_product,
        previous_dev_lock=previous_dev,
    )

    expected_packages = []
    for purl in verification["expected_purls"]:
        path = purl.removeprefix("pkg:pypi/")
        name, version = path.rsplit("@", 1)
        expected_packages.append({"name": name, "versionInfo": version})

    verify_sbom(
        verification=verification,
        sbom={"sbom": {"packages": expected_packages}},
    )

    with pytest.raises(DependencySnapshotError, match="stale dependency"):
        verify_sbom(
            verification=verification,
            sbom={
                "sbom": {
                    "packages": [
                        *expected_packages,
                        {"name": "httpx2", "versionInfo": "2.10.0"},
                    ]
                }
            },
        )


def test_provider_verifier_fails_closed_when_expected_dependency_is_missing(
    tmp_path: Path,
) -> None:
    paths = _write_fixture(tmp_path)
    snapshot = build_snapshot(
        sha=SHA,
        ref="refs/heads/main",
        scanned=SCANNED,
        **paths,
    )
    snapshot_bytes = (
        json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode()
    verification = build_verification_spec(
        snapshot=snapshot,
        snapshot_bytes=snapshot_bytes,
        product_lock=paths["product_lock"],
        dev_lock=paths["dev_lock"],
        previous_product_lock=None,
        previous_dev_lock=None,
    )

    with pytest.raises(DependencySnapshotError, match="missing expected"):
        verify_sbom(
            verification=verification,
            sbom={"sbom": {"packages": []}},
        )


def test_dependency_refresh_workflow_is_main_only_and_separates_write_authority() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "push:" in text
    assert "- main" in text
    assert "pull_request:" not in text
    assert "workflow_dispatch:" not in text
    assert "permissions: {}" in text
    assert "queue: max" in text
    assert "cancel-in-progress: false" in text
    assert "cancel-in-progress: true" not in text
    assert text.count("contents: write") == 1

    build = text.split("\n  build:", 1)[1].split("\n  submit:", 1)[0]
    submit = text.split("\n  submit:", 1)[1].split("\n  verify:", 1)[0]
    verify = text.split("\n  verify:", 1)[1]

    assert "contents: read" in build
    assert "contents: write" not in build
    assert "fetch-depth: 0" in build
    assert "git fetch" not in build
    assert "contents: write" in submit
    assert "actions/checkout@" not in submit
    assert "scripts/" not in submit
    assert "contents: read" in verify
    assert "contents: write" not in verify

    assert 'expected_ref != "refs/heads/main"' in text
    assert "current_main != expected_sha" in text
    assert submit.index("current_main != expected_sha") < submit.index('method="POST"')
    assert "voodoo-one-provider-reconciliation" in text
    assert "voodoo-one-dependency-reconciliation" in text
    assert 'repository != "eimyroot/Voodoo-One"' in submit
    assert submit.count("dependency-graph/snapshots") == 1
    assert submit.count('method="POST"') == 1
    assert "for attempt in 1 2 3 4 5 6" in text
    assert "verify-sbom" in text

    for forbidden in (
        "dependabot/alerts/",
        "dismiss",
        "release",
        "deploy",
        "production",
        "pull-requests: write",
        "actions: write",
        "packages: write",
    ):
        assert forbidden not in submit.lower()


def test_stale_version_is_not_rejected_when_another_current_manifest_still_requires_it(
    tmp_path: Path,
) -> None:
    paths = _write_fixture(tmp_path)
    paths["product_input"].write_text(
        "fastapi==0.141.1\n"
        "pydantic==2.13.4\n"
        "uvicorn[standard]==0.52.4\n",
        encoding="utf-8",
    )
    paths["product_lock"].write_text(
        "fastapi==0.141.1 \\\n"
        "pydantic==2.13.4 \\\n"
        "starlette==0.48.0 \\\n"
        "uvicorn==0.52.4 \\\n",
        encoding="utf-8",
    )
    paths["dev_lock"].write_text(
        paths["dev_lock"].read_text(encoding="utf-8")
        + "pydantic==2.13.5 \\\n",
        encoding="utf-8",
    )
    previous_product = tmp_path / "previous-product.lock"
    previous_product.write_text(paths["product_lock"].read_text(encoding="utf-8"), encoding="utf-8")
    previous_dev = tmp_path / "previous-dev.lock"
    previous_dev.write_text(
        paths["dev_lock"]
        .read_text(encoding="utf-8")
        .replace("pydantic==2.13.5", "pydantic==2.13.4"),
        encoding="utf-8",
    )

    snapshot = build_snapshot(
        sha=SHA,
        ref="refs/heads/main",
        scanned=SCANNED,
        **paths,
    )
    snapshot_bytes = (
        json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode()
    verification = build_verification_spec(
        snapshot=snapshot,
        snapshot_bytes=snapshot_bytes,
        product_lock=paths["product_lock"],
        dev_lock=paths["dev_lock"],
        previous_product_lock=previous_product,
        previous_dev_lock=previous_dev,
    )

    assert "pkg:pypi/pydantic@2.13.4" in verification["expected_purls"]
    assert "pkg:pypi/pydantic@2.13.4" not in verification["stale_purls"]
