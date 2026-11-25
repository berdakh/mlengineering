"""Regenerate the data figures of lesson w7d4 and handbook H15.5.

    python project/get_skab.py                                              # once
    python labs/w7d4_model_updates_rollback/figures/make_figures.py      # about 1-2 minutes

Real data: figures 1 and 2 use the reference solution's build_models.py and update_report.py on SKAB
(gate on the 7 test experiments of the frozen manifest v2). Figures 3 and 4 are SYNTHETIC: the worked
example's generator and the challenge's canary logs (rates stated in their files).
Every plotted number is also written to figure_data.csv.
"""
from __future__ import annotations

import csv
import importlib.util
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
UNIT = HERE.parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
SOL = ROOT / "solutions" / "labs" / "w7d4_model_updates_rollback"
sys.path.insert(0, str(SOL / "lab" / "src"))

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

from flowguard.data import load_raw  # noqa: E402
from flowguard.registry import load_bundle  # noqa: E402

ROWS: list[dict] = []


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fig_gate(out: dict) -> None:
    items = [("1.1.0 vs 1.0.0", out["gate"]["1.1.0 non_inferiority"]["diff"]),
             ("2.0.0 vs 1.0.0", out["gate"]["2.0.0 non_inferiority"]["diff"])]
    fig, ax = plt.subplots(figsize=(6.6, 2.6))
    for y, (label, (est, lo, hi)) in enumerate(items):
        ax.plot([lo, hi], [y, y], color=SERIES[y], linewidth=3, solid_capstyle="round")
        ax.plot([est], [y], "o", color=SERIES[y], markersize=8)
        right = hi > 0
        ax.annotate(f"{est:+.3f} [{lo:+.3f}, {hi:+.3f}]", (hi if right else lo, y), xytext=(8 if right else -8, 0),
                    textcoords="offset points", va="center", ha="left" if right else "right", fontsize=8,
                    color=INK["secondary"])
        ROWS.append({"figure": "gate_intervals", "x": label, "series": "estimate,low,high", "value": f"{est:.4f},{lo:.4f},{hi:.4f}"})
    ax.axvline(0, color=INK["primary"], linewidth=1)
    ax.axvline(-0.05, color=INK["muted"], linewidth=1, linestyle="--")
    ax.text(-0.05, 1.45, "non-inferiority margin -0.05", ha="right", fontsize=8, color=INK["secondary"])
    ax.set_yticks([0, 1], [i[0] for i in items])
    ax.set_ylim(-0.6, 1.7)
    ax.set_xlim(-1.45, 0.8)
    ax.set_xlabel("event recall: candidate minus current (paired bootstrap, 95 %)")
    ax.set_title("Gate on 7 test experiments: 1.1.0 is non-inferior but not shown better")
    save(fig, HERE / "gate_intervals.svg")


def fig_probe(raw: Path, bundles: Path) -> None:
    tidy = load_raw(raw)
    run = tidy[tidy["experiment_id"] == "valve1/8"].sort_values("t")
    m10, _ = load_bundle(bundles / "flowguard-1.0.0")
    m11, _ = load_bundle(bundles / "flowguard-1.1.0")
    s = m10.score_run(run)
    t = run["t"].to_numpy()
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    an = run["anomaly"].to_numpy().astype(bool)
    ax.fill_between(t, 0, 1, where=an, transform=ax.get_xaxis_transform(), color=INK["grid"], step="mid",
                    label="labelled fault")
    ax.plot(t, s, color=SERIES[0], linewidth=1.2, label="burn-in |z| of flow rate (both versions)")
    ax.axhline(m10.threshold, color=SERIES[1], linestyle="--", linewidth=1.5, label=f"1.0.0 threshold {m10.threshold:.2f}")
    ax.axhline(m11.threshold, color=SERIES[2], linestyle="--", linewidth=1.5, label=f"1.1.0 threshold {m11.threshold:.2f}")
    for name, m in (("1.0.0", m10), ("1.1.0", m11)):
        ROWS.append({"figure": "probe_valve1_8", "x": name, "series": "alarm_events", "value": str(m.alarm_events(run))})
    ax.set_xlabel("sample (1 s each), valve1/8")
    ax.set_ylabel("score")
    ax.set_ylim(0, max(12, np.nanmax(s) * 1.05))
    ax.set_title("valve1/8: the fault holds the score between the thresholds; only 1.1.0 alarms")
    ax.legend(loc="upper left", fontsize=8)
    save(fig, HERE / "probe_valve1_8.svg")


