"""Milestone-1 pipeline: raw files -> tidy table -> results.json -> reports/evaluation.md.

Three steps, each a command (see cli.py) and a Makefile target:

    ingest    raw SKAB files       -> data/interim/skab.csv     (deterministic CSV)
    evaluate  tidy CSV + manifest  -> results/results.json      (ALL numbers are computed here)
    report    results.json         -> reports/evaluation.md + reports/figures/*.svg
                                      (formats numbers; computes nothing)

Contract the checks rely on (everything else is your design):
* ``results.json`` has ``provenance.splits_sha256`` (sha256 of the manifest file's bytes) and
  ``protocol.test_experiments`` (the manifest's test list), and is identical when rebuilt from the
  same inputs: no wall-clock times, no host-dependent measurements.
* every number shown in a table of ``evaluation.md`` is a value in ``results.json``, shown at the
  precision printed (so 0.8841 may appear as 0.884, never as 88.4 %).
* the report has the sections Problem, Data, Protocol, Results, Error analysis, Decision,
  Limitations, Provenance, and links at least one figure that exists.
"""
from __future__ import annotations

import hashlib
import json
import math
import platform
import subprocess
from importlib import metadata
from pathlib import Path

import numpy as np
import pandas as pd

from flowguard.data import load_raw
from flowguard.decision import decision_table, model_size_bytes, recommend
from flowguard.detectors import candidates, score_experiments
from flowguard.evaluation import evaluate_experiments
from flowguard.metrics import pr_auc
from flowguard.operating import choose_operating_point
from flowguard.splits import dev_experiments, load_splits, validate_splits
from flowguard.svgplot import interval_plot
from flowguard.uncertainty import cluster_bootstrap, paired_bootstrap_diff, wilson_interval

MPID = 0.05
BUDGET_HOURS = 8              # at most one false alarm per this many hours of normal operation
SCHEMA = "flowguard-evaluation/1"


# --------------------------------------------------------------------------- ingest
def ingest(raw_dir: str | Path, out: str | Path) -> Path:
    """Raw SKAB files -> one tidy CSV. Same input files, same output bytes."""
    tidy = load_raw(raw_dir)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tidy.to_csv(out, index=False, lineterminator="\n", date_format="%Y-%m-%d %H:%M:%S")
    return out


def read_tidy(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["datetime"])


