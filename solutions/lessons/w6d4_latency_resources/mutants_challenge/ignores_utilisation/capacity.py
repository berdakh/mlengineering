"""Capacity planning from a measured service curve. REFERENCE SOLUTION (w6d4 challenge).

Model: each worker process serves one CPU-bound request at a time (the GIL; lesson section 2.6), so a
worker's capacity is 1 / S requests per second for a mean service time S. Little's law relates the
average number of requests in the system to arrival rate and time in system: L = lambda * W.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path


def littles_law_concurrency(arrival_rps: float, mean_time_in_system_ms: float) -> float:
    """L = lambda * W: the average number of requests in the system (W converted to seconds)."""
    if arrival_rps < 0 or mean_time_in_system_ms < 0:
        raise ValueError("arrival rate and time in system must be non-negative")
    return arrival_rps * mean_time_in_system_ms / 1000.0


def workers_needed(arrival_rps: float, service_time_ms: float, target_utilisation: float = 0.7) -> int:
    """Smallest number of single-request-at-a-time workers that keeps utilisation <= target.

    Offered load in busy workers is a = lambda * S (Little's law applied to the servers only);
    utilisation with n workers is a / n, so n = ceil(a / rho_target). At least 1.
    """
    if not 0 < target_utilisation <= 1:
        raise ValueError("target_utilisation must be in (0, 1]")
    if arrival_rps < 0 or service_time_ms <= 0:
        raise ValueError("arrival rate must be >= 0 and service time > 0")
    offered = arrival_rps * service_time_ms / 1000.0
    return max(1, math.ceil(offered))


def load_curve(path: str | Path) -> list[dict]:
    """Rows of a measured curve CSV with numeric columns (rate_rps, p50_ms, p95_ms, p99_ms, error_rate, ...)."""
    with Path(path).open() as fh:
        return [{k: float(v) for k, v in row.items()} for row in csv.DictReader(fh)]


def max_rate_within_slo(curve: list[dict], slo_ms: float, percentile_key: str = "p95_ms",
                        max_error_rate: float = 0.001) -> float:
    """Highest measured rate such that it and every lower measured rate meet the SLO.

    A rate meets the SLO if row[percentile_key] <= slo_ms and row["error_rate"] <= max_error_rate.
    Rates are considered in increasing order; the first violation ends the search (a service that
    fails at 60/s and "passes" at 80/s is noise, not capacity). Returns 0.0 if the lowest rate fails.
    """
    best = 0.0
    for row in sorted(curve, key=lambda r: r["rate_rps"]):
        if row[percentile_key] <= slo_ms and row["error_rate"] <= max_error_rate:
            best = row["rate_rps"]
        else:
            break
    return best


def sensitivity(arrival_rps: float, service_time_ms: float, target_utilisation: float = 0.7,
                traffic_factors: tuple[float, ...] = (0.5, 1.0, 1.5, 2.0)) -> list[dict]:
    """Workers needed when traffic is scaled by each factor: [{"factor", "arrival_rps", "workers"}]."""
    return [{"factor": f, "arrival_rps": arrival_rps * f,
             "workers": workers_needed(arrival_rps * f, service_time_ms, target_utilisation)}
            for f in traffic_factors]
