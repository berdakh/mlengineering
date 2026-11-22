"""Worked example: a trustworthy artifact for a small demand forecaster, without pickle.

    python lessons/w5d2_artifacts_versioning/example/demand_artifact.py      # under a second

SYNTHETIC data: 3 years of weekly demand for one product with trend, yearly season and noise. The
model is a ridge regression on lag-1, lag-52 and a trend term. The script

1. fits it and saves the *function*: a JSON spec (feature names in order, lags, version, training
   window, library versions) plus an .npz of the numbers, plus a SHA-256 for each file;
2. loads it back, verifying the hashes, and checks the forecasts are identical;
3. flips one bit in the weights file and shows the load is refused;
4. compares with the pickle of the scikit-learn object: what it contains and what loading it means.
"""
from __future__ import annotations

import hashlib
import io
import json
import pickle
import pickletools
import sys
import tempfile
from pathlib import Path

import numpy as np
import sklearn
from sklearn.linear_model import Ridge

FEATURES = ["lag_1", "lag_52", "trend"]


def make_series(weeks: int = 156, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.arange(weeks)
    return 200 + 0.8 * t + 40 * np.sin(2 * np.pi * t / 52) + rng.normal(0, 8, weeks)


def design(y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    t = np.arange(52, len(y))
    return np.column_stack([y[t - 1], y[t - 52], t]), y[52:]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(model: Ridge, folder: Path, n_train: int) -> None:
    spec = {"kind": "ridge-demand", "format_version": 1, "version": "1.0.0", "features": FEATURES,
            "trained_on_weeks": n_train, "alpha": model.alpha, "trained_with": {"scikit-learn": sklearn.__version__}}
    (folder / "spec.json").write_text(json.dumps(spec, indent=2, sort_keys=True))
    np.savez(folder / "weights.npz", coef=model.coef_, intercept=np.array([model.intercept_]))
    sums = {name: sha256(folder / name) for name in ("spec.json", "weights.npz")}
    (folder / "checksums.json").write_text(json.dumps(sums, indent=2))


def load(folder: Path):
    sums = json.loads((folder / "checksums.json").read_text())
    for name, digest in sums.items():
        if sha256(folder / name) != digest:
            raise ValueError(f"{name} does not match its checksum: refusing to load")
    spec = json.loads((folder / "spec.json").read_text())
    if spec["format_version"] != 1 or spec["features"] != FEATURES:
        raise ValueError("unsupported format or feature layout")
    with np.load(folder / "weights.npz", allow_pickle=False) as npz:
        coef, intercept = npz["coef"], float(npz["intercept"][0])
    return lambda X: X @ coef + intercept, spec


def main() -> int:
    y = make_series()
    X, target = design(y)
    model = Ridge(alpha=1.0).fit(X[:-12], target[:-12])          # last 12 weeks held out
    expected = model.predict(X[-12:])
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        save(model, folder, n_train=len(X) - 12)
        predict, spec = load(folder)
        print(f"files: " + ", ".join(f"{p.name} {p.stat().st_size} B" for p in sorted(folder.iterdir())))
        print(f"reloaded forecasts identical: {np.array_equal(predict(X[-12:]), expected)} "
              f"(max diff {np.abs(predict(X[-12:]) - expected).max():.3g})")
        weights = folder / "weights.npz"
        data = bytearray(weights.read_bytes())
        data[len(data) // 2] ^= 0x01
        weights.write_bytes(bytes(data))
        try:
            load(folder)
        except ValueError as exc:
            print(f"after flipping one bit in weights.npz: refused ({exc})")

    blob = pickle.dumps(model, protocol=5)
    globals_used = sorted({arg for op, arg, _ in pickletools.genops(blob)
                           if op.name in ("GLOBAL", "STACK_GLOBAL") and arg} |
                          {a for a in (str(x) for x in pickle_module_names(blob))})
    print(f"pickle of the Ridge object: {len(blob)} B; it names these importables, which are imported "
          f"and called when it is loaded: {globals_used}")
    return 0


def pickle_module_names(blob: bytes):
    """Module and attribute names that a STACK_GLOBAL pickle pushes as strings before importing them."""
    strings = [arg for op, arg, _ in pickletools.genops(blob) if op.name in ("SHORT_BINUNICODE", "BINUNICODE")]
    ops = [op.name for op, _, _ in pickletools.genops(blob)]
    out, i = [], 0
    for op, arg, _ in pickletools.genops(blob):
        if op.name in ("SHORT_BINUNICODE", "BINUNICODE"):
            out.append(arg)
    # keep the dotted ones: module paths are what get imported
    return [s for s in out if "." in s and s.startswith(("sklearn", "numpy", "_codecs", "copyreg", "builtins"))]


if __name__ == "__main__":
    sys.exit(main())
