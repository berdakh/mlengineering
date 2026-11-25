"""Choosing an operating point under an alert budget, using development data only.

SNAPSHOT of the w3d4 challenge module, given to you in this lab; you do not need to edit it.
"""
from __future__ import annotations

import itertools
import math

import numpy as np
from scipy.stats import chi2


from flowguard.evaluation import evaluate_experiments


def rate_upper_bound(n_false_alarms: int, hours: float, confidence: float = 0.95) -> float:
    """Exact one-sided upper confidence bound for a Poisson rate, in false alarms per hour.

    Solves P(N <= n | rate * hours) = 1 - confidence. With n = 0 this is -ln(1 - confidence) / hours,
    about 3 / hours at 95 % (the "rule of three"). Assumes independent arrivals at a constant rate.
    """
    if n_false_alarms < 0:
        raise ValueError("n_false_alarms must be >= 0")
    if hours <= 0:
        return math.inf
    return float(chi2.ppf(confidence, 2 * (n_false_alarms + 1)) / (2.0 * hours))


def choose_operating_point(dev_tidy, dev_scores, budget_per_hour: float, thresholds, min_durations=(1,),
                           merge_gaps=(0,), burn_in: int = 0, early_tolerance: int = 0) -> dict:
    """Pick (threshold, min_duration, merge_gap) from the grid using ``dev_tidy`` only.

    A configuration is feasible when its dev false-alarm rate is <= ``budget_per_hour``. Among the
    feasible ones: highest event recall, then lowest median delay, then lowest false-alarm rate.
    If none is feasible, the configuration with the lowest dev false-alarm rate is returned
    (ties: highest recall) with ``feasible = False``; the caller must not present it as meeting the budget.
    """
    scores = np.asarray(dev_scores, dtype=float)
    best, best_key, fallback, fallback_key = None, None, None, None
    for threshold, min_duration, merge_gap in itertools.product(thresholds, min_durations, merge_gaps):
        result = evaluate_experiments(dev_tidy, scores >= threshold, burn_in=burn_in, min_duration=min_duration,
                                      merge_gap=merge_gap, early_tolerance=early_tolerance)
        rate, recall, delay = result["false_alarms_per_hour"], result["event_recall"], result["median_delay_s"]
        config = {"threshold": float(threshold), "min_duration": int(min_duration), "merge_gap": int(merge_gap),
                  "dev": result}
        if rate <= budget_per_hour:
            key = (-recall, delay, rate)
            if best_key is None or key < best_key:
                best, best_key = config, key
        key = (rate, -recall, delay)
        if fallback_key is None or key < fallback_key:
            fallback, fallback_key = config, key
    if fallback is None:
        raise ValueError("the grid is empty")
    chosen = dict(best if best is not None else fallback)
    chosen["feasible"] = best is not None
    chosen["dev_rate_upper_bound"] = rate_upper_bound(chosen["dev"]["n_false_alarms"], chosen["dev"]["normal_hours"])
    return chosen
