"""Model artifact bundles without pickle. SNAPSHOT written to the w5d2 description; given to you.

A bundle is a directory::

    <model_dir>/
        model.json       format version, model type, detector parameters, input schema, provenance
        checksums.json   SHA-256 of every other file in the bundle

The w5d2 format also allows an ``arrays.npz`` for models with array parameters (covariance
matrices, weights). The z-score detector has only scalars, so it has none.

``load_bundle`` verifies the checksums and the format before it builds anything, and raises
``BundleError`` with a message that says what is wrong. It never executes code from the bundle.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from flowguard.data import SENSOR_COLUMNS
from flowguard.inference import Detector

FORMAT_VERSION = 1
MODEL_TYPE = "flowguard.burn_in_z"


class BundleError(Exception):
    """The bundle is missing, incomplete, corrupted or incompatible."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_bundle(detector: Detector, out_dir: str | Path, provenance: dict | None = None) -> Path:
    """Write ``detector`` as a bundle into ``out_dir`` (created; existing files are overwritten)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    model = {
        "format_version": FORMAT_VERSION,
        "model_type": MODEL_TYPE,
        "model_version": detector.version,
        "params": detector.to_dict(),
        "input_schema": {"time_column": "datetime", "required": [detector.sensor],
                         "sensor_columns": list(SENSOR_COLUMNS)},
        "provenance": provenance or {},
    }
    (out / "model.json").write_text(json.dumps(model, indent=2, sort_keys=True) + "\n")
    checksums = {"model.json": _sha256(out / "model.json")}
    (out / "checksums.json").write_text(json.dumps(checksums, indent=2, sort_keys=True) + "\n")
    return out


def load_bundle(model_dir: str | Path) -> tuple[Detector, dict]:
    """Verify and load a bundle. Returns ``(detector, model_json)``. Raises ``BundleError``."""
    root = Path(model_dir) if model_dir is not None else None
    if root is None or not root.is_dir():
        raise BundleError(f"model directory not found: {model_dir}")
    try:
        checksums = json.loads((root / "checksums.json").read_text())
    except FileNotFoundError as exc:
        raise BundleError(f"{root}: checksums.json missing") from exc
    except json.JSONDecodeError as exc:
        raise BundleError(f"{root}: checksums.json is not valid JSON") from exc
    if "model.json" not in checksums:
        raise BundleError(f"{root}: checksums.json does not list model.json")
    for name, expected in checksums.items():
        path = root / name
        if not path.is_file():
            raise BundleError(f"{root}: {name} listed in checksums.json is missing")
        if _sha256(path) != expected:
            raise BundleError(f"{root}: checksum mismatch for {name}")
    model = json.loads((root / "model.json").read_text())
    if model.get("format_version") != FORMAT_VERSION:
        raise BundleError(f"{root}: unsupported format_version {model.get('format_version')!r}")
    if model.get("model_type") != MODEL_TYPE:
        raise BundleError(f"{root}: unsupported model_type {model.get('model_type')!r}")
    try:
        detector = Detector.from_dict(model["params"])
    except (KeyError, TypeError, ValueError) as exc:
        raise BundleError(f"{root}: invalid detector parameters: {exc}") from exc
    if detector.version != model.get("model_version"):
        raise BundleError(f"{root}: model_version does not match the parameters")
    return detector, model
