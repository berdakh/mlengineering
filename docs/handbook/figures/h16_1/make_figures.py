"""Figure for handbook H16.1 (decision memos). SYNTHETIC; deterministic.

    python handbook/figures/h16_1/make_figures.py      # about 40 seconds

intervals_by_unit.svg: the w4d5 challenge case (labs/w4d5_model_choice/challenge/case, SYNTHETIC),
interval for AUC(B) - AUC(A) by customer-level and by region-level paired bootstrap, against the MPID
band. The memo must say which unit was resampled; this is why.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CASE = ROOT / "labs" / "w4d5_model_choice" / "challenge" / "case"
sys.path.insert(0, str(ROOT))

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

N_BOOT, MPID = 1000, 0.02


def intervals() -> pd.DataFrame:
    d = pd.read_csv(CASE / "predictions.csv")
    y, a, b = (d[c].to_numpy() for c in ("churned", "score_a", "score_b"))
    groups = [g.index.to_numpy() for _, g in d.groupby("region")]
    rng = np.random.default_rng(0)
    out = {"customer": [], "region": []}
    for _ in range(N_BOOT):
        i = rng.integers(0, len(y), len(y))
        out["customer"].append(roc_auc_score(y[i], b[i]) - roc_auc_score(y[i], a[i]))
        i = np.concatenate([groups[k] for k in rng.integers(0, len(groups), len(groups))])
        out["region"].append(roc_auc_score(y[i], b[i]) - roc_auc_score(y[i], a[i]))
    est = roc_auc_score(y, b) - roc_auc_score(y, a)
    rows = [{"unit": u, "estimate": est, "lo": np.percentile(v, 2.5), "hi": np.percentile(v, 97.5)}
            for u, v in out.items()]
    return pd.DataFrame(rows)


def main() -> None:
    df = intervals()
    df.to_csv(HERE / "intervals_by_unit.csv", index=False)
    print(df.round(4).to_string(index=False))
    fig, ax = plt.subplots(figsize=(6.8, 2.6))
    ax.axvspan(-MPID, MPID, color=INK["grid"], alpha=0.6, lw=0)
    ax.axvline(0, color=INK["axis"], lw=1)
    labels = {"customer": "customers (15,295)\ntreated as independent", "region": "regions (40)\npaired, the stated unit"}
    for y, (color, (_, r)) in enumerate(zip((SERIES[1], SERIES[0]), df.iterrows())):
        ax.plot([r["lo"], r["hi"]], [y, y], color=color, lw=3, solid_capstyle="round")
        ax.plot(r["estimate"], y, "o", color=color, ms=7, mec=INK["surface"], mew=1.5)
        ax.text(r["hi"] + 0.003, y, f"[{r['lo']:+.3f}, {r['hi']:+.3f}]", va="center", fontsize=9, color=INK["secondary"])
    ax.set_yticks([0, 1])
    ax.set_yticklabels([labels[u] for u in df["unit"]])
    ax.set_xlim(-0.03, 0.06)
    ax.set_ylim(-0.6, 1.6)
    ax.text(0, 1.45, "±MPID 0.02", ha="center", fontsize=8, color=INK["secondary"])
    ax.set_xlabel("AUC(B) - AUC(A), 95 % bootstrap interval")
    ax.set_title("The same data, two units: one interval excludes zero (SYNTHETIC churn case)")
    ax.grid(axis="y", visible=False)
    save(fig, HERE / "intervals_by_unit.svg")


if __name__ == "__main__":
    main()
