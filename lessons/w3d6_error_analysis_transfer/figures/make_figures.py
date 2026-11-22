"""Figures for lesson w3d6. Regenerates every SVG in this directory deterministically.

    python project/get_skab.py                                             # once (figures 1-3 use REAL SKAB data)
    python lessons/w3d6_error_analysis_transfer/figures/make_figures.py

Figures 1-3: real SKAB development experiments, the w2d6 bar baseline (flow_rate abs z, burn-in 100),
threshold = best F1 on development. Figure 4: SYNTHETIC slice-hunting simulation (same as
example/slice_traps.py, part 2). matplotlib is needed only here; labs and checks do not import it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "solutions" / "lessons" / "w3d6_error_analysis_transfer" / "lab" / "src"))

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

from flowguard.baselines import SingleSensorZScorer, burn_in_scores  # noqa: E402
from flowguard.data import load_raw  # noqa: E402
from flowguard.erroranalysis import error_segments, per_experiment_table, summarise_segments  # noqa: E402
from flowguard.metrics import best_f1_threshold  # noqa: E402
from flowguard.splits import dev_experiments, load_splits  # noqa: E402

BURN_IN = 100
FAMILY_COLOUR = {"valve1": SERIES[0], "valve2": SERIES[1], "other": SERIES[2]}
KIND_ORDER = ["fragment", "pre_onset", "post_event", "late", "boundary", "miss", "false_alarm"]


def skab():
    tidy = load_raw(ROOT / "data" / "raw" / "skab")
    manifest = load_splits(HERE.parent / "lab" / "splits" / "v2.json")  # v2, frozen in w3d1; never redrawn (the test set is fixed once results have been seen)
    dev = tidy[tidy["experiment_id"].isin(dev_experiments(manifest))].reset_index(drop=True)
    scores = burn_in_scores(lambda: SingleSensorZScorer("flow_rate"), dev, BURN_IN)
    labels = dev["anomaly"].to_numpy()
    usable = dev["t"].to_numpy() >= BURN_IN
    threshold, _ = best_f1_threshold(labels[usable], scores[usable])
    return dev, scores, labels, threshold


def fig_recall_per_experiment(dev, scores, labels, threshold):
    table = per_experiment_table(scores, labels, threshold, dev, burn_in=BURN_IN).sort_values("recall")
    fig, ax = plt.subplots(figsize=(7.2, 5.6))
    y = np.arange(len(table))
    ax.hlines(y, 0, table["recall"], color=INK["grid"], linewidth=1.2)
    for family, colour in FAMILY_COLOUR.items():
        part = (table["family"] == family).to_numpy()
        ax.scatter(table["recall"][part], y[part], color=colour, s=42, label=family, zorder=3)
    ax.axvline(table["recall"].mean(), color=INK["muted"], linestyle="--", linewidth=1)
    ax.text(table["recall"].mean() + 0.01, len(table) - 0.4, f"mean {table['recall'].mean():.2f}",
            color=INK["secondary"], fontsize=9, va="top")
    ax.set_yticks(y, table["experiment_id"])
    ax.set_xlim(0, 1.02)
    ax.set_xlabel("point-level recall within the experiment")
    ax.set_title("The mean (0.66) describes almost no experiment: recall runs from 0.01 to 0.99")
    ax.legend(title="family", loc="lower right")
    ax.grid(axis="y", visible=False)
    save(fig, HERE / "recall_per_experiment.svg")
    print("recall_per_experiment:", table[["experiment_id", "recall"]].round(3).to_string(index=False))


def fig_failure_kinds(dev, scores, labels, threshold):
    segments = error_segments(scores, labels, threshold, dev, late_after=30, burn_in=BURN_IN)
    summary = summarise_segments(segments).set_index("kind").reindex(KIND_ORDER).fillna(0).astype(int)
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.2), sharey=True)
    y = np.arange(len(summary))[::-1]
    for ax, column, label in ((axes[0], "n_rows", "wrong rows"), (axes[1], "n_segments", "error segments")):
        ax.barh(y, summary[column], color=SERIES[0], height=0.62)
        for yi, value in zip(y, summary[column]):
            ax.text(value + summary[column].max() * 0.02, yi, f"{value:,}", va="center",
                    color=INK["secondary"], fontsize=9)
        ax.set_xlim(0, summary[column].max() * 1.2)
        ax.set_xlabel(label)
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(y, summary.index)
    axes[0].set_title("Half of all wrong rows are alarm dropouts; no event is missed outright")
    save(fig, HERE / "failure_kinds.svg")
    print("failure_kinds:\n", summary.to_string())


def fig_alarm_strips(dev, scores, labels, threshold):
    chosen = ["valve1/8", "other/5", "other/7", "other/13"]
    notes = {"valve1/8": "detected and held (recall 0.99)", "other/5": "detected at onset, then drops out (fragment)",
             "other/7": "detected 80 rows late", "other/13": "alarms before the labelled onset"}
    fig, axes = plt.subplots(len(chosen), 1, figsize=(8.4, 6.6), sharex=True)
    for ax, experiment_id in zip(axes, chosen):
        rows = (dev["experiment_id"] == experiment_id).to_numpy() & (dev["t"].to_numpy() >= BURN_IN)
        t, s, y = dev["t"].to_numpy()[rows], np.clip(scores[rows], 0, 12), labels[rows]
        event = t[y == 1]
        ax.axvspan(event.min(), event.max(), color=SERIES[3], alpha=0.18, label="labelled anomaly")
        ax.plot(t, s, color=SERIES[0], linewidth=0.9, label="score (abs z of flow, clipped at 12)")
        ax.axhline(threshold, color=INK["muted"], linestyle="--", linewidth=1, label=f"threshold {threshold:.2f}")
        flagged = s >= threshold
        ax.scatter(t[flagged], np.full(flagged.sum(), 12.8), marker="|", s=18, color=SERIES[1], label="alarm")
        ax.set_ylim(0, 13.6)
        ax.set_ylabel("score")
        ax.set_title(f"{experiment_id}: {notes[experiment_id]}", fontsize=10)
        ax.grid(axis="x", visible=False)
    axes[0].legend(ncols=4, loc="upper left", bbox_to_anchor=(0, 1.62), fontsize=8)
    axes[-1].set_xlabel("row index t within the experiment (about 1 s per row)")
    fig.suptitle("Four experiments, four different kinds of failure (real SKAB, development set)",
                 x=0.01, ha="left", fontweight="bold", fontsize=11, y=1.03)
    save(fig, HERE / "alarm_strips.svg")
    print("alarm_strips:", chosen)


def fig_slice_hunting():
    rng = np.random.default_rng(7)
    rng.binomial([400, 100, 100, 400], [0.90, 0.50, 0.94, 0.56])       # keep the stream aligned with example part 1
    n_machines, n_events, n_attributes = 24, 10, 40
    recall = rng.binomial(n_events, 0.80, size=n_machines) / n_events
    attributes = rng.integers(0, 2, size=(n_machines, n_attributes)).astype(bool)
    observed = min(min(recall[attributes[:, j]].mean(), recall[~attributes[:, j]].mean()) for j in range(n_attributes))
    minima = []
    for _ in range(2000):
        r = rng.binomial(n_events, 0.80, size=n_machines) / n_events
        a = rng.integers(0, 2, size=(n_machines, n_attributes)).astype(bool)
        minima.append(min(min(r[a[:, j]].mean(), r[~a[:, j]].mean()) for j in range(n_attributes)))
    minima = np.array(minima)
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    ax.hist(minima, bins=30, color=SERIES[0])
    ax.axvline(observed, color=SERIES[1], linewidth=2)
    ax.text(observed - 0.004, ax.get_ylim()[1] * 0.92, f"worst slice found: {observed:.3f}", color=INK["primary"],
            fontsize=9, ha="right")
    ax.axvline(0.80, color=INK["muted"], linestyle="--", linewidth=1)
    ax.text(0.801, ax.get_ylim()[1] * 0.75, "true recall of\nevery machine: 0.80", color=INK["secondary"], fontsize=9)
    ax.set_xlabel("lowest slice recall found by searching 80 slices")
    ax.set_ylabel("simulated searches (of 2,000)")
    ax.set_title("SYNTHETIC: with no real effect, the worst of 80 slices still looks bad")
    save(fig, HERE / "slice_hunting.svg")
    print(f"slice_hunting: observed {observed:.3f}, null median {np.median(minima):.3f}, "
          f"share at least as low {np.mean(minima <= observed):.2f}")


if __name__ == "__main__":
    fig_slice_hunting()
    try:
        data = skab()
    except FileNotFoundError as exc:
        sys.exit(f"error: {exc}")
    fig_recall_per_experiment(*data)
    fig_failure_kinds(*data)
    fig_alarm_strips(*data)
