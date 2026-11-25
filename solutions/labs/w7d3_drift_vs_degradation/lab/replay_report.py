"""Replay SKAB valve recordings as 60 days of production and monitor them with delayed labels.

    python project/get_skab.py                                              # once, from the repo root
    python labs/w7d3_drift_vs_degradation/lab/replay_report.py           # about 30 s
    python labs/w7d3_drift_vs_degradation/lab/replay_report.py --json results/replay.json

Given complete; it works once you have implemented ``flowguard.delayed_eval``.

What is real and what is constructed (state this whenever you quote a number from here):
* The sensor recordings, the fault labels and the model (w4d5's flow-rate |z|, threshold 7.2441,
  min_duration 30, merge_gap 10) are real.
* The production timeline is CONSTRUCTED: the 20 labelled valve recordings (valve1/*, valve2/*), in
  id order, one per day, three times over:
    - days  0-19  period A: as recorded;
    - days 20-39  period B: the same recordings with the flow sensor "recalibrated" to
                  1.08 * flow + 2.5 L/min (a stated edit of the real values);
    - days 40-59  period C: the same recordings, scored by a release whose configuration
                  regression doubled the threshold (14.488 instead of 7.244).
* The labels arrive by a SIMULATED policy (flowguard.replay.LabelPolicy below).
The drift monitor watches the model's only input (flow_rate) with PSI, calibrated on the flow rate
of the 16 development valve recordings of the frozen manifest v2, for windows of 5 days.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

from flowguard.data import load_raw  # noqa: E402
from flowguard.delayed_eval import join_verdicts, monitor_report, window_metrics  # noqa: E402
from flowguard.drift import DriftMonitor  # noqa: E402
from flowguard.models import BurnInZ  # noqa: E402
from flowguard.replay import LabelPolicy, build_timeline, faults, predict, simulate_labels  # noqa: E402
from flowguard.splits import dev_experiments, load_splits  # noqa: E402

REPO_ROOT = next((p for p in HERE.parents if (p / "project" / "get_skab.py").is_file()), HERE)
START = pd.Timestamp("2027-01-04")
WINDOW = "5D"
POLICY = LabelPolicy(verdict_delay_days=(2, 10), investigate_fraction=1.0, miss_report_prob=0.6,
                     miss_report_delay_days=(14, 60), duplicate_prob=0.1, correction_prob=0.5)
AS_OF_DAYS = (65, 90, 150)  # days after the timeline starts (it ends on day 60)


def recalibrate(_k: int, g: pd.DataFrame) -> pd.DataFrame:
    return g.assign(flow_rate=1.08 * g["flow_rate"] + 2.5)


def run(raw_dir: Path) -> dict:
    tidy = load_raw(raw_dir)
    manifest = load_splits(HERE / "splits" / "v2.json")
    valve = sorted((e for e in tidy["experiment_id"].unique() if e.startswith("valve")),
                   key=lambda e: (e.split("/")[0], int(e.split("/")[1])))
    shipped = BurnInZ()
    regressed = BurnInZ(version="1.0.1", threshold=2 * shipped.threshold)
    periods = [("A", valve, None, shipped), ("B", valve, recalibrate, shipped), ("C", valve, None, regressed)]
    timelines, preds, alarms = [], [], []
    for p, (name, order, transform, model) in enumerate(periods):
        tl = build_timeline(tidy, order, start=str(START + pd.Timedelta(days=20 * p)), transform=transform)
        tl["run_id"] = name + tl["run_id"]
        pr, al = predict(model, tl)
        timelines.append(tl.assign(period=name))
        preds.append(pr.assign(period=name))
        alarms.append(al.assign(period=name))
    timeline = pd.concat(timelines, ignore_index=True)
    alarms = pd.concat(alarms, ignore_index=True)
    truth = faults(timeline)
    verdicts, reports = simulate_labels(alarms, truth, POLICY, seed=0)

    # Drift monitor on the model's input, calibrated on development data only.
    dev_valve = [e for e in dev_experiments(manifest) if e.startswith("valve")]
    ref = tidy[tidy["experiment_id"].isin(dev_valve)].sort_values(["experiment_id", "t"])["flow_rate"].to_numpy()
    edges = [START + pd.Timedelta(days=5 * k) for k in range(13)]
    sizes = [((timeline["datetime"] >= lo) & (timeline["datetime"] < hi)).sum() for lo, hi in zip(edges[:-1], edges[1:])]
    monitor = DriftMonitor({"flow_rate": ref}, statistic="psi", quantile=0.99).calibrate(int(np.median(sizes)))
    drift = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        w = timeline[(timeline["datetime"] >= lo) & (timeline["datetime"] < hi)]
        drift.append(monitor.check({"flow_rate": w["flow_rate"].to_numpy()}))

    # Truth per window (known to the simulator only): faults caught / faults.
    caught_truth = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        f = truth[(truth["start_time"] >= lo) & (truth["start_time"] < hi)]
        j, _ = join_verdicts(alarms, verdicts)  # every label, as if all had arrived
        caught = set(j[j["verdict"].fillna(False).astype(bool)]["fault_id"]) & set(f["fault_id"])
        caught_truth.append((len(caught), len(f)))

    # Performance per period (20-day window), judged against period A's recall once all labels arrived.
    period_edges = [START + pd.Timedelta(days=20 * k) for k in range(4)]
    final = window_metrics(alarms, verdicts, reports, START, period_edges[-1], "20D")
    baseline = {"precision": None, "recall": float(final.loc[0, "recall"])}
    out = {"n_samples": int(len(timeline)), "n_alarms": int(len(alarms)), "n_faults": int(len(truth)),
           "n_verdicts": int(len(verdicts)), "n_fault_reports": int(len(reports)),
           "psi_threshold": monitor.thresholds["flow_rate"], "baseline": baseline,
           "drift_windows": [{"days": f"{5 * i}-{5 * i + 4}", "period": "ABC"[i // 4],
                              "psi": d["per_column"]["flow_rate"]["value"], "drift": d["drift"],
                              "true_caught": caught_truth[i][0], "faults": caught_truth[i][1]}
                             for i, d in enumerate(drift)],
           "five_day_windows": [], "periods": {}, "recall_over_time": []}
    w5 = window_metrics(alarms, verdicts, reports, START, period_edges[-1], WINDOW,
                        as_of=START + pd.Timedelta(days=150))
    out["five_day_windows"] = w5[["n_alarms", "n_caught", "n_missed_reported", "recall", "recall_status"]].to_dict("records")
    for day in AS_OF_DAYS:
        as_of = START + pd.Timedelta(days=day)
        wm = window_metrics(alarms, verdicts, reports, START, period_edges[-1], "20D", as_of=as_of)
        for i, w in wm.iterrows():
            flagged = sum(d["drift"] for d in drift[4 * i:4 * i + 4])
            rep = monitor_report({"drift": flagged > 2}, w, baseline, margin=0.1)
            out["periods"].setdefault("ABC"[i], {})[f"day {day}"] = {
                "drift_windows_flagged": f"{flagged}/4", "alarms": int(w["n_alarms"]),
                "precision": w["precision"], "caught": int(w["n_caught"]),
                "missed_reported": int(w["n_missed_reported"]), "recall": w["recall"],
                "recall_interval": [w["recall_low"], w["recall_high"]], "recall_status": w["recall_status"],
                "true_recall": f"{sum(c for c, _ in caught_truth[4 * i:4 * i + 4])}/20",
                "input_changed": rep["input_changed"], "model_ok": rep["model_ok"], "action": rep["action"]}
    for day in range(20, 205, 5):
        as_of = START + pd.Timedelta(days=day)
        wm = window_metrics(alarms, verdicts, reports, START, period_edges[-1], "20D", as_of=as_of)
        out["recall_over_time"].append({"day": day, **{f"recall_{n}": wm.loc[i, "recall"] for i, n in enumerate("ABC")},
                                        **{f"n_{n}": int(wm.loc[i, "n_caught"] + wm.loc[i, "n_missed_reported"])
                                           for i, n in enumerate("ABC")}})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--raw-dir", default=str(REPO_ROOT / "data" / "raw" / "skab"))
    ap.add_argument("--json", help="also write the results to this JSON file")
    args = ap.parse_args(argv)
    if not Path(args.raw_dir).is_dir():
        print(f"error: {args.raw_dir} not found; run python project/get_skab.py first", file=sys.stderr)
        return 2
    out = run(Path(args.raw_dir))
    print(f"{out['n_samples']} samples, {out['n_alarms']} alarms, {out['n_faults']} faults; "
          f"{out['n_verdicts']} verdict messages, {out['n_fault_reports']} missed-fault reports")
    print(f"PSI threshold (99th percentile over 200 calibration chunks): {out['psi_threshold']:.3f}")
    print(f"baseline recall (period A, all labels): {out['baseline']['recall']:.3f}")
    print("\ndrift monitor, 5-day windows:")
    print(pd.DataFrame(out["drift_windows"]).to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    for name, by_day in out["periods"].items():
        print(f"\nperiod {name}:")
        for day, r in by_day.items():
            lo, hi = r["recall_interval"]
            print(f"  {day:>8}: drift {r['drift_windows_flagged']}, alarms {r['alarms']}, caught {r['caught']}, "
                  f"missed reported {r['missed_reported']}, recall {r['recall']:.2f} [{lo:.2f}, {hi:.2f}] "
                  f"(true {r['true_recall']}) -> model_ok {r['model_ok']}; {r['action']}")
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(out, indent=2, default=str) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
