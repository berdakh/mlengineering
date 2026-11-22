"""Fixtures for the w5d2 lab checks. Grades <target>/src/flowguard/artifacts.py.

All data is SYNTHETIC. Bundles and registries live in pytest's temporary directories.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "lessons/w5d2_artifacts_versioning"
SENSORS = ("accelerometer1_rms", "accelerometer2_rms", "current", "pressure",
           "temperature", "thermocouple", "voltage", "flow_rate")


@pytest.fixture(scope="session")
def fg():
    target = resolve_target(UNIT, "lab")
    assert (target / "src" / "flowguard").is_dir(), f"no package found at {target}/src/flowguard"
    sys.path.insert(0, str(target / "src"))
    for name in [m for m in sys.modules if m == "flowguard" or m.startswith("flowguard.")]:
        del sys.modules[name]
    mods = {}
    for name in ("artifacts", "inference"):
        try:
            mods[name] = importlib.import_module(f"flowguard.{name}")
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"could not import flowguard.{name} from {target}/src: {exc!r}", pytrace=False)
    return type("FG", (), mods)


def make_detector(fg, version="1.0.0", threshold=4.0):
    return fg.inference.Detector(name="flowguard-test", version=version, sensor="flow_rate", n_burn=100,
                                 threshold=threshold, min_duration=5, merge_gap=3, metadata={"note": "synthetic"})


METADATA = {
    "intended_use": "SYNTHETIC test model for the w5d2 checks.",
    "limitations": ["Trained on nothing; scores synthetic runs only."],
    "training_data": {"source": "synthetic", "experiments": 0},
    "evaluation": {"note": "not evaluated"},
    "code_version": "test",
}


def reference_arrays():
    rng = np.random.default_rng(0)
    return {"burn_in_mean": rng.normal(30, 1, 27), "burn_in_std": rng.uniform(0.2, 0.6, 27)}


def serving_batch(n_runs=3, n=240):
    rng = np.random.default_rng(5)
    frames = []
    for r in range(n_runs):
        data = {"run_id": f"r{r}", "datetime": pd.date_range("2026-01-01", periods=n, freq="1s")}
        for i, s in enumerate(SENSORS):
            data[s] = rng.normal(10 + i, 0.5, n)
        run = pd.DataFrame(data)
        run.loc[160:, "flow_rate"] += 4.0 * r
        frames.append(run)
    return pd.concat(frames, ignore_index=True)


def rewrite_checksums(bundle: Path) -> None:
    """What an attacker or a careless script would do after editing a file: make the checksums agree."""
    path = bundle / "checksums.json"
    data = json.loads(path.read_text())
    data["files"] = {name: hashlib.sha256((bundle / name).read_bytes()).hexdigest() for name in data["files"]}
    path.write_text(json.dumps(data, indent=2))


@pytest.fixture()
def bundle(fg, tmp_path):
    return fg.artifacts.save_bundle(make_detector(fg), tmp_path / "bundle", METADATA, reference_arrays())
