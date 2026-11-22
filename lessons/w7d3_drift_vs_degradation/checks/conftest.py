"""Fixtures for the w7d3 lab checks. They grade <target>/src/flowguard/delayed_eval.py on SYNTHETIC
alarm, verdict and fault tables built here; no downloaded data is needed."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "lessons/w7d3_drift_vs_degradation"
T0 = pd.Timestamp("2027-03-01")


def day(d: float) -> pd.Timestamp:
    return T0 + pd.Timedelta(days=d)


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, "lab")


@pytest.fixture(scope="session")
def de(target):
    src = str(target / "src")
    for name in [m for m in sys.modules if m == "flowguard" or m.startswith("flowguard.")]:
        del sys.modules[name]
    sys.path.insert(0, src)
    try:
        return importlib.import_module("flowguard.delayed_eval")
    finally:
        sys.path.remove(src)


def alarms_table(rows):
    """rows: (alarm_id, start_day, peak_score)."""
    return pd.DataFrame([{"alarm_id": a, "run_id": "r", "experiment_id": "e", "start_time": day(s),
                          "end_time": day(s) + pd.Timedelta(minutes=5), "peak_score": p,
                          "model_version": "m-1.0.0"} for a, s, p in rows])


def verdicts_table(rows):
    """rows: (alarm_id, verdict, fault_id, label_day)."""
    return pd.DataFrame([{"alarm_id": a, "verdict": v, "fault_id": f, "label_time": day(t), "source": "maintenance"}
                         for a, v, f, t in rows], columns=["alarm_id", "verdict", "fault_id", "label_time", "source"])


def reports_table(rows):
    """rows: (fault_id, start_day, label_day)."""
    return pd.DataFrame([{"fault_id": f, "run_id": "r", "experiment_id": "e", "start_time": day(s),
                          "end_time": day(s) + pd.Timedelta(minutes=20), "label_time": day(t), "source": "inspection"}
                         for f, s, t in rows],
                        columns=["fault_id", "run_id", "experiment_id", "start_time", "end_time", "label_time", "source"])
