"""SYNTHETIC store x week demand panel (retail chain that keeps opening stores).

Generating process, per store s and week t (only weeks >= the store's opening week exist):
    demand = base_s * season(t) * shock_t * noise        base_s: store-level effect (log-normal)
    shock_t: a chain-wide weekly shock, independent from week to week (promotions, weather)
    fp_1..fp_3: "fingerprint" features (location, size, format) that identify the store
    label demand_next4 = demand summed over weeks t+1 .. t+4 (NaN when those weeks are not all present)
It isolates two leakage mechanisms (overlapping label windows; store identity). It is not a model of
any real retailer and nothing about forecasting accuracy can be concluded from it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LABEL_WEEKS = 4


def make_panel(seed: int = 0, n_stores: int = 60, n_weeks: int = 104, shock_sd: float = 0.35,
               season_amplitude: float = 0.15) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    opened = np.sort(np.r_[np.zeros(n_stores // 3, dtype=int), rng.integers(1, n_weeks - 12, n_stores - n_stores // 3)])
    base = rng.lognormal(mean=4.0, sigma=0.6, size=n_stores)
    fingerprint = rng.normal(0, 1, (n_stores, 3))
    shock = np.exp(rng.normal(0, shock_sd, n_weeks))
    weeks = np.arange(n_weeks)
    season = 1.0 + season_amplitude * np.sin(2 * np.pi * weeks / 52.0)
    rows = []
    for s in range(n_stores):
        t = weeks[weeks >= opened[s]]
        demand = base[s] * season[t] * shock[t] * np.exp(rng.normal(0, 0.05, len(t)))
        df = pd.DataFrame({"store_id": f"S{s:03d}", "week": t, "opened_week": int(opened[s]),
                           "fp_1": fingerprint[s, 0], "fp_2": fingerprint[s, 1], "fp_3": fingerprint[s, 2],
                           "demand": np.round(demand, 2)})
        future = sum(df["demand"].shift(-k) for k in range(1, LABEL_WEEKS + 1))
        df["demand_next4"] = future.round(2)
        rows.append(df)
    panel = pd.concat(rows, ignore_index=True)
    return panel.sample(frac=1.0, random_state=seed).reset_index(drop=True)   # row order carries no meaning
