"""Reviewer figure: what each planted problem does to the reported score (SYNTHETIC data).

    python solutions/lessons/w8d6_final_assessment/figures/make_figures.py

Runs the reference evaluations of f5 and t1 and the leaky variants, prints the numbers and writes
honest_vs_leaky.svg. Kept in solutions/ because it names the leaks.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(ROOT), str(HERE.parent / "f5_leakage" / "lab"), str(HERE.parent / "t1_transfer" / "lab"),
                str(ROOT / "lessons" / "w8d6_final_assessment" / "data")]
import evaluate as t1  # noqa: E402
import fixed_eval as f5  # noqa: E402
import make_data  # noqa: E402
from sklearn.compose import ColumnTransformer  # noqa: E402
from sklearn.impute import SimpleImputer  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import average_precision_score  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.preprocessing import OneHotEncoder, StandardScaler  # noqa: E402

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

# ---------------------------------------------------------------- f5
df = f5.load()


def f5_ap(extra, split):
    num = f5.NUMERIC + extra
    pre = ColumnTransformer([("n", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), num),
                             ("c", make_pipeline(SimpleImputer(strategy="constant", fill_value="missing"),
                                                 OneHotEncoder(handle_unknown="ignore")), f5.CATEGORICAL)])
    tr, te = split
    m = make_pipeline(pre, LogisticRegression(max_iter=2000)).fit(df.iloc[tr][num + f5.CATEGORICAL], df.iloc[tr].lapsed_30d)
    return average_precision_score(df.iloc[te].lapsed_30d, m.predict_proba(df.iloc[te][num + f5.CATEGORICAL])[:, 1])


temporal = f5.make_split(df)
rnd = train_test_split(np.arange(len(df)), test_size=0.3, random_state=0, stratify=df.lapsed_30d)
f5_rows = [("honest (temporal split)", f5_ap([], temporal)), ("random split instead", f5_ap([], rnd)),
           ("+ winback_call_logged", f5_ap(["winback_call_logged"], temporal)),
           ("+ last_pickup_offset_days", f5_ap(["last_pickup_offset_days"], temporal)),
           ("colleague's script (all problems)", None)]
import subprocess  # noqa: E402
out = subprocess.run([sys.executable, str(ROOT / "lessons/w8d6_final_assessment/f5_leakage/lab/leaky_eval.py")],
                     capture_output=True, text=True).stdout
f5_rows[-1] = (f5_rows[-1][0], float([l for l in out.splitlines() if "average precision" in l][0].split()[-1]))
prev5 = df.iloc[temporal[1]].lapsed_30d.mean()

# ---------------------------------------------------------------- t1
tt = make_data.simulate_tabletop(with_truth=True)
tr, te = t1.split_train_test(tt.drop(columns=["p_true"]))
honest = t1.daily_topk_precision(te, t1.fit_and_score(tr, te))
leak = LogisticRegression(max_iter=2000).fit(tr[["customer_no_show_rate"]], tr.no_show)
t1_rows = [("random calls", te.no_show.mean()), ("rule (no deposit, lead time)", t1.daily_topk_precision(te, t1.rule_scores(te))),
           ("honest model", honest), ("generator's own probabilities", t1.daily_topk_precision(te, tt.loc[te.index, "p_true"])),
           ("model on customer_no_show_rate", t1.daily_topk_precision(te, leak.predict_proba(te[["customer_no_show_rate"]])[:, 1]))]

for name, rows in (("f5 AP", f5_rows), ("t1 daily top-10% precision", t1_rows)):
    print(name)
    for label, v in rows:
        print(f"  {label:38s} {v:.3f}")

fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.4))
for ax, rows, title, ref in ((axes[0], f5_rows, "f5: average precision, test months", prev5),
                             (axes[1], t1_rows, "t1: daily top-10 % precision", None)):
    labels = [r[0] for r in rows][::-1]
    values = [r[1] for r in rows][::-1]
    colors = [SERIES[1] if ("+" in l or "script" in l or "customer_no_show" in l) else
              (INK["muted"] if (l == "random calls" or "generator" in l) else SERIES[0]) for l in labels]
    ax.barh(range(len(rows)), values, color=colors, height=0.6)
    for i, v in enumerate(values):
        ax.text(v + 0.01, i, f"{v:.2f}", va="center", fontsize=8.5, color=INK["secondary"])
    ax.set_yticks(range(len(rows)), labels, fontsize=8.5)
    ax.set_xlim(0, 1.05)
    ax.set_title(title)
    if ref is not None:
        ax.axvline(ref, color=INK["muted"], lw=1, ls="--")
        ax.text(ref + 0.01, -0.55, "prevalence", fontsize=7.5, color=INK["muted"])
fig.suptitle("SYNTHETIC data: the leaks, not the split, produce the impressive numbers", x=0.01, ha="left",
             fontsize=11, fontweight="bold")
fig.tight_layout()
save(fig, HERE / "honest_vs_leaky.svg")
print("wrote", HERE / "honest_vs_leaky.svg")
