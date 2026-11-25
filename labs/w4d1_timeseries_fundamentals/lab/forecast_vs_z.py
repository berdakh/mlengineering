"""Forecast-residual detectors versus the w2d6 burn-in z-score, on the REAL SKAB data.

    python project/get_skab.py                                          # once, from the repo root
    python labs/w4d1_timeseries_fundamentals/lab/forecast_vs_z.py    # about 1 minute

This file is complete. It works once you have implemented flowguard.forecast.

Protocol (the same as Week 3, so the numbers are comparable):
* split: the frozen manifest from w3d1 (lab/splits/v2.json; 7 test, 27 development experiments);
* every model of normal behaviour is fitted on the first BURN_IN rows of each experiment and those
  rows are excluded from evaluation;
* the AR order p and every alarm threshold are chosen on the development experiments only;
* point-level PR-AUC on the test experiments with a cluster-bootstrap interval (one cluster per
  experiment; no test experiment belongs to an overlap group), and event-level recall, false alarms
  per hour and median detection delay at the development-chosen threshold.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "splits" / "v2.json"
sys.path.insert(0, str(HERE / "src"))

from flowguard.baselines import MaxAbsZScorer, SingleSensorZScorer, burn_in_scores  # noqa: E402
from flowguard.data import SENSOR_COLUMNS, load_raw  # noqa: E402
from flowguard.evaluation import evaluate_experiments  # noqa: E402
from flowguard.forecast import (ARForecaster, NaiveForecaster, acf,  # noqa: E402
                                burn_in_forecast_scores, cusum)
from flowguard.metrics import best_f1_threshold, pr_auc  # noqa: E402
from flowguard.splits import dev_experiments, load_splits, validate_splits  # noqa: E402
from flowguard.uncertainty import cluster_bootstrap  # noqa: E402

BURN_IN = 100
CLIP = 50.0          # a sensor that barely moved during burn-in has a tiny sigma; cap its scores
AR_ORDERS = (1, 2, 3, 5)
REPO_ROOT = next((p for p in HERE.parents if (p / "project" / "get_skab.py").is_file()), HERE)
DEFAULT_RAW = REPO_ROOT / "data" / "raw" / "skab"
SENSORS = list(SENSOR_COLUMNS)


def clip(s: np.ndarray) -> np.ndarray:
    return np.clip(np.nan_to_num(s, nan=0.0), 0.0, CLIP)


def ar_cusum(tidy, p: int, k: float = 0.5) -> np.ndarray:
    """max over sensors of the two-sided CUSUM of each sensor's standardised AR residual."""
    signed = burn_in_forecast_scores(tidy, lambda: ARForecaster(p), SENSORS, BURN_IN, signed=True)
    signed = np.clip(signed, -CLIP, CLIP)
    out = np.zeros(len(tidy))
    exp = tidy["experiment_id"].to_numpy()
    for e in tidy["experiment_id"].unique():
        rows = np.flatnonzero(exp == e)
        rows = rows[np.argsort(tidy["t"].to_numpy()[rows], kind="stable")]
        out[rows] = np.max([cusum(signed[rows, j], k) for j in range(len(SENSORS))], axis=0)
    return out


