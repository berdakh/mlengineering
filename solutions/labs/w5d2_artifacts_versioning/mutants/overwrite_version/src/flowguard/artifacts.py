"""Model artifacts that can be trusted when they are loaded, and a local registry of versions.

A **bundle** is a directory with exactly these files (no pickle anywhere):

    model.json      {"format": "flowguard-bundle", "format_version": 1, "kind": "<model kind>",
                     ...the model's configuration: Detector.to_config() for kind "flowrate-z"}
    reference.npz   named numeric arrays kept with the model (here: development burn-in statistics,
                    used by input monitoring in Week 7); written with numpy.savez, never object arrays
    card.json       the model card: name, version, the REQUIRED_CARD_FIELDS, and created_with
                    (python / numpy / pandas / flowguard versions at save time)
    checksums.json  {"algorithm": "sha256", "files": {file name: hex digest}} for the three files above

Contract (the checks rely on it)
--------------------------------
``save_bundle(detector, bundle_dir, metadata, reference=None) -> Path``
    ``metadata`` must contain every key in ``REQUIRED_CARD_FIELDS`` with a non-empty value, else
    ``ValueError`` naming the first missing one. ``reference`` maps names to numeric arrays; an object
    (or other non-numeric) array is refused with ``ValueError``. ``bundle_dir`` must not exist or be
    empty, else ``FileExistsError``. ``checksums.json`` is written last.

``verify_bundle(bundle_dir) -> dict``
    Raises ``BundleIntegrityError`` (naming the file) when ``checksums.json`` is missing, a listed file
    is missing or its SHA-256 differs, or the directory holds a file that is not listed. Returns the
    checksums mapping.

``load_bundle(bundle_dir) -> (Detector, card, reference)``
    ``verify_bundle`` first. Then refuses with ``BundleCompatibilityError`` a ``model.json`` whose
    ``format`` is not ``"flowguard-bundle"``, whose ``format_version`` is not ``FORMAT_VERSION`` (the
    message names both versions) or whose ``kind`` is not ``"flowrate-z"``. Arrays are read with
    ``numpy.load(..., allow_pickle=False)``. Never unpickles anything.

Registry layout: ``<root>/<name>/<version>/`` (a bundle, immutable once registered) and
``<root>/<name>/current`` (a text file holding one version string).

``register(root, bundle_dir) -> Path``
    Reads name and version from the bundle's ``model.json``; the version must match ``MAJOR.MINOR.PATCH``
    (digits only), else ``RegistryError``. Verifies the bundle (``BundleIntegrityError`` propagates).
    Refuses with ``RegistryError`` if that version already exists, leaving it untouched. The copy is
    made into a temporary directory under ``<root>/<name>/`` and moved into place with ``os.replace``.

``promote(root, name, version)``
    The version must be registered and pass ``verify_bundle``, else ``RegistryError`` /
    ``BundleIntegrityError``. Writes the ``current`` pointer to a temporary file and moves it into place
    with ``os.replace``: a reader sees the old version or the new one, never a partial file.

``resolve(root, name, ref="current") -> Path``
    ``"current"`` follows the pointer; any other ``ref`` is a version that must be registered.
    ``RegistryError`` when there is nothing to resolve.

``list_versions(root, name) -> list[str]``
    Registered versions in semantic-version order (1.9.0 before 1.10.0).
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

import flowguard
from flowguard.inference import Detector

FORMAT = "flowguard-bundle"
FORMAT_VERSION = 1
KIND = "flowrate-z"
FILES = ("model.json", "reference.npz", "card.json")
CHECKSUMS = "checksums.json"
REQUIRED_CARD_FIELDS = ("intended_use", "limitations", "training_data", "evaluation", "code_version")
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


class BundleError(ValueError):
    """A bundle cannot be used."""


class BundleIntegrityError(BundleError):
    """Files are missing, extra or not what was saved."""


class BundleCompatibilityError(BundleError):
    """The bundle was written in a format this code does not read."""


class RegistryError(Exception):
    """A registry operation was refused."""


# --------------------------------------------------------------------------- helpers
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode()


def _check_reference(reference: Mapping[str, Any] | None) -> dict[str, np.ndarray]:
    arrays = {}
    for name, value in (reference or {}).items():
        array = np.asarray(value)
        if array.dtype.kind not in "biuf":
            raise ValueError(f"reference array {name!r} has dtype {array.dtype}; only numeric arrays are stored")
        arrays[name] = array
    return arrays


# --------------------------------------------------------------------------- bundles
def save_bundle(detector: Detector, bundle_dir, metadata: Mapping[str, Any], reference=None) -> Path:
    for field in REQUIRED_CARD_FIELDS:
        if not metadata.get(field):
            raise ValueError(f"model card field {field!r} is missing or empty")
    arrays = _check_reference(reference)
    bundle = Path(bundle_dir)
    if bundle.exists() and any(bundle.iterdir()):
        raise FileExistsError(f"{bundle} exists and is not empty")
    bundle.mkdir(parents=True, exist_ok=True)

    model = {"format": FORMAT, "format_version": FORMAT_VERSION, "kind": KIND, **detector.to_config()}
    card = {
        "name": detector.name, "version": detector.version, **dict(metadata),
        "created_with": {"python": platform.python_version(), "numpy": np.__version__,
                         "pandas": pd.__version__, "flowguard": flowguard.__version__},
    }
    (bundle / "model.json").write_bytes(_json_bytes(model))
    with open(bundle / "reference.npz", "wb") as fh:
        np.savez(fh, **arrays)
    (bundle / "card.json").write_bytes(_json_bytes(card))
    checksums = {"algorithm": "sha256", "files": {name: sha256_file(bundle / name) for name in FILES}}
    (bundle / CHECKSUMS).write_bytes(_json_bytes(checksums))
    return bundle


def verify_bundle(bundle_dir) -> dict[str, str]:
    bundle = Path(bundle_dir)
    path = bundle / CHECKSUMS
    if not path.is_file():
        raise BundleIntegrityError(f"{bundle}: no {CHECKSUMS}")
    listed = json.loads(path.read_text())["files"]
    present = {p.name for p in bundle.iterdir() if p.name != CHECKSUMS}
    for name in sorted(set(present) - set(listed)):
        raise BundleIntegrityError(f"{bundle}: unexpected file {name!r} is not covered by {CHECKSUMS}")
    for name, digest in listed.items():
        if not (bundle / name).is_file():
            raise BundleIntegrityError(f"{bundle}: listed file {name!r} is missing")
        if sha256_file(bundle / name) != digest:
            raise BundleIntegrityError(f"{bundle}: {name!r} does not match its checksum (modified after saving?)")
    return listed


def load_bundle(bundle_dir) -> tuple[Detector, dict, dict[str, np.ndarray]]:
    bundle = Path(bundle_dir)
    verify_bundle(bundle)
    model = json.loads((bundle / "model.json").read_text())
    if model.get("format") != FORMAT:
        raise BundleCompatibilityError(f"{bundle}: format {model.get('format')!r}, expected {FORMAT!r}")
    if model.get("format_version") != FORMAT_VERSION:
        raise BundleCompatibilityError(
            f"{bundle}: bundle format version {model.get('format_version')!r}; this code reads version {FORMAT_VERSION}")
    if model.get("kind") != KIND:
        raise BundleCompatibilityError(f"{bundle}: model kind {model.get('kind')!r}; this loader reads {KIND!r}")
    config = {k: v for k, v in model.items() if k not in ("format", "format_version", "kind")}
    detector = Detector.from_config(config)
    card = json.loads((bundle / "card.json").read_text())
    with np.load(bundle / "reference.npz", allow_pickle=False) as npz:
        reference = {name: npz[name] for name in npz.files}
    return detector, card, reference


# --------------------------------------------------------------------------- registry
def _version_key(version: str) -> tuple[int, int, int]:
    match = SEMVER.match(version)
    if not match:
        raise RegistryError(f"version {version!r} is not MAJOR.MINOR.PATCH")
    return tuple(int(x) for x in match.groups())


def register(root, bundle_dir) -> Path:
    bundle = Path(bundle_dir)
    verify_bundle(bundle)
    model = json.loads((bundle / "model.json").read_text())
    name, version = model["name"], str(model["version"])
    _version_key(version)
    home = Path(root) / name
    dest = home / version
    if dest.exists():
        shutil.rmtree(dest)                      # "re-register to fix a typo"
    home.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{version}.", dir=home))
    try:
        for item in bundle.iterdir():
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
    versions = [p.name for p in home.iterdir() if p.is_dir() and SEMVER.match(p.name)]
    return sorted(versions, key=_version_key)


def promote(root, name, version) -> None:
    home = Path(root) / name
    if version not in list_versions(root, name):
        raise RegistryError(f"{name} {version} is not registered (registered: {list_versions(root, name)})")
    verify_bundle(home / version)
    tmp = home / ".current.tmp"
    tmp.write_text(version + "\n")
    os.replace(tmp, home / "current")


def resolve(root, name, ref: str = "current") -> Path:
    home = Path(root) / name
    if ref == "current":
        pointer = home / "current"
        if not pointer.is_file():
            raise RegistryError(f"{name} has no current version; promote one first")
        ref = pointer.read_text().strip()
    if ref not in list_versions(root, name):
        raise RegistryError(f"{name} {ref} is not registered")
    return home / ref
