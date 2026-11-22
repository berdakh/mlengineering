"""One-step-ahead forecasters whose residuals serve as anomaly scores.

Conventions (the checks rely on them)
-------------------------------------
* A series is a 1-D float array in time order. ``predict(x)`` returns an array of the same length
  whose entry ``i`` is the forecast of ``x[i]`` made from ``x[:i]`` only (strictly the past).
  Entries that cannot be forecast (not enough history) are NaN.
* ``fit(x)`` learns from the series it is given and returns ``self``. It sets ``sigma_``, the
  standard deviation of the one-step residuals on that series; residual scores are divided by it.
* Nothing here looks at labels. These are models of *normal* behaviour, fitted on data assumed normal
  (the burn-in rows of an experiment, or a reference recording).
"""
from __future__ import annotations

from typing import Callable, Sequence

import numpy as np
import pandas as pd

_EPS = 1e-12


def _as_series(x) -> np.ndarray:
    x = np.asarray(x, dtype=float).ravel()
    if x.ndim != 1:
        raise ValueError("expected a 1-D series")
    return x


# --------------------------------------------------------------------------- autocorrelation
def acf(x, nlags: int) -> np.ndarray:
    """Sample autocorrelation r_0..r_nlags (r_0 = 1).

    r_k = sum_{t=k}^{n-1} (x_t - m)(x_{t-k} - m) / sum_t (x_t - m)^2, with m the sample mean.
    The denominator is the same for every lag (the standard biased estimator), which keeps the
    sequence positive semi-definite.
    """
    x = _as_series(x)
    if nlags < 0 or nlags >= len(x):
        raise ValueError("need 0 <= nlags < len(x)")
    d = x - x.mean()
    denom = float(d @ d)
    if denom <= _EPS:
        raise ValueError("series is constant; autocorrelation is undefined")
    return np.array([1.0] + [float(d[k:] @ d[:-k]) / denom for k in range(1, nlags + 1)])


# --------------------------------------------------------------------------- forecasters
class _Forecaster:
    sigma_: float

    def _set_sigma(self, x: np.ndarray) -> None:
        resid = x - self.predict(x)
        resid = resid[np.isfinite(resid)]
        if len(resid) < 2:
            raise ValueError("series too short to estimate the residual spread")
        s = float(resid.std(ddof=1))
        self.sigma_ = s if s > _EPS else 1.0      # a perfectly predictable series carries no scale


class NaiveForecaster(_Forecaster):
    """x_hat[i] = x[i-1]: tomorrow looks like today. The residual is the first difference."""

    def fit(self, x) -> "NaiveForecaster":
        self._set_sigma(_as_series(x))
        return self

    def predict(self, x) -> np.ndarray:
        x = _as_series(x)
        pred = np.full(len(x), np.nan)
        pred[1:] = x[:-1]
        return pred


class SeasonalNaiveForecaster(_Forecaster):
    """x_hat[i] = x[i - period]: this point looks like the same point one cycle ago."""

    def __init__(self, period: int):
        if period < 1:
            raise ValueError("period must be >= 1")
        self.period = int(period)

    def fit(self, x) -> "SeasonalNaiveForecaster":
        self._set_sigma(_as_series(x))
        return self

    def predict(self, x) -> np.ndarray:
        x = _as_series(x)
        pred = np.full(len(x), np.nan)
        pred[self.period:] = x[:-self.period]
        return pred


class ARForecaster(_Forecaster):
    """AR(p) with intercept, fitted by ordinary least squares:

        x_t = c + phi_1 x_{t-1} + ... + phi_p x_{t-p} + e_t

    ``coef_`` holds phi_1..phi_p (phi_1 multiplies the most recent value) and ``intercept_`` holds c.
    """

    def __init__(self, p: int):
        if p < 1:
            raise ValueError("p must be >= 1")
        self.p = int(p)

    def _design(self, x: np.ndarray) -> np.ndarray:
        n, p = len(x), self.p
        # column k-1 holds x_{t-k} for t = p .. n-1
        return np.column_stack([x[p - k:n - k] for k in range(1, p + 1)])

    def fit(self, x) -> "ARForecaster":
        x = _as_series(x)
        if len(x) <= 2 * self.p + 1:
            raise ValueError(f"need more than {2 * self.p + 1} points to fit AR({self.p})")
        if not np.isfinite(x).all():
            raise ValueError("fit series contains NaN or inf")
        lags = self._design(x)
        design = np.column_stack([np.ones(len(lags)), lags])
        beta, *_ = np.linalg.lstsq(design, x[self.p:], rcond=None)
        self.intercept_ = float(beta[0])
        self.coef_ = beta[1:].astype(float)
        self._set_sigma(x)
        return self

    def predict(self, x) -> np.ndarray:
        x = _as_series(x)
        pred = np.full(len(x), np.nan)
        if len(x) > self.p:
            pred[self.p:] = self.intercept_ + self._design(x) @ self.coef_
        return pred


