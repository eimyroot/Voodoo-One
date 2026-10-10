from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

SNAPSHOT_CONTRACT = "voodoo-one-dependency-snapshot/v1"
VERIFICATION_CONTRACT = "voodoo-one-dependency-verification/v1"
DETECTOR_NAME = "voodoo-one-dependency-reconciliation"
DETECTOR_VERSION = "1"
CORRELATOR = "voodoo-one-provider-reconciliation"
MAIN_REF = "refs/heads/main"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
PIN_RE = re.compile(r"^([A-Za-z0-9_.-]+)==([^ \\]+)")
DIRECT_RE = re.compile(
    r"^([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?==([^\s;]+)$"
)


class DependencySnapshotError(ValueError):
    """Fail-closed error for dependency graph snapshot invariants."""


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _normalize_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _require_sha(value: str) -> str:
    if not SHA_RE.fullmatch(value):
        raise DependencySnapshotError("sha must be a lowercase 40-character Git SHA")
    return value


def _require_main_ref(value: str) -> str:
    if value != MAIN_REF:
        raise DependencySnapshotError("dependency snapshot ref must be refs/heads/main")
    return value


def _require_scanned(value: str) -> str:
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise DependencySnapshotError("scanned must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise DependencySnapshotError("scanned timestamp must include a timezone")
    return value


def _purl(name: str, version: str) -> str:
    normalized = _normalize_name(name)
    return (
        "pkg:pypi/"
        + quote(normalized, safe="-._~")
        + "@"
        + quote(version, safe="-._~+")
    )


def parse_direct_requirements(
    path: Path,
    *,
    allowed_includes: frozenset[str] = frozenset(),
) -> set[str]:
    direct: set[str] = set()
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-r "):
            include = line[3:].strip()
            if include not in allowed_includes:
                raise DependencySnapshotError(
                    f"{path.name}:{line_number} has unsupported requirement include {include!r}"
                )
            continue
        match = DIRECT_RE.fullmatch(line)
        if match is None:
            raise DependencySnapshotError(
                f"{path.name}:{line_number} is not a supported exact requirement"
            )
        direct.add(_normalize_name(match.group(1)))
    return direct


def parse_lock(path: Path) -> dict[str, str]:
    pins: dict[str, str] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        match = PIN_RE.match(raw)
        if match is None:
            continue
        name = _normalize_name(match.group(1))
        version = match.group(2)
        existing = pins.get(name)
        if existing is not None and existing != version:
            raise DependencySnapshotError(
                f"{path.name}:{line_number} conflicts with an earlier pin for {name}"
            )
        pins[name] = version
    if not pins:
        raise DependencySnapshotError(f"{path.name} contains no exact package pins")
    return pins


def _resolved(
    pins: dict[str, str],
    direct: set[str],
    *,
    scope: str,
) -> dict[str, dict[str, str]]:
    return {
        name: {
            "package_url": _purl(name, version),
            "relationship": "direct" if name in direct else "indirect",
            "scope": scope,
        }
        for name, version in sorted(pins.items())
    }


def build_snapshot(
    *,
    sha: str,
    ref: str,
    scanned: str,
    product_input: Path,
    product_lock: Path,
    dev_input: Path,
    dev_lock: Path,
) -> dict[str, Any]:
    sha = _require_sha(sha)
    ref = _require_main_ref(ref)
    scanned = _require_scanned(scanned)
    product_direct = parse_direct_requirements(product_input)
    dev_direct = parse_direct_requirements(
        dev_input,
        allowed_includes=frozenset({"requirements-product.txt"}),
    )
    product_pins = parse_lock(product_lock)
    dev_pins = parse_lock(dev_lock)
    return {
        "version": 0,
        "sha": sha,
        "ref": ref,
        "job": {
            "correlator": CORRELATOR,
            "id": f"main-{sha}",
        },
        "detector": {
            "name": DETECTOR_NAME,
            "version": DETECTOR_VERSION,
            "url": "https://github.com/eimyroot/Voodoo-One",
        },
        "metadata": {
            "contract": SNAPSHOT_CONTRACT,
            "exact_main": sha,
            "purpose": "durable-dependency-graph-refresh",
        },
        "scanned": scanned,
        "manifests": {
            "requirements-product.txt": {
                "name": "requirements-product.txt",
                "file": {"source_location": "requirements-product.txt"},
                "resolved": _resolved(product_pins, product_direct, scope="runtime"),
            },
            "requirements-dev.in": {
                "name": "requirements-dev.in",
                "file": {"source_location": "requirements-dev.in"},
                "resolved": _resolved(dev_pins, dev_direct, scope="development"),
            },
        },
    }


def _expected_purls(snapshot: dict[str, Any]) -> list[str]:
    expected: set[str] = set()
    manifests = snapshot.get("manifests")
    if not isinstance(manifests, dict):
        raise DependencySnapshotError("snapshot manifests are invalid")
    for manifest in manifests.values():
        if not isinstance(manifest, dict):
            raise DependencySnapshotError("snapshot manifest is invalid")
        resolved = manifest.get("resolved")
        if not isinstance(resolved, dict):
            raise DependencySnapshotError("snapshot resolved dependencies are invalid")
        for dependency in resolved.values():
            if not isinstance(dependency, dict):
                raise DependencySnapshotError("snapshot dependency is invalid")
            package_url = dependency.get("package_url")
            if not isinstance(package_url, str) or not package_url.startswith("pkg:pypi/"):
                raise DependencySnapshotError("snapshot dependency package_url is invalid")
            expected.add(package_url)
    return sorted(expected)


def _previous_versions(
    current: dict[str, str],
    previous: dict[str, str] | None,
) -> set[str]:
    if previous is None:
        return set()
    stale: set[str] = set()
    for name, old_version in previous.items():
        new_version = current.get(name)
        if new_version != old_version:
            stale.add(_purl(name, old_version))
    return stale


def build_verification_spec(
    *,
    snapshot: dict[str, Any],
    snapshot_bytes: bytes,
    product_lock: Path,
    dev_lock: Path,
    previous_product_lock: Path | None,
    previous_dev_lock: Path | None,
) -> dict[str, Any]:
    current_product = parse_lock(product_lock)
    current_dev = parse_lock(dev_lock)
    previous_product = (
        parse_lock(previous_product_lock)
        if previous_product_lock is not None
        else None
    )
    previous_dev = (
        parse_lock(previous_dev_lock)
        if previous_dev_lock is not None
        else None
    )
    expected = _expected_purls(snapshot)
    stale = _previous_versions(current_product, previous_product)
    stale.update(_previous_versions(current_dev, previous_dev))
    stale.difference_update(expected)

    return {
        "contract": VERIFICATION_CONTRACT,
        "sha": snapshot["sha"],
        "ref": snapshot["ref"],
        "detector_name": DETECTOR_NAME,
        "correlator": CORRELATOR,
        "snapshot_sha256": _sha256_bytes(snapshot_bytes),
        "expected_purls": expected,
        "stale_purls": sorted(stale),
    }


def write_snapshot(
    *,
    sha: str,
    ref: str,
    scanned: str,
    product_input: Path,
    product_lock: Path,
    dev_input: Path,
    dev_lock: Path,
    previous_product_lock: Path | None,
    previous_dev_lock: Path | None,
    snapshot_out: Path,
    verification_out: Path,
) -> None:
    if (previous_product_lock is None) != (previous_dev_lock is None):
        raise DependencySnapshotError(
            "previous product/dev locks must be supplied together"
        )
    snapshot = build_snapshot(
        sha=sha,
        ref=ref,
        scanned=scanned,
        product_input=product_input,
        product_lock=product_lock,
        dev_input=dev_input,
        dev_lock=dev_lock,
    )
    snapshot_bytes = (
        json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    verification = build_verification_spec(
        snapshot=snapshot,
        snapshot_bytes=snapshot_bytes,
        product_lock=product_lock,
        dev_lock=dev_lock,
        previous_product_lock=previous_product_lock,
        previous_dev_lock=previous_dev_lock,
    )
    snapshot_out.write_bytes(snapshot_bytes)
    verification_out.write_text(
        json.dumps(verification, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _sbom_purls(sbom: dict[str, Any]) -> set[str]:
    document = sbom.get("sbom")
    if not isinstance(document, dict):
        raise DependencySnapshotError("GitHub SBOM response is missing sbom")
    packages = document.get("packages")
    if not isinstance(packages, list):
        raise DependencySnapshotError("GitHub SBOM packages are invalid")

    found: set[str] = set()
    for package in packages:
        if not isinstance(package, dict):
            continue
        name = package.get("name")
        version = package.get("versionInfo")
        if isinstance(name, str) and isinstance(version, str):
            found.add(_purl(name, version))
        external_refs = package.get("externalRefs")
        if isinstance(external_refs, list):
            for reference in external_refs:
                if not isinstance(reference, dict):
                    continue
                locator = reference.get("referenceLocator")
                if isinstance(locator, str) and locator.startswith("pkg:pypi/"):
                    found.add(locator)
    return found


def verify_sbom(*, verification: dict[str, Any], sbom: dict[str, Any]) -> None:
    if verification.get("contract") != VERIFICATION_CONTRACT:
        raise DependencySnapshotError("verification contract is unsupported")
    _require_sha(str(verification.get("sha", "")))
    _require_main_ref(str(verification.get("ref", "")))
    if verification.get("detector_name") != DETECTOR_NAME:
        raise DependencySnapshotError("verification detector identity is invalid")
    if verification.get("correlator") != CORRELATOR:
        raise DependencySnapshotError("verification correlator identity is invalid")

    expected = verification.get("expected_purls")
    stale = verification.get("stale_purls")
    if (
        not isinstance(expected, list)
        or not all(isinstance(item, str) for item in expected)
        or not isinstance(stale, list)
        or not all(isinstance(item, str) for item in stale)
    ):
        raise DependencySnapshotError("verification PURL lists are invalid")

    observed = _sbom_purls(sbom)
    missing = sorted(set(expected) - observed)
    stale_present = sorted(set(stale) & observed)
    if missing:
        raise DependencySnapshotError(
            "provider SBOM is missing expected dependencies: " + ", ".join(missing)
        )
    if stale_present:
        raise DependencySnapshotError(
            "provider SBOM still contains stale dependency versions: "
            + ", ".join(stale_present)
        )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DependencySnapshotError(f"{path.name} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise DependencySnapshotError(f"{path.name} must contain a JSON object")
    return value


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and verify VOODOO dependency snapshots.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build")
    build.add_argument("--sha", required=True)
    build.add_argument("--ref", required=True)
    build.add_argument("--scanned", required=True)
    build.add_argument("--product-input", type=Path, required=True)
    build.add_argument("--product-lock", type=Path, required=True)
    build.add_argument("--dev-input", type=Path, required=True)
    build.add_argument("--dev-lock", type=Path, required=True)
    build.add_argument("--previous-product-lock", type=Path)
    build.add_argument("--previous-dev-lock", type=Path)
    build.add_argument("--snapshot-out", type=Path, required=True)
    build.add_argument("--verification-out", type=Path, required=True)

    verify = subparsers.add_parser("verify-sbom")
    verify.add_argument("--verification", type=Path, required=True)
    verify.add_argument("--sbom", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            write_snapshot(
                sha=args.sha,
                ref=args.ref,
                scanned=args.scanned,
                product_input=args.product_input,
                product_lock=args.product_lock,
                dev_input=args.dev_input,
                dev_lock=args.dev_lock,
                previous_product_lock=args.previous_product_lock,
                previous_dev_lock=args.previous_dev_lock,
                snapshot_out=args.snapshot_out,
                verification_out=args.verification_out,
            )
        else:
            verify_sbom(
                verification=_read_json(args.verification),
                sbom=_read_json(args.sbom),
            )
    except DependencySnapshotError as exc:
        print(f"dependency snapshot rejected: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
