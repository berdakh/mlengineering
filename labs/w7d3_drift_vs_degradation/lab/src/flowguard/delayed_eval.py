"""Delayed evaluation: join late labels to logged alarms and measure what can be measured.

YOU IMPLEMENT THIS MODULE in lesson w7d3 (section 4). The contract is in the lesson; in short:

* ``join_verdicts(alarms, verdicts, as_of=None)`` -> ``(joined, report)``
* ``alarm_precision(joined, min_labelled=5, level=0.95)`` -> dict
* ``recall_estimate(joined, fault_reports, as_of=None, min_events=5, level=0.95)`` -> dict
* ``window_metrics(alarms, verdicts, fault_reports, start, end, freq="7D", as_of=None,
  min_labelled=5, min_events=5, level=0.95)`` -> DataFrame
* ``monitor_report(drift_result, window, baseline, margin=0.1)`` -> dict

Three rules hold everywhere:
1. Only labels with ``label_time <= as_of`` exist. Nothing from the future is used.
2. A metric without enough labels is reported as ``status = "insufficient_data"`` with a NaN
   estimate. It is never 0 and never 1 by default.
3. Every estimate carries its denominator and an interval (``flowguard.uncertainty.wilson_interval``).
"""
from __future__ import annotations

import pandas as pd

from flowguard.uncertainty import wilson_interval  # noqa: F401  (you will need it)

OK, INSUFFICIENT = "ok", "insufficient_data"


def join_verdicts(alarms: pd.DataFrame, verdicts: pd.DataFrame, as_of=None) -> tuple[pd.DataFrame, dict]:
    """One row per alarm (input order) with ``verdict`` (True / False / <NA> = pending), ``fault_id``
    and ``label_time`` from the LATEST verdict known at ``as_of``; plus a report dict with keys
    ``n_alarms``, ``n_labelled``, ``n_pending``, ``orphan_verdicts``, ``superseded``."""
    raise NotImplementedError("task 1")


def alarm_precision(joined: pd.DataFrame, min_labelled: int = 5, level: float = 0.95) -> dict:
    """Precision among labelled alarms: keys status, estimate, low, high, k, n, n_pending."""
    raise NotImplementedError("task 2")


def recall_estimate(joined: pd.DataFrame, fault_reports: pd.DataFrame, as_of=None,
                    min_events: int = 5, level: float = 0.95) -> dict:
    """Distinct caught faults / (caught + reported missed): keys status, estimate, low, high, k, n,
    n_caught, n_missed_reported."""
    raise NotImplementedError("task 3")


def window_metrics(alarms: pd.DataFrame, verdicts: pd.DataFrame, fault_reports: pd.DataFrame,
                   start, end, freq: str = "7D", as_of=None, min_labelled: int = 5,
                   min_events: int = 5, level: float = 0.95) -> pd.DataFrame:
    """One row per event-time window [start + k*freq, start + (k+1)*freq) covering [start, end)."""
    raise NotImplementedError("task 4")


def monitor_report(drift_result: dict, window, baseline: dict, margin: float = 0.1) -> dict:
    """Keys input_changed, model_ok, precision_ok, recall_ok, action (see the lesson, task 5)."""
    raise NotImplementedError("task 5")
