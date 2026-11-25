"""Worked example, part 2: exploratory analysis that changes a decision.

Uses the REAL SKAB files. Fetch them first:  python project/get_skab.py

    python labs/w2d3_data_quality_ingestion/example/explore_skab.py

Every block ends with the decision it forces; a plot or table that changes no
decision does not belong in an ingestion report.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw" / "skab"
sys.path.insert(0, str(ROOT / "solutions" / "labs" / "w2d3_data_quality_ingestion" / "lab" / "src"))

if not RAW.is_dir():
    sys.exit("data/raw/skab not found. Run:  python project/get_skab.py")

from flowguard.data import SENSOR_COLUMNS, load_raw  # noqa: E402

pd.set_option("display.width", 160)
tidy = load_raw(RAW)
labelled = tidy[tidy["family"] != "anomaly-free"]
print(f"rows={len(tidy)}  experiments={tidy['experiment_id'].nunique()}  labelled rows={len(labelled)}\n")

# 1. Sampling interval ------------------------------------------------------------------
step = tidy.groupby("experiment_id")["datetime"].diff().dt.total_seconds()
print("1. sampling interval (s):", step.value_counts().sort_index().head(4).to_dict(),
      f"... {int((step > 5).sum())} steps > 5 s")
gaps = tidy.loc[step > 5, ["experiment_id", "t", "anomaly"]].assign(gap_s=step[step > 5])
seg = labelled.groupby("experiment_id")["anomaly"].agg(
    start=lambda a: int(np.flatnonzero(a.to_numpy())[0]), end=lambda a: int(np.flatnonzero(a.to_numpy())[-1]))
gaps = gaps.join(seg, on="experiment_id")
gaps["where"] = np.where(gaps["t"] < gaps["start"], "before event",
                         np.where(gaps["t"] <= gaps["end"], "inside event", "after event"))
print(gaps.to_string(index=False))
print("   decision: a 'window of 60 rows' is not 60 s everywhere; windows must be defined in time or\n"
      "   must not span a gap (w2d5). Row-count windows are wrong in", gaps["experiment_id"].nunique(), "experiments.\n")

# 2. Class balance ----------------------------------------------------------------------
frac = labelled.groupby("experiment_id")["anomaly"].mean()
print("2. anomalous fraction per experiment: "
      f"min={frac.min():.3f} median={frac.median():.3f} max={frac.max():.3f}; pooled={labelled['anomaly'].mean():.3f}")
print(labelled.groupby("family")["anomaly"].agg(["mean", "size"]).round(3).to_string())
print("   decision: at point level this is NOT a rare-event problem (about 1 in 3 samples positive).\n"
      "   A constant 'always anomalous' scorer has precision ~0.35; PR-AUC must be read against that\n"
      "   base rate, and the unit that is scarce is the event (34), not the sample.\n")

# 3. Quantisation and constant runs ----------------------------------------------------------
def longest_run(x: np.ndarray) -> int:
    starts = np.flatnonzero(np.r_[True, x[1:] != x[:-1]])
    return int(np.diff(np.r_[starts, len(x)]).max())

per_exp = tidy.groupby("experiment_id")
table = pd.DataFrame({
    "min_distinct_values": per_exp[list(SENSOR_COLUMNS)].nunique().min(),
    "longest_constant_run": per_exp[list(SENSOR_COLUMNS)].agg(lambda s: longest_run(s.to_numpy())).max(),
    "min": tidy[list(SENSOR_COLUMNS)].min().round(3),
    "max": tidy[list(SENSOR_COLUMNS)].max().round(3),
})
print("3. per-sensor resolution (worst experiment) and range")
print(table.to_string())
print("   decision: pressure and flow_rate are coarsely quantised, so repeated values are normal.\n"
      "   A 'stuck sensor' rule must use a run length well above what quantisation produces\n"
      "   (longest real run: %d samples); the reference check warns at 120.\n" % table["longest_constant_run"].max())

# 4. Between-experiment versus within-experiment variation -------------------------------------
normal = labelled[labelled["anomaly"] == 0]
between = normal.groupby("experiment_id")[list(SENSOR_COLUMNS)].mean().std()
within = normal.groupby("experiment_id")[list(SENSOR_COLUMNS)].std().median()
print("4. normal-operation level: SD of experiment means / median within-experiment SD")
print((between / within).round(2).to_string())
print("   decision: where this ratio is well above 1 the experiment's own baseline dominates, exactly\n"
      "   like between-subject offsets in physiological recordings. Global thresholds on raw values will mostly detect\n"
      "   'which experiment is this'; features need per-experiment or causal rolling normalisation (w2d5).\n")

# 5. Family differences ---------------------------------------------------------------------
# Computed WITHIN each experiment first (anomalous mean - normal mean, in that experiment's own
# normal SD), then summarised per family. Pooling rows across experiments first would mix the
# fault effect with the between-experiment offsets measured in block 4.
def shift_within(g: pd.DataFrame) -> pd.Series:
    n, a = g[g["anomaly"] == 0][list(SENSOR_COLUMNS)], g[g["anomaly"] == 1][list(SENSOR_COLUMNS)]
    return (a.mean() - n.mean()) / n.std()

shifts = labelled.groupby("experiment_id")[["anomaly", *SENSOR_COLUMNS]].apply(shift_within)
shifts["family"] = shifts.index.str.split("/").str[0]
print("5. within-experiment shift under anomaly (normal-SD units): median per family")
print(shifts.groupby("family").median().round(2).T.to_string())
print("   share of experiments where the sensor moves by more than 1 SD in either direction")
print((shifts.drop(columns="family").abs() > 1).groupby(shifts["family"]).mean().round(2).T.to_string())
print("   decision: the families do not share one signature; a detector tuned on valve experiments\n"
      "   need not transfer to 'other'. This is why protocol B holds out a family (w2d4).")
