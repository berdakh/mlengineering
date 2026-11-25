"""SLIs, error budgets and burn-rate paging for flowguard. STARTER (w7d1 challenge): implement the five functions; keep the signatures.

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


def availability_sli(events: Iterable[dict]) -> tuple[int, int]:
    """(good, valid) for the availability SLI over ``/predict`` access events. TODO."""
    raise NotImplementedError


def latency_sli(events: Iterable[dict], threshold_ms: float) -> tuple[int, int]:
    """(good, valid) for the latency SLI. TODO."""
    raise NotImplementedError


def error_budget(target: float, valid: int) -> float:
    """Number of bad events allowed among ``valid`` events at SLO ``target``. TODO."""
    raise NotImplementedError


def burn_rate(bad: int, valid: int, target: float) -> float:
    """Observed bad fraction / allowed bad fraction; 0.0 without traffic. TODO."""
    raise NotImplementedError


def should_page(window_counts: dict[str, tuple[int, int]], target: float,
                rules: tuple[tuple[str, str, float], ...] = DEFAULT_PAGE_RULES) -> bool:
    """True if for ANY rule BOTH windows burn at or above the factor. TODO."""
    raise NotImplementedError
