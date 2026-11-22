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

def measure_latency(scorer, tidy: pd.DataFrame, n_warmup: int = 50, n_repeat: int = 500,
                    batch_size: int = 1, clock: Callable[[], float] = time.perf_counter) -> dict:
    """Per-call latency of ``scorer.score`` on batches of ``tidy``, warm-up excluded (milliseconds).

    Returns ``{"n", "batch_size", "mean_ms", "p50_ms", "p95_ms", "p99_ms", "max_ms"}``.
    Read the module docstring for exactly what is timed and how batches are formed.
    """
    raise NotImplementedError("TODO: implement measure_latency")


def model_size_bytes(model, path: str | Path | None = None) -> int:
    """Bytes on disk of ``model`` pickled (protocol 5). Writes to ``path`` if given, else a temp file
    that is removed afterwards."""
    raise NotImplementedError("TODO: implement model_size_bytes")


def dominated_by(table, objectives: Mapping[str, str]) -> dict[str, list[str]]:
    """For every row name, the names of the rows that dominate it (empty list: on the front).

    ``table``: a DataFrame or a list of dicts with a ``"name"`` column. ``objectives``:
    ``{column: "max" | "min"}``. Raise ValueError for an unknown direction, a missing column or a
    missing (NaN) objective value.
    """
    raise NotImplementedError("TODO: implement dominated_by")


def pareto_front(table, objectives: Mapping[str, str]) -> list[str]:
    """Names of the non-dominated rows, in table order."""
    raise NotImplementedError("TODO: implement pareto_front")


def classify_difference(lo: float, hi: float, mpid: float) -> str:
    """Place the interval [lo, hi] for (candidate - reference) against +/- mpid. See module doc.

    Raise ValueError if ``mpid <= 0`` or the interval is invalid (NaN, or lo > hi).
    """
    raise NotImplementedError("TODO: implement classify_difference")


def decision_table(rows: Sequence[Mapping], objectives: Mapping[str, str], mpid: float,
                   diff_lo: str = "diff_lo", diff_hi: str = "diff_hi") -> pd.DataFrame:
    """The comparison table: the input columns plus ``pareto`` (bool), ``dominated_by`` (names, ';'
    separated, empty string when none) and ``vs_reference`` (``classify_difference`` of each row's
    interval ``[row[diff_lo], row[diff_hi]]``).
    """
    raise NotImplementedError("TODO: implement decision_table")


def recommend(table: pd.DataFrame, constraints: Mapping[str, tuple[str, float]],
              complexity: str = "complexity", primary: str = "primary") -> dict:
    """Pick a candidate from a ``decision_table``.

    1. Drop every row that violates a hard constraint, given as ``{column: ("<=", limit)}`` or
       ``{column: (">=", limit)}``.
    2. If some remaining row is ``"better"`` than the reference, choose among those.
       Otherwise choose among the rows that are not ``"worse"``.
    3. Within that set take the lowest ``complexity`` rank; ties go to the higher ``primary`` value.

    Returns ``{"choice": name or None, "reason": str, "eligible": [names in preference order]}``;
    ``choice`` is None (with a reason) when nothing is eligible.
    """
    raise NotImplementedError("TODO: implement recommend")
