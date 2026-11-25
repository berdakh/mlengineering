"""Open-loop load generation and latency statistics. REFERENCE SOLUTION (w6d4).

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

import asyncio
import json
import math
import time
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path


def percentile(values: Sequence[float], q: float) -> float:
    """The q-th percentile (0 <= q <= 100) with linear interpolation between order statistics.

    Same definition as ``numpy.percentile(values, q)`` (method ``"linear"``): with the sorted values
    x_0 <= ... <= x_{n-1}, position h = (n - 1) q / 100, result x_floor(h) + (h - floor(h)) (x_ceil(h) - x_floor(h)).
    Raises ValueError for an empty input or q outside [0, 100]. Does not modify ``values``.
    """
    if not 0 <= q <= 100:
        raise ValueError(f"q must be in [0, 100], got {q}")
    xs = sorted(values)
    if not xs:
        raise ValueError("percentile of an empty sequence")
    h = (len(xs) - 1) * q / 100.0
    lo, hi = math.floor(h), math.ceil(h)
    return float(xs[lo] + (h - lo) * (xs[hi] - xs[lo]))


def intended_schedule(rate: float, duration: float) -> list[float]:
    """Offsets (seconds from the start) at which to send: i / rate for i = 0 .. round(rate * duration) - 1."""
    if rate <= 0 or duration <= 0:
        raise ValueError("rate and duration must be positive")
    return [i / rate for i in range(int(round(rate * duration)))]


async def run_open_loop(send: Callable[[], Awaitable[int]], rate: float, duration: float,
                        clock: Callable[[], float] = time.perf_counter) -> list[dict]:
    """Issue ``send()`` on an open-loop schedule and record what happened to each request.

    ``send`` is an async function returning an HTTP status code; an exception counts as a failed
    request (status None). Each record has: ``intended``, ``started``, ``finished`` (clock seconds),
    ``status``, ``error`` and ``latency`` = finished - intended. Records are returned in schedule order.
    """
    t0 = clock()
    records: list[dict] = []

    async def one(intended: float) -> dict:
        rec = {"intended": intended, "started": clock(), "status": None, "error": None}
        try:
            rec["status"] = int(await send())
        except Exception as exc:  # noqa: BLE001 - every failure is data
            rec["error"] = f"{type(exc).__name__}: {exc}"[:200]
        rec["finished"] = clock()
        rec["latency"] = rec["finished"] - rec["started"]
        return rec

    tasks = []
    for offset in intended_schedule(rate, duration):
        intended = t0 + offset
        delay = intended - clock()
        if delay > 0:
            await asyncio.sleep(delay)
        tasks.append(asyncio.create_task(one(intended)))
    records = list(await asyncio.gather(*tasks))
    return records


def summarise(records: Sequence[dict], warmup_s: float = 0.0, late_threshold_s: float = 0.010) -> dict:
    """Latency and error statistics, in milliseconds, excluding requests scheduled in the warm-up.

    Successful = 2xx status. Latency percentiles use successful requests only; every other request
    counts in ``error_rate``. ``throughput_rps`` = successful responses per second over the measured
    window (first intended start to last finish). ``late_starts`` counts requests sent more than
    ``late_threshold_s`` after their intended start (a sign that the generator itself fell behind).
    """
    if not records:
        raise ValueError("no records")
    first = min(r["intended"] for r in records)
    kept = [r for r in records if r["intended"] >= first + warmup_s]
    if not kept:
        raise ValueError("warm-up excludes every request")
    ok = [r for r in kept if r["status"] is not None and 200 <= r["status"] < 300]
    lat_ms = [1000.0 * r["latency"] for r in ok]
    window = max(r["finished"] for r in kept) - min(r["intended"] for r in kept)
    lags = [r["started"] - r["intended"] for r in kept]
    out = {
        "n_sent": len(kept),
        "n_ok": len(ok),
        "n_errors": len(kept) - len(ok),
        "error_rate": (len(kept) - len(ok)) / len(kept),
        "throughput_rps": len(ok) / window if window > 0 else float("nan"),
        "late_starts": sum(lag > late_threshold_s for lag in lags),
        "max_start_lag_ms": 1000.0 * max(lags),
    }
    if lat_ms:
        out.update({"p50_ms": percentile(lat_ms, 50), "p95_ms": percentile(lat_ms, 95),
                    "p99_ms": percentile(lat_ms, 99), "mean_ms": sum(lat_ms) / len(lat_ms),
                    "max_ms": max(lat_ms)})
    else:
        out.update({k: float("nan") for k in ("p50_ms", "p95_ms", "p99_ms", "mean_ms", "max_ms")})
    return out


def compare_to_budget(summary: dict, budget: dict) -> dict:
    """Check a summary against a budget such as {"p95_ms": 150, "p99_ms": 400, "error_rate": 0.001}.

    Every budget key is an upper limit on the summary value of the same name; a missing or NaN
    observation fails. Returns {"ok": bool, "checks": {key: {"limit", "observed", "ok"}}}.
    """
    checks = {}
    for key, limit in budget.items():
        observed = summary.get(key)
        ok = observed is not None and not (isinstance(observed, float) and math.isnan(observed)) \
            and observed <= limit
        checks[key] = {"limit": limit, "observed": observed, "ok": bool(ok)}
    return {"ok": all(c["ok"] for c in checks.values()), "checks": checks}


def write_report(path: str | Path, runs: list[dict], meta: dict) -> Path:
    """Write ``{"meta": ..., "runs": [...]}`` as JSON; each run has target_rps, duration_s, summary, budget."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"meta": meta, "runs": runs}, indent=2, default=float) + "\n")
    return path
