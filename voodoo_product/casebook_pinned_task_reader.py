"""Exact-source CASEBOOK task reader for an explicitly attached local V-One pane.

No automatic discovery of owner CASEBOOK data, service account or runtime
activation. A caller supplies a preapproved existing data root, and an
authenticated native gateway controls who may read each bound session.

Only the following SHA-256-pinned source files are imported as executable
code. They are checked before import and again before/after every read. A
private code package namespace isolates these pinned modules from any
unrelated voodoo_casebook installed on the application sys.path.
"""
from __future__ import annotations

import hashlib
import os
import pwd
import stat
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

from .casebook_task_gateway import CasebookTaskUnavailable

PINNED_CASEBOOK_COMMIT = "086d96182753fffb8632b0f12a0ed2848256ee66"
PINNED_PACKAGE_DIGESTS = {
    "__init__.py": "7c793f774948a89abb76fb6e26980dce5e3cfbf98051e68cab730d1414e98357",
    "core.py": "cc94b132efcab90a5b0d5bdc610d51e18c73909130e7b62bc8aaf81e3cd03a83",
    "task_view.py": "a784f3495cda7926a68af14d36cb9f87f1f9cb6edf2ac517c93475507cf24036",
}
CASEBOOK_PACKAGE = "voodoo_casebook"
EVIDENCE_SHELF = Path(pwd.getpwuid(os.getuid()).pw_dir) / "0_EVIDENCE"


def _canonical_path(path: Path, *, label: str) -> Path:
    if (
        not isinstance(path, Path)
        or not path.is_absolute()
        or ".." in path.parts
        or any(parent.is_symlink() for parent in (path, *path.parents))
        or path != path.resolve(strict=False)
    ):
        raise CasebookTaskUnavailable(f"{label} is not a canonical absolute path")
    return path


def _read_pinned_source(root: Path) -> dict[str, bytes]:
    _canonical_path(root, label="CASEBOOK source")
    package = root / CASEBOOK_PACKAGE
    _canonical_path(package, label="CASEBOOK package")
    if not root.is_dir() or not package.is_dir():
        raise CasebookTaskUnavailable("CASEBOOK source is missing")
    bodies: dict[str, bytes] = {}
    for name, expected in PINNED_PACKAGE_DIGESTS.items():
        path = package / name
        _canonical_path(path, label="CASEBOOK source file")
        if not path.is_file() or path.stat().st_size > 100_000:
            raise CasebookTaskUnavailable("CASEBOOK source file is unavailable")
        body = path.read_bytes()
        if hashlib.sha256(body).hexdigest() != expected:
            raise CasebookTaskUnavailable("CASEBOOK source SHA-256 differs from pinned release candidate")
        bodies[name] = body
    return bodies


def _load_pinned_package(root: Path, bodies: dict[str, bytes]) -> tuple[type, Callable[..., dict[str, Any]]]:
    # Deterministic per absolute code root; no unrelated package on sys.path
    # may silently substitute its own CasebookStore or project_task_status.
    name = "_voodoo_pinned_casebook_" + hashlib.sha256(str(root).encode()).hexdigest()[:24]
    names = [name, name + ".core", name + ".task_view"]
    if any(part in sys.modules for part in names):
        raise CasebookTaskUnavailable("CASEBOOK pinned package namespace already in use")
    package_path = root / CASEBOOK_PACKAGE
    package = ModuleType(name)
    package.__file__ = str(package_path / "__init__.py")
    package.__package__ = name
    package.__path__ = [str(package_path)]
    core = ModuleType(name + ".core")
    core.__file__ = str(package_path / "core.py")
    core.__package__ = name
    task_view = ModuleType(name + ".task_view")
    task_view.__file__ = str(package_path / "task_view.py")
    task_view.__package__ = name
    try:
        sys.modules[name] = package
        sys.modules[name + ".core"] = core
        exec(compile(bodies["core.py"], core.__file__, "exec"), core.__dict__)  # noqa: S102 -- exact SHA-256-pinned bytes, no dynamic caller code
        exec(compile(bodies["__init__.py"], package.__file__, "exec"), package.__dict__)  # noqa: S102 -- exact SHA-256-pinned bytes, no dynamic caller code
        sys.modules[name + ".task_view"] = task_view
        exec(compile(bodies["task_view.py"], task_view.__file__, "exec"), task_view.__dict__)  # noqa: S102 -- exact SHA-256-pinned bytes, no dynamic caller code
        store_type = package.CasebookStore
        projector = task_view.project_task_status
        if store_type is not core.CasebookStore or not callable(projector):
            raise CasebookTaskUnavailable("CASEBOOK package contract is invalid")
        return store_type, projector
    except BaseException:
        for part in names:
            sys.modules.pop(part, None)
        raise


@dataclass(frozen=True, slots=True)
class PinnedCasebookTaskReader:
    """Read an existing evidence journal using precisely reviewed code bytes.

    Creating this reader verifies an existing private journal; it
    never creates or modifies it. The native gateway is still required for
    user identity, workspace membership and explicit session ID scoping.
    """

    source_root: Path
    data_root: Path
    _store: Any = field(init=False, repr=False, compare=False)
    _projector: Callable[..., dict[str, Any]] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        _canonical_path(self.source_root, label="CASEBOOK source")
        _canonical_path(self.data_root, label="CASEBOOK evidence")
        if (
            self.source_root == self.data_root
            or self.source_root in self.data_root.parents
            or self.data_root in self.source_root.parents
        ):
            raise CasebookTaskUnavailable("CASEBOOK code and private journal must be separate")
        if not self.data_root.is_dir():
            raise CasebookTaskUnavailable("CASEBOOK evidence root is not present")
        if stat.S_IMODE(self.data_root.stat().st_mode) & 0o077:
            raise CasebookTaskUnavailable("CASEBOOK evidence root is not owner-private")
        bodies = _read_pinned_source(self.source_root)
        store_type, projector = _load_pinned_package(self.source_root, bodies)
        store = store_type(self.data_root)
        if store.verify().get("verdict") != "VERIFIED_INTEGRITY":
            raise CasebookTaskUnavailable("CASEBOOK journal integrity is not verified")
        object.__setattr__(self, "_store", store)
        object.__setattr__(self, "_projector", projector)

    def __call__(self, session_id: str) -> dict[str, Any]:
        _read_pinned_source(self.source_root)
        value = self._projector(self._store, session_id)
        _read_pinned_source(self.source_root)
        return value
