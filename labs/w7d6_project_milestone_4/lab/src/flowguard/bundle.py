"""Model artifact bundle: model.json + MANIFEST.json (schema, package version, provenance, checksums)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from flowguard import __version__
from flowguard.scoring import ZScoreModel

SCHEMA = "flowguard-bundle/1"


class BundleError(Exception):
    """The directory is not a loadable bundle."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_bundle(model: ZScoreModel, directory: str | Path, provenance: dict | None = None) -> Path:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    model_file = directory / "model.json"
    model_file.write_text(json.dumps(model.to_dict(), indent=2, sort_keys=True) + "\n")
    manifest = {"schema": SCHEMA, "package_version": __version__, "provenance": provenance or {},
                "files": {"model.json": _sha256(model_file)}}
    (directory / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return directory


def read_manifest(directory: str | Path) -> dict:
    path = Path(directory) / "MANIFEST.json"
    if not path.is_file():
        raise BundleError(f"no MANIFEST.json in {directory}")
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise BundleError(f"MANIFEST.json is not valid JSON: {exc}") from exc


def load_bundle(directory: str | Path) -> ZScoreModel:
    directory = Path(directory)
    manifest = read_manifest(directory)
    if manifest.get("schema") != SCHEMA:
        raise BundleError(f"unsupported bundle schema {manifest.get('schema')!r}")
    for name, digest in manifest.get("files", {}).items():
        path = directory / name
        if not path.is_file() or _sha256(path) != digest:
            raise BundleError(f"missing or modified bundle file: {name}")
    try:
        return ZScoreModel(**json.loads((directory / "model.json").read_text()))
    except (TypeError, json.JSONDecodeError) as exc:
        raise BundleError(f"model.json does not describe a ZScoreModel: {exc}") from exc
