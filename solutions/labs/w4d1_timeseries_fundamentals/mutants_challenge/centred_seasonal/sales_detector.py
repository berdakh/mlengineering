"""w4d1 challenge, reference solution: promotion detection on SYNTHETIC daily store sales.

Design decisions (defended in DECISION.md):
* models are fitted per store on development dates only, never on the period being evaluated;
* the score is ONE-SIDED: a promotion only raises sales, and a seasonal-naive forecast made from a
  promotion week produces a large *negative* residual one period later (the "echo"); absolute
  residuals would turn every promotion into a second, false alarm a week later;
* the method and threshold are chosen on the second half of the development period, with models
  fitted on the first half; the test period is touched once, by ``evaluate``.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

METHODS = ("seasonal_naive", "ar")
PERIOD = 7
AR_P = 7


def _fit_predict(x: np.ndarray, n_fit: int, method: str) -> tuple[np.ndarray, float]:
    """One-step-ahead forecasts for the whole series and the residual spread on the fit window."""
    n = len(x)
    pred = np.full(n, np.nan)
    if method == "seasonal_naive":
        pred[PERIOD:] = x[:-PERIOD]
        pred[:-PERIOD] = x[PERIOD:]
    elif method == "ar":
        p = AR_P
        lags = lambda a: np.column_stack([a[p - k:len(a) - k] for k in range(1, p + 1)])  # noqa: E731
        fit = x[:n_fit]
        design = np.column_stack([np.ones(len(fit) - p), lags(fit)])
        beta, *_ = np.linalg.lstsq(design, fit[p:], rcond=None)
        pred[p:] = beta[0] + lags(x) @ beta[1:]
    else:
        raise ValueError(f"unknown method {method!r}; expected one of {METHODS}")
    resid = (x - pred)[:n_fit]
    sigma = float(np.nanstd(resid[np.isfinite(resid)], ddof=1))
    return pred, sigma if sigma > 0 else 1.0


def store_scores(df: pd.DataFrame, method: str, fit_end: str) -> np.ndarray:
    """One score per row of ``df`` (in df order): positive part of the standardised one-step residual.

    Per store, in date order, the model is fitted on dates < ``fit_end``. NaN where no forecast exists.
    Works on log sales, where the weekly pattern and promotion uplifts are additive.
    """
    out = np.full(len(df), np.nan)
    frame = df.reset_index(drop=True)
    for _, g in frame.groupby("store", sort=False):
        g = g.sort_values("date", kind="stable")
        x = np.log(g["sales"].to_numpy(dtype=float))
        n_fit = int((g["date"] < fit_end).sum())
        pred, sigma = _fit_predict(x, n_fit, method)
        out[g.index.to_numpy()] = np.clip((x - pred) / sigma, 0.0, None)
    return out


def _f1(y: np.ndarray, flag: np.ndarray) -> tuple[float, float, float]:
    flag = np.asarray(flag, dtype=bool)
    tp = int((flag & (y == 1)).sum())
    p = tp / flag.sum() if flag.sum() else 0.0
    r = tp / (y == 1).sum() if (y == 1).sum() else float("nan")
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def choose(df: pd.DataFrame, dev_end: str) -> dict:
    """Pick method and threshold using development dates only (``date < dev_end``)."""
    dev = df[df["date"] < dev_end].reset_index(drop=True)
    dates = np.sort(dev["date"].unique())
    inner_end = dates[len(dates) // 2]
    val = (dev["date"] >= inner_end).to_numpy()
    y = dev["promo"].to_numpy()
    best = None
    for method in METHODS:
        s = np.nan_to_num(store_scores(dev, method, inner_end), nan=0.0)
        for threshold in np.unique(np.round(s[val], 3)):
            f1 = _f1(y[val], s[val] >= threshold)[2]
            if best is None or f1 > best["dev_f1"]:
                best = {"method": method, "threshold": float(threshold), "dev_f1": float(f1)}
    return best


def evaluate(df: pd.DataFrame, dev_end: str, choice: dict) -> dict:
    """Refit on all development dates, score the test dates once, report row-level P/R/F1."""
    s = np.nan_to_num(store_scores(df, choice["method"], dev_end), nan=0.0)
    test = (df["date"] >= dev_end).to_numpy()
    p, r, f1 = _f1(df["promo"].to_numpy()[test], s[test] >= choice["threshold"])
    return {"precision": p, "recall": r, "f1": f1, "n_test_rows": int(test.sum())}


if __name__ == "__main__":
    from pathlib import Path
    here = Path(__file__).resolve()
    root = next(q for q in here.parents if (q / "project" / "get_skab.py").is_file())
    data = pd.read_csv(root / "labs" / "w4d1_timeseries_fundamentals" / "challenge" / "data" / "sales.csv")
    choice = choose(data, "2025-07-01")
    print("choice:", choice)
    print("test:  ", evaluate(data, "2025-07-01", choice))
