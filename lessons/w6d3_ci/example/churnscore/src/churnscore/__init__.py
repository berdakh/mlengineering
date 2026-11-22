"""A churn-risk score from two account facts. The coefficients are invented (SYNTHETIC rule)."""
from __future__ import annotations

import math

__version__ = "0.1.0"


def churn_risk(tenure_months: float, tickets_90d: int) -> float:
    """Probability-like score in (0, 1): rises with recent support tickets, falls with tenure."""
    if tenure_months < 0 or tickets_90d < 0:
        raise ValueError("tenure_months and tickets_90d must be non-negative")
    z = -1.2 - 0.05 * tenure_months + 0.6 * tickets_90d
    return 1.0 / (1.0 + math.exp(-z))
