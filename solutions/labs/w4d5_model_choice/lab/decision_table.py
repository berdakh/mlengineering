"""The project's model-choice evidence on the REAL SKAB data.

    python project/get_skab.py                                  # once, from the repository root
    python labs/w4d5_model_choice/lab/decision_table.py      # about 2 minutes

This file is complete. It works once you have implemented flowguard.decision.

Protocol (the decision is made on DEVELOPMENT data only)
--------------------------------------------------------
* Split: the frozen manifest v2 from w3d1 (27 development, 7 test experiments). Unit of resampling:
  the overlap group (files sharing rows are one cluster).
* Scores: every candidate is calibrated on each run's first 100 rows (excluded from evaluation).
  The supervised candidate is scored out-of-fold on the development folds.
* Primary metric: pooled point-level PR-AUC; difference to the simplest candidate by a paired cluster
  bootstrap; MPID fixed before running: 0.05.
* Operating point: chosen on development data for an alert budget of 1 false alarm per 8 h (w3d4);
  event recall, false alarms per hour and median delay are reported at that point.
* Costs: per-sample p95 latency of the deployed step, size of the pickled step, retraining time.
* Hard constraint: p95 latency <= 20 ms per sample (the plant samples once per second; the budget
  leaves room for 8 sensors x several machines on one small host).
* Then, ONCE: the chosen candidate on the test experiments. The other candidates' test numbers are
  printed for the record and are not used for the choice.
"""
from __future__ import annotations

import os

# One OpenMP thread, so latency measures the model rather than thread contention on a shared host.
os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

from flowguard.data import load_raw  # noqa: E402
from flowguard.decision import decision_table, measure_latency, model_size_bytes, recommend  # noqa: E402
from flowguard.detectors import candidates, score_experiments  # noqa: E402
from flowguard.evaluation import evaluate_experiments  # noqa: E402
from flowguard.metrics import pr_auc  # noqa: E402
from flowguard.operating import choose_operating_point  # noqa: E402
from flowguard.splits import dev_experiments, load_splits, validate_splits  # noqa: E402
from flowguard.uncertainty import cluster_bootstrap, paired_bootstrap_diff, wilson_interval  # noqa: E402

BURN_IN = 100
MPID = 0.05
BUDGET = 1 / 8
P95_BUDGET_MS = 20.0
N_BOOT = 2000
REPO_ROOT = next((p for p in HERE.parents if (p / "project" / "get_skab.py").is_file()), HERE)


def clusters(manifest: dict, experiments) -> dict[str, str]:
    """experiment -> cluster id (its overlap group, or itself)."""
    out = {e: e for e in experiments}
    for group in manifest.get("overlap_groups", []):
        members = sorted(set(group) & set(out))
        for e in members:
            out[e] = "+".join(members)
    return out


def per_cluster(frame: pd.DataFrame, scores: np.ndarray, cluster_of: dict) -> dict:
    keep = frame["t"].to_numpy() >= BURN_IN
    f = frame[keep].assign(_s=scores[keep])
    f["_c"] = f["experiment_id"].map(cluster_of)
    return {c: (g["anomaly"].to_numpy(), g["_s"].to_numpy()) for c, g in f.groupby("_c", sort=True)}


def pooled_pr_auc(results: list) -> float:
    y = np.concatenate([r[0] for r in results])
    s = np.concatenate([r[1] for r in results])
    return pr_auc(y, s) if y.any() else float("nan")