def masks(tidy, experiments):
    return (tidy["experiment_id"].isin(experiments) & (tidy["t"] >= BURN_IN)).to_numpy()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw-dir", default=str(DEFAULT_RAW))
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--json", default=None, help="also write the results table to this JSON file")
    args = ap.parse_args(argv)
    try:
        tidy = load_raw(args.raw_dir)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    manifest = load_splits(MANIFEST)          # frozen in w3d1; never redrawn
    validate_splits(manifest, tidy)
    dev, test = dev_experiments(manifest), manifest["test"]
    y = tidy["anomaly"].to_numpy()
    dev_m, test_m = masks(tidy, dev), masks(tidy, test)

    # ---- 1. autocorrelation of normal operation (burn-in rows of the development experiments)
    print("1. Lag-1 and lag-10 autocorrelation in the burn-in rows (median over development experiments)")
    burn = tidy[tidy["experiment_id"].isin(dev) & (tidy["t"] < BURN_IN)]
    for sensor in SENSORS:
        r = []
        for _, g in burn.groupby("experiment_id"):
            x = g.sort_values("t")[sensor].to_numpy(dtype=float)
            if x.std() > 0:
                r.append(acf(x, 10)[[1, 10]])
        r = np.array(r)
        print(f"   {sensor:<20} r1 = {np.median(r[:, 0]):+.2f}   r10 = {np.median(r[:, 1]):+.2f}   (n = {len(r)})")

    # ---- 2. choose the AR order on development experiments
    print("\n2. AR order chosen by development PR-AUC (max over sensors of |residual|/sigma)")
    ar_dev = {}
    for p in AR_ORDERS:
        s = clip(burn_in_forecast_scores(tidy, lambda p=p: ARForecaster(p), SENSORS, BURN_IN))
        ar_dev[p] = (pr_auc(y[dev_m], s[dev_m]), s)
        print(f"   p = {p}: development PR-AUC {ar_dev[p][0]:.3f}")
    best_p = max(AR_ORDERS, key=lambda p: ar_dev[p][0])
    print(f"   chosen p = {best_p}")

    scores = {
        "flow_rate abs z, burn-in (w2d6)": clip(burn_in_scores(lambda: SingleSensorZScorer("flow_rate"), tidy, BURN_IN)),
        "max abs z over sensors, burn-in": clip(burn_in_scores(MaxAbsZScorer, tidy, BURN_IN)),
        "naive residual, max over sensors": clip(burn_in_forecast_scores(tidy, NaiveForecaster, SENSORS, BURN_IN)),
        f"AR({best_p}) residual, max over sensors": ar_dev[best_p][1],
        f"AR({best_p}) residual + CUSUM (k=0.5)": ar_cusum(tidy, best_p),
    }

    # ---- 3. test table
    print("\n3. Test experiments (7). Point PR-AUC with 95% cluster-bootstrap interval; event metrics at the")
    print("   threshold that maximises F1 on the development experiments.")
    print("| detector | test PR-AUC [95% CI] | events detected | false alarms / h | median delay (s) |")
    print("|---|---|---|---|---|")
    exp = tidy["experiment_id"].to_numpy()
    rows_out = []
    for name, s in scores.items():
        per_exp = {e: {"y": y[(exp == e) & test_m], "s": s[(exp == e) & test_m]} for e in test}
        ci = cluster_bootstrap(lambda rs: pr_auc(np.concatenate([r["y"] for r in rs]),
                                                 np.concatenate([r["s"] for r in rs])),
                               per_exp, n_boot=args.n_boot, seed=0)
        threshold, _ = best_f1_threshold(y[dev_m], s[dev_m])
        test_tidy = tidy[tidy["experiment_id"].isin(test)]
        ev = evaluate_experiments(test_tidy, (s[tidy["experiment_id"].isin(test).to_numpy()] >= threshold),
                                  burn_in=BURN_IN)
        print(f"| {name} | {ci['estimate']:.3f} [{ci['low']:.3f}, {ci['high']:.3f}] | "
              f"{ev['n_detected']}/{ev['n_events']} | {ev['false_alarms_per_hour']:.1f} | {ev['median_delay_s']:.0f} |")
        rows_out.append({"detector": name, "pr_auc": ci["estimate"], "low": ci["low"], "high": ci["high"],
                         "threshold": float(threshold), "detected": ev["n_detected"], "events": ev["n_events"],
                         "false_alarms_per_hour": ev["false_alarms_per_hour"],
                         "median_delay_s": ev["median_delay_s"]})
    if args.json:
        Path(args.json).write_text(json.dumps({"best_p": best_p, "ar_dev": {p: v[0] for p, v in ar_dev.items()},
                                               "rows": rows_out}, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
