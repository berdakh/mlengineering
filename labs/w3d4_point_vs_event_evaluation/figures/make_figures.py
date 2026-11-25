"""Regenerate every figure of lesson w3d4. Author-side script (matplotlib is not a lab dependency).

    python project/get_skab.py                                              # once (figures 1-3 use REAL SKAB)
    python labs/w3d4_point_vs_event_evaluation/figures/make_figures.py

Uses the reference flowguard package from the solutions tree, so the numbers equal those quoted
in the lesson. Every plotted number is also printed.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "solutions" / "labs" / "w3d4_point_vs_event_evaluation" / "lab" / "src"))
sys.path.insert(0, str(HERE.parent / "example"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

from flowguard.baselines import SingleSensorZScorer, burn_in_scores  # noqa: E402
from flowguard.benchmark import evaluate_scores  # noqa: E402
from flowguard.data import load_raw  # noqa: E402
from flowguard.evaluation import evaluate_experiments, extract_events, match_events  # noqa: E402
from flowguard.splits import dev_experiments, load_splits  # noqa: E402

BURN_IN = 100
C_SIGNAL, C_RAW, C_POST = SERIES[0], SERIES[1], SERIES[2]      # fixed roles across the lesson's figures
LABEL_COLOUR = {"hit": SERIES[2], "redundant": SERIES[3], "false_alarm": SERIES[7]}


ALARM_EXPERIMENT = "valve1/10"   # a test experiment of the frozen v2 manifest


def fig_alarms(tidy, scores, threshold: float) -> None:
    """One REAL test experiment: signal, score, and the alarms before and after post-processing."""
    g = tidy[tidy["experiment_id"] == ALARM_EXPERIMENT].sort_values("t")
    s = scores[g.index.to_numpy()]
    g = g.reset_index(drop=True)
    t = g["t"].to_numpy()
    keep = t >= BURN_IN
    (ts, te), = extract_events(g["anomaly"].to_numpy())
    flags = ((s >= threshold) & keep).astype(int)
    fig, axes = plt.subplots(3, 1, figsize=(8, 6.2), sharex=True, height_ratios=[2, 2, 1.3])
    axes[0].plot(t, g["flow_rate"], color=C_SIGNAL, lw=1.2)
    axes[0].set_ylabel("flow rate (L/min)")
    axes[1].plot(t[keep], s[keep], color=C_SIGNAL, lw=1.0)
    axes[1].axhline(threshold, color=INK["secondary"], lw=1.0, ls="--")
    axes[1].text(t[-1], threshold, f" threshold {threshold:.2f}", va="bottom", ha="right", color=INK["secondary"], fontsize=9)
    axes[1].set_ylabel("|z| of flow rate\n(burn-in reference)")
    for ax in axes[:2]:
        ax.axvspan(ts, te, color=INK["grid"], alpha=0.9, lw=0)
        ax.axvspan(0, BURN_IN, color=INK["axis"], alpha=0.35, lw=0)
    axes[0].text((ts + te) / 2, axes[0].get_ylim()[1], "labelled anomalous segment", ha="center", va="top",
                 color=INK["secondary"], fontsize=9)
    axes[1].text(BURN_IN / 2, axes[1].get_ylim()[1], "burn-in", ha="center", va="top", color=INK["secondary"], fontsize=9)
    rows = [("raw flags\n(min_duration 1, merge_gap 0)", 1, 0), ("post-processed\n(min_duration 10, merge_gap 30)", 10, 30)]
    counts = []
    for y, (name, md, mg) in enumerate(rows):
        alarms = extract_events(flags, min_duration=md, merge_gap=mg)
        counts.append(len(alarms))
        labels = match_events([(ts, te)], alarms)["pred_label"]
        for (a, b), lab in zip(alarms, labels):
            axes[2].barh(y, t[b - 1] - t[a] + 1, left=t[a], height=0.6, color=LABEL_COLOUR[lab], zorder=3)
        print(f"fig alarms: {name.splitlines()[0]}: {len(alarms)} alarms "
              f"({labels.count('hit')} hit, {labels.count('redundant')} redundant, {labels.count('false_alarm')} false)")
    axes[0].set_title(f"{ALARM_EXPERIMENT} (real SKAB): one fault, {counts[0]} raw alarms, {counts[1]} after post-processing")
    axes[2].axvspan(ts, te, color=INK["grid"], alpha=0.9, lw=0, zorder=0)
    axes[2].set_yticks([0, 1], [r[0] for r in rows])
    axes[2].set_ylim(-0.6, 1.6)
    axes[2].set_xlabel("row index t (about 1 s per row)")
    axes[2].grid(axis="y", visible=False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in LABEL_COLOUR.values()]
    axes[2].legend(handles, ["hit", "redundant", "false alarm"], ncol=3, loc="upper left", bbox_to_anchor=(0, -0.45))
    save(fig, HERE / "alarms_on_signal.svg")


def fig_point_adjust() -> None:
    """Random scorer on REAL SKAB labels: point F1 before and after point-adjust."""
    from point_adjust_random import f1, load_labels, point_adjust
    labels = load_labels()
    y_all = np.concatenate(labels)
    lengths = [int(y.sum()) for y in labels]
    qs = np.array([0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5])
    raw, adj = [], []
    rng = np.random.default_rng(0)
    for q in qs:
        preds = [(rng.random(len(y)) < q).astype(int) for y in labels]
        raw.append(f1(y_all, np.concatenate(preds))[2])
        adj.append(f1(y_all, np.concatenate([point_adjust(y, p) for y, p in zip(labels, preds)]))[2])
        print(f"fig point-adjust: q={q:.4f} raw F1 {raw[-1]:.3f} point-adjusted F1 {adj[-1]:.3f}")
    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.plot(qs, raw, marker="o", color=C_SIGNAL, label="random flags, scored as they are")
    ax.plot(qs, adj, marker="o", color=C_RAW, label="the same flags after point-adjust")
    ax.axhline(0.78, color=INK["muted"], lw=1.0, ls="--")
    ax.text(qs[0], 0.79, "best F1 on the SKAB README leaderboard (0.78, not point-adjusted)", color=INK["secondary"],
            fontsize=9, va="bottom")
    ax.text(qs[4], adj[4] + 0.02, f"{adj[4]:.2f} at q = 1 %", ha="center", va="bottom", fontsize=9)
    ax.text(qs[-1], raw[-1] - 0.04, "scored as they are", ha="right", va="top", color=INK["secondary"], fontsize=9)
    ax.text(qs[-1], adj[-1] + 0.03, "after point-adjust", ha="right", va="bottom", color=INK["secondary"], fontsize=9)
    ax.set_xscale("log")
    ax.set_ylim(0, 1.08)
    ax.set_xlabel("fraction of rows flagged at random, q (log scale)")
    ax.set_ylabel("point-level F1")
    ax.set_title("Point-adjust turns a random scorer into a near-perfect one (real SKAB labels)")
    ax.legend(loc=(0.28, 0.42))
    save(fig, HERE / "point_adjust_inflation.svg")


def fig_tradeoff(tidy, scores, manifest) -> None:
    """Dev experiments: event recall and median delay against false alarms per hour."""
    is_dev = tidy["experiment_id"].isin(dev_experiments(manifest)).to_numpy()
    dev, dev_scores = tidy[is_dev].reset_index(drop=True), scores[is_dev]
    thresholds = (2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0, 10.0)
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.9), sharex=True)
    n_dev = len(dev_experiments(manifest))
    best_in_budget = 0
    for (md, mg), colour, name in (((1, 0), C_RAW, "raw flags"), ((10, 30), C_POST, "min_duration 10, merge_gap 30")):
        rate, recall, delay = [], [], []
        for th in thresholds:
            r = evaluate_experiments(dev, dev_scores >= th, burn_in=BURN_IN, min_duration=md, merge_gap=mg)
            rate.append(max(r["false_alarms_per_hour"], 0.1))           # 0 drawn at 0.1 on the log axis
            recall.append(r["event_recall"])
            delay.append(r["median_delay_s"])
            if r["false_alarms_per_hour"] <= 0.125:
                best_in_budget = max(best_in_budget, r["n_detected"])
            print(f"fig tradeoff: {name}: threshold {th}: {r['n_detected']}/{r['n_events']} found, "
                  f"{r['false_alarms_per_hour']:.1f} false alarms/h, median delay {r['median_delay_s']}")
        axes[0].plot(rate, recall, marker="o", color=colour, label=name)
        finite = [(x, d) for x, d in zip(rate, delay) if math.isfinite(d)]
        axes[1].plot(*zip(*finite), marker="o", color=colour, label=name)
        for th, x, y in zip(thresholds, rate, recall):
            if th in (2.5, 10.0):
                axes[0].annotate(f"|z| ≥ {th:g}", (x, y), textcoords="offset points",
                                 xytext=(6, -13) if th == 10.0 else (-48, 6), fontsize=8, color=INK["secondary"])
    for ax in axes:
        ax.set_xscale("log")
        ax.axvline(0.125, color=INK["muted"], lw=1.0, ls="--")
        ax.set_xlabel("false alarms per hour of normal operation (log scale)")
    axes[1].text(0.14, 0.97, "budget:\n1 per 8 h", color=INK["secondary"], fontsize=9, va="top",
                 transform=axes[1].get_xaxis_transform())
    axes[0].set_ylabel(f"event recall ({n_dev} dev events)")
    axes[0].set_ylim(0, 1.05)
    axes[0].set_title(f"Inside the budget: at most {best_in_budget} of {n_dev} faults found")
    print(f"fig tradeoff: inside the budget at most {best_in_budget}/{n_dev} found")
    axes[1].set_ylabel("median detection delay (s)")
    axes[1].set_title("Median delay (drawn only where it is finite)")
    axes[0].legend(loc="upper left")
    fig.suptitle(f"flow-rate |z| detector on the {n_dev} development experiments (real SKAB)", x=0.01, y=1.04, ha="left", fontsize=10,
                 color=INK["secondary"])
    save(fig, HERE / "tradeoff_dev.svg")


def fig_toy_ranking() -> None:
    """SYNTHETIC toy detectors: point F1 and event recall disagree."""
    from toy_point_vs_event import detectors, evaluate, make_labels
    y = make_labels()
    names, f1s, recalls = [], [], []
    for name, pred in detectors(y).items():
        r = evaluate(y, pred)
        found, total = (int(v) for v in r["events found"].split("/"))
        names.append(name)
        f1s.append(r["point F1"])
        recalls.append(found / total)
        print(f"fig toy: {name}: point F1 {r['point F1']}, events {r['events found']}")
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.2), sharey=True)
    pos = np.arange(len(names))[::-1]
    for ax, values, title in ((axes[0], f1s, "point-level F1"), (axes[1], recalls, "event recall (10 events)")):
        ax.barh(pos, values, color=C_SIGNAL, height=0.6)
        for p, v in zip(pos, values):
            ax.text(v + 0.02, p, f"{v:.2f}", va="center", fontsize=9)
        ax.set_xlim(0, 1.15)
        ax.set_title(title)
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(pos, names)
    fig.suptitle("SYNTHETIC hand-built detectors: the two metrics order them differently", x=0.01, y=1.04, ha="left",
                 fontsize=10, color=INK["secondary"])
    save(fig, HERE / "toy_point_vs_event.svg")


def main() -> None:
    apply()
    fig_toy_ranking()
    fig_point_adjust()
    tidy = load_raw(ROOT / "data" / "raw" / "skab")
    manifest = load_splits(HERE.parent / "lab" / "splits" / "v2.json")  # v2, frozen in w3d1; never redrawn (the test set is fixed once results have been seen)
    scores = burn_in_scores(lambda: SingleSensorZScorer("flow_rate"), tidy, BURN_IN)
    threshold = evaluate_scores(tidy, scores, manifest, burn_in=BURN_IN)["threshold"]
    print(f"threshold (best point F1 on dev): {threshold:.4f}")
    fig_alarms(tidy, scores, threshold)
    fig_tradeoff(tidy, scores, manifest)


if __name__ == "__main__":
    main()
