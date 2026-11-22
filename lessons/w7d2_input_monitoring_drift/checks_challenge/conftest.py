"""Fixtures for the w7d2 challenge checks: grades <target>/stream_monitor.py on SYNTHETIC streams."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent / "challenge" / "data"))

from tools.wbcheck import resolve_target  # noqa: E402
import make_stream  # noqa: E402

UNIT = "lessons/w7d2_input_monitoring_drift"
SEEDS = (0, 1, 2, 3, 4, 5, 6, 7)


@pytest.fixture(scope="session")
def monitor():
    path = resolve_target(UNIT, "challenge") / "stream_monitor.py"
    assert path.is_file(), f"no {path}"
    spec = importlib.util.spec_from_file_location("learner_stream_monitor", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def calendar() -> pd.DataFrame:
    return pd.read_csv(HERE.parent / "challenge" / "data" / "calendar.csv")


@pytest.fixture(scope="session")
def alerts_by_seed(monitor, calendar) -> dict[int, pd.DataFrame]:
    out = {}
    for seed in SEEDS:
        alerts = monitor.monitor_stream(make_stream.generate(seed), calendar)
        df = pd.DataFrame(alerts, columns=["day", "feature", "kind"])
        out[seed] = df
    return out
