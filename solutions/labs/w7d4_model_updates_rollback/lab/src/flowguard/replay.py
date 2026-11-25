"""Replay SKAB experiments as a production timeline, with labels that arrive later. Given to you.

Production is simulated, not observed. ``build_timeline`` places experiment ``k`` of an ordered list
at ``start + k * spacing`` (one recording per day by default), keeping each recording's own timing.
``predict`` runs the deployed model at prediction time and writes what a service would log.
``simulate_labels`` then decides which outcomes the plant *ever* learns, and when:

* **Alarm verdicts.** An investigated alarm gets a verdict after ``verdict_delay_days`` (uniform):
  ``True`` if it overlaps a labelled fault of the same recording, else ``False``. With
  ``investigate_fraction < 1`` only the alarms with the highest peak scores are investigated; the
  rest stay unlabelled for ever (operators look at the alarms that look worst).
* **Missed faults.** A fault that no alarm overlapped is found by a later inspection with
  probability ``miss_report_prob``, after ``miss_report_delay_days``. Otherwise nobody learns of it.
* **Messiness.** With ``duplicate_prob`` a verdict is sent twice, the second copy later. With
  ``correction_prob`` the first copy was wrong and the later one corrects it, so the latest verdict
  for an alarm is the one to trust. Arrival order is whatever the delays produce, not alarm order.

Every output carries the ids needed for a join: ``alarm_id`` for verdicts, ``fault_id`` for both
verdicts (the fault an alarm was confirmed against) and fault reports.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from flowguard.evaluation import extract_events
from flowguard.models import BurnInZ


@dataclass(frozen=True)
class LabelPolicy:
    verdict_delay_days: tuple[float, float] = (2.0, 10.0)
    investigate_fraction: float = 1.0
    miss_report_prob: float = 0.0
    miss_report_delay_days: tuple[float, float] = (14.0, 60.0)
    duplicate_prob: float = 0.0
    correction_prob: float = 0.0


def build_timeline(tidy: pd.DataFrame, order: list[str], start: str = "2027-01-04",
                   spacing: str = "1D", transform=None) -> pd.DataFrame:
    """Experiments in ``order`` placed one per ``spacing``. ``transform(k, frame) -> frame`` may edit a
    recording (e.g. a recalibrated sensor) before it is placed; the edit is the caller's to state."""
    origin, step = pd.Timestamp(start), pd.Timedelta(spacing)
    parts = []
    for k, eid in enumerate(order):
        g = tidy[tidy["experiment_id"] == eid].sort_values("t").copy()
        if g.empty:
            raise ValueError(f"unknown experiment {eid}")
        if transform is not None:
            g = transform(k, g)
        g["datetime"] = origin + k * step + (g["datetime"] - g["datetime"].iloc[0])
        g["slot"] = k
        g["run_id"] = f"{k:03d}:{eid}"
        parts.append(g)
    return pd.concat(parts, ignore_index=True)


def predict(model: BurnInZ, timeline: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """What the service logs at prediction time: per-sample predictions and alarm events."""
    preds, alarms = [], []
    for run_id, g in timeline.groupby("run_id", sort=False):
        scores = model.score_run(g)
        flags = model.flags(scores)
        times = g["datetime"].to_numpy()
        preds.append(pd.DataFrame({
            "prediction_id": [f"{run_id}#{t}" for t in g["t"]], "run_id": run_id,
            "experiment_id": g["experiment_id"].to_numpy(), "datetime": times,
            "score": scores, "flag": flags, "model_version": model.label}))
        for j, (s, e) in enumerate(extract_events(flags.astype(int), model.min_duration, model.merge_gap)):
            alarms.append({"alarm_id": f"{run_id}/a{j}", "run_id": run_id,
                           "experiment_id": g["experiment_id"].iloc[0],
                           "start_time": times[s], "end_time": times[e - 1],
                           "peak_score": float(np.nanmax(scores[s:e])), "model_version": model.label})
    alarm_cols = ["alarm_id", "run_id", "experiment_id", "start_time", "end_time", "peak_score", "model_version"]
    return pd.concat(preds, ignore_index=True), pd.DataFrame(alarms, columns=alarm_cols)


def faults(timeline: pd.DataFrame) -> pd.DataFrame:
    """Ground truth (known to the simulator only): labelled anomalous segments as fault events."""
    rows = []
    for run_id, g in timeline.groupby("run_id", sort=False):
        times = g["datetime"].to_numpy()
        for j, (s, e) in enumerate(extract_events(g["anomaly"].to_numpy())):
            rows.append({"fault_id": f"{run_id}/f{j}", "run_id": run_id,
                         "experiment_id": g["experiment_id"].iloc[0],
                         "start_time": times[s], "end_time": times[e - 1]})
    return pd.DataFrame(rows, columns=["fault_id", "run_id", "experiment_id", "start_time", "end_time"])


def _overlapping_fault(alarm, fault_table: pd.DataFrame):
    same = fault_table[fault_table["run_id"] == alarm["run_id"]]
    hit = same[(same["start_time"] <= alarm["end_time"]) & (same["end_time"] >= alarm["start_time"])]
    return None if hit.empty else hit["fault_id"].iloc[0]


def simulate_labels(alarms: pd.DataFrame, fault_table: pd.DataFrame, policy: LabelPolicy,
                    seed: int = 0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return ``(verdicts, fault_reports)`` as they would arrive, in arrival (label_time) order."""
    rng = np.random.default_rng(seed)
    day = pd.Timedelta(days=1)
    n_investigate = int(round(policy.investigate_fraction * len(alarms)))
    investigated = set(alarms.sort_values("peak_score", ascending=False)["alarm_id"].head(n_investigate))
    verdicts, caught = [], set()
    for _, a in alarms.iterrows():
        fid = _overlapping_fault(a, fault_table)
        if fid is not None:
            caught.add(fid)
        if a["alarm_id"] not in investigated:
            continue
        t = a["end_time"] + rng.uniform(*policy.verdict_delay_days) * day
        truth = {"alarm_id": a["alarm_id"], "verdict": fid is not None, "fault_id": fid, "source": "maintenance"}
        if rng.random() < policy.duplicate_prob:
            if rng.random() < policy.correction_prob:  # a wrong first verdict, corrected later
                verdicts.append({**truth, "verdict": fid is None, "fault_id": None, "label_time": t})
            else:                                      # the same verdict sent twice
                verdicts.append({**truth, "label_time": t})
            t = t + rng.uniform(0.5, 5.0) * day
        verdicts.append({**truth, "label_time": t})
    reports = []
    for _, f in fault_table.iterrows():
        if f["fault_id"] in caught or rng.random() >= policy.miss_report_prob:
            continue
        reports.append({"fault_id": f["fault_id"], "run_id": f["run_id"], "experiment_id": f["experiment_id"],
                        "start_time": f["start_time"], "end_time": f["end_time"],
                        "label_time": f["end_time"] + rng.uniform(*policy.miss_report_delay_days) * day,
                        "source": "inspection"})
    v = pd.DataFrame(verdicts, columns=["alarm_id", "verdict", "fault_id", "label_time", "source"])
    r = pd.DataFrame(reports, columns=["fault_id", "run_id", "experiment_id", "start_time", "end_time",
                                       "label_time", "source"])
    return (v.sort_values("label_time", kind="stable").reset_index(drop=True),
            r.sort_values("label_time", kind="stable").reset_index(drop=True))
