"""End to end on a SYNTHETIC tidy table: the given replay simulator + your delayed_eval agree with the
ground truth once every label has arrived, and early estimates use only what had arrived."""
from __future__ import annotations

import importlib
import sys

import numpy as np
import pandas as pd
import pytest


def _tidy(n_runs=12, n=400, seed=1):
    rng = np.random.default_rng(seed)
    rows = []
    for k in range(n_runs):
        flow = 32 + 0.4 * rng.standard_normal(n)
        anomaly = np.zeros(n, dtype=int)
        anomaly[250:330] = 1
        if k % 3 != 0:                     # two runs in three have a visible fault
            flow[250:330] -= 6.0
        rows.append(pd.DataFrame({"experiment_id": f"valve1/{k}", "family": "valve1", "t": np.arange(n),
                                  "datetime": pd.Timestamp("2020-03-01") + pd.to_timedelta(np.arange(n), "s"),
                                  "flow_rate": flow, "anomaly": anomaly, "changepoint": 0}))
    return pd.concat(rows, ignore_index=True)


def test_full_labels_recover_truth_and_early_estimates_do_not_peek(de, target):
    sys.path.insert(0, str(target / "src"))
    try:
        replay = importlib.import_module("flowguard.replay")
        models = importlib.import_module("flowguard.models")
    finally:
        sys.path.remove(str(target / "src"))
    tidy = _tidy()
    order = sorted(tidy["experiment_id"].unique(), key=lambda e: int(e.split("/")[1]))
    tl = replay.build_timeline(tidy, order)
    _, alarms = replay.predict(models.BurnInZ(threshold=6.0), tl)
    faults = replay.faults(tl)
    policy = replay.LabelPolicy(miss_report_prob=1.0, duplicate_prob=0.5, correction_prob=0.5)
    verdicts, reports = replay.simulate_labels(alarms, faults, policy, seed=3)
    joined, report = de.join_verdicts(alarms, verdicts)
    r = de.recall_estimate(joined, reports, min_events=1)
    assert r["n_caught"] == 8 and r["n_caught"] + r["n_missed_reported"] == 12
    assert report["n_pending"] == 0
    first_label = min(verdicts["label_time"].min(), reports["label_time"].min())
    early, _ = de.join_verdicts(alarms, verdicts, as_of=first_label - pd.Timedelta(seconds=1))
    assert early["verdict"].isna().all()
