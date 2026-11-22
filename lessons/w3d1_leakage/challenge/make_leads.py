"""SYNTHETIC lead-conversion data for the w3d1 challenge: few rows, many features, weak signal.

    python lessons/w3d1_leakage/challenge/make_leads.py     # writes leads.csv next to this file

240 leads x 300 marketing-touch features (standard normal). Conversion depends weakly on
``n_signal`` of them. With ``n_signal=0`` the features are pure noise and the only honest
answer is "ROC AUC about 0.5". Simulated; no conclusion about real marketing data follows.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

N_ROWS, N_FEATURES = 240, 300


def simulate(seed: int = 7, n_rows: int = N_ROWS, n_features: int = N_FEATURES,
             n_signal: int = 6, strength: float = 0.45) -> tuple[pd.DataFrame, pd.Series]:
    """Features and labels. The signal features are fixed by ``seed`` so that more rows from the
    same world can be drawn with ``n_rows`` alone changed (``draw`` below)."""
    world = np.random.default_rng(seed)
    signal = world.choice(n_features, size=n_signal, replace=False) if n_signal else np.array([], dtype=int)
    weights = world.choice([-1.0, 1.0], size=n_signal) * strength
    return _draw(np.random.default_rng([seed, 1]), n_rows, n_features, signal, weights)


def draw_more(seed: int, n_rows: int, n_features: int = N_FEATURES, n_signal: int = 6,
              strength: float = 0.45) -> tuple[pd.DataFrame, pd.Series]:
    """Fresh rows from the same world as ``simulate(seed, ...)`` (independent of the first sample)."""
    world = np.random.default_rng(seed)
    signal = world.choice(n_features, size=n_signal, replace=False) if n_signal else np.array([], dtype=int)
    weights = world.choice([-1.0, 1.0], size=n_signal) * strength
    return _draw(np.random.default_rng([seed, 2]), n_rows, n_features, signal, weights)


def _draw(rng, n_rows, n_features, signal, weights):
    x = rng.standard_normal((n_rows, n_features))
    logit = -0.4 + x[:, signal] @ weights if len(signal) else np.full(n_rows, -0.4)
    y = (rng.random(n_rows) < 1.0 / (1.0 + np.exp(-logit))).astype(int)
    columns = [f"touch_{i:03d}" for i in range(n_features)]
    return pd.DataFrame(x.round(4), columns=columns), pd.Series(y, name="converted")


if __name__ == "__main__":
    X, y = simulate()
    out = Path(__file__).parent / "leads.csv"
    X.assign(converted=y).to_csv(out, index=False, lineterminator="\n")
    print(f"wrote {out}: {X.shape[0]} rows x {X.shape[1]} features, conversion rate {y.mean():.3f}")
