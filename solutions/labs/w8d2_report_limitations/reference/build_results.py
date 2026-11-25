"""Assemble results.json for the flowguard technical report from files committed in the course.

    python solutions/labs/w8d2_report_limitations/reference/build_results.py

Every value is read from a committed file named in `sources`; nothing is typed in. Machine-readable
results (JSON, CSV) are read directly. A few findings exist only as text in a lesson or the project
brief: those are extracted with a pattern that must match the file, so if the source changes, this
script fails instead of silently reporting a stale number. Derived values (a mean over seeds, a
difference) are computed here and say so in `derived`.
"""
from __future__ import annotations

import csv
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent / "results.json"

SRC = {
    "evaluation": "solutions/labs/w4d6_project_milestone_1/example_report/results.json",
    "protocols": "labs/w4d2_classical_detectors/figures/protocols.csv",
    "neural": "labs/w4d3_neural_comparison/figures/neural_vs_classical.json",
    "parity": "solutions/labs/w5d6_project_milestone_2/example_release/parity.json",
    "fallback": "solutions/labs/w7d5_reliability/drill_log/fallback_vs_model.json",
    "demo": "solutions/labs/w7d6_project_milestone_4/example_demo/results.json",
    "reproduction": "solutions/labs/w8d1_project_completion/real_audit/REPRODUCTION_LOG.json",
    "project": "docs/guides/project.md",
    "drift_lesson": "docs/notebooks/38_input_monitoring_drift.md",
    "degradation_lesson": "docs/notebooks/39_drift_vs_degradation.md",
    "updates_lesson": "docs/notebooks/40_model_updates_rollback.md",
    "demo_lesson": "docs/notebooks/42_project_milestone_4.md",
}


def load(key):
    return json.loads((ROOT / SRC[key]).read_text())


def quote(key: str, pattern: str, *groups: int) -> list[float]:
    """Numbers captured by `pattern` in a text source; fails loudly if the text no longer says so."""
    text = (ROOT / SRC[key]).read_text()
    m = re.search(pattern, text)
    if not m:
        sys.exit(f"pattern {pattern!r} no longer matches {SRC[key]}: refusing to report a stale number")
    return [float(m.group(g).replace(",", "")) for g in groups]


def main() -> int:
    ev = load("evaluation")
    test = {t["name"]: t for t in ev["test"]}
    dev = {d["name"]: d for d in ev["development"]}
    with open(ROOT / SRC["protocols"]) as fh:
        prot = {r["detector"]: r for r in csv.DictReader(fh)}
    neural = load("neural")
    seeds = [s["test_pr_auc"] for s in neural["neural_seeds"]]
    fb = load("fallback")["summary"]
    demo = load("demo")
    repro = load("reproduction")

    dup = quote("project", r"\*\*Rows are duplicated across files\.\*\* ([\d,]+) rows", 1)[0]
    contra = quote("project", r"In (\d+) of them the two files give", 1)[0]
    onset_n, onset_of = quote("project", r"In (\d+) of (\d+) experiments the anomaly starts at row 550-600", 1, 2)
    clock_f1 = quote("project", r"reaches test F1 ([\d.]+) \(w2d6\)", 1)[0]
    drift_fault_a, drift_fault_b = quote("drift_lesson", r"and (\d+) % of fault windows; reference B on \d+ % and (\d+) %", 1, 2)
    psi_lo, psi_hi = quote("degradation_lesson", r"period B \(recalibrated sensor\) sits at ([\d.]+)-([\d.]+)", 1, 2)
    rec_before, rec_after, rec_of = quote("degradation_lesson", r"Recall fell from (\d+)/20 to (\d+)/(\d+)", 1, 2, 3)
    gate = quote("updates_lesson", r"gate 1\.1\.0 non_inferiority: PROMOTE .*?diff \+([\d.]+) \[\+([\d.]+), \+([\d.]+)\]", 1, 2, 3)
    healthy_psi = quote("demo_lesson", r"a healthy test experiment reaches ([\d.]+)", 1)[0]

    gbt, flow, iforest, t2 = (prot["gradient-boosted trees"], prot["flow_rate abs z (w2d6 baseline)"],
                              prot["isolation forest"], prot["PCA T2"])
    results = {
        "schema": "flowguard-technical-report/1",
        "sources": SRC,
        "data": {**ev["data"], "events": onset_of, "anomalous_percent": ev["data"]["anomalous_row_fraction"],
                 "duplicated_rows": dup, "contradictory_labels": contra,
                 "onset_550_600": onset_n, "clock_test_f1": clock_f1},
        "protocol": ev["protocol"],
        "decision": ev["decision"],
        "development": ev["development"],
        "test": ev["test"],
        "test_per_experiment": ev["test_per_experiment"],
        "protocol_b": {
            "gbt": {"a": float(gbt["pr_auc_A_test"]), "b": float(gbt["pr_auc_B_unseen_family"]),
                    "b_lo": float(gbt["low_B_unseen_family"]), "b_hi": float(gbt["high_B_unseen_family"])},
            "flow": {"a": float(flow["pr_auc_A_test"]), "b": float(flow["pr_auc_B_unseen_family"]),
                     "b_lo": float(flow["low_B_unseen_family"]), "b_hi": float(flow["high_B_unseen_family"])},
            "iforest": {"a": float(iforest["pr_auc_A_test"]), "b": float(iforest["pr_auc_B_unseen_family"])},
            "pca_t2": {"a": float(t2["pr_auc_A_test"]), "b": float(t2["pr_auc_B_unseen_family"])},
        },
        "neural": {"seeds": len(seeds), "test_pr_auc_mean": statistics.mean(seeds),
                   "test_pr_auc_sd": statistics.stdev(seeds), "test_pr_auc_min": min(seeds),
                   "test_pr_auc_max": max(seeds),
                   "vs_mahalanobis": neural["paired"]["Mahalanobis burn-in (shrinkage 0.3)"]},
        "parity": load("parity"),
        "fallback": {"model_detected": fb["model"]["faults_detected"], "fallback_detected": fb["fallback"]["faults_detected"],
                     "faults": fb["model"]["faults"]},
        "monitoring": {**demo["summary"], "healthy_psi_max_test": healthy_psi,
                       "drift_fault_windows_share_a": drift_fault_a / 100, "drift_fault_windows_share_b": drift_fault_b / 100,
                       "recalibration_psi_lo": psi_lo, "recalibration_psi_hi": psi_hi,
                       "regression_recall_before": rec_before, "regression_recall_after": rec_after,
                       "regression_faults": rec_of,
                       "gate_diff": gate[0], "gate_diff_lo": gate[1], "gate_diff_hi": gate[2]},
        "reproduction": {"verdict": repro["verdict"], "total_seconds": repro["total_seconds"],
                         "headline_values": len(repro["headline"]),
                         "max_abs_diff": max(h["abs_diff"] for h in repro["headline"] if h["abs_diff"] is not None)},
        "derived": {
            "protocol_b_gbt_drop": float(gbt["pr_auc_A_test"]) - float(gbt["pr_auc_B_unseen_family"]),
            "chosen_minus_logistic_test": test["flow-rate |z|"]["pr_auc"] - test["logistic (supervised)"]["pr_auc"],
            "dev_logistic_diff": dev["logistic (supervised)"]["diff"],
            "notes": "differences computed here from the source values; neural mean/sd over seeds",
        },
    }
    OUT.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
