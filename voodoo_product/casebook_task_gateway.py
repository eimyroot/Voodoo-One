"""Opt-in, read-only CASEBOOK task detail gateway for V-One's existing console.

This does NOT import CASEBOOK as a global product dependency or automatically
register a reader. A reviewed, pinned CASEBOOK source and an explicit native
ProductComposition-owned attachment are required before any local/test read.

Session->workspace binding is server-owned. Nothing in a browser-provided
session ID can choose an evidence data root, project, or workspace.
"""
from __future__ import annotations

import re
import sqlite3
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI

if TYPE_CHECKING:
    from .composition import ProductComposition

from .permission_authority import DatabasePermissionAuthority, PermissionQuery
from .security import Principal

SESSION = re.compile(r"[A-Za-z0-9_-]{5,128}\Z")
SCHEMA = "voodoo-casebook/task-view/v1"
INTEGRITY = "LOCAL_HASH_CHAIN_VERIFIED_ONLY"
STATES = frozenset(
    {"GOAL_RECORDED", "HANDOFF_RECORDED_UNVERIFIED", "RESULT_RECORDED_UNVERIFIED"}
)
JOURNAL_TYPES = frozenset({
    "GOAL", "CONTEXT", "IDEA", "DECISION", "ISSUE", "TODO",
    "COMMAND_PLAN", "COMMAND_RESULT", "EVIDENCE", "LINK", "BLOCKER",
    "RISK", "LEARNING", "RESULT", "CANONICAL_CANDIDATE",
})
JOURNAL_STATUSES = frozenset({"OPEN", "RESOLVED", "SUPERSEDED", "CANDIDATE"})
JOURNAL_SOURCES = frozenset({"user", "assistant", "tool", "system"})
NEXT_ACTIONS = {
    "GOAL_RECORDED": "PREPARE_AND_AUTHORIZE_CASER_HANDOFF",
    "HANDOFF_RECORDED_UNVERIFIED": "AUTHORIZE_AND_EXECUTE_THROUGH_VOODOO_ONE",
    "RESULT_RECORDED_UNVERIFIED": "VERIFY_NATIVE_APPROVAL_EXECUTION_AND_INDEPENDENT_RESULT",
}
NON_ATTESTED = "NOT_ATTESTED"


class CasebookTaskAccessDenied(PermissionError):
    """The request is not bound to an authorized CASEBOOK scope."""


class CasebookTaskUnavailable(RuntimeError):
    """The attached CASEBOOK evidence could not be read or authenticated."""


@dataclass(frozen=True, slots=True)
class TaskScope:
    session_id: str
    workspace_id: str
    environment: str
    project: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.session_id, str)
            or not SESSION.fullmatch(self.session_id)
            or not isinstance(self.workspace_id, str)
            or not 5 <= len(self.workspace_id) <= 128
            or not isinstance(self.project, str)
            or not 1 <= len(self.project) <= 120
            or not isinstance(self.environment, str)
            or self.environment not in {"local", "development", "staging"}
        ):
            raise ValueError("CASEBOOK task scope is invalid")


