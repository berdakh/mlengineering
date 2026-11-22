"""Canary analysis with a stated stopping rule. REFERENCE SOLUTION for the w7d4 challenge.

``decide(log, rule)`` looks at all rows of ``log`` (cumulative data so far) and returns
``{"decision": "stop" | "continue" | "promote", "reasons": [...], "stats": {...}}``.
``run_canary(log, rule)`` applies ``decide`` after every hour, in order, and returns the first
non-"continue" decision with the hour it was reached (or "continue" at the last hour).

The rule (lesson w7d4, challenge README):
* stop  if the canary error rate's lower confidence bound exceeds the control error rate + margin;
* stop  if the canary alert rate's lower confidence bound exceeds ``max_alerts_per_hour``;
* promote only when the canary has run ``min_canary_hours`` hours and served ``min_canary_requests``
  requests AND the error rate's upper bound is within control + margin AND the alert rate's upper
  bound is within ``max_alerts_per_hour``;
* otherwise continue.
Bounds: Wilson for the error proportion (two-sided at ``confidence``), exact one-sided Poisson bounds
for the alert rate per machine-hour.
"""
from __future__ import annotations

import math

import pandas as pd
from scipy.stats import chi2

RULE = {"max_alerts_per_hour": 1.0, "error_margin": 0.01, "min_canary_hours": 24,
        "min_canary_requests": 2000, "confidence": 0.95}


def wilson(k: int, n: int, confidence: float) -> tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    from scipy.stats import norm
    z = norm.ppf(0.5 + confidence / 2)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def poisson_rate_bounds(k: int, exposure: float, confidence: float) -> tuple[float, float]:
    """One-sided exact bounds: P(rate >= low) = confidence and P(rate <= high) = confidence."""
    if exposure <= 0:
        return 0.0, math.inf
    low = 0.0 if k == 0 else chi2.ppf(1 - confidence, 2 * k) / (2 * exposure)
    high = chi2.ppf(confidence, 2 * (k + 1)) / (2 * exposure)
    return float(low), float(high)


def decide(log: pd.DataFrame, rule: dict = RULE) -> dict:
    canary, control = log[log["arm"] == "canary"], log[log["arm"] == "control"]
    c_req, c_err = int(canary["requests"].sum()), int(canary["errors"].sum())
    k_req, k_err = int(control["requests"].sum()), int(control["errors"].sum())
    control_rate = k_err / k_req if k_req else math.nan
    err_lo, err_hi = wilson(c_err, c_req, rule["confidence"])
    alerts, exposure = int(canary["alerts"].sum()), float(canary["machine_hours"].sum())
    al_lo, al_hi = poisson_rate_bounds(alerts, exposure, rule["confidence"])
    hours = int(canary["hour"].nunique())
    limit = control_rate + rule["error_margin"]
    stats = {"hours": hours, "canary_requests": c_req, "canary_error_rate": c_err / c_req if c_req else math.nan,
             "error_bounds": (err_lo, err_hi), "control_error_rate": control_rate,
             "alert_rate": alerts / exposure if exposure else math.nan, "alert_bounds": (al_lo, al_hi)}
    reasons = []
    if err_lo > limit:
        reasons.append(f"errors: canary lower bound {err_lo:.4f} > control {control_rate:.4f} + {rule['error_margin']}")
    if al_lo > rule["max_alerts_per_hour"]:
        reasons.append(f"alerts: canary lower bound {al_lo:.3f}/h > {rule['max_alerts_per_hour']}/h")
    if reasons:
        return {"decision": "stop", "reasons": reasons, "stats": stats}
    enough = hours >= rule["min_canary_hours"] and c_req >= rule["min_canary_requests"]
    safe = err_hi <= limit and al_hi <= rule["max_alerts_per_hour"]
    if enough and safe:
        return {"decision": "promote", "reasons": ["enough evidence and both guardrails bounded"], "stats": stats}
    why = []
    if not enough:
        why.append(f"not enough data yet ({hours} h, {c_req} requests)")
    if err_hi > limit:
        why.append(f"error upper bound {err_hi:.4f} > {limit:.4f}")
    if al_hi > rule["max_alerts_per_hour"]:
        why.append(f"alert upper bound {al_hi:.3f}/h > {rule['max_alerts_per_hour']}/h")
    return {"decision": "continue", "reasons": why, "stats": stats}


def run_canary(log: pd.DataFrame, rule: dict = RULE) -> dict:
    result, last = None, None
    last = int(log["hour"].max())
    result = decide(log, rule)
    return {"decision": result["decision"], "hour": last, "reasons": result["reasons"]}
