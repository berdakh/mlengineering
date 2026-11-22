"""Worked example: how a faithful-looking re-implementation of preprocessing skews a model.

    python lessons/w5d1_inference_pipeline/example/skew_demo.py      # about 2 seconds

SYNTHETIC data: a subscription business's churn table (tenure_months, monthly_spend, support_tickets).
A data scientist trains StandardScaler + LogisticRegression. A serving engineer, who cannot import
the training code, re-implements the scaling "from the notebook": stats computed with pandas and the
features read from a dict. Three serving paths are compared with the trained pipeline:

  A. re-implemented scaling, pandas std (ddof=1) and features in alphabetical order;
  B. as A, but with the column order fixed;
  C. the trained object itself, loaded by the service (one object for training and serving).

Nothing here says anything about real churn; the point is the size and the shape of the error.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = ["tenure_months", "monthly_spend", "support_tickets"]   # the order the model was trained in


def make_table(n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    tenure = rng.gamma(2.0, 12.0, n)
    spend = rng.normal(40.0, 12.0, n).clip(5)
    tickets = rng.poisson(1.0 + 0.04 * (60 - spend.clip(0, 60)), n)
    logit = -1.0 - 0.06 * tenure + 0.02 * (spend - 40) + 0.45 * tickets
    churn = rng.random(n) < 1 / (1 + np.exp(-logit))
    return pd.DataFrame({"tenure_months": tenure, "monthly_spend": spend, "support_tickets": tickets,
                         "churned": churn.astype(int)})


def main() -> None:
    train, live = make_table(400, seed=1), make_table(10_000, seed=2)
    model = make_pipeline(StandardScaler(), LogisticRegression()).fit(train[FEATURES], train["churned"])
    trained_p = model.predict_proba(live[FEATURES])[:, 1]

    scaler, clf = model[0], model[1]
    stats = {c: (train[c].mean(), train[c].std()) for c in FEATURES}     # pandas: ddof=1
    weights = dict(zip(FEATURES, clf.coef_[0]))

    def reimplemented(rows: pd.DataFrame, order: list[str]) -> np.ndarray:
        z = np.column_stack([(rows[c] - stats[c][0]) / stats[c][1] for c in order])
        w = np.array([weights[c] for c in FEATURES])                     # weights in the trained order
        return 1 / (1 + np.exp(-(z @ w + clf.intercept_[0])))

    paths = {
        "A. re-implemented, ddof=1, alphabetical columns": reimplemented(live, sorted(FEATURES)),
        "B. re-implemented, ddof=1, trained column order": reimplemented(live, FEATURES),
        "C. the trained object itself": model.predict_proba(live[FEATURES])[:, 1],
    }
    print(f"training rows {len(train)}, live rows {len(live)}, decision threshold 0.5")
    print(f"scaler std (ddof=0) vs pandas std (ddof=1), tenure: {scaler.scale_[0]:.4f} vs {stats['tenure_months'][1]:.4f}")
    for name, p in paths.items():
        flips = int(((p >= 0.5) != (trained_p >= 0.5)).sum())
        print(f"  {name:<50} max |dp| = {np.abs(p - trained_p).max():.2e}; decisions flipped: {flips}")


if __name__ == "__main__":
    main()