@dataclass(frozen=True, slots=True)
class CasebookTaskGateway:
    """Single secured projection over exact pre-bound CASEBOOK sessions."""

    composition: ProductComposition
    scopes: tuple[TaskScope, ...]
    reader: Callable[[str], dict[str, Any]]
    passport_correlation_enabled: bool = False
    _bound: Mapping[str, TaskScope] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        from .composition import ProductComposition

        if not isinstance(self.composition, ProductComposition):
            raise ValueError("CASEBOOK requires the canonical ProductComposition")
        if self.composition.service.config.environment not in {"local", "test"}:
            raise CasebookTaskAccessDenied("CASEBOOK task pane is local/test only")
        if not callable(self.reader):
            raise ValueError("CASEBOOK reader must be an explicit callable")
        if self.composition.service.config.environment == "local":
            # Test fixtures may inject synthetic projections; a real local
            # ProductComposition must only attach an exact source-pinned
            # reader with its data root under the private evidence shelf.
            from .casebook_pinned_task_reader import (
                EVIDENCE_SHELF,
                PinnedCasebookTaskReader,
            )
            if (
                not isinstance(self.reader, PinnedCasebookTaskReader)
                or EVIDENCE_SHELF not in self.reader.data_root.parents
            ):
                raise CasebookTaskAccessDenied(
                    "local CASEBOOK runtime requires a source-pinned evidence reader"
                )
        if type(self.passport_correlation_enabled) is not bool:
            raise ValueError("CASEBOOK correlation opt-in must be explicit")
        if self.passport_correlation_enabled:
            from .casebook_pinned_task_reader import PinnedCasebookTaskReader

            if not isinstance(self.reader, PinnedCasebookTaskReader):
                raise CasebookTaskAccessDenied("correlation requires pinned CASEBOOK source")
            if self.composition.service.config.database_backend != "sqlite":
                raise CasebookTaskAccessDenied("correlation requires native SQLite")
        if not isinstance(self.scopes, tuple) or not self.scopes:
            raise ValueError("at least one explicit task scope is required")
        if any(not isinstance(item, TaskScope) for item in self.scopes):
            raise ValueError("CASEBOOK task scopes must be typed")
        if len({item.session_id for item in self.scopes}) != len(self.scopes):
            raise ValueError("duplicate CASEBOOK task session binding")
        db = self.composition.service.db
        authority = self.composition.database_permission_authority
        if (
            not isinstance(authority, DatabasePermissionAuthority)
            or authority.db is not db
        ):
            raise ValueError("CASEBOOK must use native DB permission authority")
        # Bind immutable session IDs to precise operator-selected workspaces.
        object.__setattr__(
            self, "_bound",
            MappingProxyType({scope.session_id: scope for scope in self.scopes}),
        )

    @staticmethod
    def _require_principal(principal: Principal) -> None:
        if not isinstance(principal, Principal):
            raise CasebookTaskAccessDenied("native authenticated principal required")
        if not principal.can("evidence.read"):
            raise CasebookTaskAccessDenied("evidence.read required")

    def list_bound(self, *, principal: Principal) -> dict[str, Any]:
        """Discover only explicitly bound sessions with current native authority.

        A binding is not proof that its journal is readable or that a run exists.
        Never query the private reader, filesystem or journal for discovery.
        """
        self._require_principal(principal)
        items: list[dict[str, str]] = []
        for scope in sorted(self._bound.values(), key=lambda item: item.session_id):
            try:
                allowed = self._scope_authorized(principal, scope)
            except (ValueError, LookupError, RuntimeError, sqlite3.Error) as exc:
                raise CasebookTaskUnavailable("CASEBOOK scope authority unavailable") from exc
            if not allowed:
                continue
            items.append({
                "session_id": scope.session_id,
                "workspace_id": scope.workspace_id,
                "environment": scope.environment,
                "project": scope.project,
            })
            if len(items) == 51:
                break
        return {
            "schema": "voodoo-casebook/bound-task-index/v1",
            "items": items[:50],
            "has_more": len(items) > 50,
            "journal_integrity": "NOT_CHECKED_BY_INDEX",
        }

    def _scope_authorized(
        self, principal: Principal, scope: TaskScope, *, permission: str = "evidence.read",
    ) -> bool:
        query = PermissionQuery(
            actor_id=principal.user_id,
            workspace_id=scope.workspace_id,
            environment=scope.environment,
            permission=permission,
        )
        decision = self.composition.database_permission_authority.decide(query)
        return (
            decision.granted is True
            and decision.actor_id == principal.user_id
            and decision.workspace_id == scope.workspace_id
            and decision.environment == scope.environment
            and decision.permission == permission
        )

    def read(self, *, principal: Principal, session_id: str) -> dict[str, Any]:
        self._require_principal(principal)
        if not isinstance(session_id, str) or SESSION.fullmatch(session_id) is None:
            raise LookupError("CASEBOOK task not found")
        # Do not reveal whether an unknown session lives in another workspace.
        scope = self._bound.get(session_id)
        if scope is None:
            raise LookupError("CASEBOOK task not found")
        try:
            allowed = self._scope_authorized(principal, scope)
        except (ValueError, LookupError, RuntimeError, sqlite3.Error) as exc:
            raise CasebookTaskAccessDenied("current workspace permission unavailable") from exc
        if not allowed:
            raise CasebookTaskAccessDenied("current workspace evidence.read denied")

        try:
            projection = self.reader(session_id)
        except (ValueError, LookupError, OSError, PermissionError, RuntimeError, sqlite3.Error) as exc:
            # The reader may contain private paths, SQLite errors or user text.
            # Do not reflect any such messages into HTTP errors.
            raise CasebookTaskUnavailable("CASEBOOK evidence is unavailable") from exc
        result = _validate_projection(projection, scope)
        result["passport_correlation_available"] = self.passport_correlation_enabled
        return result

    def correlate_passport(
        self, *, principal: Principal, session_id: str, execution_id: str,
    ) -> dict[str, Any]:
        """Explicitly attached, read-only correlation; never an execution route."""
        from .casebook_handoff_verifier import (
            CasebookHandoffRejected,
            correlate_casebook_passport,
            verify_casebook_handoff,
        )
        from .casebook_pinned_task_reader import PinnedCasebookTaskReader

        self._require_principal(principal)
        if not principal.can("read"):
            raise CasebookTaskAccessDenied("read required")
        if not self.passport_correlation_enabled or not isinstance(
            self.reader, PinnedCasebookTaskReader,
        ):
            raise CasebookTaskUnavailable("CASEBOOK correlation is not configured")
        if not isinstance(execution_id, str) or not re.fullmatch(
            r"[A-Za-z0-9._:-]{5,80}", execution_id,
        ):
            raise LookupError("CASEBOOK correlation not found")
        task = self.read(principal=principal, session_id=session_id)
        scope = self._bound[session_id]
        try:
            if not self._scope_authorized(principal, scope, permission="read"):
                raise CasebookTaskAccessDenied("current workspace read denied")
            service = self.composition.operation_passport_service
            if service.db is not self.composition.service.db:
                raise CasebookTaskUnavailable("native Passport owner mismatch")
            passport = service.get(execution_id)
            if (
                passport.operation.get("workspace_id") != scope.workspace_id
                or passport.operation.get("environment") != scope.environment
            ):
                raise LookupError("CASEBOOK correlation not found")
            handoff = verify_casebook_handoff(
                vone_database=self.composition.service.config.database_path,
                casebook_database=self.reader.data_root / "casebook.sqlite3",
                execution_id=execution_id,
                workspace_id=scope.workspace_id,
                session_id=session_id,
            )
            correlation = correlate_casebook_passport(handoff=handoff, passport=passport)
            # A structural event must also belong to the independently validated,
            # exact session/project view. Never infer a binding from prose.
            if not any(
                event["event_hash"] == handoff.casebook_event_hash
                and event["type"] == "CONTEXT"
                for event in task["timeline"]
            ):
                raise CasebookTaskUnavailable("CASEBOOK event not in selected session")
            # Refresh native authorization and pinned journal integrity before disclosure.
            refreshed = self.read(principal=principal, session_id=session_id)
            if (
                not self._scope_authorized(principal, scope, permission="read")
                or not any(
                    event["event_hash"] == handoff.casebook_event_hash
                    and event["type"] == "CONTEXT"
                    for event in refreshed["timeline"]
                )
            ):
                raise CasebookTaskAccessDenied("CASEBOOK scope changed")
            return {
                **correlation,
                "passport": passport.to_dict(),
            }
        except (CasebookTaskAccessDenied, CasebookTaskUnavailable, LookupError):
            raise
        except (CasebookHandoffRejected, ValueError, OSError, sqlite3.Error, RuntimeError) as exc:
            raise CasebookTaskUnavailable("CASEBOOK correlation unavailable") from exc