# --------------------------------------------------------------------------- scores and alarm rules
def residual_scores(forecaster: _Forecaster, x) -> np.ndarray:
    """|x - x_hat| / sigma_, with NaN where no forecast exists. ``forecaster`` must already be fitted."""
    x = _as_series(x)
    return np.abs(x - forecaster.predict(x)) / forecaster.sigma_


def cusum(z, k: float = 0.5) -> np.ndarray:
    """Two-sided tabular CUSUM statistic of a standardised series.

        S+_t = max(0, S+_{t-1} + z_t - k),   S-_t = max(0, S-_{t-1} - z_t - k),   S_0 = 0

    returns max(S+_t, S-_t) for every t. NaN inputs contribute nothing (treated as z = 0 would
    still subtract k, so they are skipped: the statistic is carried forward unchanged).
    An alarm is raised where the statistic exceeds a limit h chosen by the caller.
    """
    z = _as_series(z)
    if k < 0:
        raise ValueError("k must be >= 0")
    up = down = 0.0
    out = np.empty(len(z))
    for i, v in enumerate(z):
        if np.isfinite(v):
            up = up + v - k
            down = down - v - k
        out[i] = max(up, down)
    return out


def ewma(z, lam: float = 0.2) -> np.ndarray:
    """EWMA of a standardised series: w_t = lam z_t + (1 - lam) w_{t-1}, w_0 = 0. NaN carried forward."""
    z = _as_series(z)
    if not 0.0 < lam <= 1.0:
        raise ValueError("lam must be in (0, 1]")
    w = 0.0
    out = np.empty(len(z))
    for i, v in enumerate(z):
        if np.isfinite(v):
            w = lam * v + (1.0 - lam) * w
        out[i] = w
    return out


# --------------------------------------------------------------------------- per-experiment application
def burn_in_forecast_scores(tidy: pd.DataFrame, make_forecaster: Callable[[], _Forecaster],
                            sensors: Sequence[str], n_burn: int, signed: bool = False) -> np.ndarray:
    """For every experiment and sensor: fit a fresh forecaster on the first ``n_burn`` rows, compute
    residuals for the whole experiment. Returns one score per row of ``tidy`` (in ``tidy`` order):

    * ``signed=False``: the maximum over sensors of |residual| / sigma_ (NaN-safe; NaN only if every
      sensor is NaN, i.e. in the first rows of each experiment);
    * ``signed=True``: an array of shape (rows, sensors) of signed standardised residuals, for
      control charts that need the direction.

    Each experiment is processed in time order (column ``t``) and never sees another experiment.
    """
    tidy = tidy.reset_index(drop=True)
    signed_out = np.full((len(tidy), len(sensors)), np.nan)
    for _, group in tidy.groupby("experiment_id", sort=False):
        group = group.sort_values("t", kind="stable")
        if len(group) <= n_burn:
            raise ValueError(f"experiment {group['experiment_id'].iloc[0]!r} has only {len(group)} rows")
        rows = group.index.to_numpy()
        for j, sensor in enumerate(sensors):
            x = group[sensor].to_numpy(dtype=float)
            model = make_forecaster().fit(x[:n_burn])
            signed_out[rows, j] = (x - model.predict(x)) / model.sigma_
    if signed:
        return signed_out
    with np.errstate(all="ignore"):
        absolute = np.abs(signed_out)
        all_nan = np.isnan(absolute).all(axis=1)
        out = np.where(all_nan, np.nan, np.nanmax(np.where(np.isnan(absolute), -np.inf, absolute), axis=1))
    return out
