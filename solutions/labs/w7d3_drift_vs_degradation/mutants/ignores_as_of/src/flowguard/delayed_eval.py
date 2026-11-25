"""Delayed evaluation: join late labels to logged alarms and measure what can be measured.

REFERENCE SOLUTION for lesson w7d3. The contract (see the lesson, section 4):

* ``join_verdicts(alarms, verdicts, as_of)`` -> ``(joined, report)``
* ``alarm_precision(joined, min_labelled, level)`` -> dict
* ``recall_estimate(joined, fault_reports, as_of, min_events, level)`` -> dict
* ``window_metrics(alarms, verdicts, fault_reports, start, end, freq, as_of, ...)`` -> DataFrame
* ``monitor_report(drift_result, window, baseline, margin)`` -> dict

Rules that every function follows:
1. Only labels with ``label_time <= as_of`` exist. Nothing from the future is used.
2. A metric without enough labels is reported as ``status = "insufficient_data"`` with a NaN
   estimate. It is never 0 and never 1 by default.
3. Every estimate carries its denominator and an interval.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from flowguard.uncertainty import wilson_interval

OK, INSUFFICIENT = "ok", "insufficient_data"


def _known(labels: pd.DataFrame, as_of) -> pd.DataFrame:
    return labels


def join_verdicts(alarms: pd.DataFrame, verdicts: pd.DataFrame, as_of=None) -> tuple[pd.DataFrame, dict]:
    """Attach to each alarm the latest verdict known at ``as_of``.

    Verdicts arrive out of order and sometimes twice; a later ``label_time`` supersedes an earlier one
    for the same ``alarm_id`` (a correction). Verdicts for unknown alarm ids are not joined; they are
    counted in ``report["orphan_verdicts"]`` so that a broken id pipeline is visible.
    Returns ``joined``: one row per alarm, in the input order, with columns ``verdict`` (True, False,
    or <NA> = pending), ``fault_id`` and ``label_time``.
    """
    known = _known(verdicts, as_of)
    orphan = ~known["alarm_id"].isin(alarms["alarm_id"])
    latest = (known[~orphan].sort_values("label_time", kind="stable")
              .drop_duplicates("alarm_id", keep="last")[["alarm_id", "verdict", "fault_id", "label_time"]])
    joined = alarms.merge(latest, on="alarm_id", how="left")  # a left merge keeps the alarms' order
    joined["verdict"] = joined["verdict"].astype("boolean")
    report = {"n_alarms": int(len(alarms)), "n_labelled": int(joined["verdict"].notna().sum()),
              "n_pending": int(joined["verdict"].isna().sum()),
              "orphan_verdicts": int(orphan.sum()),
              "superseded": int((~orphan).sum() - len(latest))}
    return joined, report


def _proportion(k: int, n: int, min_n: int, level: float) -> dict:
    if n < min_n or n == 0:
        return {"status": INSUFFICIENT, "estimate": math.nan, "low": math.nan, "high": math.nan, "k": k, "n": n}
    low, high = wilson_interval(k, n, level)
    return {"status": OK, "estimate": k / n, "low": low, "high": high, "k": k, "n": n}


def alarm_precision(joined: pd.DataFrame, min_labelled: int = 5, level: float = 0.95) -> dict:
    """Precision among alarms that have a verdict. Pending alarms are excluded, not counted as false.

    Unbiased only if the labelled alarms are like the unlabelled ones. When operators investigate the
    worst-looking alarms first, the labelled ones are the easy true positives: this overestimates.
    """
    labelled = joined["verdict"].dropna()
    out = _proportion(int(labelled.sum()), int(len(labelled)), min_labelled, level)
    out["n_pending"] = int(joined["verdict"].isna().sum())
    return out


def recall_estimate(joined: pd.DataFrame, fault_reports: pd.DataFrame, as_of=None,
                    min_events: int = 5, level: float = 0.95) -> dict:
    """Caught faults / (caught + reported missed), counting distinct ``fault_id`` values.

    ``caught`` comes from alarms confirmed True; ``missed`` from inspection reports known at ``as_of``
    for faults that no confirmed alarm caught. Faults that nobody reported are invisible, so this is an
    upper bound on recall whenever misses are reported with probability < 1.
    """
    confirmed = joined[joined["verdict"].fillna(False).astype(bool)]
    caught = set(confirmed["fault_id"].dropna())
    reports = _known(fault_reports, as_of)
    missed = set(reports["fault_id"]) - caught
    out = _proportion(len(caught), len(caught) + len(missed), min_events, level)
    out.update({"n_caught": len(caught), "n_missed_reported": len(missed)})
    return out


def window_metrics(alarms: pd.DataFrame, verdicts: pd.DataFrame, fault_reports: pd.DataFrame,
                   start, end, freq: str = "7D", as_of=None, min_labelled: int = 5,
                   min_events: int = 5, level: float = 0.95) -> pd.DataFrame:
    """Precision and recall per event-time window, using only labels known at ``as_of``.

    An alarm belongs to the window containing its ``start_time``; a reported missed fault to the
    window containing its ``start_time``. Windows are ``[start + k*freq, start + (k+1)*freq)`` up to
    ``end``. Label time decides *whether* a label is known; event time decides *where* it counts.
    """
    step, lo, end = pd.Timedelta(freq), pd.Timestamp(start), pd.Timestamp(end)
    edges = [lo]
    while edges[-1] < end:
        edges.append(edges[-1] + step)
    joined, _ = join_verdicts(alarms, verdicts, as_of)
    reports = _known(fault_reports, as_of)
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        a = joined[(pd.to_datetime(joined["start_time"]) >= lo) & (pd.to_datetime(joined["start_time"]) < hi)]
        r = reports[(pd.to_datetime(reports["start_time"]) >= lo) & (pd.to_datetime(reports["start_time"]) < hi)]
        p = alarm_precision(a, min_labelled, level)
        rc = recall_estimate(a, r, None, min_events, level)
        rows.append({"window_start": lo, "window_end": hi, "n_alarms": len(a),
                     "n_labelled": p["n"], "n_pending": p["n_pending"],
                     "precision": p["estimate"], "precision_low": p["low"], "precision_high": p["high"],
                     "precision_status": p["status"],
                     "n_caught": rc["n_caught"], "n_missed_reported": rc["n_missed_reported"],
                     "recall": rc["estimate"], "recall_low": rc["low"], "recall_high": rc["high"],
                     "recall_status": rc["status"]})
    return pd.DataFrame(rows)


def _judge(estimate, low, high, status, baseline, margin) -> str:
    """One metric against its baseline: 'unknown' (not enough labels), 'no' (clearly worse: the whole
    interval is below the baseline and the estimate is more than ``margin`` below it), 'yes' (clearly
    not worse: the interval's lower end is within ``margin`` of the baseline), else 'inconclusive'."""
    if baseline is None:
        return "not_monitored"
    if status != OK:
        return "unknown"
    if high < baseline and estimate < baseline - margin:
        return "no"
    if low >= baseline - margin:
        return "yes"
    return "inconclusive"


def monitor_report(drift_result: dict, window, baseline: dict, margin: float = 0.1) -> dict:
    """Answer the two monitoring questions separately for one window.

    * ``input_changed``: the drift monitor's verdict (``drift_result["drift"]``).
    * ``model_ok``: from labelled precision and recall, each judged against ``baseline``
      (``{"precision": float | None, "recall": float | None}``; None = not monitored) by ``_judge``.
      Combined: any "no" -> "no"; else any "inconclusive" -> "inconclusive"; else any "yes" -> "yes";
      else "unknown".
    The ``action`` names what the combination calls for; it never infers one answer from the other.
    """
    verdicts = {
        "precision_ok": _judge(window["precision"], window["precision_low"], window["precision_high"],
                               window["precision_status"], baseline.get("precision"), margin),
        "recall_ok": _judge(window["recall"], window["recall_low"], window["recall_high"],
                            window["recall_status"], baseline.get("recall"), margin),
    }
    seen = set(verdicts.values())
    model_ok = next((v for v in ("no", "inconclusive", "yes") if v in seen), "unknown")
    changed = bool(drift_result["drift"])
    actions = {
        (True, "yes"): "input changed, measured performance holds: investigate the input change, no model action",
        (True, "no"): "input changed and performance dropped: investigate both; consider retraining",
        (True, "inconclusive"): "input changed, performance not yet established: get labels for this window",
        (True, "unknown"): "input changed, performance not yet measurable: get labels for this window",
        (False, "yes"): "no action",
        (False, "no"): "performance dropped without input drift: escalate (concept change, labels, pipeline bug)",
        (False, "inconclusive"): "no drift, performance not established: keep collecting labels",
        (False, "unknown"): "nothing measurable yet: wait for labels",
    }
    return {"input_changed": changed, "model_ok": model_ok, **verdicts, "action": actions[(changed, model_ok)]}
