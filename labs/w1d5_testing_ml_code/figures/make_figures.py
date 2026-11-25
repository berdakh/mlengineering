"""Figures for lesson w1d5.

    python labs/w1d5_testing_ml_code/figures/make_figures.py

* tolerance_regions.svg  - pure arithmetic: which errors pass under absolute, relative and combined tolerances.
* kill_matrix.svg        - REAL runs of the grading harness: which injected defects each test suite detects.
                           Defects are numbered, not named, so the figure does not give the lab away.
                           Takes about a minute (it runs pytest 15 times per suite).
* auc_over_seeds.svg     - the correct code on the SYNTHETIC pump data under 20 split seeds.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
LESSON = ROOT / "labs" / "w1d5_testing_ml_code"
SOL = ROOT / "solutions" / "labs" / "w1d5_testing_ml_code"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(LESSON / "checks"))
from tools.figstyle import INK, SEQUENTIAL, SERIES, STATUS, apply, save  # noqa: E402

OUT = Path(__file__).resolve().parent


def fig_tolerance(plt) -> None:
    expected = np.logspace(-9, 3, 400)
    rel, abs_ = 1e-6, 1e-9
    fig, ax = plt.subplots(figsize=(8.5, 3.9))
    ax.loglog(expected, np.full_like(expected, abs_), color=SERIES[1], label="absolute only: |a - b| <= 1e-9")
    ax.loglog(expected, rel * expected, color=SERIES[0], label="relative only: |a - b| <= 1e-6 * |b|")
    ax.loglog(expected, np.maximum(rel * expected, abs_), color=INK["primary"], lw=1.2, ls="--",
              label="combined: max(rel * |b|, abs)")
    ax.fill_between(expected, 1e-16, np.maximum(rel * expected, abs_), color=SERIES[0], alpha=0.07, lw=0)
    ax.axvline(abs_ / rel, color=INK["muted"], lw=0.8)
    ax.text(abs_ / rel * 1.3, 2e-15, "crossover at |b| = abs / rel = 1e-3", fontsize=8, color=INK["secondary"])
    ax.text(3e-8, 3e-12, "errors below the dashed line pass", fontsize=8, color=INK["secondary"])
    ax.set_xlabel("magnitude of the expected value |b|")
    ax.set_ylabel("largest error that passes")
    ax.set_ylim(1e-16, 1e-2)
    ax.set_title("A relative tolerance vanishes near zero; an absolute one is meaningless for large values")
    ax.legend(loc="upper left")
    save(fig, OUT / "tolerance_regions.svg")


def suite_dir(tmp: Path, name: str, overlay: Path | None) -> Path:
    """Reference tests with a weak suite overlaid, exactly as tools/verify_checks.py builds a mutant."""
    work = tmp / name
    shutil.copytree(SOL / "lab", work, ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
    if overlay is not None:
        shutil.copytree(overlay, work, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
        delete = overlay / "DELETE.txt"
        if delete.is_file():
            for rel in delete.read_text().split():
                victim = work / rel
                shutil.rmtree(victim) if victim.is_dir() else victim.unlink(missing_ok=True)
    return work / "tests"


def fig_kill_matrix(plt) -> None:
    from bugs import BUGS
    from harness import grade

    reference_pkg = LESSON / "checks" / "reference_pkg"
    suites = [("starter (2 weak tests)", "starter", None),
              ("runs without error", "runs_without_error", SOL / "mutants" / "runs_without_error"),
              ("compares code with itself", "self_consistency_only", SOL / "mutants" / "self_consistency_only"),
              ("end-to-end metric only", "end_to_end_metric_only", SOL / "mutants" / "end_to_end_metric_only"),
              ("loose tolerances", "loose_tolerances", SOL / "mutants" / "loose_tolerances"),
              ("reference suite", "reference", None)]
    matrix, labels = [], []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for label, key, overlay in suites:
            tests = LESSON / "lab" / "tests" if key == "starter" else suite_dir(tmp, key, overlay)
            ref, runs = grade(tests, reference_pkg, BUGS)
            assert ref.passed, f"{key} does not pass on the correct package:\n{ref.output}"
            killed = [int(runs[b.name].failed_tests) for b in BUGS]
            matrix.append(killed)
            labels.append(f"{label}  ({sum(killed)}/{len(BUGS)})")
            print(f"{label:<28} detects {sum(killed):>2} of {len(BUGS)}")
    m = np.array(matrix)
    fig, ax = plt.subplots(figsize=(8.5, 3.3))
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            ax.add_patch(plt.Rectangle((j + 0.06, i + 0.1), 0.88, 0.8, color=SEQUENTIAL[4] if m[i, j] else "#eceae4"))
    ax.set_xlim(0, m.shape[1]); ax.set_ylim(m.shape[0], 0)
    ax.set_xticks(np.arange(m.shape[1]) + 0.5, [str(j + 1) for j in range(m.shape[1])])
    ax.set_yticks(np.arange(m.shape[0]) + 0.5, labels)
    ax.set_xlabel("injected defect (numbered, not named)   dark = detected, pale = survived")
    ax.set_title("All six suites pass on the correct code; they differ in how many defects they notice")
    ax.grid(visible=False)
    ax.tick_params(length=0)
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    save(fig, OUT / "kill_matrix.svg")


def fig_auc(plt) -> None:
    sys.path.insert(0, str(LESSON / "lab" / "src"))
    from pumpwatch.features import build_feature_table
    from pumpwatch.io import load_windows
    from pumpwatch.model import train_and_evaluate

    table = build_feature_table(load_windows(ROOT / "data" / "synthetic" / "pump_vibration.csv"), fs=256.0)
    auc = np.array([train_and_evaluate(table, seed=s)["auc"] for s in range(20)])
    below = auc <= 0.95
    fig, ax = plt.subplots(figsize=(8.5, 3.4))
    ax.axhline(0.95, color=STATUS["critical"], lw=1.2, ls="--")
    ax.text(19.6, 0.9505, "assert auc > 0.95", ha="right", va="bottom", fontsize=8, color=INK["secondary"])
    ax.scatter(np.arange(20)[~below], auc[~below], s=40, color=SERIES[0], zorder=3, label="assertion passes")
    ax.scatter(np.arange(20)[below], auc[below], s=52, color=SERIES[1], marker="X", zorder=3, label="assertion fails")
    ax.set_xticks(range(20))
    ax.set_xlabel("split seed")
    ax.set_ylabel("test ROC AUC")
    ax.set_title(f"SYNTHETIC: correct code fails the metric assertion on {int(below.sum())} of 20 split seeds")
    ax.grid(axis="x", visible=False)
    ax.legend(loc="center", ncols=2)
    save(fig, OUT / "auc_over_seeds.svg")
    print(f"AUC min {auc.min():.4f} max {auc.max():.4f}; at or below 0.95: {int(below.sum())} of 20")


def main() -> None:
    apply()
    import matplotlib.pyplot as plt
    fig_tolerance(plt)
    fig_auc(plt)
    fig_kill_matrix(plt)


if __name__ == "__main__":
    main()
