"""Fixtures for the w5d3 lab checks. Grades <target>/src/flowguard/streaming.py.

All data here is SYNTHETIC (generated below); no downloaded data is needed.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "labs/w5d3_online_inference"


def _import_fresh(src: Path):
    sys.path.insert(0, str(src))
    for name in [m for m in sys.modules if m == "flowguard" or m.startswith("flowguard.")]:
        del sys.modules[name]
    return importlib.import_module("flowguard.inference"), importlib.import_module("flowguard.streaming")


@pytest.fixture(scope="session")
def mods():
    target = resolve_target(UNIT, "lab")
    src = target / "src"
    assert (src / "flowguard" / "streaming.py").is_file(), f"no {src}/flowguard/streaming.py"
    try:
        inference, streaming = _import_fresh(src)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"could not import flowguard.streaming from {src}: {exc!r}", pytrace=False)
    return inference, streaming


@pytest.fixture(scope="session")
def stream(mods):
    return mods[1]


@pytest.fixture(scope="session")
def detector(mods):
    return mods[0].Detector(n_burn=50, threshold=3.0, version="synthetic-test-1")


def make_run(n: int = 400, seed: int = 0, shift_at: int | None = 300, level: float = 120.0,
             start: str = "2026-01-01 00:00:00") -> pd.DataFrame:
    """SYNTHETIC run: 1 Hz flow-rate around ``level`` with a step fault from ``shift_at``."""
    rng = np.random.default_rng(seed)
    x = level + rng.normal(0.0, 0.7, n)
    if shift_at is not None:
        x[shift_at:] -= 6.0
    times = pd.date_range(start, periods=n, freq="1s")
    return pd.DataFrame({"datetime": times, "flow_rate": x, "pressure": rng.normal(0.1, 0.01, n)})


def stream_scores(scorer, run: pd.DataFrame) -> np.ndarray:
    out = []
    for row in run.to_dict("records"):
        r = scorer.update(row)
        out.append(np.nan if r.score is None else r.score)
    return np.array(out, dtype=float)


def assert_parity(batch: np.ndarray, streamed: np.ndarray) -> None:
    assert batch.shape == streamed.shape
    np.testing.assert_array_equal(np.isnan(batch), np.isnan(streamed),
                                  err_msg="streamed None/score positions differ from batch NaN/score positions")
    ok = ~np.isnan(batch)
    np.testing.assert_allclose(streamed[ok], batch[ok], rtol=1e-9, atol=1e-9,
                               err_msg="streamed scores differ from Detector.score_batch")
