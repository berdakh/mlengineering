"""Regenerate the figures of lesson w2d6 and handbook H5.1 / H5.2 / H6.2 (deterministic).

    python project/get_skab.py                                         # once, for the real-data figures
    python labs/w2d6_baselines_metrics/figures/make_figures.py      # about 1 minute

SYNTHETIC (same generators and seeds as example/metrics_under_imbalance.py):
  pr_roc_prevalence.svg   ROC and PR curves of one fixed classifier at three prevalences.
  reliability.svg         reliability curves of a plain and a class-weighted logistic regression.
REAL SKAB (reference solution of the lab, same protocol as lab/baseline_table.py):
  baseline_ladder.svg     test PR-AUC of every baseline against the constant floor.
  score_by_class.svg      distribution of the burn-in flow-rate |z| on test rows, by true class.
SYNTHETIC, for handbook H5.1:
  mahalanobis_2d.svg      alarm regions of max-|z| versus Mahalanobis on two correlated sensors.

Numbers behind every figure are printed and written to figures/figure_data.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score, roc_curve
from sklearn.model_selection import train_test_split

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOLUTION_LAB = ROOT / "solutions" / "labs" / "w2d6_baselines_metrics" / "lab"
sys.path[:0] = [str(ROOT), str(SOLUTION_LAB / "src"), str(SOLUTION_LAB)]

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

RECORDS: list[dict] = []


def record(figure: str, **values) -> None:
    RECORDS.append({"figure": figure, **values})


def fig_pr_roc_prevalence() -> None:
    rng = np.random.default_rng(0)
    fig, (ax_roc, ax_pr) = plt.subplots(1, 2, figsize=(8.6, 3.6))
    for colour, prevalence in zip(SERIES, (0.35, 0.05, 0.005)):
        n = 400_000
        y = (rng.random(n) < prevalence).astype(int)
        score = rng.standard_normal(n) + 1.5 * y
        fpr, tpr, _ = roc_curve(y, score)
        precision, recall, _ = precision_recall_curve(y, score)
        auc, ap = roc_auc_score(y, score), average_precision_score(y, score)
        label = f"prevalence {prevalence:g}"
        ax_roc.plot(fpr, tpr, color=colour, label=f"{label}: AUC {auc:.3f}")
        ax_pr.plot(recall, precision, color=colour, label=f"{label}: AP {ap:.3f}")
        ax_pr.axhline(y.mean(), color=colour, lw=1, ls=":")
        record("pr_roc_prevalence", prevalence=prevalence, roc_auc=round(auc, 3), pr_auc=round(ap, 3))
    ax_roc.plot([0, 1], [0, 1], color=INK["axis"], lw=1)
    ax_roc.set(title="ROC: the three curves coincide", xlabel="false-positive rate", ylabel="recall (TPR)",
               xlim=(0, 1), ylim=(0, 1.01))
    ax_pr.set(title="PR: precision collapses with prevalence", xlabel="recall", ylabel="precision",
              xlim=(0, 1), ylim=(0, 1.01))
    ax_roc.legend(loc="lower right")
    ax_pr.legend(loc="upper right")
    fig.suptitle("Same classifier, three class ratios (SYNTHETIC; dotted lines = PR floor)", x=0.01, ha="left",
                 fontsize=10, color=INK["secondary"])
    fig.tight_layout()
    save(fig, HERE / "pr_roc_prevalence.svg")


def fig_reliability() -> None:
    rng = np.random.default_rng(1)
    n = 60_000
    X = rng.standard_normal((n, 4))
    logit = -4.2 + 1.2 * X[:, 0] + 0.8 * X[:, 1] - 0.6 * X[:, 2]
    y = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    X_fit, X_eval, y_fit, y_eval = train_test_split(X, y, test_size=0.5, random_state=0, stratify=y)
    models = {"plain": LogisticRegression(max_iter=1000),
              "class_weight='balanced'": LogisticRegression(max_iter=1000, class_weight="balanced")}
    edges = np.array([0.0, 0.02, 0.05, 0.1, 0.2, 0.4, 0.7, 1.0])
    fig, ax = plt.subplots(figsize=(5.2, 4.4))
    ax.plot([0, 1], [0, 1], color=INK["axis"], lw=1)
    ax.text(0.60, 0.50, "perfectly calibrated", rotation=40, color=INK["muted"], fontsize=9)
    for colour, (name, model) in zip(SERIES, models.items()):
        p = model.fit(X_fit, y_fit).predict_proba(X_eval)[:, 1]
        bins = np.clip(np.searchsorted(edges, p, side="right") - 1, 0, len(edges) - 2)
        pred = [p[bins == b].mean() for b in range(len(edges) - 1) if (bins == b).any()]
        obs = [y_eval[bins == b].mean() for b in range(len(edges) - 1) if (bins == b).any()]
        ax.plot(pred, obs, color=colour, marker="o", label=name)
        ax.annotate(name, (pred[-1], obs[-1]), xytext=(-6, 8), textcoords="offset points", ha="right",
                    color=INK["secondary"], fontsize=9)
        for a, b in zip(pred, obs):
            record("reliability", model=name, mean_predicted=round(a, 3), observed=round(b, 3))
    ax.set(title="Reweighting keeps the ranking, breaks the probabilities", xlabel="mean predicted probability (bin)",
           ylabel="observed positive rate", xlim=(0, 1), ylim=(0, 1))
    ax.legend(loc="upper left")
    ax.text(0.99, 0.02, "SYNTHETIC, prevalence 4 %", transform=ax.transAxes, ha="right", color=INK["muted"], fontsize=8)
    save(fig, HERE / "reliability.svg")


def real_baselines():
    raw = ROOT / "data" / "raw" / "skab"
    if not raw.is_dir():
        print("data/raw/skab missing: run `python project/get_skab.py` first; skipping real-data figures")
        return None
    import baseline_table as bt  # the lab's table script, run against the reference implementation
    from flowguard.benchmark import evaluate_scores
    from flowguard.data import load_raw
    from flowguard.splits import make_splits, validate_splits

    tidy = load_raw(raw)
    manifest = make_splits(tidy, seed=0)          # the w2d4 v1 manifest, exactly as baseline_table.py uses
    validate_splits(manifest, tidy)
    rows = []
    for name, scores in bt.build_rows(tidy, manifest):
        r = evaluate_scores(tidy, scores, manifest, burn_in=bt.BURN_IN)
        rows.append((name, r, scores))
    return tidy, manifest, rows


def fig_baseline_ladder(real) -> None:
    tidy, manifest, rows = real
    names = [n for n, _, _ in rows]
    test_ap = [r["test"]["pr_auc"] for _, r, _ in rows]
    floor = rows[0][1]["test"]["pr_auc"]
    order = np.argsort(test_ap)
    fig, ax = plt.subplots(figsize=(8.0, 4.4))
    for rank, i in enumerate(order):
        name = names[i]
        colour = SERIES[1] if name.startswith("elapsed") else (INK["muted"] if name in ("constant", "random") else SERIES[0])
        ax.barh(rank, test_ap[i], color=colour, height=0.62)
        ax.text(test_ap[i] + 0.008, rank, f"{test_ap[i]:.3f}", va="center", fontsize=9, color=INK["primary"])
        record("baseline_ladder", baseline=name, test_pr_auc=round(test_ap[i], 3),
               test_f1=round(rows[i][1]["test"]["f1"], 3))
    ax.set_yticks(range(len(order)), [names[i] for i in order])
    ax.axvline(floor, color=INK["secondary"], lw=1, ls="--")
    ax.text(floor + 0.005, -0.85, f"floor = prevalence {floor:.3f}", color=INK["secondary"], fontsize=9)
    ax.set_ylim(-1.1, len(order) - 0.4)
    ax.set(xlim=(0, 1), xlabel="test PR-AUC (row level, 9 test experiments, no intervals)",
           title="Baselines on real SKAB: the clock (orange) is a protocol probe, not a detector")
    ax.grid(axis="y", visible=False)
    save(fig, HERE / "baseline_ladder.svg")


def fig_score_by_class(real) -> None:
    tidy, manifest, rows = real
    from flowguard.splits import dev_experiments  # noqa: F401  (documented dependency)
    name, result, scores = next(x for x in rows if x[0] == "flow_rate abs z, burn-in")
    test = tidy["experiment_id"].isin(manifest["test"]).to_numpy() & (tidy["t"].to_numpy() >= 100)
    y = tidy["anomaly"].to_numpy()[test]
    s = np.clip(scores[test], 0, 30)
    threshold = result["threshold"] if "threshold" in result else None
    bins = np.linspace(0, 30, 61)
    fig, axes = plt.subplots(2, 1, figsize=(7.4, 4.4), sharex=True)
    for ax, cls, colour, label in ((axes[0], 0, SERIES[0], "normal rows"), (axes[1], 1, SERIES[1], "anomalous rows")):
        ax.hist(s[y == cls], bins=bins, color=colour)
        ax.text(0.99, 0.85, f"{label}: n = {(y == cls).sum():,}, median |z| = {np.median(s[y == cls]):.1f}",
                transform=ax.transAxes, ha="right", color=INK["secondary"], fontsize=9)
        ax.set_ylabel("rows")
        if threshold is not None:
            ax.axvline(min(threshold, 30), color=INK["primary"], lw=1, ls="--")
        record("score_by_class", cls=label, n=int((y == cls).sum()), median=round(float(np.median(s[y == cls])), 2))
    if threshold is not None:
        axes[0].text(min(threshold, 30) + 0.3, axes[0].get_ylim()[1] * 0.55, f"dev threshold {threshold:.1f}",
                     fontsize=9, color=INK["primary"])
        record("score_by_class", cls="threshold", n=0, median=round(float(threshold), 2))
    axes[1].set_xlabel("burn-in |z| of flow rate (clipped at 30)")
    axes[0].set_title("Real SKAB test rows: the classes overlap, so every threshold trades misses for alarms")
    fig.tight_layout()
    save(fig, HERE / "score_by_class.svg")


def fig_mahalanobis_2d() -> None:
    rng = np.random.default_rng(3)
    cov = np.array([[1.0, 0.9], [0.9, 1.0]])
    normal = rng.multivariate_normal([0, 0], cov, size=600)
    probe = np.array([1.3, -1.3])                                    # each value in range, relationship broken
    grid = np.linspace(-4, 4, 401)
    gx, gy = np.meshgrid(grid, grid)
    pts = np.column_stack([gx.ravel(), gy.ravel()])
    mu, sd, inv = normal.mean(0), normal.std(0), np.linalg.inv(np.cov(normal.T))
    maxz = np.abs((pts - mu) / sd).max(1).reshape(gx.shape)
    d = pts - mu
    maha = np.sqrt(np.einsum("ij,jk,ik->i", d, inv, d)).reshape(gx.shape)
    z_thr = np.quantile(np.abs((normal - mu) / sd).max(1), 0.99)
    dn = normal - mu
    m_thr = np.quantile(np.sqrt(np.einsum("ij,jk,ik->i", dn, inv, dn)), 0.99)
    p = probe - mu
    probe_z, probe_m = np.abs(p / sd).max(), float(np.sqrt(p @ inv @ p))
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 4.2), sharex=True, sharey=True)
    for ax, field, thr, title, val in ((axes[0], maxz, z_thr, "max |z|: a square", probe_z),
                                       (axes[1], maha, m_thr, "Mahalanobis: an ellipse", probe_m)):
        ax.scatter(normal[:, 0], normal[:, 1], s=6, color=SERIES[0], alpha=0.5, linewidths=0)
        ax.contour(gx, gy, field, levels=[thr], colors=[INK["primary"]], linewidths=1.5)
        flagged = val > thr
        ax.scatter(*probe, s=60, color=SERIES[1], edgecolors=INK["surface"], linewidths=2, zorder=3)
        ax.text(0.0, -3.55, f"orange probe: score {val:.1f} vs limit {thr:.1f} -> {'ALARM' if flagged else 'no alarm'}",
                ha="center", fontsize=9, color=INK["primary"])
        ax.set(title=title, xlabel="sensor 1 (z units)", xlim=(-4, 4), ylim=(-4, 4), aspect="equal")
        record("mahalanobis_2d", scorer=title.split(":")[0], probe_score=round(val, 2), limit_99pct=round(thr, 2),
               alarm=bool(flagged))
    axes[0].set_ylabel("sensor 2 (z units)")
    fig.suptitle("Two correlated sensors (SYNTHETIC, r = 0.9); limits at the 99th percentile of normal rows",
                 x=0.01, ha="left", fontsize=10, color=INK["secondary"])
    fig.tight_layout()
    save(fig, HERE / "mahalanobis_2d.svg")


def main() -> None:
    fig_pr_roc_prevalence()
    fig_reliability()
    fig_mahalanobis_2d()
    real = real_baselines()
    if real is not None:
        fig_baseline_ladder(real)
        fig_score_by_class(real)
    table = pd.DataFrame(RECORDS)
    table.to_csv(HERE / "figure_data.csv", index=False)
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
