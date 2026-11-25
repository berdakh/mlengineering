"""SLIs, error budgets and burn-rate paging for flowguard. REFERENCE SOLUTION (w7d1 challenge).

Inputs are the JSON access-log events of the lab (``event == "access"``), so the SLIs are computed
from exactly what the service records.

Definitions (also in SLO.md):

* **Availability SLI** over valid ``/predict`` requests: good = status < 500. A request is valid unless
  it was the client's fault (4xx): a malformed request answered with 422 is the service working.
  503 (not ready) is the service's fault and therefore bad.
* **Latency SLI** over successful ``/predict`` requests (status 200): good = duration <= threshold.
  Errors are excluded so a fast 500 cannot improve the latency SLI.
* **Burn rate** = observed bad fraction / allowed bad fraction (1 - target). Burn rate 1 spends the
  whole budget in exactly one SLO window.
"""
from __future__ import annotations

from typing import Iterable

# (long window, short window, burn-rate factor). Multi-window rule from the Google SRE workbook as
# recalled (not re-verified this session): page on 2 % of a 30-day budget burnt in 1 h, or 5 % in 6 h.
DEFAULT_PAGE_RULES: tuple[tuple[str, str, float], ...] = (("1h", "5m", 14.4), ("6h", "30m", 6.0))
PREDICT_ROUTE = "/predict"


def _predict_access(events: Iterable[dict]) -> list[dict]:
    return [e for e in events if e.get("event") == "access" and e.get("route") == PREDICT_ROUTE]


def availability_sli(events: Iterable[dict]) -> tuple[int, int]:
    """(good, valid) for the availability SLI."""
    valid = [e for e in _predict_access(events) if not 400 <= int(e["status"]) < 500]
    good = sum(int(e["status"]) < 500 for e in valid)
    return good, len(valid)


def latency_sli(events: Iterable[dict], threshold_ms: float) -> tuple[int, int]:
    """(good, valid) for the latency SLI: successful requests at or under ``threshold_ms``."""
    valid = _predict_access(events)
    good = sum(float(e["duration_ms"]) <= threshold_ms for e in valid)
    return good, len(valid)


def error_budget(target: float, valid: int) -> float:
    """Number of bad events allowed among ``valid`` events at SLO ``target`` (e.g. 0.999)."""
    if not 0.0 < target < 1.0:
        raise ValueError("target must be strictly between 0 and 1")
    return (1.0 - target) * valid


def burn_rate(bad: int, valid: int, target: float) -> float:
    """Observed bad fraction divided by the allowed bad fraction. 0.0 when there is no traffic."""
    if not 0.0 < target < 1.0:
        raise ValueError("target must be strictly between 0 and 1")
    if valid <= 0:
        return 0.0
    return (bad / valid) / (1.0 - target)


def should_page(window_counts: dict[str, tuple[int, int]], target: float,
                rules: tuple[tuple[str, str, float], ...] = DEFAULT_PAGE_RULES) -> bool:
    """Page if, for ANY rule, BOTH the long and the short window burn at or above the factor.

    ``window_counts`` maps a window name ("5m", "1h", ...) to (bad, valid) in that window. The long
    window makes the alert significant; the short window makes it stop soon after the problem stops.
    A window missing from ``window_counts`` counts as no traffic.
    """
    for long_w, short_w, factor in rules:
        long_bad, long_valid = window_counts.get(long_w, (0, 0))
        short_bad, short_valid = window_counts.get(short_w, (0, 0))
        if (burn_rate(long_bad, long_valid, target) >= factor
                and burn_rate(short_bad, short_valid, target) >= factor):
            return True
    return False
