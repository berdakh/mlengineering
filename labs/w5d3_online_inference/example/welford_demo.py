"""Worked example (w5d3): three ways to compute a running variance, on SYNTHETIC data.

    python labs/w5d3_online_inference/example/welford_demo.py

A temperature-like signal of 10,000 samples with standard deviation 0.5 sits on an offset that we
raise from 20 to 1e9 (think: a counter, a timestamp in nanoseconds, a sensor reporting in mV with a
large bias). The true variance is the same in every case. Three one-pass streaming estimators:

  naive     keep n, sum(x), sum(x^2);   var = (sum(x^2) - sum(x)^2 / n) / n
  shifted   the same sums of (x - K) with K = the first sample (a cheap, common fix)
  welford   keep n, mean, M2;   delta = x - mean; mean += delta / n; M2 += delta * (x - mean)

and the two-pass reference ``np.var`` (all data in memory). Then a 30-line streaming z-scorer is
checked for parity against its batch twin, the same pattern lesson w5d3 asks of you.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def naive(xs):
    n = s = s2 = 0.0
    for x in xs:
        n += 1
        s += x
        s2 += x * x
    return (s2 - s * s / n) / n


def shifted(xs):
    k = xs[0]
    n = s = s2 = 0.0
    for x in xs:
        d = x - k
        n += 1
        s += d
        s2 += d * d
    return (s2 - s * s / n) / n


def welford(xs):
    n, mean, m2 = 0, 0.0, 0.0
    for x in xs:
        n += 1
        delta = x - mean
        mean += delta / n
        m2 += delta * (x - mean)
    return m2 / n


class StreamingZ:
    """Calibrate on the first n_burn samples (Welford), then score |x - mu| / sigma."""

    def __init__(self, n_burn: int):
        self.n_burn, self.n, self.mean, self.m2, self.mu, self.sigma = n_burn, 0, 0.0, 0.0, None, None

    def update(self, x: float) -> float | None:
        if self.mu is not None:
            return abs(x - self.mu) / self.sigma
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        self.m2 += delta * (x - self.mean)
        if self.n == self.n_burn:
            self.mu, self.sigma = self.mean, math.sqrt(self.m2 / self.n) or 1.0
        return None


def batch_z(x: np.ndarray, n_burn: int) -> np.ndarray:
    out = np.full(len(x), np.nan)
    mu, sigma = x[:n_burn].mean(), x[:n_burn].std() or 1.0
    out[n_burn:] = np.abs(x[n_burn:] - mu) / sigma
    return out


def main() -> None:
    rng = np.random.default_rng(20261122)
    noise = rng.normal(0.0, 0.5, 10_000)
    rows = []
    for offset in (20.0, 1e4, 1e6, 1e8, 1e9):
        xs = (offset + noise).tolist()
        ref = float(np.var(np.array(xs)))
        rows.append({"offset": f"{offset:.0e}", "two-pass np.var": ref,
                     "naive rel.err": abs(naive(xs) - ref) / ref,
                     "shifted rel.err": abs(shifted(xs) - ref) / ref,
                     "welford rel.err": abs(welford(xs) - ref) / ref})
    pd.set_option("display.float_format", lambda v: f"{v:.3g}")
    print("Running variance of 10,000 SYNTHETIC samples, true SD 0.5 (variance about 0.25):")
    print(pd.DataFrame(rows).to_string(index=False))

    x = 1e6 + rng.normal(0.0, 0.5, 2_000)
    x[1500:] += 4.0                                                # a step fault
    scorer = StreamingZ(n_burn=100)
    streamed = np.array([np.nan if (s := scorer.update(v)) is None else s for v in x])
    batch = batch_z(x, 100)
    same_nan = bool((np.isnan(streamed) == np.isnan(batch)).all())
    diff = float(np.nanmax(np.abs(streamed - batch)))
    print(f"\nStreaming vs batch z on 2,000 samples at offset 1e6: same warm-up mask: {same_nan}; "
          f"max |diff| = {diff:.2e}")


if __name__ == "__main__":
    main()
