from __future__ import annotations

import secrets
from collections.abc import Callable
from dataclasses import dataclass
from typing import NamedTuple


@dataclass(frozen=True, slots=True)
class _CredentialBinding:
    token: str
    token_fingerprint: str
    credential_class: str
    attested_principal: str


class _CredentialPin(NamedTuple):
    token_fingerprint: str
    credential_class: str
    attested_principal: str


class _ProviderReadEffectPin(NamedTuple):
    transport_type: type
    init_method: Callable[..., None]
    read_ref_method: Callable[..., str]
    source_identity: str


class _CredentialSourceImplementationPin(NamedTuple):
    transport_type: type
    pin_snapshot_method: Callable[..., _CredentialPin]
    read_ref_with_pin_method: Callable[..., str]


class _G8IndependentCredentialPairTransport(NamedTuple):
    """Immutable use-time guard over both independently pinned credential sources."""

    runner_transport: object
    verifier_transport: object
    role: str
    runner_pin: _CredentialPin
    verifier_pin: _CredentialPin
    source_implementation_pin: _CredentialSourceImplementationPin
    provider_effect_pin: _ProviderReadEffectPin

    @property
    def source_identity(self) -> str:
        return self.provider_effect_pin.source_identity

    def read_ref(self, *, repository: str, ref: str) -> str:
        runner_transport = self.runner_transport
        verifier_transport = self.verifier_transport
        source_implementation_pin = self.source_implementation_pin
        provider_effect_pin = self.provider_effect_pin
        if type(source_implementation_pin) is not _CredentialSourceImplementationPin:
            raise PermissionError("G8 credential source implementation pin is invalid")
        if type(provider_effect_pin) is not _ProviderReadEffectPin:
            raise PermissionError("G8 provider effect pin is invalid")
        if type(runner_transport) is not source_implementation_pin.transport_type:
            raise PermissionError("G8 Runner credential source type changed")
        if type(verifier_transport) is not source_implementation_pin.transport_type:
            raise PermissionError("G8 Verifier credential source type changed")
        if self.role not in {"runner", "verifier"}:
            raise PermissionError("G8 credential pair role is invalid")

        runner_now = source_implementation_pin.pin_snapshot_method(runner_transport)
        verifier_now = source_implementation_pin.pin_snapshot_method(verifier_transport)
        if runner_now != self.runner_pin:
            raise PermissionError("G8 Runner credential changed after runtime pinning")
        if verifier_now != self.verifier_pin:
            raise PermissionError("G8 Verifier credential changed after runtime pinning")
        if secrets.compare_digest(
            runner_now.token_fingerprint,
            verifier_now.token_fingerprint,
        ):
            raise PermissionError("G8 Runner and Verifier credential material collapsed")
        if runner_now.attested_principal == verifier_now.attested_principal:
            raise PermissionError("G8 Runner and Verifier provider principals collapsed")
        if runner_now.credential_class == verifier_now.credential_class:
            raise PermissionError("G8 Runner and Verifier credential classes collapsed")

        if self.role == "runner":
            return source_implementation_pin.read_ref_with_pin_method(
                runner_transport,
                pin=self.runner_pin,
                provider_effect_pin=provider_effect_pin,
                repository=repository,
                ref=ref,
            )
        return source_implementation_pin.read_ref_with_pin_method(
            verifier_transport,
            pin=self.verifier_pin,
            provider_effect_pin=provider_effect_pin,
            repository=repository,
            ref=ref,
        )


def _assert_pair_transport_parity(
    runner_transport: object,
    verifier_transport: object,
) -> tuple[_G8IndependentCredentialPairTransport, _G8IndependentCredentialPairTransport]:
    if type(runner_transport) is not _G8IndependentCredentialPairTransport:
        raise PermissionError("G8 Runner handler transport is not canonical")
    if type(verifier_transport) is not _G8IndependentCredentialPairTransport:
        raise PermissionError("G8 Verifier handler transport is not canonical")
    if runner_transport.role != "runner":
        raise PermissionError("G8 Runner handler credential role mismatch")
    if verifier_transport.role != "verifier":
        raise PermissionError("G8 Verifier handler credential role mismatch")
    if runner_transport.runner_transport is not verifier_transport.runner_transport:
        raise PermissionError("G8 credential-pair Runner source mismatch")
    if runner_transport.verifier_transport is not verifier_transport.verifier_transport:
        raise PermissionError("G8 credential-pair Verifier source mismatch")
    if runner_transport.runner_pin != verifier_transport.runner_pin:
        raise PermissionError("G8 credential-pair Runner pin mismatch")
    if runner_transport.verifier_pin != verifier_transport.verifier_pin:
        raise PermissionError("G8 credential-pair Verifier pin mismatch")
    if runner_transport.source_implementation_pin != verifier_transport.source_implementation_pin:
        raise PermissionError("G8 credential-pair source implementation mismatch")
    if runner_transport.provider_effect_pin != verifier_transport.provider_effect_pin:
        raise PermissionError("G8 credential-pair provider effect mismatch")
    return runner_transport, verifier_transport
