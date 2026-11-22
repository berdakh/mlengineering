"""Seed-variance reporting and a conservative verdict for comparing two detectors (reference solution).

Inputs are per-seed results of ONE metric on ONE fixed evaluation set, for example
``{0: 0.71, 1: 0.68, 2: 0.74}``. A deterministic detector is reported with several seeds that
give the same value (its seed spread is exactly zero, which is a fact worth showing).
"""
from __future__ import annotations

import math
from typing import Mapping

import numpy as np


def seed_summary(values: Mapping[int, float]) -> dict:
    """``{"n", "mean", "sd", "min", "max"}`` over seeds; ``sd`` uses ddof = 1 (sample sd).

    Raises ValueError for fewer than two seeds (one run is not a result: its spread is unknown)
    and for non-finite values (a crashed or diverged run must be reported, not averaged in).
    """
    v = np.array(list(values.values()), dtype=float)
    if len(v) < 2:
        raise ValueError("need at least two seeds: one run says nothing about seed variance")
    if not np.isfinite(v).all():
        raise ValueError("non-finite metric value: report the failed run instead of averaging it")
    return {"n": int(len(v)), "mean": float(v.mean()), "sd": float(v.std(ddof=1)),
            "min": float(v.min()), "max": float(v.max())}


def compare(a: Mapping[int, float], b: Mapping[int, float], test_halfwidth: float) -> dict:
    """Compare detector A with detector B. Returns the two summaries, the difference of means and a verdict.

    ``test_halfwidth`` is the half-width of a 95% test-set interval for the difference (for example
    from a paired cluster bootstrap, w3d5); it represents uncertainty that seeds cannot reveal.

    Verdict rule (documented in the lesson):
      seed_se = sqrt(sd_a^2 / n_a + sd_b^2 / n_b)      standard error of the difference of seed means
      margin  = max(2 * seed_se, test_halfwidth)
      "A better" if diff > margin, "B better" if diff < -margin, otherwise "cannot tell".
    """
    if test_halfwidth < 0 or not math.isfinite(test_halfwidth):
        raise ValueError("test_halfwidth must be a finite, non-negative number")
    sa, sb = seed_summary(a), seed_summary(b)
    diff = sa["mean"] - sb["mean"]
    seed_se = math.sqrt(sa["sd"] ** 2 / sa["n"] + sb["sd"] ** 2 / sb["n"])
    margin = test_halfwidth
    verdict = "A better" if diff > margin else "B better" if diff < -margin else "cannot tell"
    return {"a": sa, "b": sb, "difference": diff, "seed_se": seed_se, "margin": margin, "verdict": verdict}


def format_table(rows: Mapping[str, Mapping[int, float]]) -> str:
    """Markdown table "detector | seeds | mean ± sd | range" for any number of detectors."""
    lines = ["| detector | seeds | mean ± sd | range |", "|---|---|---|---|"]
    for name, values in rows.items():
        s = seed_summary(values)
        lines.append(f"| {name} | {s['n']} | {s['mean']:.3f} ± {s['sd']:.3f} | [{s['min']:.3f}, {s['max']:.3f}] |")
    return "\n".join(lines)
