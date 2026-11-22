"""Training/serving parity on the REAL test experiments: the batch command against the evaluated path.

    python project/get_skab.py                                       # once, from the repository root
    python lessons/w5d1_inference_pipeline/lab/build_model.py        # writes model/model.json
    python lessons/w5d1_inference_pipeline/lab/parity_report.py      # about 20 seconds

Given complete. It works once you have implemented flowguard.inference and flowguard.batch.

1. Export the 7 frozen test experiments as serving input: run_id, datetime, 8 sensors, NO labels.
2. Score them with ``predict_batch`` exactly as the CLI would, into results/predictions/.
3. Score them again with the path that was EVALUATED in w4d5 (``flowguard.detectors``).
4. Compare: scores, alarms, and the event metrics computed from each. Any difference is skew.
"""
from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

from flowguard.batch import load_detector, predict_batch  # noqa: E402
from flowguard.data import load_raw  # noqa: E402
from flowguard.detectors import candidates, score_experiments  # noqa: E402
from flowguard.evaluation import evaluate_experiments, extract_events  # noqa: E402
from flowguard.inference import serving_frame  # noqa: E402
from flowguard.metrics import pr_auc  # noqa: E402
from flowguard.splits import load_splits, validate_splits  # noqa: E402
from flowguard.uncertainty import wilson_interval  # noqa: E402

REPO_ROOT = next((p for p in HERE.parents if (p / "project" / "get_skab.py").is_file()), HERE)


def evaluated_path(test: pd.DataFrame, n_burn: int) -> np.ndarray:
    """The w4d5 code path: calibrate the flow-rate z-scorer per experiment, score every row."""
    flow_rate = next(c for c in candidates(n_burn) if c.name == "flow-rate |z|")
    return score_experiments(flow_rate, test, n_burn)


def report(name: str, test: pd.DataFrame, scores: np.ndarray, detector) -> dict:
    keep = test["t"].to_numpy() >= detector.n_burn
    ev = evaluate_experiments(test, np.nan_to_num(scores, nan=-np.inf) >= detector.threshold,
                              burn_in=detector.n_burn, min_duration=detector.min_duration,
                              merge_gap=detector.merge_gap)
    auc = pr_auc(test["anomaly"].to_numpy()[keep], scores[keep])
    lo, hi = wilson_interval(ev["n_detected"], ev["n_events"])
    delay = "missed" if math.isinf(ev["median_delay_s"]) else f"{ev['median_delay_s']:.0f} s"
    print(f"  {name:<28} PR-AUC {auc:.3f}; events {ev['n_detected']}/{ev['n_events']} (Wilson 95% "
          f"[{lo:.2f}, {hi:.2f}]); false alarms/h {ev['false_alarms_per_hour']:.2f}; median delay {delay}")
    return {"pr_auc": auc, **{k: ev[k] for k in ("n_detected", "n_events", "false_alarms_per_hour")}}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--raw-dir", default=str(REPO_ROOT / "data" / "raw" / "skab"))
    ap.add_argument("--model-dir", default=str(HERE / "model"))
    ap.add_argument("--out", default=str(HERE / "results"))
    args = ap.parse_args(argv)
    try:
        tidy = load_raw(args.raw_dir)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    manifest = load_splits(HERE / "splits" / "v2.json")
    validate_splits(manifest, tidy)
    test = tidy[tidy["experiment_id"].isin(manifest["test"])].reset_index(drop=True)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    input_csv = out / "test_input.csv"
    serving_frame(test).to_csv(input_csv, index=False)

    detector = load_detector(args.model_dir)
    t0 = time.perf_counter()
    manifest_out = predict_batch(args.model_dir, input_csv, out / "predictions", force=True)
    seconds = time.perf_counter() - t0
    served = pd.read_csv(out / "predictions" / "predictions.csv", float_precision="round_trip")
    evaluated = evaluated_path(test, detector.n_burn)

    keep = test["t"].to_numpy() >= detector.n_burn
    served_scores = served["score"].to_numpy()
    diff = np.abs(served_scores[keep] - evaluated[keep])
    print(f"batch: {manifest_out['input_rows']} rows, {manifest_out['runs']} runs in {seconds:.2f} s "
          f"({manifest_out['input_rows'] / seconds:,.0f} rows/s, including file I/O); runs failed: "
          f"{len(manifest_out['runs_failed'])}")
    print(f"burn-in rows reported as burn_in: {(served['status'][~keep] == 'burn_in').all()}; "
          f"scored rows: {(served['status'][keep] == 'scored').sum()} of {keep.sum()}")
    print(f"score parity on scored rows: max |served - evaluated| = {diff.max():.3g}")

    expected_alarm = np.zeros(len(test), dtype=int)
    for _, g in test.groupby("experiment_id", sort=False):
        g = g[g["t"] >= detector.n_burn].sort_values("t")
        flags = evaluated[g.index.to_numpy()] >= detector.threshold
        for s, e in extract_events(flags, detector.min_duration, detector.merge_gap):
            expected_alarm[g.index.to_numpy()[s:e]] = 1
    print(f"alarm parity: {int((served['alarm'].to_numpy() != expected_alarm).sum())} rows differ; "
          f"{int(served['alarm'].sum())} alarm rows in total")

    print("\nevent metrics on the 7 frozen test experiments (operating point fixed on development data):")
    a = report("evaluated path (w4d5 code)", test, evaluated, detector)
    b = report("served path (predict-batch)", test, served_scores, detector)
    same = all(np.isclose(a[k], b[k]) for k in a)
    print(f"\nidentical metrics: {same}")
    return 0 if same and diff.max() == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
