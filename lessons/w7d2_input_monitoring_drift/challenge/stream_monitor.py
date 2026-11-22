"""Monitor for a feature stream with a change calendar. STARTER (w7d2 challenge).

Implement ``monitor_stream``; keep its signature. Read ../challenge/README.md first.
"""
from __future__ import annotations

import pandas as pd

FEATURES = ("price", "basket_size", "session_length_s", "page_views")


def monitor_stream(df: pd.DataFrame, calendar: pd.DataFrame, reference_days: int = 14) -> list[dict]:
    """Return alerts as dicts {"day": int, "feature": str, "kind": "unexpected" | "expected" | "missing"}.

    ``df`` has one row per session with a ``day`` column and the FEATURES; ``calendar`` has columns
    ``day``, ``features`` (";"-separated) and ``note`` and lists PLANNED changes only.
    """
    raise NotImplementedError("TODO w7d2 challenge")
