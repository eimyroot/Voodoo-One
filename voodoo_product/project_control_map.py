"""Opt-in, read-only Project Control Map evidence projection.

The product never discovers Git projects or runs provider commands here. It only
renders a bounded, SHA-pinned offline snapshot supplied by trusted configuration.
This is *not* a project, authority, approval, or workflow registry.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SNAPSHOT_SCHEMA = "ProjectControlMapSnapshot/v1"
PROJECTION_SCHEMA = "ProjectControlMapProjection/v1"
MAX_SNAPSHOT_BYTES = 262_144
MAX_AGE_SECONDS = 86_400
_ID = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_SHA = re.compile(r"^[0-9a-f]{40}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


class ProjectControlMapUnavailable(Exception):
    """Missing or untrusted evidence. Never expose its filesystem path to HTTP."""


def _need(condition: bool) -> None:
    if not condition:
        raise ProjectControlMapUnavailable


def _string(value: Any, *, max_length: int = 240) -> str:
    _need(isinstance(value, str) and 0 < len(value) <= max_length)
    _need(not any(ord(ch) < 32 for ch in value))
    return value


def _date(value: Any) -> datetime:
    raw = _string(value, max_length=64)
    try:
        d = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProjectControlMapUnavailable from exc
    _need(d.tzinfo is not None)
    return d.astimezone(UTC)


def _read_pinned_snapshot(path: Path | None, expected_sha256: str) -> dict[str, Any]:
    if path is None:
        raise ProjectControlMapUnavailable
    _need(path.is_absolute() and bool(_DIGEST.fullmatch(expected_sha256)))
    try:
        # O_NOFOLLOW prevents a trusted config from following a replaced file symlink.
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        try:
            meta = os.fstat(fd)
            _need(stat.S_ISREG(meta.st_mode) and 0 < meta.st_size <= MAX_SNAPSHOT_BYTES)
            with os.fdopen(fd, "rb", closefd=False) as source:
                raw = source.read(MAX_SNAPSHOT_BYTES + 1)
        finally:
            os.close(fd)
        _need(len(raw) <= MAX_SNAPSHOT_BYTES)
        _need(hashlib.sha256(raw).hexdigest() == expected_sha256)
        doc = json.loads(raw)
        _need(isinstance(doc, dict))
        return doc
    except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ProjectControlMapUnavailable from exc


def project_control_map_projection(
    snapshot_path: Path | None,
    expected_sha256: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return a whitelisted observation; no Git, network, SQL, or policy I/O."""
    doc = _read_pinned_snapshot(snapshot_path, expected_sha256)
    _need(doc.get("schema") == SNAPSHOT_SCHEMA)
    rules = doc.get("truth_policy")
    _need(isinstance(rules, dict))
    _need(rules.get("read_only") is True)
    _need(rules.get("project_authority_effect") == "NONE")
    for flag in ("automatic_git_merge", "automatic_priority_change", "unknown_is_pass"):
        _need(rules.get(flag) is False)
    _need(rules.get("provider_effects") == "NOT_AUTHORIZED")

    seen_at = _date(doc.get("observed_at_utc"))
    checked_at = (now or datetime.now(UTC)).astimezone(UTC)
    age = (checked_at - seen_at).total_seconds()
    _need(age >= -300)  # Reject implausible future evidence.
    freshness = "STALE_SNAPSHOT" if age > MAX_AGE_SECONDS else "CURRENT_SNAPSHOT"

    focus = doc.get("finishgate")
    _need(isinstance(focus, dict))
    _need(focus.get("status") == "IN_PROGRESS")
    _need(focus.get("delivery") == "PROJECT-CONTROL-MAP-R1")
    # Identifier is an external candidate focus ID, never an authorization token.
    active_delivery = _string(focus.get("delivery"), max_length=80)

    raw_projects = doc.get("projects")
    _need(isinstance(raw_projects, list) and 0 < len(raw_projects) <= 25)
    projects: list[dict[str, Any]] = []
    ids: set[str] = set()
    for item in raw_projects:
        _need(isinstance(item, dict))
        pid = _string(item.get("id"), max_length=64)
        _need(bool(_ID.fullmatch(pid)) and pid not in ids)
        ids.add(pid)
        repo = _string(item.get("canonical_repo"), max_length=150)
        _need(bool(_REPO.fullmatch(repo)))
        _need(all(segment not in {".", ".."} for segment in repo.split("/")))
        git = item.get("git")
        _need(isinstance(git, dict))
        local = _string(git.get("local_head"), max_length=40)
        hosted = _string(git.get("remote_main_head_observed"), max_length=40)
        _need(bool(_SHA.fullmatch(local)) and bool(_SHA.fullmatch(hosted)))
        projects.append({
            "id": pid,
            "name": _string(item.get("name"), max_length=150),
            "kind": _string(item.get("kind"), max_length=90),
            "repo": repo,
            "branch": _string(git.get("local_branch"), max_length=130),
            "local_head": local[:12],
            "hosted_head": hosted[:12],
            "head_comparison": "MATCHED_AT_OBSERVATION" if local == hosted else "DIFFERENT_HEADS",
            "worktree": _string(git.get("local_worktree"), max_length=90),
            "status": _string(item.get("observed_status"), max_length=230),
            "freshness": freshness,
        })

    subs = doc.get("subworkstreams", [])
    _need(isinstance(subs, list) and len(subs) <= 50)
    subids = set()
    for s in subs:
        _need(isinstance(s, dict))
        sid = _string(s.get("id"), max_length=64)
        _need(bool(_ID.fullmatch(sid)) and sid not in ids and sid not in subids)
        subids.add(sid)
        _need(s.get("parent_project_id") in ids)

    relations = doc.get("relationships")
    _need(isinstance(relations, list) and len(relations) <= 100)
    edges = []
    for rel in relations:
        _need(isinstance(rel, dict) and rel.get("from") in ids | subids and rel.get("to") in ids)
        edges.append({
            "from": rel["from"], "to": rel["to"],
            "kind": _string(rel.get("kind"), max_length=110),
            "status": _string(rel.get("status"), max_length=220),
        })

    raw_gaps = doc.get("known_gaps", [])
    _need(isinstance(raw_gaps, list) and len(raw_gaps) <= 35)
    gaps = [_string(g, max_length=420) for g in raw_gaps]
    return {
        "schema": PROJECTION_SCHEMA,
        "mode": "READ_ONLY",
        "authority_effect": "NONE",
        "freshness": freshness,
        "observed_at_utc": doc["observed_at_utc"],
        "snapshot_sha256": expected_sha256,
        "active_delivery": active_delivery,
        "focus_status": "IN_PROGRESS",
        "projects": projects,
        "relationships": edges,
        "known_gaps": gaps,
    }