def _validate_projection(value: object, scope: TaskScope) -> dict[str, Any]:
    """Never trust reader metadata as independently attested execution proof."""
    if not isinstance(value, dict):
        raise CasebookTaskUnavailable("CASEBOOK projection is invalid")
    if (
        value.get("schema") != SCHEMA
        or value.get("session_id") != scope.session_id
        or value.get("project") != scope.project
        or value.get("journal_integrity") != INTEGRITY
        or type(value.get("display_state")) is not str
        or value.get("display_state") not in STATES
        or type(value.get("goal")) is not str
        or not 0 < len(value["goal"]) <= 8192
        or type(value.get("created_at")) is not str
        or len(value["created_at"]) > 100
        or value.get("native_approval") != NON_ATTESTED
        or value.get("isolated_runner_execution") != NON_ATTESTED
        or value.get("independent_verifier") != NON_ATTESTED
        or value.get("execution_authorized_by_this_view") is not False
        or value.get("execution_verified_by_this_view") is not False
    ):
        raise CasebookTaskUnavailable("CASEBOOK projection verification is incomplete")
    timeline = value.get("timeline")
    if (
        not isinstance(timeline, list)
        or len(timeline) < 1
        or len(timeline) > 500
        or value.get("recorded_event_count") != len(timeline)
        or not all(
            type(item) is dict
            and set(item) == {
                "seq", "event_id", "type", "timestamp",
                "source_claim", "summary", "status_claim", "event_hash",
            }
            and type(item["seq"]) is int
            and item["seq"] > 0
            and type(item["event_id"]) is str
            and 1 <= len(item["event_id"]) <= 128
            and type(item["type"]) is str
            and item["type"] in JOURNAL_TYPES
            and type(item["timestamp"]) is str
            and 1 <= len(item["timestamp"]) <= 100
            and type(item["source_claim"]) is str
            and item["source_claim"] in JOURNAL_SOURCES
            and type(item["status_claim"]) is str
            and item["status_claim"] in JOURNAL_STATUSES
            and type(item["event_hash"]) is str
            and re.fullmatch(r"[0-9a-f]{64}", item["event_hash"]) is not None
            and type(item["summary"]) is str
            and len(item["summary"]) <= 8192
            for item in timeline
        )
    ):
        raise CasebookTaskUnavailable("CASEBOOK timeline is invalid")
    if timeline[0]["type"] != "GOAL" or timeline[0]["summary"] != value.get("goal"):
        raise CasebookTaskUnavailable("CASEBOOK goal does not match journal")
    has_result = any(item["type"] == "RESULT" for item in timeline)
    has_context = any(item["type"] == "CONTEXT" for item in timeline)
    if (value["display_state"] == "RESULT_RECORDED_UNVERIFIED") != has_result:
        raise CasebookTaskUnavailable("CASEBOOK result state is inconsistent")
    if value.get("handoff") == "RECORDED_UNATTESTED" and not has_context:
        raise CasebookTaskUnavailable("CASEBOOK handoff has no recorded context")
    if (
        value["display_state"] == "HANDOFF_RECORDED_UNVERIFIED"
        and (value.get("handoff") != "RECORDED_UNATTESTED" or has_result)
    ):
        raise CasebookTaskUnavailable("CASEBOOK handoff state is inconsistent")
    if (
        value["display_state"] == "GOAL_RECORDED"
        and (has_result or value.get("handoff") == "RECORDED_UNATTESTED")
    ):
        raise CasebookTaskUnavailable("CASEBOOK GOAL state is inconsistent")
    # Reconstruct a strict presentation subset. Ignore excess fields even if
    # source contains an untrusted "VERIFIED" claim or credential-like data.
    return {
        "schema": SCHEMA,
        "session_id": scope.session_id,
        "workspace_id": scope.workspace_id,
        "project": scope.project,
        "goal": value["goal"],
        "created_at": value.get("created_at", ""),
        "display_state": value["display_state"],
        "journal_integrity": INTEGRITY,
        "handoff": (
            "RECORDED_UNATTESTED" if value.get("handoff") == "RECORDED_UNATTESTED"
            else "NOT_ESTABLISHED"
        ),
        "native_approval": NON_ATTESTED,
        "isolated_runner_execution": NON_ATTESTED,
        "independent_verifier": NON_ATTESTED,
        # Explicit non-attestation flags are part of the public UI contract.
        # These report only this projection's authority, not a verified run.
        "execution_authorized_by_this_view": False,
        "execution_verified_by_this_view": False,
        "result": (
            "RECORDED_UNVERIFIED"
            if value["display_state"] == "RESULT_RECORDED_UNVERIFIED"
            else "NOT_RECORDED"
        ),
        "next_action": NEXT_ACTIONS[value["display_state"]],
        "recorded_event_count": len(timeline),
        "timeline": timeline,
    }


