"""Worked example (w4d5): choosing a demand-forecasting model by evidence, not by leaderboard.

    python lessons/w4d5_model_choice/example/forecast_choice.py        # about 15 seconds

SYNTHETIC data: 60 stores x 104 weeks of unit sales with store-specific level, trend and yearly
season. Three candidates predict next week's sales from the past only:

  seasonal-naive   sales 52 weeks ago, scaled by the recent level ratio   (no training)
  ridge            ridge regression on the last 8 weeks and the value 52 weeks ago (one model)
  boosted trees    HistGradientBoosting on the same features              (one model)

Training: weeks 53-90 of every store; evaluation: weeks 91-104. The unit of resampling is the STORE:
errors of one store's weeks share its level, trend and noise. Metric: mean absolute percentage error
(MAPE, lower is better). The planning team says a forecast must be at least 1.0 percentage point
better to change ordering decisions (the MPID), and scoring all stores must take under 1 s.

Nothing here says anything about real retail data; it shows the decision mechanics.
"""
from __future__ import annotations

import os

# One thread: latency numbers then measure the model, not contention between OpenMP threads on a
# shared machine (with the default, boosted-tree timings swung from milliseconds to seconds here).
os.environ.setdefault("OMP_NUM_THREADS", "1")

import pickle  # noqa: E402
import time  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.ensemble import HistGradientBoostingRegressor  # noqa: E402
from sklearn.linear_model import Ridge  # noqa: E402

RNG = np.random.default_rng(7)
N_STORES, N_WEEKS = 60, 104
MPID = 1.0                       # percentage points of MAPE
N_BOOT = 2000


def simulate() -> pd.DataFrame:
    weeks = np.arange(N_WEEKS)
    rows = []
    for s in range(N_STORES):
        level = RNG.uniform(50, 400)
        trend = RNG.normal(0.002, 0.003)
        amp = RNG.uniform(0.05, 0.35)
        phase = RNG.uniform(0, 2 * np.pi)
        promo = RNG.random(N_WEEKS) < 0.08                          # promotions: +30 %, not in the features
        mean = level * (1 + trend) ** weeks * (1 + amp * np.sin(2 * np.pi * weeks / 52 + phase)) * (1 + 0.3 * promo)
        sales = RNG.poisson(mean)
        rows += [(f"S{s:02d}", w, int(v)) for w, v in zip(weeks, sales)]
    return pd.DataFrame(rows, columns=["store", "week", "sales"])


def features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["store", "week"]).copy()
    g = df.groupby("store")["sales"]
    for k in range(1, 9):
        df[f"lag{k}"] = g.shift(k)
    df["lag52"] = g.shift(52)
    df["level_ratio"] = g.shift(1).rolling(4).mean().reset_index(level=0, drop=True) / \
        g.shift(53).rolling(4).mean().reset_index(level=0, drop=True)
    return df


def mape_by_store(df: pd.DataFrame, pred: np.ndarray) -> dict[str, np.ndarray]:
    err = np.abs(df["sales"].to_numpy() - pred) / np.maximum(df["sales"].to_numpy(), 1) * 100
    return {s: err[(df["store"] == s).to_numpy()] for s in sorted(df["store"].unique())}


def pooled(results: list[np.ndarray]) -> float:
    return float(np.concatenate(results).mean())


def paired_diff(a: dict, b: dict, seed: int = 0) -> tuple[float, float, float]:
    ids = sorted(a)
    rng = np.random.default_rng(seed)
    reps = []
    for _ in range(N_BOOT):
        draw = [ids[i] for i in rng.integers(0, len(ids), len(ids))]
        reps.append(pooled([a[i] for i in draw]) - pooled([b[i] for i in draw]))
    return pooled(list(a.values())) - pooled(list(b.values())), *np.percentile(reps, [2.5, 97.5])


def main() -> None:
    df = features(simulate())
    cols = [f"lag{k}" for k in range(1, 9)] + ["lag52"]
    train = df[(df["week"] >= 53) & (df["week"] <= 90)].dropna()
    test = df[df["week"] >= 91].dropna()
    print(f"SYNTHETIC panel: {N_STORES} stores, train {len(train)} rows (weeks 53-90), test {len(test)} rows (91-104)\n")

    candidates = {}
    t0 = time.perf_counter()
    candidates["seasonal-naive"] = (None, time.perf_counter() - t0)
    t0 = time.perf_counter()
    ridge = Ridge(alpha=1.0).fit(train[cols], train["sales"])
    candidates["ridge"] = (ridge, time.perf_counter() - t0)
    t0 = time.perf_counter()
    gbt = HistGradientBoostingRegressor(max_iter=300, random_state=0).fit(train[cols], train["sales"])
    candidates["boosted trees"] = (gbt, time.perf_counter() - t0)

    def predict(name, frame):
        model = candidates[name][0]
        if model is None:
            return (frame["lag52"] * frame["level_ratio"]).to_numpy()
        return model.predict(frame[cols])

    per_store = {name: mape_by_store(test, predict(name, test)) for name in candidates}
    rows = []
    for rank, name in enumerate(candidates):
        lat = []
        for _ in range(30):                                     # score all 60 stores for one week
            batch = test.groupby("store").tail(1)
            t0 = time.perf_counter()
            predict(name, batch)
            lat.append((time.perf_counter() - t0) * 1000)
        d, lo, hi = paired_diff(per_store[name], per_store["seasonal-naive"])
        # lower MAPE is better, so "candidate better" means the difference is NEGATIVE
        verdict = ("better" if hi < -MPID else "worse" if lo > MPID else
                   "equivalent" if -MPID < lo and hi < MPID else "inconclusive")
        rows.append({"name": name, "complexity": rank, "mape": pooled(list(per_store[name].values())),
                     "diff_vs_naive": d, "lo": lo, "hi": hi, "verdict": verdict,
                     "p95_ms_all_stores": float(np.percentile(lat[5:], 95)),
                     "size_bytes": len(pickle.dumps(candidates[name][0], protocol=5)),
                     "fit_s": candidates[name][1]})
    table = pd.DataFrame(rows)
    with pd.option_context("display.width", 160, "display.float_format", "{:.3f}".format):
        print(table.to_string(index=False))

    v = table[["mape", "p95_ms_all_stores", "size_bytes"]].to_numpy() * -1      # all "lower is better"
    front = [table["name"][i] for i in range(len(v))
             if not any((v[j] >= v[i]).all() and (v[j] > v[i]).any() for j in range(len(v)) if j != i)]
    print(f"\nPareto front (MAPE, p95 latency, size; all minimised): {front}")
    better = table[table["verdict"] == "better"]
    pool = better if len(better) else table[table["verdict"] != "worse"]
    choice = pool.sort_values(["complexity", "mape"]).iloc[0]["name"]
    print(f"choice: {choice}  (rule: the simplest candidate among those shown practically better "
          f"than seasonal-naive, else the simplest not shown worse; MPID {MPID} points)")


if __name__ == "__main__":
    main()
