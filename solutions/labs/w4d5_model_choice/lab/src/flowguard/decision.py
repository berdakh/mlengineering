"""Evidence for choosing between candidate models: cost to run, size, dominance, practical difference.

Conventions (the checks rely on them)
-------------------------------------
* ``measure_latency`` times ``scorer.score(batch)`` with ``clock`` (``time.perf_counter`` by default):
  ``t0 = clock(); scorer.score(batch); t1 = clock()``, one pair of clock readings per call, nothing
  else timed. The first ``n_warmup`` calls are made and discarded; the next ``n_repeat`` calls are the
  sample. Batch ``i`` is ``batch_size`` consecutive rows of ``tidy`` starting at row
  ``(i * batch_size) % len(tidy)`` (wrapping around). Results are in **milliseconds per call**;
  percentiles use NumPy's default (linear interpolation).
* ``model_size_bytes`` serialises the object with :mod:`pickle` (protocol 5) to a real file and
  returns that file's size. Pickle is used because it is what a naive deployment would do; w5d2 is
  about safer artifact formats.
* ``pareto_front`` keeps a row unless another row **dominates** it: at least as good on every
  objective and strictly better on at least one. Identical rows do not dominate each other, so
  ties are all kept. Rows are returned in their original order.
* ``classify_difference(lo, hi, mpid)`` reads an interval for "candidate minus reference" (higher is
  better) against the minimum practically important difference ``mpid`` (> 0), fixed in advance:
    - ``"better"``      the whole interval is above ``+mpid``;
    - ``"worse"``       the whole interval is below ``-mpid``;
    - ``"equivalent"``  the whole interval is strictly inside ``(-mpid, +mpid)``;
    - ``"inconclusive"`` anything else (the interval reaches across a boundary).
  A difference whose interval excludes zero but still reaches inside ``(-mpid, mpid)`` is
  *inconclusive*: detectable, perhaps, but not shown to matter.
"""
from __future__ import annotations

import os
import pickle
import tempfile
import time
from pathlib import Path
from typing import Callable, Mapping, Sequence

import numpy as np
import pandas as pd

_DIRECTIONS = ("max", "min")


# --------------------------------------------------------------------------- cost to run
def measure_latency(scorer, tidy: pd.DataFrame, n_warmup: int = 50, n_repeat: int = 500,
                    batch_size: int = 1, clock: Callable[[], float] = time.perf_counter) -> dict:
    """Per-call latency of ``scorer.score`` on batches of ``tidy``, warm-up excluded (milliseconds)."""
    if n_warmup < 0 or n_repeat < 1 or batch_size < 1:
        raise ValueError("need n_warmup >= 0, n_repeat >= 1 and batch_size >= 1")
    if len(tidy) == 0:
        raise ValueError("tidy has no rows to score")
    tidy = tidy.reset_index(drop=True)
    n = len(tidy)
    durations = np.empty(n_repeat)
    for i in range(n_warmup + n_repeat):
        start = (i * batch_size) % n
        idx = [(start + k) % n for k in range(batch_size)]
        batch = tidy.iloc[idx]
        t0 = clock()
        scorer.score(batch)
        t1 = clock()
        if i >= n_warmup:
            durations[i - n_warmup] = (t1 - t0) * 1000.0
    return {
        "n": int(n_repeat), "batch_size": int(batch_size),
        "mean_ms": float(durations.mean()),
        "p50_ms": float(np.percentile(durations, 50)),
        "p95_ms": float(np.percentile(durations, 95)),
        "p99_ms": float(np.percentile(durations, 99)),
        "max_ms": float(durations.max()),
    }


def model_size_bytes(model, path: str | Path | None = None) -> int:
    """Bytes on disk of ``model`` pickled (protocol 5). Writes to ``path`` if given, else a temp file."""
    if path is not None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as fh:
            pickle.dump(model, fh, protocol=5)
        return path.stat().st_size
    fd, tmp = tempfile.mkstemp(suffix=".pkl")
    try:
        with os.fdopen(fd, "wb") as fh:
            pickle.dump(model, fh, protocol=5)
        return Path(tmp).stat().st_size
    finally:
        Path(tmp).unlink(missing_ok=True)


# --------------------------------------------------------------------------- dominance
def _frame(table) -> pd.DataFrame:
    df = pd.DataFrame(table).reset_index(drop=True)
    if "name" not in df.columns:
        raise ValueError("table needs a 'name' column")
    return df