def attach_casebook_task_gateway(
    *, app: FastAPI, composition: ProductComposition,
    reader: Callable[[str], dict[str, Any]],
    scopes: Iterable[TaskScope],
    passport_correlation_enabled: bool = False,
) -> CasebookTaskGateway:
    """Explicit local-only attachment; never called by the default installer.

    The caller must supply a reviewed/pinned read-only CASEBOOK implementation,
    task ownership/provenance and authorized workspace bindings. No API route
    is changed, no new credential or grant is created, and there is no
    production capability activation.
    """
    if not isinstance(app, FastAPI):
        raise ValueError("CASEBOOK requires the native FastAPI application")
    if (
        getattr(app.state, "voodoo_product_composition", None) is not composition
        or getattr(app.state, "voodoo_identity_provider", None) is None
    ):
        raise CasebookTaskAccessDenied("CASEBOOK cannot attach to foreign composition")
    if getattr(app.state, "voodoo_casebook_task_gateway", None) is not None:
        raise CasebookTaskAccessDenied("CASEBOOK task gateway is already attached")
    gateway = CasebookTaskGateway(
        composition=composition,
        scopes=tuple(scopes),
        reader=reader,
        passport_correlation_enabled=passport_correlation_enabled,
    )
    app.state.voodoo_casebook_task_gateway = gateway
    return gateway