def fig_paired() -> None:
    demo = _load(UNIT / "example" / "paired_gate_demo.py", "paired_gate_demo")
    pairs = [("paired", demo.bootstrap(paired=True)), ("unpaired", demo.bootstrap(paired=False))]
    est = demo.recall(demo.candidate) - demo.recall(demo.current)
    fig, ax = plt.subplots(figsize=(6.6, 2.4))
    for y, (label, (lo, hi)) in enumerate(pairs):
        ax.plot([lo, hi], [y, y], color=SERIES[y], linewidth=3, solid_capstyle="round")
        ax.plot([est], [y], "o", color=SERIES[y], markersize=8)
        ax.annotate(f"[{lo:+.3f}, {hi:+.3f}]", (hi, y), xytext=(8, 0), textcoords="offset points", va="center",
                    fontsize=8, color=INK["secondary"])
        ROWS.append({"figure": "paired_vs_unpaired", "x": label, "series": "low,high", "value": f"{lo:.4f},{hi:.4f}"})
    ax.axvline(0, color=INK["primary"], linewidth=1)
    ax.set_yticks([0, 1], [p[0] for p in pairs])
    ax.set_ylim(-0.6, 1.6)
    ax.set_xlim(-0.08, 0.3)
    ax.set_xlabel("recall: candidate minus current, 40 stores (95 %)")
    ax.set_title("SYNTHETIC: pairing removes store difficulty from the comparison")
    save(fig, HERE / "paired_vs_unpaired.svg")


def fig_canary() -> None:
    canary = _load(SOL / "challenge" / "canary.py", "canary_ref")
    log = pd.read_csv(UNIT / "challenge" / "canary_logs" / "e_borderline_alerts.csv")
    hours, lows, highs = [], [], []
    for h in sorted(log["hour"].unique()):
        d = canary.decide(log[log["hour"] <= h])
        lo, hi = d["stats"]["alert_bounds"]
        hours.append(h)
        lows.append(lo)
        highs.append(hi)
        ROWS.append({"figure": "canary_bounds", "x": int(h), "series": "low,high", "value": f"{lo:.4f},{hi:.4f}"})
    fig, ax = plt.subplots(figsize=(7.0, 3.2))
    ax.fill_between(hours, lows, highs, color=SERIES[0], alpha=0.25, linewidth=0, label="95 % bounds on the canary alert rate")
    ax.plot(hours, lows, color=SERIES[0], linewidth=1)
    ax.plot(hours, highs, color=SERIES[0], linewidth=1)
    ax.axhline(1.0, color=SERIES[1], linestyle="--", label="budget: 1 alert per machine-hour")
    first = next(h for h, lo in zip(hours, lows) if lo > 1.0)
    ax.plot([first], [lows[first]], "o", color=SERIES[1], markersize=7)
    ax.annotate(f"hour {first}: lower bound > budget,\nthe hourly rule stops here", (first, lows[first]),
                xytext=(30, 40), textcoords="offset points", fontsize=8, color=INK["secondary"],
                arrowprops={"arrowstyle": "->", "color": INK["secondary"]})
    ax.set_yscale("log")
    ax.set_xlabel("hours of canary (cumulative data)")
    ax.set_ylabel("alerts per machine-hour (log)")
    ax.set_title("SYNTHETIC: one early look crosses the line; on all 96 hours the bounds straddle it")
    ax.legend(loc="upper right", fontsize=8)
    save(fig, HERE / "canary_bounds.svg")


def main() -> None:
    raw = ROOT / "data" / "raw" / "skab"
    build = _load(SOL / "lab" / "build_models.py", "build_models_ref")
    report = _load(SOL / "lab" / "update_report.py", "update_report_ref")
    with tempfile.TemporaryDirectory() as tmp:
        bundles = Path(tmp) / "bundles"
        build.build(raw, bundles)
        out = report.run(raw, bundles, Path(tmp))
        fig_gate(out)
        fig_probe(raw, bundles)
    fig_paired()
    fig_canary()
    with open(HERE / "figure_data.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["figure", "x", "series", "value"])
        w.writeheader()
        w.writerows(ROWS)
    print("wrote 4 figures and figure_data.csv to", HERE)


if __name__ == "__main__":
    main()
