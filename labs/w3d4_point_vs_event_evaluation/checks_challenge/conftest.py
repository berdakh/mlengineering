"""Fixtures for the w3d4 challenge checks. Grades <target>/operating_point.py. All data is SYNTHETIC.

``flowguard`` is taken from <target>/src if present, otherwise from <target>/../lab/src (your lab
package), exactly as challenge/_paths.py does. Finish the lab first.
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

UNIT = "labs/w3d4_point_vs_event_evaluation"
SENSORS = ("accelerometer1_rms", "accelerometer2_rms", "current", "pressure",
           "temperature", "thermocouple", "voltage", "flow_rate")


@pytest.fixture(scope="session")
def op():
    target = resolve_target(UNIT, "challenge")
    assert (target / "operating_point.py").is_file(), f"no operating_point.py in {target}"
    sys.path.insert(0, str(target))
    try:
        return importlib.import_module("operating_point")
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"could not import operating_point from {target}: {exc!r}", pytrace=False)


@pytest.fixture(scope="session")
def evaluate(op):
    return importlib.import_module("flowguard.evaluation").evaluate_experiments


@pytest.fixture(scope="session")
def dev():
    """SYNTHETIC development set: 6 experiments of 1500 rows at 1 Hz, one 300-row event each.

    Scores are unit-variance noise plus a step during the event whose size differs by experiment,
    plus short spurious bursts in normal operation and a large artefact in the first 50 rows.
    """
    rng = np.random.default_rng(42)
    frames, scores = [], []
    for k, step in enumerate((0.9, 1.4, 2.0, 2.6, 3.2, 4.0)):
        n = 1500
        y = np.zeros(n, dtype=int)
        y[800:1100] = 1
        s = rng.standard_normal(n) + step * y
        s[:50] += 9.0                                           # calibration artefact, inside the burn-in
        for start in rng.choice(np.arange(100, 700), size=3, replace=False):
            s[start:start + 3] += 4.0                           # 3-row spikes
        if k % 2 == 0:
            s[1300:1312] += 3.5                                 # a 12-row burst after the event
        frame = pd.DataFrame({
            "experiment_id": f"valve1/{k}", "family": "valve1", "t": np.arange(n),
            "datetime": pd.Timestamp("2024-01-01") + pd.to_timedelta(np.arange(n) + 5000 * k, unit="s"),
        })
        for name in SENSORS:
            frame[name] = 0.0
        frame["anomaly"] = y
        frame["changepoint"] = 0
        frames.append(frame)
        scores.append(s)
    return pd.concat(frames, ignore_index=True), np.concatenate(scores)


GRID = {"thresholds": (1.5, 2.0, 2.5, 3.0, 4.0), "min_durations": (1, 5, 20), "merge_gaps": (0, 5)}
BURN_IN = 50


@pytest.fixture(scope="session")
def grid():
    return GRID


@pytest.fixture(scope="session")
def table(dev, evaluate):
    """Every grid configuration evaluated on dev with the target's own flowguard.evaluation."""
    tidy, scores = dev
    rows = []
    for th in GRID["thresholds"]:
        for md in GRID["min_durations"]:
            for mg in GRID["merge_gaps"]:
                r = evaluate(tidy, scores >= th, burn_in=BURN_IN, min_duration=md, merge_gap=mg)
                rows.append({"threshold": th, "min_duration": md, "merge_gap": mg,
                             "rate": r["false_alarms_per_hour"], "recall": r["event_recall"],
                             "delay": r["median_delay_s"], "n_false": r["n_false_alarms"], "hours": r["normal_hours"]})
    return pd.DataFrame(rows)
