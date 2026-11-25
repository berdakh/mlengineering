"""Choosing an operating point under an alert budget, using development data only. CHALLENGE STARTER.

Return value of choose_operating_point: a dict with keys
  threshold, min_duration, merge_gap   the chosen grid values
  feasible                             True if the dev false-alarm rate is within the budget
  dev                                  the evaluate_experiments(...) result for the chosen values on dev
  dev_rate_upper_bound                 rate_upper_bound(dev false alarms, dev normal hours)
"""
from __future__ import annotations

import itertools
import math

import numpy as np
from scipy.stats import chi2

import _paths  # noqa: F401  (puts flowguard on the path)
from flowguard.evaluation import evaluate_experiments


def rate_upper_bound(n_false_alarms: int, hours: float, confidence: float = 0.95) -> float:
    """Exact one-sided upper confidence bound for a Poisson rate, in false alarms per hour.

    Solves P(N <= n | rate * hours) = 1 - confidence. With n = 0 this is -ln(1 - confidence) / hours,
    about 3 / hours at 95 % (the "rule of three"). Assumes independent arrivals at a constant rate.
    """
    raise NotImplementedError("TODO: implement rate_upper_bound")


def choose_operating_point(dev_tidy, dev_scores, budget_per_hour: float, thresholds, min_durations=(1,),
                           merge_gaps=(0,), burn_in: int = 0, early_tolerance: int = 0) -> dict:
    """Pick (threshold, min_duration, merge_gap) from the grid using ``dev_tidy`` only.

    A configuration is feasible when its dev false-alarm rate is <= ``budget_per_hour``. Among the
    feasible ones: highest event recall, then lowest median delay, then lowest false-alarm rate.
    If none is feasible, the configuration with the lowest dev false-alarm rate is returned
    (ties: highest recall) with ``feasible = False``; the caller must not present it as meeting the budget.
    """
    raise NotImplementedError("TODO: implement choose_operating_point")
