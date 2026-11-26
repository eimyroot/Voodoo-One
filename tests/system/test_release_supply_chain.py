from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.validate_release_candidate import main, validate_release_candidate_version
from voodoo_product.version import RELEASE_CANDIDATE_VERSION, __version__

ROOT = Path(__file__).resolve().parents[2]


def test_release_candidate_version_is_derived_from_development_version() -> None:
    assert __version__ == "0.9.0-rc2-dev"
    assert __version__.removesuffix("-dev") == RELEASE_CANDIDATE_VERSION
    assert validate_release_candidate_version(RELEASE_CANDIDATE_VERSION) == "0.9.0-rc2"


@pytest.mark.parametrize(
    "candidate",
    [
        "0.9.0",
        "v0.9.0-rc2",
        "0.9.0-rc02",
        "0.9.0-rc3",
        "0.9.0-rc2/../../artifact",
        "0.9.0-rc2\nforged-log-entry",
    ],
)
def test_release_candidate_version_rejects_noncanonical_or_unbound_values(
    candidate: str,
) -> None:
    with pytest.raises(ValueError):
        validate_release_candidate_version(candidate)


def test_release_candidate_cli_does_not_echo_rejected_input(capsys: pytest.CaptureFixture[str]) -> None:
    forged = "0.9.0-rc2\nforged-log-entry"

    assert main([forged]) == 2

    captured = capsys.readouterr()
    assert forged not in captured.err
    assert "release candidate rejected" in captured.err


def test_product_image_smoke_uses_running_container_python_for_health_payload() -> None:
    script = (ROOT / "scripts/smoke_product_image.sh").read_text(encoding="utf-8")

    assert 'docker exec --interactive "$container" python -c' in script
    assert "\n  python -c " not in script