def oof_scores(candidate, tidy: pd.DataFrame, manifest: dict) -> np.ndarray:
    """Development scores; out-of-fold for a supervised candidate."""
    if not candidate.supervised:
        return score_experiments(candidate, tidy, BURN_IN)
    scores = np.full(len(tidy), np.nan)
    exp = tidy["experiment_id"]
    for fold in manifest["dev_folds"]:
        train = [e for e in dev_experiments(manifest) if e not in fold]
        candidate.fit(tidy[exp.isin(train)])
        held = exp.isin(fold).to_numpy()
        scores[held] = score_experiments(candidate, tidy[held], BURN_IN)
    return scores


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--raw-dir", default=str(REPO_ROOT / "data" / "raw" / "skab"))
    ap.add_argument("--out", default=str(HERE / "results"))
    args = ap.parse_args(argv)
    try:
        tidy = load_raw(args.raw_dir)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    manifest = load_splits(HERE / "splits" / "v2.json")      # frozen in w3d1; never redrawn
    validate_splits(manifest, tidy)
    dev_ids, test_ids = dev_experiments(manifest), manifest["test"]
    dev = tidy[tidy["experiment_id"].isin(dev_ids)].reset_index(drop=True)
    test = tidy[tidy["experiment_id"].isin(test_ids)].reset_index(drop=True)
    cluster_of = clusters(manifest, dev_ids + test_ids)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    cands = candidates(BURN_IN)
    dev_scores, rows, steps = {}, [], {}
    for rank, cand in enumerate(cands):
        dev_scores[cand.name] = oof_scores(cand, dev, manifest)
        t0 = time.perf_counter()
        cand.fit(dev)                                        # the model that would be deployed
        first = dev[dev["experiment_id"] == dev_ids[0]].sort_values("t")
        step = cand.calibrate(first.iloc[:BURN_IN])
        fit_s = time.perf_counter() - t0
        steps[cand.name] = step
        latency = measure_latency(step, first.iloc[BURN_IN:], n_warmup=50, n_repeat=1000)
        point = choose_operating_point(
            dev, dev_scores[cand.name], BUDGET,
            np.unique(np.quantile(dev_scores[cand.name][dev["t"].to_numpy() >= BURN_IN], np.linspace(0.5, 0.999, 30))),
            min_durations=(1, 5, 10, 30), merge_gaps=(0, 10, 60), burn_in=BURN_IN)
        ev = point["dev"]
        rows.append({
            "name": cand.name, "complexity": rank, "supervised": cand.supervised,
            "primary": pooled_pr_auc(list(per_cluster(dev, dev_scores[cand.name], cluster_of).values())),
            "event_recall": ev["event_recall"], "events": f"{ev['n_detected']}/{ev['n_events']}",
            "false_alarms_per_hour": ev["false_alarms_per_hour"], "budget_met_on_dev": point["feasible"],
            "median_delay_s": ev["median_delay_s"],
            "p50_ms": latency["p50_ms"], "p95_ms": latency["p95_ms"],
            "size_bytes": model_size_bytes(step), "fit_s": fit_s,
            "dependencies": cand.dependencies, "explanation": cand.explanation,
            "threshold": point["threshold"], "min_duration": point["min_duration"], "merge_gap": point["merge_gap"],
        })

    reference = cands[0].name
    ref_clusters = per_cluster(dev, dev_scores[reference], cluster_of)
    for row in rows:
        mine = per_cluster(dev, dev_scores[row["name"]], cluster_of)
        ci = cluster_bootstrap(pooled_pr_auc, mine, n_boot=N_BOOT, seed=0)
        row["primary_lo"], row["primary_hi"] = ci["low"], ci["high"]
        if row["name"] == reference:
            row["diff"], row["diff_lo"], row["diff_hi"] = 0.0, 0.0, 0.0
        else:
            d = paired_bootstrap_diff(pooled_pr_auc, mine, ref_clusters, n_boot=N_BOOT, seed=0)
            row["diff"], row["diff_lo"], row["diff_hi"] = d["estimate"], d["low"], d["high"]

    table = decision_table(rows, {"primary": "max", "false_alarms_per_hour": "min", "p95_ms": "min"}, MPID)
    choice = recommend(table, {"p95_ms": ("<=", P95_BUDGET_MS)})
    table.to_csv(out / "decision_table.csv", index=False)

    n_clusters = len(ref_clusters)
    print(f"DEVELOPMENT evidence ({len(dev_ids)} experiments, {n_clusters} clusters; burn-in {BURN_IN} rows; "
          f"MPID {MPID}; alert budget {BUDGET:.3f}/h; p95 budget {P95_BUDGET_MS:.0f} ms)\n")
    show = table[["name", "primary", "primary_lo", "primary_hi", "diff", "diff_lo", "diff_hi", "vs_reference",
                  "events", "false_alarms_per_hour", "median_delay_s", "p50_ms", "p95_ms", "size_bytes",
                  "fit_s", "pareto"]]
    with pd.option_context("display.width", 200, "display.max_columns", 30, "display.float_format", "{:.3f}".format):
        print(show.to_string(index=False))
    print(f"\nPareto front (PR-AUC max, false alarms/h min, p95 min): {table.loc[table['pareto'], 'name'].tolist()}")
    print(f"recommendation: {choice['reason']}")

    # ---- one test look for the chosen candidate (others printed for the record only)
    print(f"\nTEST, frozen ({len(test_ids)} experiments), operating point fixed on development data:")
    test_rows = []
    for cand in cands:
        if cand.supervised:
            cand.fit(dev)
        s = score_experiments(cand, test, BURN_IN)
        r = table.set_index("name").loc[cand.name]
        ev = evaluate_experiments(test, s >= r["threshold"], burn_in=BURN_IN,
                                  min_duration=int(r["min_duration"]), merge_gap=int(r["merge_gap"]))
        lo, hi = wilson_interval(ev["n_detected"], ev["n_events"])
        auc = pooled_pr_auc(list(per_cluster(test, s, cluster_of).values()))
        tag = "CHOSEN" if cand.name == choice["choice"] else "record only"
        delay = "missed" if math.isinf(ev["median_delay_s"]) else f"{ev['median_delay_s']:.0f} s"
        print(f"  {cand.name:<22} [{tag:<11}] PR-AUC {auc:.3f}; events {ev['n_detected']}/{ev['n_events']} "
              f"(Wilson 95% [{lo:.2f}, {hi:.2f}]); false alarms/h {ev['false_alarms_per_hour']:.2f}; "
              f"median delay {delay}")
        test_rows.append({"name": cand.name, "chosen": cand.name == choice["choice"], "pr_auc": auc,
                          "events": f"{ev['n_detected']}/{ev['n_events']}", "recall_lo": lo, "recall_hi": hi,
                          "false_alarms_per_hour": ev["false_alarms_per_hour"], "median_delay_s": ev["median_delay_s"]})
    pd.DataFrame(test_rows).to_csv(out / "test_look.csv", index=False)
    (out / "recommendation.json").write_text(json.dumps(choice, indent=2) + "\n")
    print(f"\nwrote {out}/decision_table.csv, test_look.csv, recommendation.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
