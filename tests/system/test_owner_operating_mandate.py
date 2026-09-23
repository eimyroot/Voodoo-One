from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANDATE = ROOT / "docs/governance/OWNER_OPERATING_MANDATE.md"
REGISTER = ROOT / "docs/governance/AUTHORITY_AND_ADOPTION_REGISTER.md"
AGENTS = ROOT / "AGENTS.md"
INDEX = ROOT / "docs/README.md"

WORKSTREAM_STATES = {
    "PRIMARY",
    "PARALLEL_SAFE",
    "DEPENDENT",
    "PAUSED",
    "SUPERSEDED",
    "BLOCKED",
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    return " ".join(text.split())


def test_rook_is_the_named_delegated_operator() -> None:
    mandate = _read(MANDATE)
    assert "delegated role is named `VOODOO_SUBADMIN`" in mandate
    assert "**Rook** (`ROOK`)" in mandate
    assert "expand its own authority" in mandate
    normalized = _normalized(mandate)
    assert "This mandate never converts `DENY` into `ALLOW`" in normalized
    assert "expose secret or credential material" in mandate


def test_agents_requires_mandate_and_cross_workstream_preflight() -> None:
    agents = _read(AGENTS)
    assert "docs/governance/OWNER_OPERATING_MANDATE.md" in agents
    assert "/Users/eimyna/0_EVIDENCE/Voodoo-One/WORKSTREAM_COORDINATION/CURRENT.md" in agents
    for state in WORKSTREAM_STATES:
        assert f"`{state}`" in agents
    assert "affected chat" in agents


def test_mandate_defines_exact_workstream_state_machine() -> None:
    mandate = _read(MANDATE)
    defined = {
        match.group(1)
        for match in re.finditer(
            r"^(PRIMARY|PARALLEL_SAFE|DEPENDENT|PAUSED|SUPERSEDED|BLOCKED)\s+=",
            mandate,
            re.MULTILINE,
        )
    }
    assert defined == WORKSTREAM_STATES
    assert "A chat must never assume that it is `PRIMARY`" in mandate
    assert "only one may remain `PRIMARY`" in mandate
    normalized = _normalized(mandate)
    assert "must state that classification and reason in every affected active chat" in normalized


def test_mandate_preserves_product_and_architecture_direction() -> None:
    mandate = _read(MANDATE)
    for invariant in (
        "ONE CANONICAL OPERATION LANGUAGE",
        "ONE SMALL PROVIDER-NEUTRAL TRUST / AUTHORITY KERNEL",
        "MONOTONIC AUTHORITY",
        "FRACTAL CAPABILITY-CELL CONTRACTS",
        "PROVIDER MODULES OUTSIDE THE KERNEL",
        "PROFILE-CORRECT ISOLATED EXECUTION",
        "INDEPENDENT POST-STATE VERIFICATION",
        "RECONSTRUCTABLE EVIDENCE",
    ):
        assert invariant in mandate
    normalized = _normalized(mandate)
    assert 'Adoption means "current best governed direction", not "never improve this".' in normalized
    assert "challenge the current target and drive the superior design" in normalized
    assert "ADR" in mandate and "rollback" in mandate


def test_effect_eligibility_does_not_self_authorize_protected_effects() -> None:
    mandate = _read(MANDATE)
    assert "only when" in mandate
    assert "active higher-priority policy" in mandate
    assert "This mandate never converts `DENY` into `ALLOW`" in _normalized(mandate)
    for effect in ("merge", "release", "deployment", "provider mutation / WRITE", "production effects"):
        assert effect in mandate


def test_documentation_index_exposes_owner_mandate() -> None:
    index = _read(INDEX)
    assert "governance/OWNER_OPERATING_MANDATE.md" in index


def test_latest_owner_mandate_adoption_binds_current_bytes() -> None:
    mandate_sha = hashlib.sha256(MANDATE.read_bytes()).hexdigest()
    register = _read(REGISTER)
    marker = "VOODOO_SUBADMIN Rook identity / mandate refresh"
    assert marker in register
    latest = register.rsplit(marker, 1)[1]
    assert f"CONTENT_SHA256: {mandate_sha}" in latest
    assert "DELEGATED_OPERATOR_NAME: ROOK" in latest
    assert "EFFECTIVE_STATUS: ADOPTED / STANDING OWNER MANDATE" in latest
    assert "SUPERSEDES_CONTENT_IDENTITY:" in latest