def _oriented(df: pd.DataFrame, objectives: Mapping[str, str]) -> np.ndarray:
    """Objective values turned so that larger is always better."""
    if not objectives:
        raise ValueError("give at least one objective")
    cols = []
    for col, direction in objectives.items():
        if direction not in _DIRECTIONS:
            raise ValueError(f"objective {col!r}: direction must be 'max' or 'min', not {direction!r}")
        if col not in df.columns:
            raise ValueError(f"objective {col!r} is not a column of the table")
        values = pd.to_numeric(df[col], errors="raise").to_numpy(dtype=float)
        if np.isnan(values).any():
            raise ValueError(f"objective {col!r} has missing values; decide what they mean first")
        cols.append(values if direction == "max" else -values)
    return np.column_stack(cols)


def dominated_by(table, objectives: Mapping[str, str]) -> dict[str, list[str]]:
    """For every row name, the names of the rows that dominate it (empty list: on the front)."""
    df = _frame(table)
    v = _oriented(df, objectives)
    names = df["name"].tolist()
    out: dict[str, list[str]] = {}
    for i, name in enumerate(names):
        out[name] = [names[j] for j in range(len(df))
                     if j != i and (v[j] >= v[i]).all() and (v[j] > v[i]).any()]
    return out


def pareto_front(table, objectives: Mapping[str, str]) -> list[str]:
    """Names of the non-dominated rows, in table order."""
    return [name for name, by in dominated_by(table, objectives).items() if not by]


# --------------------------------------------------------------------------- practical difference
def classify_difference(lo: float, hi: float, mpid: float) -> str:
    """Place the interval [lo, hi] for (candidate - reference) against +/- mpid. See module doc."""
    if not mpid > 0:
        raise ValueError("mpid must be positive")
    if np.isnan(lo) or np.isnan(hi) or lo > hi:
        raise ValueError("need a valid interval lo <= hi")
    if lo > mpid:
        return "better"
    if hi < -mpid:
        return "worse"
    if -mpid < lo and hi < mpid:
        return "equivalent"
    return "inconclusive"


def decision_table(rows: Sequence[Mapping], objectives: Mapping[str, str], mpid: float,
                   diff_lo: str = "diff_lo", diff_hi: str = "diff_hi") -> pd.DataFrame:
    """The comparison table: the input columns plus ``pareto`` (bool), ``dominated_by`` (names, ';'
    separated) and ``vs_reference`` (``classify_difference`` of each row's difference interval).

    The reference row itself has the interval (0, 0) and is classified ``"equivalent"``.
    """
    df = _frame(rows)
    by = dominated_by(df, objectives)
    df["pareto"] = [not by[n] for n in df["name"]]
    df["dominated_by"] = [";".join(by[n]) for n in df["name"]]
    df["vs_reference"] = [classify_difference(lo, hi, mpid) for lo, hi in zip(df[diff_lo], df[diff_hi])]
    return df


def recommend(table: pd.DataFrame, constraints: Mapping[str, tuple[str, float]],
              complexity: str = "complexity", primary: str = "primary") -> dict:
    """Pick a candidate from a ``decision_table``.

    1. Drop every row that violates a hard constraint, given as ``{column: ("<=", limit)}`` or
       ``{column: (">=", limit)}``.
    2. If some remaining row is ``"better"`` than the reference, choose among those.
       Otherwise choose among the rows that are not ``"worse"`` (the reference is always eligible).
    3. Within that set take the lowest ``complexity`` rank; ties go to the higher ``primary`` value.

    Returns ``{"choice": name or None, "reason": str, "eligible": [names]}``.
    """
    df = table.reset_index(drop=True)
    keep = np.ones(len(df), dtype=bool)
    for col, (op, limit) in constraints.items():
        if op == "<=":
            keep &= df[col].to_numpy(dtype=float) <= limit
        elif op == ">=":
            keep &= df[col].to_numpy(dtype=float) >= limit
        else:
            raise ValueError(f"constraint on {col!r}: operator must be '<=' or '>='")
    ok = df[keep]
    if ok.empty:
        return {"choice": None, "eligible": [],
                "reason": "no candidate meets the hard constraints; relax a constraint or find another option"}
    better = ok[ok["vs_reference"] == "better"]
    pool, why = (better, "practically better than the reference") if len(better) else \
        (ok[ok["vs_reference"] != "worse"], "no candidate is shown to be practically better, so the simplest "
                                            "candidate that is not shown to be worse")
    if pool.empty:
        return {"choice": None, "eligible": [],
                "reason": "every candidate meeting the constraints is shown to be worse than the reference"}
    pool = pool.sort_values([complexity, primary], ascending=[True, False], kind="stable")
    choice = pool["name"].iloc[0]
    return {"choice": choice, "eligible": pool["name"].tolist(), "reason": f"{choice}: {why}"}
