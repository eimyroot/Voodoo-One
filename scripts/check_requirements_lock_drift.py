from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parents[1]
EXACT_PIN = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)(?P<extras>\[[A-Za-z0-9._,-]+\])?"
    r"==(?P<version>[^\s\\]+)$"
)
LOCK_PIN = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)(?P<extras>\[[A-Za-z0-9._,-]+\])?"
    r"==(?P<version>[^\s\\]+)"
)


class RequirementLockDriftError(ValueError):
    """Fail-closed error for unsupported or inconsistent requirement inputs."""


def _normalize_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _normalize_extras(value: str | None) -> str:
    if not value:
        return ""
    items = [_normalize_name(item.strip()) for item in value[1:-1].split(",")]
    if not all(items):
        raise RequirementLockDriftError("requirement extras contain an empty value")
    return "[" + ",".join(sorted(items)) + "]"


def _requirement_key(name: str, extras: str | None) -> str:
    return _normalize_name(name) + _normalize_extras(extras)


def _confined_path(root: Path, candidate: Path) -> Path:
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise RequirementLockDriftError(
            f"requirements include escapes repository root: {candidate}"
        ) from exc
    return resolved


def _parse_manifest(
    path: Path,
    *,
    root: Path,
    seen: set[Path] | None = None,
) -> dict[str, str]:
    resolved = _confined_path(root, path)
    active = set() if seen is None else seen
    if resolved in active:
        raise RequirementLockDriftError(f"requirements include cycle: {resolved}")
    active.add(resolved)

    pins: dict[str, str] = {}
    for line_number, raw in enumerate(resolved.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        include: str | None = None
        if line.startswith("-r "):
            include = line[3:].strip()
        elif line.startswith("--requirement "):
            include = line[len("--requirement ") :].strip()

        if include is not None:
            if not include:
                raise RequirementLockDriftError(
                    f"{resolved}:{line_number}: empty requirements include"
                )
            nested = _parse_manifest(
                resolved.parent / include,
                root=root,
                seen=active,
            )
            for key, version in nested.items():
                previous = pins.get(key)
                if previous is not None and previous != version:
                    raise RequirementLockDriftError(
                        f"{resolved}:{line_number}: conflicting pin for {key}"
                    )
                pins[key] = version
            continue

        match = EXACT_PIN.fullmatch(line)
        if match is None:
            raise RequirementLockDriftError(
                f"{resolved}:{line_number}: unsupported requirement syntax: {line!r}"
            )
        key = _requirement_key(match.group("name"), match.group("extras"))
        version = match.group("version")
        previous = pins.get(key)
        if previous is not None and previous != version:
            raise RequirementLockDriftError(
                f"{resolved}:{line_number}: conflicting pin for {key}"
            )
        pins[key] = version

    active.remove(resolved)
    return pins


def _parse_lock(path: Path, *, root: Path) -> dict[str, str]:
    resolved = _confined_path(root, path)
    pins: dict[str, str] = {}
    for line_number, raw in enumerate(resolved.read_text(encoding="utf-8").splitlines(), 1):
        if raw[:1].isspace() or not raw or raw.startswith("#"):
            continue
        match = LOCK_PIN.match(raw)
        if match is None:
            continue
        key = _requirement_key(match.group("name"), match.group("extras"))
        version = match.group("version")
        previous = pins.get(key)
        if previous is not None and previous != version:
            raise RequirementLockDriftError(
                f"{resolved}:{line_number}: duplicate lock pin for {key}"
            )
        pins[key] = version
    return pins


def check_pair(*, manifest: Path, lock: Path, root: Path) -> dict[str, object]:
    required = _parse_manifest(manifest, root=root)
    locked = _parse_lock(lock, root=root)

    missing = sorted(key for key in required if key not in locked)
    mismatched = [
        {
            "requirement": key,
            "manifest_version": required[key],
            "lock_version": locked[key],
        }
        for key in sorted(required)
        if key in locked and required[key] != locked[key]
    ]
    return {
        "manifest": str(manifest.relative_to(root)),
        "lock": str(lock.relative_to(root)),
        "required_pin_count": len(required),
        "missing": missing,
        "mismatched": mismatched,
        "ok": not missing and not mismatched,
    }


def evaluate(root: Path = ROOT) -> dict[str, object]:
    resolved = root.resolve()
    pairs = (
        ("product", resolved / "requirements-product.txt", resolved / "requirements-product.lock"),
        ("development", resolved / "requirements-dev.in", resolved / "requirements-dev.lock"),
    )
    checks = {
        name: check_pair(manifest=manifest, lock=lock, root=resolved)
        for name, manifest, lock in pairs
    }
    return {
        "schema": "requirements-lock-drift/v1",
        "ok": all(bool(value["ok"]) for value in checks.values()),
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail closed when direct requirement pins drift from generated lockfiles."
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        report = evaluate(args.root)
    except (OSError, RequirementLockDriftError) as exc:
        report = {
            "schema": "requirements-lock-drift/v1",
            "ok": False,
            "error": str(exc),
        }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