def test_product_image_smoke_script_has_valid_bash_syntax() -> None:
    result = subprocess.run(
        ["bash", "-n", "scripts/smoke_product_image.sh"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_product_image_smoke_script_rejects_option_like_image_before_docker() -> None:
    result = subprocess.run(
        ["bash", "scripts/smoke_product_image.sh", "--privileged", "test-run"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2
    assert "safe identifier characters" in result.stderr


def test_ci_and_release_candidate_share_the_hardened_image_smoke_gate() -> None:
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    release = (ROOT / ".github/workflows/release-candidate.yml").read_text(encoding="utf-8")

    assert "bash scripts/smoke_product_image.sh" in ci
    assert "bash scripts/smoke_product_image.sh" in release
    checkout = "actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7"
    setup_python = "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1 # v6"
    upload = "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7"
    final_sums = (
        'sha256sum "v-one-${RC_VERSION}.tar.gz" sbom.cdx.json '
        "g0-governance-evidence.json > SHA256SUMS.txt"
    )
    assert checkout in ci
    assert checkout in release
    assert setup_python in ci
    assert setup_python in release
    assert upload in release
    assert "github.ref == 'refs/heads/main'" in release
    assert 'VOODOO_ALLOW_PRODUCTION_EFFECTS: "false"' in release
    assert release.index("Validate release candidate version") < release.index("docker build")
    assert release.index("-o dist/sbom.cdx.json") < release.index(final_sums)
    assert "sha256sum --check SHA256SUMS.txt" in release


def test_release_candidate_is_fail_closed_on_live_g0_governance() -> None:
    release = (ROOT / ".github/workflows/release-candidate.yml").read_text(encoding="utf-8")

    assert "Verify G0 main governance" in release
    assert "VONE_GITHUB_GOVERNANCE_TOKEN" in release
    assert "scripts/verify_github_main_governance.py" in release
    assert "--token-env VONE_GITHUB_GOVERNANCE_TOKEN" in release
    assert '--expected-source-sha "${GITHUB_SHA}"' in release
    assert "--output g0-governance-evidence.json" in release
    assert release.index("Verify G0 main governance") < release.index(
        "Validate release candidate version"
    )
    assert release.index("Verify G0 main governance") < release.index("docker build")
    assert "cp g0-governance-evidence.json dist/" in release
    assert (
        'sha256sum "v-one-${RC_VERSION}.tar.gz" sbom.cdx.json '
        "g0-governance-evidence.json > SHA256SUMS.txt"
    ) in release


def test_product_readiness_retains_g0_governance_evidence_surface() -> None:
    required_g0_artifacts = (
        ".github/governance/main-branch-baseline.v1.json",
        ".github/workflows/g0-governance-verify.yml",
        "docs/governance/GITHUB_MAIN_GOVERNANCE_BASELINE_V1.md",
        "scripts/verify_github_main_governance.py",
        "tests/system/test_github_main_governance_verifier.py",
    )

    missing = [path for path in required_g0_artifacts if not (ROOT / path).is_file()]
    assert missing == []

    readiness = (ROOT / "scripts/product_readiness_gate.py").read_text(encoding="utf-8")
    assert '"tests/system/test_release_supply_chain.py"' in readiness
    assert '"voodoo_product/static/workflow_boards.js"' in readiness
    assert '"voodoo_product/static/workflow_boards.css"' in readiness
    assert '"tests/system/test_workflow_boards_render.cjs"' in readiness


def test_ci_and_release_gate_run_workflow_console_static_safety() -> None:
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    release = (ROOT / ".github/workflows/release-candidate.yml").read_text(encoding="utf-8")
    for source in (ci, release):
        assert "node --check voodoo_product/static/workflow_boards.js" in source
        assert "node tests/system/test_workflow_boards_render.cjs" in source


def test_ci_and_release_candidate_execute_operator_canonical_read_contract() -> None:
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    release = (ROOT / ".github/workflows/release-candidate.yml").read_text(encoding="utf-8")
    readiness = (ROOT / "scripts/product_readiness_gate.py").read_text(encoding="utf-8")

    for workflow in (ci, release):
        assert "node --check tests/system/test_operator_canonical_read.cjs" in workflow
        assert "node tests/system/test_operator_canonical_read.cjs" in workflow
    assert readiness.count('"tests/system/test_operator_canonical_read.cjs"') == 2



def test_readiness_subprocess_progress_preserves_report_and_failure(monkeypatch, capsys):
    import json
    import sys

    from scripts import product_readiness_gate as gate

    monkeypatch.setattr(gate, "PROGRESS_INTERVAL_SECONDS", 0.05)
    result = gate.run([
        sys.executable, "-c",
        "import time,sys; print('synthetic-output',flush=True); time.sleep(.35); "
        "print('synthetic-error',file=sys.stderr); sys.exit(7)",
    ], stage="synthetic_test")
    captured = capsys.readouterr()
    assert captured.out == ""
    events = [json.loads(line) for line in captured.err.splitlines()]
    assert all(event["stage"] == "synthetic_test" for event in events)
    assert events[0]["state"] == "START"
    assert any(event["state"] == "RUNNING" for event in events)
    assert events[-1]["state"] == "FAIL"
    assert events[-1]["returncode"] == 7
    assert result["returncode"] == 7
    assert result["stdout"] == "synthetic-output\n"
    assert result["stderr"] == "synthetic-error\n"
    assert "synthetic-output" not in captured.err
    assert "synthetic-error" not in captured.err


def test_readiness_subprocess_success_has_distinct_terminal_event(capsys):
    import json
    import sys

    from scripts import product_readiness_gate as gate

    result = gate.run([sys.executable, "-c", "print('ok')"], stage="synthetic_success")
    captured = capsys.readouterr()
    assert captured.out == ""
    events = [json.loads(line) for line in captured.err.splitlines()]
    assert events[0]["state"] == "START"
    assert events[-1]["state"] == "PASS"
    assert result["returncode"] == 0
    assert result["stdout"].strip() == "ok"


def _casebook_adoption_fixture(tmp_path: Path, monkeypatch):
    import hashlib

    from scripts import product_readiness_gate as gate

    records = []
    fence = chr(96) * 3
    for name in gate.CASEBOOK_ADOPTION_DOCUMENTS:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Synthetic proposed ADR: " + name, encoding="utf-8")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        records.append(
            f"{fence}text\nDOCUMENT: {name}\nEFFECTIVE_STATUS: ADOPTED\n"
            f"OWNER: project owner VOODOO — ENGINEERING\n"
            f"ADOPTION_METHOD: explicit owner decision (synthetic fixture)\nADOPTION_DATE: 2026-11-26\n"
            f"ADOPTED_CONTENT_COMMIT: {'a' * 40}\nCONTENT_SHA256: {digest}\n{fence}\n"
        )
    register = tmp_path / gate.ADOPTION_REGISTER
    register.parent.mkdir(parents=True, exist_ok=True)
    register.write_text("\n".join(records), encoding="utf-8")
    monkeypatch.setattr(
        gate, "adopted_content_commit_matches", lambda root, document, commit, digest: commit == "a" * 40,
    )
    return gate, register, records


def test_casebook_candidate_readiness_is_not_release_authority(tmp_path: Path, monkeypatch) -> None:
    gate, register, records = _casebook_adoption_fixture(tmp_path, monkeypatch)
    adoption = gate.casebook_adoption_check(tmp_path)
    assert adoption["ok"] is True
    assert all(item["reason"] == "EXACT_CONTENT_REGISTER_RECORD_MATCH" for item in adoption["documents"])
    report = gate.readiness_report({"synthetic": {"ok": True}}, True, adoption)
    assert report["scope"] == "TECHNICAL_CANDIDATE_READINESS_ONLY"
    assert report["release_admission"] == "OTHER_GATES_REQUIRED"
    assert report["release_authorized"] is False
    assert report["runtime_activation_authorized"] is False
    register.write_text(records[0], encoding="utf-8")
    blocked = gate.casebook_adoption_check(tmp_path)
    assert blocked["ok"] is False
    report = gate.readiness_report({"synthetic": {"ok": True}}, True, blocked)
    assert report["passed"] is True  # technical result is not adoption
    assert report["release_admission"] == "BLOCKED_CASEBOOK_ADOPTION"
    assert report["release_authorized"] is False


@pytest.mark.parametrize("fault", [
    "missing", "duplicate", "wrong_hash", "proposed", "malformed_commit",
    "duplicate_field", "wrong_owner", "missing_adr", "missing_method", "wrong_commit",
])
def test_casebook_adoption_fails_closed(tmp_path: Path, fault: str, monkeypatch) -> None:
    gate, register, records = _casebook_adoption_fixture(tmp_path, monkeypatch)
    text = "\n".join(records)
    if fault == "missing":
        register.unlink()
    elif fault == "duplicate":
        register.write_text("\n".join(records + [records[0]]), encoding="utf-8")
    elif fault == "wrong_hash":
        (tmp_path / gate.CASEBOOK_ADOPTION_DOCUMENTS[0]).write_text("changed", encoding="utf-8")
    elif fault == "proposed":
        register.write_text(text.replace("EFFECTIVE_STATUS: ADOPTED", "EFFECTIVE_STATUS: PROPOSED"), encoding="utf-8")
    elif fault == "malformed_commit":
        register.write_text(text.replace("a" * 40, "unknown"), encoding="utf-8")
    elif fault == "duplicate_field":
        register.write_text(text.replace("EFFECTIVE_STATUS: ADOPTED", "EFFECTIVE_STATUS: PROPOSED\nEFFECTIVE_STATUS: ADOPTED"), encoding="utf-8")
    elif fault == "wrong_owner":
        register.write_text(text.replace("project owner VOODOO — ENGINEERING", "unrelated actor"), encoding="utf-8")
    elif fault == "wrong_commit":
        register.write_text(text.replace("a" * 40, "b" * 40), encoding="utf-8")
    elif fault == "missing_adr":
        (tmp_path / gate.CASEBOOK_ADOPTION_DOCUMENTS[0]).unlink()
    else:
        register.write_text(text.replace("ADOPTION_METHOD: explicit owner decision (synthetic fixture)", "ADOPTION_METHOD: "), encoding="utf-8")
    assert gate.casebook_adoption_check(tmp_path)["ok"] is False


def test_release_mode_blocks_before_full_tests_on_missing_casebook_adoption(tmp_path, monkeypatch, capsys):
    import json

    gate, register, _ = _casebook_adoption_fixture(tmp_path, monkeypatch)
    register.unlink()
    monkeypatch.setattr(gate, "ROOT", tmp_path)

    def unexpected_run(*args, **kwargs):
        pytest.fail("release adoption must fail before subprocess verification")

    monkeypatch.setattr(gate, "run", unexpected_run)
    assert gate.main(["--require-casebook-adoption"]) == 1
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert report["passed"] is False
    assert report["checks"] == {}
    assert report["release_admission"] == "BLOCKED_CASEBOOK_ADOPTION"
    assert report["runtime_activation_authorized"] is False
    assert "python scripts/product_readiness_gate.py --require-casebook-adoption" in (
        ROOT / ".github/workflows/release-candidate.yml"
    ).read_text(encoding="utf-8")


def test_adopted_content_commit_matches_actual_git_bytes(tmp_path: Path) -> None:
    import hashlib

    from scripts import product_readiness_gate as gate

    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=tmp_path, check=True, capture_output=True,
        ).stdout.decode().strip()

    git("init", "--quiet", "--template=")
    document = gate.CASEBOOK_ADOPTION_DOCUMENTS[0]
    path = tmp_path / document
    path.parent.mkdir(parents=True)
    path.write_bytes(b"exact synthetic decision bytes")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    git("add", "--", document)
    git(
        "-c", "user.name=Adoption Test", "-c", "user.email=adoption@example.invalid",
        "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null",
        "commit", "--quiet", "-m", "synthetic content candidate",
    )
    commit = git("rev-parse", "HEAD")
    assert gate.adopted_content_commit_matches(tmp_path, document, commit, digest)
    assert not gate.adopted_content_commit_matches(tmp_path, document, "0" * 40, digest)
    path.write_bytes(b"changed synthetic decision bytes")
    drift = hashlib.sha256(path.read_bytes()).hexdigest()
    assert not gate.adopted_content_commit_matches(tmp_path, document, commit, drift)
