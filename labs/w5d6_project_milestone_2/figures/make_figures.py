"""Regenerate the figures of lesson w5d6 from real runs. From the repository root:

    python project/get_skab.py                       # once, if data/raw/skab is missing
    python labs/w5d6_project_milestone_2/figures/make_figures.py

Uses the reference project (solutions/.../lab, the fixed API) and the shipped starter (lab/, whose API
still has the ddof=1 skew). Writes figures/*.svg and figures/figure_data.csv.
"""
from __future__ import annotations

import csv
import importlib
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
UNIT = HERE.parent
ROOT = UNIT.parents[1]
REF = ROOT / "solutions" / "labs" / "w5d6_project_milestone_2" / "lab"
RAW = ROOT / "data" / "raw" / "skab"
sys.path.insert(0, str(ROOT))

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

ROWS: list[dict] = []
EXPERIMENTS = ("valve1/13", "valve2/0", "other/14")
YMAX = 25.0


def load_package(src: Path):
    """Import the flowguard package found in ``src`` (fresh import each time)."""
    for name in [m for m in sys.modules if m == "flowguard" or m.startswith("flowguard.")]:
        del sys.modules[name]
    sys.path.insert(0, str(src))
    try:
        return {m: importlib.import_module(f"flowguard.{m}") for m in ("api", "bundle", "data", "inference", "scoring")}
    finally:
        sys.path.remove(str(src))


def api_scores(pkg, model_dir, tidy, eid):
    from fastapi.testclient import TestClient
    model = pkg["bundle"].load_bundle(model_dir)
    x = tidy[tidy["experiment_id"] == eid].sort_values("t")[model.sensor].to_numpy(dtype=float)
    scores = []
    with TestClient(pkg["api"].create_app(model_dir)) as client:
        for i in range(0, len(x), 3600):                       # the API takes at most 3,600 values
            r = client.post("/predict", json={"burn_in": x[: model.n_burn_in].tolist(), "values": x[i:i + 3600].tolist()})
            r.raise_for_status()
            scores += r.json()["scores"]
    return model, np.asarray(scores)


def main() -> None:
    if not RAW.is_dir():
        sys.exit("data/raw/skab not found: run `python project/get_skab.py` first")
    ref = load_package(REF / "src")
    tidy = ref["data"].load_raw(RAW)
    config = dict(model_version="flowrate-z-2026.11", sensor="flow_rate", n_burn_in=100, threshold=7.2441307141,
                  min_duration=30, merge_gap=10)
    with tempfile.TemporaryDirectory() as tmp:
        model_dir = Path(tmp) / "bundle"
        ref["bundle"].save_bundle(ref["scoring"].ZScoreModel(**config), model_dir)

        # Figure 1: what the fixed API returns for three test experiments.
        fig, axes = plt.subplots(len(EXPERIMENTS), 1, figsize=(7.2, 6.0), sharex=False)
        for ax, eid in zip(axes, EXPERIMENTS):
            model, scores = api_scores(ref, model_dir, tidy, eid)
            e = tidy[tidy["experiment_id"] == eid].sort_values("t")
            anomalous = e["anomaly"].to_numpy() == 1
            t = e["t"].to_numpy()
            if anomalous.any():
                ax.axvspan(t[anomalous].min(), t[anomalous].max(), color=INK["grid"], linewidth=0)
            ax.axvspan(0, model.n_burn_in, color=SERIES[3], alpha=0.15, linewidth=0)
            ax.plot(t, np.minimum(scores, YMAX), color=SERIES[0], linewidth=1.2)
            ax.axhline(model.threshold, color=SERIES[1], linewidth=1.2)
            ax.set_ylim(0, YMAX * 1.05)
            if scores.max() > YMAX:
                ax.annotate(f"clipped; max {scores.max():.0f}", (t[np.argmax(scores)], YMAX), xytext=(-6, -2),
                            textcoords="offset points", ha="right", va="top", fontsize=8, color=INK["secondary"])
            ax.set_ylabel("score")
            ax.set_title(eid, loc="left", fontsize=10)
            ROWS.append({"figure": "api_traces", "series": eid, "x": "max_score", "value": round(float(scores.max()), 3)})
            ROWS.append({"figure": "api_traces", "series": eid, "x": "flagged_rows_after_burn_in",
                         "value": int(np.sum(scores[t >= model.n_burn_in] >= model.threshold))})
        axes[-1].set_xlabel("row (seconds since start)")
        fig.suptitle("Scores returned by POST /predict for three test experiments\n"
                     "orange line: threshold 7.24 · yellow: burn-in rows · grey: labelled anomaly",
                     x=0.02, ha="left", fontsize=10)
        fig.tight_layout()
        save(fig, HERE / "api_traces.svg")

        # Figure 2: the starter's skew, measured on real data, against the formula.
        starter = load_package(UNIT / "lab" / "src")
        measured = []
        for eid in sorted(tidy["experiment_id"].unique()):
            _, fixed = api_scores(ref, model_dir, tidy, eid)
            _, skewed = api_scores(starter, model_dir, tidy, eid)
            nz = fixed > 0
            measured.append(float(np.median(skewed[nz] / fixed[nz])))
        ratio = float(np.median(measured))
        ROWS.append({"figure": "skew", "series": "measured_ratio_n100", "x": 100, "value": round(ratio, 6)})
        ROWS.append({"figure": "skew", "series": "measured_ratio_spread", "x": 100,
                     "value": round(float(np.max(measured) - np.min(measured)), 9)})
    n = np.arange(2, 301)
    rel = (np.sqrt((n - 1) / n) - 1) * 100
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ax.plot(n, rel, color=SERIES[0], label="ddof=1 API vs ddof=0 batch, by formula")
    ax.plot([100], [(ratio - 1) * 100], marker="o", markersize=8, color=SERIES[1], linestyle="none",
            label="measured on 35 SKAB experiments (n = 100)")
    ax.annotate(f"{(ratio - 1) * 100:.2f} %", (100, (ratio - 1) * 100), xytext=(8, -14), textcoords="offset points",
                color=INK["secondary"], fontsize=9)
    ax.set_xscale("log")
    ax.set_xlabel("burn-in rows n")
    ax.set_ylabel("API score relative to batch, %")
    ax.set_title("A one-character default (ddof) shrinks every served score")
    ax.legend(loc="lower right")
    save(fig, HERE / "skew_vs_burn_in.svg")
    for k in (2, 10, 30, 100):
        ROWS.append({"figure": "skew", "series": "formula_percent", "x": k, "value": round(float(rel[k - 2]), 4)})

    with (HERE / "figure_data.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["figure", "series", "x", "value"])
        writer.writeheader()
        writer.writerows(ROWS)
    for r in ROWS:
        print(r)


if __name__ == "__main__":
    main()
