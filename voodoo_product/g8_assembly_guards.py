from __future__ import annotations

from typing import NamedTuple

from .g8_credential_pins import (
    _CredentialPin,
    _CredentialSourceImplementationPin,
    _G8IndependentCredentialPairTransport,
    _ProviderReadEffectPin,
)
from .permission_authority import DatabasePermissionAuthority
from .trusted_clock import TrustedClockAuthority


class _G8AssemblyAnchors(NamedTuple):
    """Immutable assembly-time roots that execution must never reconstruct."""

    canonical_db: object
    runner_clock: TrustedClockAuthority
    runner_source: object
    verifier_source: object
    runner_pin: _CredentialPin
    verifier_pin: _CredentialPin
    source_implementation_pin: _CredentialSourceImplementationPin
    provider_effect_pin: _ProviderReadEffectPin


class _G8ResumeAssemblyBinding(NamedTuple):
    snapshot_store: object
    permission_authority: DatabasePermissionAuthority
    terminal_profile_registry: object
    envelope_revision: str


def _assert_g8_transport_matches_assembly(
    transport: object,
    *,
    role: str,
    anchors: _G8AssemblyAnchors,
) -> _G8IndependentCredentialPairTransport:
    """Require current transport parity *and* independent assembly-time provenance."""

    if type(anchors) is not _G8AssemblyAnchors:
        raise PermissionError("G8 assembly anchors are invalid")
    if type(transport) is not _G8IndependentCredentialPairTransport:
        raise PermissionError(f"G8 {role.title()} handler transport is not canonical")
    if transport.role != role:
        raise PermissionError(f"G8 {role.title()} handler credential role mismatch")
    if transport.runner_transport is not anchors.runner_source:
        raise PermissionError("G8 Runner credential source is not assembly-bound")
    if transport.verifier_transport is not anchors.verifier_source:
        raise PermissionError("G8 Verifier credential source is not assembly-bound")
    if transport.runner_pin != anchors.runner_pin:
        raise PermissionError("G8 Runner credential pin is not assembly-bound")
    if transport.verifier_pin != anchors.verifier_pin:
        raise PermissionError("G8 Verifier credential pin is not assembly-bound")
    if transport.source_implementation_pin != anchors.source_implementation_pin:
        raise PermissionError("G8 credential source implementation is not assembly-bound")
    if transport.provider_effect_pin != anchors.provider_effect_pin:
        raise PermissionError("G8 provider READ effect is not assembly-bound")
    return transport
