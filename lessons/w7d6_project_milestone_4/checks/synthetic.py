"""A tiny SYNTHETIC SKAB-format data set, split manifest and scenario for the w7d6 checks.

Six development and two test experiments of 600 rows each (1 Hz). Flow rate ~ N(level, 2) with a
per-experiment level in [98, 102]; experiments named t1/t2 are test, d1..d6 development. Faulty
experiments drop the flow by 30 L/min between rows 350 and 500. Nothing here is real data.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

COLUMNS = ["datetime", "Accelerometer1RMS", "Accelerometer2RMS", "Current", "Pressure", "Temperature",
           "Thermocouple", "Voltage", "Volume Flow RateRMS", "anomaly", "changepoint"]
N = 600
FAULT = (350, 500)
EXPERIMENTS = {"d1": False, "d2": True, "d3": False, "d4": True, "d5": False, "d6": True, "t1": False, "t2": True}

SCENARIO = """
name = "synthetic check scenario"
alarm_rate_budget = 0.05
drift_bins = 10
drift_quantile = 1.0

[model]
bad_threshold = 1.5
bad_version = "synthetic-bad-rc"

[[event]]
id = "S1-normal"
kind = "normal"
experiment = "valve1/t1"
rows = [0, 340]
expect = "no_alert"

[[event]]
id = "S2-units"
kind = "bad_input"
experiment = "valve1/t1"
rows = [0, 340]
scale = 60.0
expect = "out_of_support"

[[event]]
id = "S3-drift"
kind = "drift"
experiment = "valve1/t1"
rows = [0, 340]
scale = 0.8
expect = "drift"

[[event]]
id = "S4-fault"
kind = "fault"
experiment = "valve1/t2"
expect = "detector"

[[event]]
id = "S5-labels"
kind = "labels"
experiments = ["valve1/t1", "valve1/t2"]
expect = "delayed_eval"

[[event]]
id = "S6-promote-bad"
kind = "promote"
version = "bad"
reason = "check: mistyped threshold"
experiment = "valve1/t1"
rows = [0, 340]
expect = "alarm_rate"

[[event]]
id = "S7-rollback"
kind = "rollback"
reason = "check: alarm rate above budget"
experiment = "valve1/t1"
rows = [0, 340]
expect = "version_restored"
"""


def write(root: Path) -> dict:
    rng = np.random.default_rng(7)
    raw = root / "raw" / "valve1"
    raw.mkdir(parents=True, exist_ok=True)
    start = pd.Timestamp("2026-01-01 00:00:00")
    for name, faulty in EXPERIMENTS.items():
        level = rng.uniform(98, 102)
        flow = rng.normal(level, 2.0, N)
        anomaly = np.zeros(N, dtype=int)
        if faulty:
            flow[FAULT[0]:FAULT[1]] -= 30.0
            anomaly[FAULT[0]:FAULT[1]] = 1
        df = pd.DataFrame({c: rng.normal(1.0, 0.1, N) for c in COLUMNS[1:8]})
        df.insert(0, "datetime", (start + pd.to_timedelta(np.arange(N), unit="s")).strftime("%Y-%m-%d %H:%M:%S"))
        df["Volume Flow RateRMS"] = np.round(flow, 3)
        df["anomaly"] = anomaly.astype(float)
        df["changepoint"] = 0.0
        df.to_csv(raw / f"{name}.csv", sep=";", index=False)
    manifest = {"version": "v2", "unit": "experiment_id", "seed": 0,
                "test": ["valve1/t1", "valve1/t2"],
                "dev_folds": [["valve1/d1", "valve1/d2"], ["valve1/d3", "valve1/d4"], ["valve1/d5", "valve1/d6"]]}
    (root / "splits.json").write_text(json.dumps(manifest, indent=2))
    (root / "scenario.toml").write_text(SCENARIO)
    return {"raw": root / "raw", "splits": root / "splits.json", "scenario": root / "scenario.toml"}
