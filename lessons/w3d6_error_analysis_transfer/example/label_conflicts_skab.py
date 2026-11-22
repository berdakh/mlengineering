"""Worked example (REAL SKAB data): errors the model cannot avoid, because the labels disagree.

    python project/get_skab.py                                                   # once
    python lessons/w3d6_error_analysis_transfer/example/label_conflicts_skab.py

Some SKAB files contain rows that are identical in timestamp and all eight sensors. Where the two
copies carry different `anomaly` labels, every detector that is a function of the sensors is wrong on
exactly one copy. This script counts those rows and shows what share of a baseline's errors they are.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO_ROOT = next(p for p in HERE.parents if (p / "project" / "get_skab.py").is_file())
sys.path.insert(0, str(REPO_ROOT / "solutions" / "lessons" / "w3d6_error_analysis_transfer" / "lab" / "src"))
if not (REPO_ROOT / "solutions" / "lessons" / "w3d6_error_analysis_transfer").is_dir():
    sys.path.insert(0, str(HERE.parent / "lab" / "src"))

from flowguard.baselines import SingleSensorZScorer, burn_in_scores  # noqa: E402
from flowguard.data import SENSOR_COLUMNS, load_raw  # noqa: E402

BURN_IN, THRESHOLD = 100, 2.577     # the w2d6 bar baseline and its development threshold (error_report.py)

try:
    tidy = load_raw(REPO_ROOT / "data" / "raw" / "skab")
except FileNotFoundError as exc:
    sys.exit(f"error: {exc}")

key = ["datetime", *SENSOR_COLUMNS]
labelled = tidy[tidy["family"] != "anomaly-free"].reset_index(drop=True)
dup = labelled[labelled.duplicated(key, keep=False)]
agreement = dup.groupby(key)["anomaly"].transform("nunique")
conflict = dup[agreement > 1]
print(f"labelled rows: {len(labelled)}")
print(f"rows that also occur in another labelled file: {len(dup)}")
print(f"of those, rows whose copies carry contradictory labels: {len(conflict)} "
      f"({conflict.groupby(key).ngroups} distinct measurements)")
print("\nby experiment:")
print(conflict.groupby("experiment_id")["anomaly"].agg(rows="size", labelled_anomalous="sum").to_string())

scores = burn_in_scores(lambda: SingleSensorZScorer("flow_rate"), labelled, BURN_IN)
flag = scores >= THRESHOLD
wrong = (flag.astype(int) != labelled["anomaly"].to_numpy()) & (labelled["t"].to_numpy() >= BURN_IN)
in_conflict = np.zeros(len(labelled), dtype=bool)
in_conflict[conflict.index.to_numpy()] = True
affected = sorted(conflict["experiment_id"].unique())
in_affected = labelled["experiment_id"].isin(affected).to_numpy()
print(f"\nbaseline errors in the affected experiments {affected}: {int((wrong & in_affected).sum())}")
print(f"  of which on contradictory rows: {int((wrong & in_conflict).sum())}")
print("note: burn-in normalisation depends on the file, so the two copies of a row can receive different")
print("scores. A model of the sensors alone must be wrong on at least one copy of each contradictory pair:")
print(f"  irreducible errors = {conflict.groupby(key).ngroups} of {len(conflict)} contradictory rows")