# --------------------------------------------------------------------------- helpers
def sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _code_version() -> str:
    try:
        out = subprocess.run(["git", "describe", "--always", "--dirty", "--abbrev=12"], capture_output=True, text=True,
                             cwd=Path(__file__).parent, timeout=5)
        return out.stdout.strip() if out.returncode == 0 and out.stdout.strip() else "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def provenance(splits_path: str | Path, tidy_path: str | Path) -> dict:
    """What a reader needs to rebuild these numbers. No timestamps: they would break rebuilds."""
    versions = {}
    for pkg in ("numpy", "pandas", "scikit-learn", "scipy"):
        try:
            versions[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            versions[pkg] = "not installed"
    return {"splits_file": Path(splits_path).name, "splits_sha256": sha256(splits_path),
            "tidy_sha256": sha256(tidy_path), "python": platform.python_version(),
            "packages": versions, "code_version": _code_version()}


def _clusters(manifest: dict, experiments) -> dict[str, str]:
    out = {e: e for e in experiments}
    for group in manifest.get("overlap_groups", []):
        members = sorted(set(group) & set(out))
        for e in members:
            out[e] = "+".join(members)
    return out


def _per_cluster(frame: pd.DataFrame, scores: np.ndarray, cluster_of: dict, burn_in: int) -> dict:
    keep = frame["t"].to_numpy() >= burn_in
    f = frame[keep].assign(_s=scores[keep])
    f["_c"] = f["experiment_id"].map(cluster_of)
    return {c: (g["anomaly"].to_numpy(), g["_s"].to_numpy()) for c, g in f.groupby("_c", sort=True)}


def _pooled_pr_auc(results: list) -> float:
    y = np.concatenate([r[0] for r in results])
    s = np.concatenate([r[1] for r in results])
    return pr_auc(y, s) if y.any() else float("nan")


def _finite(x) -> float | None:
    """JSON has no infinity: a missed event's delay is stored as null."""
    x = float(x)
    return x if math.isfinite(x) else None


def _oof(candidate, dev: pd.DataFrame, manifest: dict, burn_in: int) -> np.ndarray:
    if not candidate.supervised:
        return score_experiments(candidate, dev, burn_in)
    scores = np.full(len(dev), np.nan)
    exp = dev["experiment_id"]
    for fold in manifest["dev_folds"]:
        train = [e for e in dev_experiments(manifest) if e not in fold]
        candidate.fit(dev[exp.isin(train)])
        held = exp.isin(fold).to_numpy()
        scores[held] = score_experiments(candidate, dev[held], burn_in)
    return scores


# --------------------------------------------------------------------------- evaluate
def evaluate(tidy_path: str | Path, splits_path: str | Path, burn_in: int = 100, n_boot: int = 2000,
             seed: int = 0) -> dict:
    """Every number of the report, computed once. Development data chooses; the test set is looked at once."""
    tidy = read_tidy(tidy_path)
    manifest = load_splits(splits_path)
    validate_splits(manifest, tidy)
    dev_ids, test_ids = dev_experiments(manifest), sorted(manifest["test"])
    dev = tidy[tidy["experiment_id"].isin(dev_ids)].reset_index(drop=True)
    test = tidy[tidy["experiment_id"].isin(test_ids)].reset_index(drop=True)
    cluster_of = _clusters(manifest, dev_ids + test_ids)
    budget = 1.0 / BUDGET_HOURS

    cands = candidates(burn_in, seed)
    rows, dev_clusters, points = [], {}, {}
    for rank, cand in enumerate(cands):
        s = _oof(cand, dev, manifest, burn_in)
        dev_clusters[cand.name] = _per_cluster(dev, s, cluster_of, burn_in)
        usable = s[dev["t"].to_numpy() >= burn_in]
        point = choose_operating_point(dev, s, budget, np.unique(np.quantile(usable, np.linspace(0.5, 0.999, 30))),
                                       min_durations=(1, 5, 10, 30), merge_gaps=(0, 10, 60), burn_in=burn_in)
        points[cand.name] = point
        ev = point["dev"]
        ci = cluster_bootstrap(_pooled_pr_auc, dev_clusters[cand.name], n_boot=n_boot, seed=seed)
        cand.fit(dev)                                     # the artifact that would be deployed
        first = dev[dev["experiment_id"] == dev_ids[0]].sort_values("t")
        size = model_size_bytes(cand.calibrate(first.iloc[:burn_in]))   # deterministic; latency is not
        rows.append({"name": cand.name, "complexity": rank, "supervised": cand.supervised,
                     "primary": ci["estimate"], "primary_lo": ci["low"], "primary_hi": ci["high"],
                     "events_detected": ev["n_detected"], "events_total": ev["n_events"],
                     "false_alarms_per_hour": ev["false_alarms_per_hour"],
                     "threshold": point["threshold"], "min_duration": point["min_duration"],
                     "merge_gap": point["merge_gap"], "budget_met_on_dev": bool(point["feasible"]),
                     "size_bytes": size})
    reference = cands[0].name
    for row in rows:
        if row["name"] == reference:
            row.update(diff=0.0, diff_lo=0.0, diff_hi=0.0)
        else:
            d = paired_bootstrap_diff(_pooled_pr_auc, dev_clusters[row["name"]], dev_clusters[reference],
                                      n_boot=n_boot, seed=seed)
            row.update(diff=d["estimate"], diff_lo=d["low"], diff_hi=d["high"])
    table = decision_table(rows, {"primary": "max", "false_alarms_per_hour": "min", "size_bytes": "min"}, MPID)
    choice = recommend(table, {})
    table_rows = json.loads(table.to_json(orient="records"))

    # ---- the one test look
    test_rows, per_experiment = [], []
    test_clusters = sorted(set(cluster_of[e] for e in test_ids))
    for cand in cands:
        if cand.supervised:
            cand.fit(dev)
        s = score_experiments(cand, test, burn_in)
        p = points[cand.name]
        flagged = s >= p["threshold"]
        ev = evaluate_experiments(test, flagged, burn_in=burn_in, min_duration=p["min_duration"], merge_gap=p["merge_gap"])
        lo, hi = wilson_interval(ev["n_detected"], ev["n_events"])
        ci = cluster_bootstrap(_pooled_pr_auc, _per_cluster(test, s, cluster_of, burn_in), n_boot=n_boot, seed=seed) \
            if len(test_clusters) > 1 else {"estimate": _pooled_pr_auc(list(_per_cluster(test, s, cluster_of, burn_in).values())),
                                            "low": float("nan"), "high": float("nan")}
        test_rows.append({"name": cand.name, "chosen": cand.name == choice["choice"],
                          "pr_auc": ci["estimate"], "pr_auc_lo": _finite(ci["low"]), "pr_auc_hi": _finite(ci["high"]),
                          "events_detected": ev["n_detected"], "events_total": ev["n_events"],
                          "recall_lo": lo, "recall_hi": hi, "false_alarms": ev["n_false_alarms"],
                          "normal_hours": ev["normal_hours"], "false_alarms_per_hour": _finite(ev["false_alarms_per_hour"]),
                          "median_delay_s": _finite(ev["median_delay_s"])})
        if cand.name == choice["choice"]:
            for e in test_ids:
                one = test["experiment_id"] == e
                r = evaluate_experiments(test[one], flagged[one.to_numpy()], burn_in=burn_in,
                                         min_duration=p["min_duration"], merge_gap=p["merge_gap"])
                per_experiment.append({"experiment_id": e, "family": e.split("/")[0],
                                       "detected": int(r["n_detected"]), "events": int(r["n_events"]),
                                       "delay_s": _finite(r["delays_s"][0]) if r["delays_s"] else None,
                                       "false_alarms": int(r["n_false_alarms"])})

    # ---- error analysis on development data (larger): per-family event recall of the chosen candidate
    chosen = next(c for c in cands if c.name == choice["choice"])
    s = _oof(chosen, dev, manifest, burn_in)
    p = points[chosen.name]
    by_family = []
    for fam in sorted(dev["family"].unique()):
        part = dev["family"] == fam
        r = evaluate_experiments(dev[part], (s >= p["threshold"])[part.to_numpy()], burn_in=burn_in,
                                 min_duration=p["min_duration"], merge_gap=p["merge_gap"])
        by_family.append({"family": fam, "experiments": int(dev.loc[part, "experiment_id"].nunique()),
                          "events_detected": r["n_detected"], "events_total": r["n_events"],
                          "false_alarms": r["n_false_alarms"]})

    counts = tidy.groupby("family")["experiment_id"].nunique().to_dict()
    return {
        "_inputs": {"tidy_path": str(Path(tidy_path).resolve()), "splits_path": str(Path(splits_path).resolve()),
                    "burn_in": burn_in, "n_boot": n_boot, "seed": seed},
        "schema": SCHEMA,
        "provenance": provenance(splits_path, tidy_path),
        "data": {"rows": int(len(tidy)), "experiments": int(tidy["experiment_id"].nunique()),
                 "experiments_by_family": {k: int(v) for k, v in sorted(counts.items())},
                 "anomalous_row_fraction": float(tidy.loc[tidy["family"] != "anomaly-free", "anomaly"].mean())},
        "protocol": {"burn_in_rows": burn_in, "n_boot": n_boot, "seed": seed, "mpid": MPID, "interval_level": 0.95,
                     "alert_budget_hours": BUDGET_HOURS, "unit": "overlap group",
                     "dev_experiments": len(dev_ids), "dev_clusters": len(dev_clusters[reference]),
                     "test_experiments": test_ids, "test_clusters": len(test_clusters),
                     "reference": reference},
        "development": table_rows,
        "decision": {"chosen": choice["choice"], "reason": choice["reason"], "eligible": choice["eligible"]},
        "test": test_rows,
        "test_per_experiment": per_experiment,
        "dev_by_family": by_family,
    }


def write_results(results: dict, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return path


# --------------------------------------------------------------------------- report
def _n(x, d: int = 3) -> str:
    """A number at ``d`` decimals; never "-0.000" (a rounded tiny negative reads as a sign error)."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    text = f"{x:.{d}f}"
    return text[1:] if text.startswith("-") and float(text) == 0 else text


def _cell(text: str) -> str:
    """Markdown table cells cannot contain a bare '|' (as in 'flow-rate |z|')."""
    return str(text).replace("|", "\\|")


def _ci(est, lo, hi, d: int = 3) -> str:
    return f"{_n(est, d)} [{_n(lo, d)}, {_n(hi, d)}]"


def render(results: dict, out: str | Path) -> Path:
    """results dict -> markdown + figures. Formats numbers; never computes a new one."""
    out = Path(out)
    if "_inputs" in results:                       # "always fresh": rerun the evaluation
        results = dict(evaluate(**results["_inputs"]), _inputs=results["_inputs"])
    fig_dir = out.parent / "figures"
    pr, dt, pv = results["protocol"], results["data"], results["provenance"]
    dev, test = results["development"], results["test"]
    fam = ", ".join(f"{k} {v}" for k, v in dt["experiments_by_family"].items())
    interval_plot([{"label": r["name"], "estimate": r["diff"], "lo": r["diff_lo"], "hi": r["diff_hi"]}
                   for r in dev if r["name"] != pr["reference"]],
                  fig_dir / "dev_differences.svg",
                  title=f"PR-AUC difference to {pr['reference']} (development, paired cluster bootstrap)",
                  xlabel="candidate minus reference; shaded band = ± MPID", band=(-pr["mpid"], pr["mpid"]))
    L = ["# flowguard evaluation report: milestone 1", "",
         "Generated by `make evaluate` from the files named under Provenance. Do not edit by hand.", "",
         "## Problem", "",
         "Raise an alarm soon after the SKAB water-circulation testbed leaves normal operation, with at most "
         f"one false alarm per {pr['alert_budget_hours']} hours of normal operation. Educational prototype; "
         "no claim about any real plant.", "",
         "## Data", "",
         "| Quantity | Value |", "|---|---|",
         f"| Rows | {dt['rows']} |", f"| Experiments | {dt['experiments']} |",
         f"| Anomalous fraction of labelled rows | {_n(dt['anomalous_row_fraction'])} |", "",
         f"Experiments by family: {fam}. Source, licence and hashes: `project/README.md` and `data/raw/skab/MANIFEST.json`.", "",
         "## Protocol", "",
         "| Setting | Value |", "|---|---|",
         f"| Split | frozen manifest `{pv['splits_file']}`: {pr['dev_experiments']} development experiments, "
         f"{len(pr['test_experiments'])} test experiments |",
         f"| Unit of resampling | {pr['unit']}: {pr['dev_clusters']} development clusters, {pr['test_clusters']} test clusters |",
         f"| Calibration | first {pr['burn_in_rows']} rows of every run, excluded from evaluation |",
         f"| Bootstrap | {pr['n_boot']} replicates, seed {pr['seed']}, percentile intervals at level {_n(pr['interval_level'], 2)} |",
         f"| MPID (point-level PR-AUC) | {_n(pr['mpid'], 2)} |", "",
         "Development data chooses the operating point and the model; the test set is looked at once.", "",
         "## Results", "",
         "### Development comparison", "",
         "| Candidate | PR-AUC [95 % CI] | Difference to reference [95 % CI] | Reading | Events at budget | False alarms per hour | Size, bytes | Pareto |",
         "|---|---|---|---|---|---|---|---|"]
    for r in dev:
        diff = "reference" if r["name"] == pr["reference"] else _ci(r["diff"], r["diff_lo"], r["diff_hi"])
        L.append(f"| {_cell(r['name'])} | {_ci(r['primary'], r['primary_lo'], r['primary_hi'])} | {diff} | {r['vs_reference']} | "
                 f"{r['events_detected']} of {r['events_total']} | {_n(r['false_alarms_per_hour'])} | {r['size_bytes']} | "
                 f"{'yes' if r['pareto'] else 'no'} |")
    L += ["", "Pareto front over PR-AUC (max), false alarms per hour (min) and size (min). Latency is measured "
          "separately (w4d5) because it depends on the host.", "",
          "![Differences to the reference with paired intervals against the MPID band](figures/dev_differences.svg)", "",
          "### Test, one look (operating points fixed on development data)", "",
          "| Candidate | Role | PR-AUC [95 % CI] | Events detected | Recall [Wilson 95 %] | False alarms | Median delay, s |",
          "|---|---|---|---|---|---|---|"]
    for r in test:
        L.append(f"| {_cell(r['name'])} | {'chosen' if r['chosen'] else 'record only'} | {_ci(r['pr_auc'], r['pr_auc_lo'], r['pr_auc_hi'])} | "
                 f"{r['events_detected']} of {r['events_total']} | [{_n(r['recall_lo'], 2)}, {_n(r['recall_hi'], 2)}] | "
                 f"{r['false_alarms']} | {'missed' if r['median_delay_s'] is None else _n(r['median_delay_s'], 0)} |")
    L += ["", "## Error analysis", "", f"Chosen candidate ({results['decision']['chosen']}), test experiments:", "",
          "| Experiment | Family | Detected | Delay, s | False alarms |", "|---|---|---|---|---|"]
    for r in results["test_per_experiment"]:
        L.append(f"| {r['experiment_id']} | {r['family']} | {'yes' if r['detected'] else 'no'} | "
                 f"{'-' if r['delay_s'] is None else _n(r['delay_s'], 0)} | {r['false_alarms']} |")
    L += ["", "Development experiments by family (out-of-fold where the model is trained):", "",
          "| Family | Experiments | Events detected | False alarms |", "|---|---|---|---|"]
    for r in results["dev_by_family"]:
        L.append(f"| {r['family']} | {r['experiments']} | {r['events_detected']} of {r['events_total']} | {r['false_alarms']} |")
    L += ["", "## Decision", "", f"**{results['decision']['chosen']}.** {results['decision']['reason']}.", "",
          "Rule fixed in advance: among the candidates, the simplest one shown practically better than the reference "
          "(whole interval above the MPID); otherwise the simplest one not shown worse.", "",
          "## Limitations", "",
          f"* {pr['test_clusters']} independent test clusters: test intervals are wide, and no comparison between candidates "
          "is made on test data.",
          "* One laboratory testbed and three fault families; nothing here is evidence about other equipment.",
          "* Labels mark whole anomalous segments; some duplicated rows carry contradictory labels (project/README.md).",
          "* Latency and size are host-dependent and are reported in the w4d5 decision memo, not here, so that this report rebuilds byte for byte.",
          "", "## Provenance", "",
          "| Item | Value |", "|---|---|",
          f"| Split manifest sha256 | `{pv['splits_sha256']}` |",
          f"| Tidy data sha256 | `{pv['tidy_sha256']}` |",
          f"| Code version | `{pv['code_version']}` |",
          f"| Python | `{pv['python']}` |"]
    L += [f"| {k} | `{v}` |" for k, v in pv["packages"].items()]
    L += ["", f"Schema `{results['schema']}`. Rebuild: `make evaluate`."]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n")
    return out
