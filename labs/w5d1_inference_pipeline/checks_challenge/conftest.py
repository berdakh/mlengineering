"""Fixtures for the w5d1 challenge checks. Grades <target>/serve_scores.py, <target>/test_parity.py and
<target>/SKEW_REPORT.md. All runs are SYNTHETIC; the model is the committed challenge/model/logistic.json.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
UNIT_DIR = HERE.parent
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "labs/w5d1_inference_pipeline"
MODEL = json.loads((UNIT_DIR / "challenge" / "model" / "logistic.json").read_text())


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def oracle(run: pd.DataFrame, model: dict) -> np.ndarray:
    """The training path (w4d5 SupervisedLogistic arithmetic), independent of the learner's files."""
    n_burn = int(model["n_burn"])
    x = run[model["sensors"]].to_numpy(dtype=float)
    mean, std = x[:n_burn].mean(axis=0), x[:n_burn].std(axis=0)
    std = np.where(std > 0, std, 1.0)
    z = np.clip((x[n_burn:] - mean) / std, -model["z_clip"], model["z_clip"])
    return np.hstack([z, np.abs(z)]) @ np.asarray(model["coef"], dtype=float) + float(model["intercept"])


def make_run(n=260, seed=0, shift=0.0, sensor=-1, at=170):
    rng = np.random.default_rng(seed)
    run = pd.DataFrame({s: rng.normal(20 + 5 * i, 0.5 + 0.2 * i, n) for i, s in enumerate(MODEL["sensors"])})
    run.loc[at:, MODEL["sensors"][sensor]] += shift
    return run


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, "challenge")


@pytest.fixture(scope="session")
def serve(target):
    path = target / "serve_scores.py"
    assert path.is_file(), f"missing {path}"
    return load_module(path, "learner_serve_scores")
