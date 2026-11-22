"""Bundle the supervised logistic candidate (w4d5) without pickle, in the flowguard bundle layout.

Reference solution. Serialisation choice: store the *mathematics* of the fitted model, not the
scikit-learn object. A fitted LogisticRegression's decision function is ``X @ coef + intercept``; with
the calibration rule (burn-in mean/std, ddof=0, std 0 -> 1), the clip and the feature layout, that is
the whole function. JSON holds the parameters that define the layout, an ``.npz`` holds the numbers,
and loading needs NumPy only. The scikit-learn version used for training is recorded for provenance
but is not needed to load (see COMPATIBILITY.md).

``save_logistic(model, bundle_dir, metadata, *, version, name="flowguard-logistic") -> Path``
``load_logistic(bundle_dir) -> LoadedLogistic`` with ``score_run(run) -> ndarray``
"""
from __future__ import annotations

import json
import platform
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn

import flowguard
from flowguard.artifacts import (CHECKSUMS, FORMAT, FORMAT_VERSION, REQUIRED_CARD_FIELDS, BundleCompatibilityError,
                                 sha256_file, verify_bundle)
from flowguard.data import SENSOR_COLUMNS
from flowguard.detectors import Z_CLIP

KIND = "logistic-z"
SENSORS = list(SENSOR_COLUMNS)
FEATURES = [f"z:{s}" for s in SENSORS] + [f"abs_z:{s}" for s in SENSORS]   # the layout this loader implements
FILES = ("model.json", "weights.npz", "card.json")


def _json_bytes(obj) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode()


def save_logistic(model, bundle_dir, metadata, *, version: str, name: str = "flowguard-logistic") -> Path:
    if not hasattr(model, "model_"):
        raise ValueError("the model is not fitted")
    for field in REQUIRED_CARD_FIELDS:
        if not metadata.get(field):
            raise ValueError(f"model card field {field!r} is missing or empty")
    lr = model.model_
    coef = np.asarray(lr.coef_, dtype=np.float64).ravel()
    if coef.shape != (len(FEATURES),) or list(lr.classes_) != [0, 1]:
        raise ValueError("expected a binary logistic regression on the 16 z / |z| features")
    bundle = Path(bundle_dir)
    if bundle.exists() and any(bundle.iterdir()):
        raise FileExistsError(f"{bundle} exists and is not empty")
    bundle.mkdir(parents=True, exist_ok=True)
    spec = {"format": FORMAT, "format_version": FORMAT_VERSION, "kind": KIND, "name": name, "version": version,
            "n_burn": int(model.n_burn), "z_clip": float(Z_CLIP), "calibration": "burn-in mean and std (ddof=0), std 0 -> 1",
            "sensors": SENSORS, "features": FEATURES,
            "trained_with": {"scikit-learn": sklearn.__version__, "C": float(model.C)}}
    card = {"name": name, "version": version, **dict(metadata),
            "created_with": {"python": platform.python_version(), "numpy": np.__version__,
                             "scikit-learn": sklearn.__version__, "flowguard": flowguard.__version__}}
    (bundle / "model.json").write_bytes(_json_bytes(spec))
    with open(bundle / "weights.npz", "wb") as fh:
        np.savez(fh, coef=coef, intercept=np.zeros(1))
    (bundle / "card.json").write_bytes(_json_bytes(card))
    checksums = {"algorithm": "sha256", "files": {f: sha256_file(bundle / f) for f in FILES}}
    (bundle / CHECKSUMS).write_bytes(_json_bytes(checksums))
    return bundle


@dataclass(frozen=True)
class LoadedLogistic:
    name: str
    version: str
    n_burn: int
    z_clip: float
    coef: np.ndarray
    intercept: float

    def score_run(self, run: pd.DataFrame) -> np.ndarray:
        x = run[SENSORS].to_numpy(dtype=float)
        burn = x[: self.n_burn]
        mean, std = burn.mean(axis=0), burn.std(axis=0)
        std = np.where(std > 0, std, 1.0)
        z = np.clip((x[self.n_burn:] - mean) / std, -self.z_clip, self.z_clip)
        return np.hstack([z, np.abs(z)]) @ self.coef + self.intercept


def load_logistic(bundle_dir) -> LoadedLogistic:
    bundle = Path(bundle_dir)
    verify_bundle(bundle)
    spec = json.loads((bundle / "model.json").read_text())
    if spec.get("format") != FORMAT or spec.get("format_version") != FORMAT_VERSION:
        raise BundleCompatibilityError(
            f"{bundle}: format {spec.get('format')!r} v{spec.get('format_version')!r}; this loader reads {FORMAT!r} v{FORMAT_VERSION}")
    if spec.get("kind") != KIND:
        raise BundleCompatibilityError(f"{bundle}: kind {spec.get('kind')!r}; this loader reads {KIND!r}")
    if spec.get("features") != FEATURES or spec.get("sensors") != SENSORS:
        raise BundleCompatibilityError(f"{bundle}: feature layout differs from the one this loader implements")
    with np.load(bundle / "weights.npz", allow_pickle=False) as npz:
        coef, intercept = npz["coef"], npz["intercept"]
    if coef.shape != (len(FEATURES),) or intercept.shape != (1,):
        raise BundleCompatibilityError(f"{bundle}: weights have shapes {coef.shape}, {intercept.shape}")
    return LoadedLogistic(spec["name"], spec["version"], int(spec["n_burn"]), float(spec["z_clip"]),
                          coef, float(intercept[0]))
