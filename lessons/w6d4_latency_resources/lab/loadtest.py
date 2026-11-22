"""Open-loop load generation and latency statistics. YOUR LAB (w6d4): implement the five functions marked TODO.

The five functions below are the lab. ``measure_service.py`` uses them against a real uvicorn process;
the checks use them with fake, deterministic ``send`` functions (no network).

Vocabulary (lesson section 2):
* *intended start*: when a request was scheduled to be sent, ``t0 + i / rate``;
* *open loop*: requests are issued on that schedule whether or not earlier ones have finished;
* *latency*: ``finished - intended start``. Measuring from the intended start, not from the moment the
  request was actually sent, counts the time a request spent waiting behind a stalled generator or
  server. Measuring from the actual send is the "coordinated omission" error.
"""
from __future__ import annotations

import asyncio  # noqa: F401  (you will need it)
import json
import math  # noqa: F401  (you will need it)
import time
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path


def percentile(values: Sequence[float], q: float) -> float:
    """The q-th percentile (0 <= q <= 100) with linear interpolation between order statistics.

    Same definition as ``numpy.percentile(values, q)`` (method ``"linear"``): with the sorted values
    x_0 <= ... <= x_{n-1}, position h = (n - 1) q / 100, result x_floor(h) + (h - floor(h)) (x_ceil(h) - x_floor(h)).
    Raises ValueError for an empty input or q outside [0, 100]. Does not modify ``values``.
    Do not call numpy here: writing it is the point.
    """
    raise NotImplementedError("TODO (task 1)")


def intended_schedule(rate: float, duration: float) -> list[float]:
    """Offsets (seconds from the start) at which to send: i / rate for i = 0 .. round(rate * duration) - 1.
    Raises ValueError if rate or duration is not positive."""
    raise NotImplementedError("TODO (task 2)")


async def run_open_loop(send: Callable[[], Awaitable[int]], rate: float, duration: float,
                        clock: Callable[[], float] = time.perf_counter) -> list[dict]:
    """Issue ``send()`` on an open-loop schedule and record what happened to each request.

    ``send`` is an async function returning an HTTP status code; an exception counts as a failed
    request (status None, ``error`` holds a short description). Each record has: ``intended``,
    ``started``, ``finished`` (clock seconds), ``status``, ``error`` and ``latency`` = finished - intended.
    Requests must be issued at their intended times even while earlier ones are still running.
    Return the records in schedule order.
    """
    raise NotImplementedError("TODO (task 3)")


def summarise(records: Sequence[dict], warmup_s: float = 0.0, late_threshold_s: float = 0.010) -> dict:
    """Latency and error statistics, in milliseconds, excluding requests scheduled in the warm-up.

    Keys: n_sent, n_ok, n_errors, error_rate, throughput_rps, late_starts, max_start_lag_ms,
    p50_ms, p95_ms, p99_ms, mean_ms, max_ms.
    * Warm-up: drop records whose intended start is earlier than (first intended start + warmup_s).
    * Successful = 2xx status. Latency statistics use successful requests only (NaN if there are
      none); every other request counts in error_rate.
    * throughput_rps = successful responses / (last finish - first intended start) over kept records.
    * late_starts = number of kept requests sent more than late_threshold_s after their intended start.
    Raises ValueError if there are no records, or the warm-up excludes all of them.
    """
    raise NotImplementedError("TODO (task 4)")


def compare_to_budget(summary: dict, budget: dict) -> dict:
    """Check a summary against a budget such as {"p95_ms": 150, "p99_ms": 400, "error_rate": 0.001}.

    Every budget key is an upper limit on the summary value of the same name (<= passes); a missing
    or NaN observation fails. Returns {"ok": bool, "checks": {key: {"limit", "observed", "ok"}}}.
    """
    raise NotImplementedError("TODO (task 5)")


def write_report(path: str | Path, runs: list[dict], meta: dict) -> Path:
    """Write ``{"meta": ..., "runs": [...]}`` as JSON; each run has target_rps, duration_s, summary, budget."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"meta": meta, "runs": runs}, indent=2, default=float) + "\n")
    return path
