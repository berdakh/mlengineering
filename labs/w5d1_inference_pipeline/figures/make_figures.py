"""Regenerate every figure of lesson w5d1 and print the numbers they show.

    python project/get_skab.py                                          # once
    python labs/w5d1_inference_pipeline/figures/make_figures.py      # about 15 seconds

Figures 1 and 3 use REAL SKAB data (the 7 frozen test experiments) scored by the reference
solution's Detector and by the challenge's serving variants. Figures 2 and 4 are SYNTHETIC.
matplotlib is needed only here; the lab and the checks do not import it. Pass --png DIR to also
write PNG copies for visual inspection.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
UNIT = HERE.parent
ROOT = HERE.parents[2]
REF = ROOT / "solutions" / "labs" / "w5d1_inference_pipeline"
sys.path[:0] = [str(ROOT), str(REF / "lab" / "src"), str(UNIT / "example")]

from tools.figstyle import INK, SERIES, STATUS, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

from flowguard.batch import load_detector  # noqa: E402
from flowguard.data import load_raw  # noqa: E402
from flowguard.inference import Detector, serving_frame  # noqa: E402
from flowguard.splits import load_splits  # noqa: E402

PNG: Path | None = None


def out(fig, name):
    if PNG:
        fig.savefig(PNG / f"{name}.png", dpi=110)
    save(fig, HERE / f"{name}.svg")
    print(f"wrote {name}.svg")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def shade_runs(ax, t, mask, color, label=None):
    """Shade contiguous runs of True in mask over x = t."""
    edges = np.diff(np.r_[0, mask.astype(int), 0])
    for k, (s, e) in enumerate(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1))):
        ax.axvspan(t[s], t[e - 1], color=color, alpha=0.18, lw=0, label=label if k == 0 else None)


def fig_served_run(test: pd.DataFrame, detector: Detector, experiment: str) -> None:
    run = test[test["experiment_id"] == experiment].sort_values("t")
    frame, _ = detector.score_batch(serving_frame(run))
    t = run["t"].to_numpy()
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 4.6), sharex=True, height_ratios=[1, 1.1])
    a1.plot(t, run["flow_rate"], color=SERIES[0], lw=1.2)
    a1.axvspan(t[0], t[detector.n_burn - 1], color=INK["muted"], alpha=0.22, lw=0, label="burn-in (calibration)")
    shade_runs(a1, t, run["anomaly"].to_numpy() == 1, STATUS["critical"], "labelled anomaly")
    a1.set_ylabel("flow rate, L/min")
    a1.legend(loc="lower left", ncols=2, frameon=True, facecolor=INK["surface"], edgecolor="none", framealpha=0.9)
    a1.set_title(f"Real SKAB test run {experiment}: what the service sees and what it says")
    score = frame["score"].to_numpy()
    a2.plot(t, score, color=SERIES[0], lw=1.2, label="served score |z|")
    a2.axhline(detector.threshold, color=INK["secondary"], lw=1, ls="--")
    a2.text(t[-1], detector.threshold, f"threshold {detector.threshold:.2f}", ha="right", va="bottom",
            color=INK["secondary"], fontsize=9)
    shade_runs(a2, t, frame["alarm"].to_numpy() == 1, SERIES[1], "alarm (after post-processing)")
    a2.set_ylabel("score")
    a2.set_xlabel("row within run (1 s per row)")
    a2.legend(loc="upper left", frameon=True, facecolor=INK["surface"], edgecolor="none", framealpha=0.9)
    out(fig, "served_run")
    print(f"  {experiment}: alarm rows {int(frame['alarm'].sum())}, first alarm row "
          f"{int(t[np.flatnonzero(frame['alarm'].to_numpy())[0]]) if frame['alarm'].any() else 'none'}, "
          f"labelled onset row {int(t[np.flatnonzero(run['anomaly'].to_numpy())[0]])}")


def fig_normalise_away() -> None:
    rng = np.random.default_rng(3)
    n, at = 400, 200
    x = rng.normal(30.0, 0.4, n)
    x[at:] += 6 * 0.4                                              # a fault of 6 burn-in SDs
    burn = x[:100]
    good = np.abs((x - burn.mean()) / burn.std())
    bad = np.abs((x - x.mean()) / x.std())                         # "normalise the input"
    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.plot(np.arange(100, n), good[100:], color=SERIES[0], lw=1.2, label="calibrated on burn-in rows (evaluated path)")
    ax.plot(np.arange(100, n), bad[100:], color=SERIES[1], lw=1.2, label="calibrated on the whole run (skew)")
    ax.axvline(at, color=INK["muted"], lw=1, ls=":")
    ax.text(at + 3, ax.get_ylim()[1] * 0.92, "fault starts", color=INK["secondary"], fontsize=9)
    ax.set_xlabel("row within run")
    ax.set_ylabel("|z| score")
    ax.set_title("SYNTHETIC: normalising each batch by itself shrinks the fault it should detect")
    ax.legend(loc="center left")
    out(fig, "normalise_away")
    print(f"  median score after the fault: burn-in {np.median(good[at:]):.2f}, whole-run {np.median(bad[at:]):.2f}")


def fig_challenge_skew(test: pd.DataFrame) -> None:
    challenge = UNIT / "challenge"
    model = json.loads((challenge / "model" / "logistic.json").read_text())
    train = load_module(REF / "challenge" / "train_features.py", "train_features")
    variants = {"burn-in hard-coded\nat today's 100": UNIT / "checks_challenge" / "variants" / "bug_burnin.py",
                "clip missing": UNIT / "checks_challenge" / "variants" / "bug_clip.py",
                "feature order swapped": UNIT / "checks_challenge" / "variants" / "bug_order.py",
                "all three (original)": UNIT / "checks_challenge" / "variants" / "original.py",
                "fixed": REF / "challenge" / "serve_scores.py"}
    threshold = 3.964503
    rows = []
    for label, path in variants.items():
        mod = load_module(path, "serve_" + path.stem)
        flips = 0
        for _, g in test.groupby("experiment_id", sort=False):
            g = g.sort_values("t")
            a, b = train.training_scores(g, model), mod.score_run(g, model)
            b = b[len(b) - len(a):]
            flips += int(((a >= threshold) != (b >= threshold)).sum())
        rows.append((label, flips))
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    labels, values = zip(*rows)
    y = np.arange(len(rows))[::-1]
    colors = [SERIES[1]] * 4 + [SERIES[0]]
    ax.barh(y, values, color=colors, height=0.6)
    for yi, v in zip(y, values):
        ax.text(v + 8, yi, f"{v}", va="center", color=INK["primary"], fontsize=9)
    ax.set_yticks(y, labels)
    ax.set_xlabel("test rows whose raw alarm decision differs from the training path")
    ax.set_title("Real SKAB test runs: the challenge's skew bugs, one at a time (logistic candidate)")
    ax.set_xlim(0, max(values) * 1.15)
    ax.grid(axis="y", visible=False)
    out(fig, "challenge_skew")
    for label, v in rows:
        print(f"  {label.replace(chr(10), ' ')}: {v} rows")


def fig_worked_example() -> None:
    import skew_demo  # noqa: E402

    train, live = skew_demo.make_table(400, 1), skew_demo.make_table(10_000, 2)
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    feats = skew_demo.FEATURES
    model = make_pipeline(StandardScaler(), LogisticRegression()).fit(train[feats], train["churned"])
    p = model.predict_proba(live[feats])[:, 1]
    stats = {c: (train[c].mean(), train[c].std()) for c in feats}
    w = model[1].coef_[0]

    def reimpl(order):
        z = np.column_stack([(live[c] - stats[c][0]) / stats[c][1] for c in order])
        return 1 / (1 + np.exp(-(z @ w + model[1].intercept_[0])))

    a, b = reimpl(sorted(feats)), reimpl(feats)
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.4), sharey=True)
    for ax, q, title, colour in ((axes[0], a, "A: ddof=1 and alphabetical columns", SERIES[1]),
                                 (axes[1], b, "B: ddof=1 only", SERIES[3])):
        ax.scatter(p, q, s=4, alpha=0.35, color=colour, lw=0)
        ax.plot([0, 1], [0, 1], color=INK["muted"], lw=1)
        flips = int(((q >= 0.5) != (p >= 0.5)).sum())
        ax.set_title(f"{title}\n{flips} of {len(p):,} decisions flipped", fontsize=10)
        ax.set_xlabel("trained pipeline probability")
    axes[0].set_ylabel("re-implemented serving probability")
    fig.suptitle("SYNTHETIC churn table: two re-implementations of the same scaler", x=0.01, y=1.08, ha="left",
                 fontweight="bold", fontsize=11)
    out(fig, "worked_example")


def main() -> int:
    global PNG
    ap = argparse.ArgumentParser()
    ap.add_argument("--png", default=None)
    args = ap.parse_args()
    if args.png:
        PNG = Path(args.png)
        PNG.mkdir(parents=True, exist_ok=True)
    tidy = load_raw(ROOT / "data" / "raw" / "skab")
    manifest = load_splits(REF / "lab" / "splits" / "v2.json")
    test = tidy[tidy["experiment_id"].isin(manifest["test"])].reset_index(drop=True)
    detector = load_detector(REF / "lab" / "model")
    fig_served_run(test, detector, "valve1/5")
    fig_normalise_away()
    fig_challenge_skew(test)
    fig_worked_example()
    return 0


if __name__ == "__main__":
    sys.exit(main())
