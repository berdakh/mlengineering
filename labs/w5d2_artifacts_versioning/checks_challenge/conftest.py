"""Fixtures for the w5d2 challenge checks. Grades <target>/logistic_bundle.py, <target>/COMPATIBILITY.md
and <target>/src/flowguard/artifacts.py (your lab module, copied). All data is SYNTHETIC.
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
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

UNIT = "labs/w5d2_artifacts_versioning"
SENSORS = ["accelerometer1_rms", "accelerometer2_rms", "current", "pressure",
           "temperature", "thermocouple", "voltage", "flow_rate"]
METADATA = {"intended_use": "SYNTHETIC check model.", "limitations": ["synthetic"],
            "training_data": {"source": "synthetic"}, "evaluation": {"note": "none"}, "code_version": "test"}


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, "challenge")


@pytest.fixture(scope="session")
def mods(target):
    assert (target / "src" / "flowguard" / "artifacts.py").is_file(), (
        "copy your finished lab module to challenge/src/flowguard/artifacts.py")
    sys.path[:0] = [str(target), str(target / "src")]
    for name in [m for m in sys.modules if m == "flowguard" or m.startswith("flowguard.") or m == "logistic_bundle"]:
        del sys.modules[name]
    out = {}
    try:
        out["artifacts"] = importlib.import_module("flowguard.artifacts")
        out["detectors"] = importlib.import_module("flowguard.detectors")
        out["lb"] = importlib.import_module("logistic_bundle")
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"could not import from {target}: {exc!r}", pytrace=False)
    return type("M", (), out)


def make_run(run_id, seed, n=260, fault=None, size=3.0):
    rng = np.random.default_rng(seed)
    data = {s: rng.normal(10 + 3 * i, 0.4 + 0.1 * i, n) for i, s in enumerate(SENSORS)}
    run = pd.DataFrame(data)
    run.insert(0, "t", np.arange(n))
    run.insert(0, "experiment_id", run_id)
    run["anomaly"] = 0
    if fault is not None:
        run.loc[150:, SENSORS[fault]] += size * (0.4 + 0.1 * fault)
        run.loc[150:, "anomaly"] = 1
    return run


@pytest.fixture(scope="session")
def trained(mods):
    runs = [make_run(f"e{i}", i, fault=(i % 8) if i % 3 else None, size=4.0 + i % 4) for i in range(12)]
    return mods.detectors.SupervisedLogistic(n_burn=100).fit(pd.concat(runs, ignore_index=True))


def rewrite_checksums(bundle: Path) -> None:
    path = bundle / "checksums.json"
    data = json.loads(path.read_text())
    data["files"] = {name: hashlib.sha256((bundle / name).read_bytes()).hexdigest() for name in data["files"]}
    path.write_text(json.dumps(data, indent=2))
