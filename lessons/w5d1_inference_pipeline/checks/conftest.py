"""Fixtures for the w5d1 lab checks. Grades <target>/src/flowguard/{inference,batch}.py.

All data here is SYNTHETIC: a few short runs with the serving schema, some with a planted fault.
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

UNIT = "lessons/w5d1_inference_pipeline"
SENSORS = ("accelerometer1_rms", "accelerometer2_rms", "current", "pressure",
           "temperature", "thermocouple", "voltage", "flow_rate")
COLUMNS = ["run_id", "datetime", *SENSORS]


@pytest.fixture(scope="session")
def target() -> Path:
    t = resolve_target(UNIT, "lab")
    assert (t / "src" / "flowguard").is_dir(), f"no package found at {t}/src/flowguard"
    return t


@pytest.fixture(scope="session")
def fg(target):
    """The learner's flowguard package (imported fresh from <target>/src)."""
    sys.path.insert(0, str(target / "src"))
    for name in [m for m in sys.modules if m == "flowguard" or m.startswith("flowguard.")]:
        del sys.modules[name]
    mods = {}
    for name in ("inference", "batch", "detectors", "evaluation"):
        try:
            mods[name] = importlib.import_module(f"flowguard.{name}")
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"could not import flowguard.{name} from {target}/src: {exc!r}", pytrace=False)
    return type("FG", (), mods)


def make_run(run_id: str, n: int = 260, seed: int = 0, shift_at: int | None = None, shift_sd: float = 6.0,
             start: str = "2026-01-01 00:00:00") -> pd.DataFrame:
    """One SYNTHETIC run: 8 sensors with run-specific levels; optional step on flow_rate."""
    rng = np.random.default_rng(seed)
    data = {"run_id": run_id, "datetime": pd.date_range(start, periods=n, freq="1s")}
    for i, s in enumerate(SENSORS):
        level, sd = 5.0 + 3 * i + rng.normal(0, 2), 0.5 + 0.1 * i
        data[s] = rng.normal(level, sd, n)
    run = pd.DataFrame(data)
    if shift_at is not None:
        sd = run["flow_rate"].iloc[:100].std(ddof=0)
        run.loc[shift_at:, "flow_rate"] += shift_sd * sd
    return run[COLUMNS]


@pytest.fixture()
def batch_df() -> pd.DataFrame:
    """Three runs, two with a fault on flow_rate, rows shuffled across and within runs
    (as a message queue might deliver them). Timestamps are unique within a run."""
    runs = [make_run("r1", seed=1, shift_at=180), make_run("r2", seed=2),
            make_run("r3", n=300, seed=3, shift_at=150, start="2026-01-02 00:00:00")]
    df = pd.concat(runs, ignore_index=True)
    return df.iloc[np.random.default_rng(7).permutation(len(df))].reset_index(drop=True)


def as_tidy(df: pd.DataFrame) -> pd.DataFrame:
    """The serving frame as the evaluation path expects it: experiment_id, t (time order), datetime, sensors."""
    out = df.rename(columns={"run_id": "experiment_id"}).copy()
    out["t"] = out.groupby("experiment_id")["datetime"].rank(method="first").astype(int) - 1
    return out


@pytest.fixture()
def detector(fg):
    return fg.inference.Detector(name="flowguard-test", version="9.9.9", sensor="flow_rate", n_burn=100,
                                 threshold=4.0, min_duration=5, merge_gap=3)
