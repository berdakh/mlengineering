"""Model bundles and a local registry. SNAPSHOT written to the w5d2 description; given to you.

Bundle (a directory, no pickle)::

    model.json      format_version, model_type, name, version, params, input_schema, metadata
    checksums.json  SHA-256 of every other file

Registry::

    <root>/<name>/<MAJOR.MINOR.PATCH>/   immutable copies of bundles (``register`` refuses to overwrite)
    <root>/<name>/current                 one line: the version being served (replaced atomically)
    <root>/<name>/audit.jsonl             append-only log of pointer moves (written by flowguard.update)

``load_bundle`` verifies checksums and format before building anything and never executes code from
the bundle. Moving ``current`` (promote / rollback) is the job of ``flowguard.update`` in w7d4.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

from flowguard.models import MODEL_TYPE, BurnInZ

FORMAT_VERSION = 1
SCHEMA_VERSION = 1
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


class BundleError(ValueError):
    """A bundle is missing, corrupted or not in a format this code understands."""


class RegistryError(Exception):
    """An operation on the registry is not allowed."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_bundle(model: BurnInZ, out_dir, metadata: dict | None = None) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    doc = {
        "format_version": FORMAT_VERSION, "model_type": MODEL_TYPE,
        "name": model.name, "version": model.version, "params": model.params(),
        "input_schema": {"schema_version": SCHEMA_VERSION, "required": model.required_columns},
        "metadata": {**model.metadata, **(metadata or {})},
    }
    (out / "model.json").write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    (out / "checksums.json").write_text(json.dumps({"model.json": _sha256(out / "model.json")},
                                                   indent=2, sort_keys=True) + "\n")
    return out


def verify_bundle(bundle_dir) -> dict:
    root = Path(bundle_dir)
    if not root.is_dir():
        raise BundleError(f"bundle directory not found: {root}")
    try:
        checksums = json.loads((root / "checksums.json").read_text())
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise BundleError(f"{root}: checksums.json missing or invalid") from exc
    for name, expected in checksums.items():
        path = root / name
        if not path.is_file() or _sha256(path) != expected:
            raise BundleError(f"{root}: checksum mismatch or missing file: {name}")
    doc = json.loads((root / "model.json").read_text())
    if doc.get("format_version") != FORMAT_VERSION or doc.get("model_type") != MODEL_TYPE:
        raise BundleError(f"{root}: unsupported format {doc.get('format_version')!r} / {doc.get('model_type')!r}")
    return doc


def load_bundle(bundle_dir) -> tuple[BurnInZ, dict]:
    doc = verify_bundle(bundle_dir)
    try:
        model = BurnInZ.from_params(doc["params"], doc.get("metadata"))
    except (KeyError, TypeError, ValueError) as exc:
        raise BundleError(f"{bundle_dir}: invalid parameters: {exc}") from exc
    if (model.name, model.version) != (doc.get("name"), doc.get("version")):
        raise BundleError(f"{bundle_dir}: name/version do not match the parameters")
    return model, doc


def _version_key(version: str) -> tuple[int, int, int]:
    m = SEMVER.match(version)
    if not m:
        raise RegistryError(f"version {version!r} is not MAJOR.MINOR.PATCH")
    return tuple(int(x) for x in m.groups())


def register(root, bundle_dir) -> Path:
    """Copy a verified bundle to ``<root>/<name>/<version>``; refuse to overwrite a version."""
    doc = verify_bundle(bundle_dir)
    name, version = doc["name"], doc["version"]
    _version_key(version)
    home = Path(root) / name
    dest = home / version
    if dest.exists():
        raise RegistryError(f"{name} {version} is already registered; versions are immutable")
    home.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{version}.", dir=home))
    try:
        for item in Path(bundle_dir).iterdir():
            shutil.copy2(item, staging / item.name)
        verify_bundle(staging)
        os.replace(staging, dest)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return dest


def list_versions(root, name) -> list[str]:
    home = Path(root) / name
    if not home.is_dir():
        return []
    return sorted((p.name for p in home.iterdir() if p.is_dir() and SEMVER.match(p.name)), key=_version_key)


def current_version(root, name) -> str | None:
    pointer = Path(root) / name / "current"
    return pointer.read_text().strip() if pointer.is_file() else None


def resolve(root, name, ref: str = "current") -> Path:
    if ref == "current":
        ref = current_version(root, name)
        if ref is None:
            raise RegistryError(f"{name} has no current version")
    if ref not in list_versions(root, name):
        raise RegistryError(f"{name} {ref} is not registered")
    return Path(root) / name / ref


def write_pointer(root, name, version: str) -> None:
    """Atomically replace ``<root>/<name>/current`` (write a temp file, then ``os.replace``)."""
    home = Path(root) / name
    fd, tmp = tempfile.mkstemp(prefix=".current.", dir=home)
    with os.fdopen(fd, "w") as fh:
        fh.write(version + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, home / "current")
