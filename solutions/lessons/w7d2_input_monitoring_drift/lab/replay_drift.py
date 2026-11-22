"""Replay real SKAB runs through the input monitor and measure what it actually says.

    python lessons/w7d2_input_monitoring_drift/lab/replay_drift.py           # ~20 s

Given; you do not need to edit it, but read it. It uses YOUR ``flowguard.drift``.

Protocol (frozen manifest splits/v2.json; test experiments only for the final numbers):

* Windows: tumbling, 60 rows (one minute at 1 Hz), statistic W1, all 8 sensors.
* Two choices of reference, compared:
  A. **Global**: the first 300 rows (burn-in, always normal) of every development experiment, pooled.
  B. **Per run**: each run's own first 300 rows (the detector's convention since w2d5).
* Calibration: thresholds for a window-level false-alarm rate of 5 % on STABLE development data =
  rows 300 .. anomaly onset of each development run (normal operation after the burn-in).
* Evaluation on the 7 test runs, windows after the burn-in, labelled by their rows:
  normal (no anomalous row), anomalous (all rows anomalous), mixed (skipped).

Serving data is not a model decision, so replaying test runs does not spend the test set; no threshold
is chosen on them.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO_ROOT = next(p for p in HERE.parents if (p / "project" / "get_skab.py").is_file())
sys.path.insert(0, str(HERE / "src"))

from flowguard.data import SENSOR_COLUMNS, load_raw  # noqa: E402
from flowguard.drift import DriftMonitor, calibrate_thresholds  # noqa: E402
from flowguard.splits import dev_experiments, load_splits  # noqa: E402

WINDOW, BURN, TARGET = 60, 300, 0.05


def onset(run: pd.DataFrame) -> int:
    idx = np.flatnonzero(run["anomaly"].to_numpy() == 1)
    return int(idx[0]) if idx.size else len(run)


def windows_with_labels(run: pd.DataFrame, start: int):
    for s in range(start, len(run) - WINDOW + 1, WINDOW):
        w = run.iloc[s:s + WINDOW]
        frac = w["anomaly"].mean()
        yield s, w, ("normal" if frac == 0 else "anomalous" if frac == 1 else "mixed")


def evaluate(runs: dict[str, pd.DataFrame], reference_for, thresholds_for, start: int = BURN) -> pd.DataFrame:
    rows = []
    for exp, run in runs.items():
        mon = DriftMonitor(reference_for(run), SENSOR_COLUMNS, WINDOW, thresholds_for(exp))
        for s, w, label in windows_with_labels(run, start):
            rep = mon.window_stats(w)
            fired = sorted({sensor for sensor, kind, _, _ in rep.alerts if kind == "w1"})
            rows.append({"experiment": exp, "family": exp.split("/")[0], "start": s, "label": label,
                         "alert": bool(fired), "sensors": ",".join(fired),
                         "max_ratio": max(rep.stats[x]["w1"] / thresholds_for(exp)[x]["w1"] for x in SENSOR_COLUMNS)})
    return pd.DataFrame(rows)


def summarise(df: pd.DataFrame, name: str) -> dict:
    out = {"reference": name}
    for label in ("normal", "anomalous"):
        sub = df[df["label"] == label]
        out[f"{label}_windows"] = int(len(sub))
        out[f"{label}_alert_rate"] = round(float(sub["alert"].mean()), 3) if len(sub) else None
    for fam in ("valve1", "valve2", "other"):
        sub = df[(df["family"] == fam) & (df["label"] == "normal")]
        out[f"normal_alert_rate_{fam}"] = round(float(sub["alert"].mean()), 3) if len(sub) else None
    return out


def main() -> int:
    try:
        tidy = load_raw(REPO_ROOT / "data" / "raw" / "skab")
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    manifest = load_splits(HERE / "splits" / "v2.json")
    runs = {e: g.sort_values("t").reset_index(drop=True) for e, g in tidy.groupby("experiment_id")}
    dev = {e: runs[e] for e in dev_experiments(manifest)}
    test = {e: runs[e] for e in manifest["test"]}
    stable = {e: r.iloc[BURN:onset(r)] for e, r in dev.items()}

    # A. global reference
    ref_a = pd.concat([r.iloc[:BURN] for r in dev.values()], ignore_index=True)
    thr_a = calibrate_thresholds(ref_a, list(stable.values()), SENSOR_COLUMNS, WINDOW, "w1", TARGET)
    calib_a = evaluate(stable, lambda run: ref_a, lambda e: thr_a, start=0)
    res_a = evaluate(test, lambda run: ref_a, lambda e: thr_a)

    # B. per-run reference: calibrate on each dev run against its own burn-in, pooled per sensor
    stat_b: dict[str, list[float]] = {s: [] for s in SENSOR_COLUMNS}
    for e, r in dev.items():
        mon = DriftMonitor(r.iloc[:BURN], SENSOR_COLUMNS, WINDOW)
        for _, w, _ in windows_with_labels(r.iloc[:onset(r)], BURN):
            rep = mon.window_stats(w)
            for s in SENSOR_COLUMNS:
                stat_b[s].append(rep.stats[s]["w1"])
    level = 1 - TARGET / len(SENSOR_COLUMNS)
    thr_b = {s: {"w1": float(np.quantile(v, level, method="higher"))} for s, v in stat_b.items()}
    res_b = evaluate(test, lambda run: run.iloc[:BURN], lambda e: thr_b)

    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    summary = [summarise(calib_a, "A global (dev calibration windows, in-sample)"),
               summarise(res_a, "A global (test)"), summarise(res_b, "B per run (test)")]
    res_a.assign(reference="A").to_csv(out_dir / "windows_global.csv", index=False)
    res_b.assign(reference="B").to_csv(out_dir / "windows_per_run.csv", index=False)
    (out_dir / "thresholds.json").write_text(json.dumps({"A": thr_a, "B": thr_b}, indent=2))
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    pd.set_option("display.width", 160)
    print(pd.DataFrame(summary).set_index("reference").T.to_string())
    print("\nsensors that fire most on anomalous test windows (A):")
    fired = res_a[(res_a["label"] == "anomalous") & res_a["alert"]]["sensors"].str.split(",").explode()
    print(fired.value_counts().head(5).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
