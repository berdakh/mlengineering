"""Checks for the w6d4 load generator. Timing tests use fake async `send` functions and generous
tolerances; they test the generator's behaviour, not this machine's speed."""
from __future__ import annotations

import asyncio
import json
import math
import time

import numpy as np
import pytest


# ------------------------------------------------------------------ task 1: percentile

@pytest.mark.parametrize("n", [1, 2, 3, 10, 101, 1000])
def test_percentile_matches_numpy_linear(lt, n):
    rng = np.random.default_rng(n)
    values = list(rng.lognormal(3, 1, size=n))
    for q in (0, 1, 25, 50, 90, 95, 99, 99.9, 100):
        assert lt.percentile(values, q) == pytest.approx(float(np.percentile(values, q)), rel=1e-12, abs=1e-12)


def test_percentile_does_not_modify_input_and_handles_ties(lt):
    values = [5.0, 1.0, 3.0, 3.0, 3.0]
    copy = list(values)
    assert lt.percentile(values, 50) == 3.0
    assert values == copy


def test_percentile_rejects_bad_input(lt):
    with pytest.raises(ValueError):
        lt.percentile([], 50)
    with pytest.raises(ValueError):
        lt.percentile([1.0, 2.0], 101)
    with pytest.raises(ValueError):
        lt.percentile([1.0, 2.0], -1)


# ------------------------------------------------------------------ task 2: schedule

def test_schedule(lt):
    s = lt.intended_schedule(10, 1.0)
    assert len(s) == 10 and s[0] == 0.0 and s[-1] == pytest.approx(0.9)
    assert all(b > a for a, b in zip(s, s[1:]))
    assert len(lt.intended_schedule(50, 0.4)) == 20
    with pytest.raises(ValueError):
        lt.intended_schedule(0, 1.0)


# ------------------------------------------------------------------ task 3: open loop

def test_open_loop_keeps_the_schedule_when_responses_are_slow(lt):
    """Each response takes 200 ms; at 50 requests/s for 0.4 s all 20 must still be sent on time."""
    in_flight = {"now": 0, "max": 0}

    async def slow_send():
        in_flight["now"] += 1
        in_flight["max"] = max(in_flight["max"], in_flight["now"])
        await asyncio.sleep(0.2)
        in_flight["now"] -= 1
        return 200

    start = time.perf_counter()
    records = asyncio.run(lt.run_open_loop(slow_send, 50, 0.4))
    elapsed = time.perf_counter() - start
    assert len(records) == 20
    lags = [r["started"] - r["intended"] for r in records]
    assert max(lags) < 0.08, f"requests were sent late (max lag {max(lags):.3f} s): is the loop waiting for responses?"
    assert in_flight["max"] >= 5, "requests must overlap: an open-loop generator does not wait for responses"
    assert elapsed < 1.5, f"20 requests of 200 ms at 50/s should finish in ~0.6 s, took {elapsed:.2f} s"
    for r in records:
        assert r["latency"] == pytest.approx(r["finished"] - r["intended"])
        assert 0.19 <= r["latency"] < 1.0


def test_latency_is_measured_from_the_intended_start(lt):
    """The first send blocks the event loop for 0.3 s (a stalled process). Requests scheduled during
    the stall are sent late; their latency must include the time they waited (no coordinated omission)."""
    calls = {"n": 0}

    async def send():
        calls["n"] += 1
        if calls["n"] == 1:
            time.sleep(0.3)  # blocks the loop, like a GC pause or a stalled generator
        await asyncio.sleep(0.001)
        return 200

    records = asyncio.run(lt.run_open_loop(send, 50, 0.6))
    late = [r for r in records if r["started"] - r["intended"] > 0.1]
    assert late, "expected some requests to start late behind the stall"
    for r in late:
        waited = r["started"] - r["intended"]
        assert r["latency"] >= waited, (
            "latency must be finished - intended start; measuring from the actual send hides the stall")


def test_failures_are_recorded_not_raised(lt):
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        await asyncio.sleep(0.001)
        if calls["n"] % 4 == 0:
            raise ConnectionError("reset by peer")
        return 503 if calls["n"] % 4 == 1 else 200

    records = asyncio.run(lt.run_open_loop(flaky, 100, 0.2))
    assert len(records) == 20
    assert sum(r["status"] is None for r in records) == 5
    assert all(r["error"] for r in records if r["status"] is None)
    assert [r["intended"] for r in records] == sorted(r["intended"] for r in records)


# ------------------------------------------------------------------ task 4: summarise

def _rec(i, latency, status=200, lag=0.0, rate=10.0):
    intended = 100.0 + i / rate
    return {"intended": intended, "started": intended + lag, "finished": intended + latency,
            "status": status, "error": None if status else "boom", "latency": latency}


def test_summary_statistics(lt):
    lat = [0.010 * (k + 1) for k in range(100)]           # 10 ms .. 1000 ms
    records = [_rec(i, x) for i, x in enumerate(lat)]
    s = lt.summarise(records)
    lat_ms = [1000 * x for x in lat]
    assert s["n_sent"] == 100 and s["n_ok"] == 100 and s["n_errors"] == 0 and s["error_rate"] == 0
    for key, q in (("p50_ms", 50), ("p95_ms", 95), ("p99_ms", 99)):
        assert s[key] == pytest.approx(np.percentile(lat_ms, q))
    assert s["mean_ms"] == pytest.approx(np.mean(lat_ms))
    assert s["max_ms"] == pytest.approx(1000.0)
    window = (100.0 + 99 / 10 + 1.0) - 100.0
    assert s["throughput_rps"] == pytest.approx(100 / window)


def test_errors_are_counted_and_kept_out_of_latency(lt):
    records = [_rec(i, 0.010) for i in range(90)] + [_rec(90 + i, 5.0, status=s)
                                                       for i, s in enumerate([500] * 5 + [None] * 3 + [429] * 2)]
    s = lt.summarise(records)
    assert s["n_errors"] == 10 and s["error_rate"] == pytest.approx(0.10)
    assert s["n_ok"] == 90
    assert s["max_ms"] == pytest.approx(10.0), "failed requests must not enter the latency percentiles"


def test_warmup_is_excluded(lt):
    records = [_rec(i, 2.0 if i < 10 else 0.020) for i in range(60)]   # first second is slow (cold)
    s = lt.summarise(records, warmup_s=1.0)
    assert s["n_sent"] == 50
    assert s["max_ms"] == pytest.approx(20.0)
    with pytest.raises(ValueError):
        lt.summarise(records, warmup_s=100.0)
    with pytest.raises(ValueError):
        lt.summarise([])


def test_late_starts_counted(lt):
    records = [_rec(i, 0.05, lag=0.03 if i % 5 == 0 else 0.0) for i in range(50)]
    s = lt.summarise(records)
    assert s["late_starts"] == 10
    assert s["max_start_lag_ms"] == pytest.approx(30.0)


def test_all_failed_gives_nan_latency(lt):
    s = lt.summarise([_rec(i, 0.1, status=503) for i in range(5)])
    assert s["error_rate"] == 1.0 and math.isnan(s["p95_ms"])


# ------------------------------------------------------------------ task 5: budget

def test_budget_comparison(lt):
    summary = {"p95_ms": 120.0, "p99_ms": 300.0, "error_rate": 0.0}
    r = lt.compare_to_budget(summary, {"p95_ms": 150.0, "p99_ms": 250.0, "error_rate": 0.001})
    assert r["ok"] is False
    assert r["checks"]["p95_ms"]["ok"] is True and r["checks"]["p99_ms"]["ok"] is False
    assert r["checks"]["p99_ms"]["observed"] == 300.0 and r["checks"]["p99_ms"]["limit"] == 250.0
    assert lt.compare_to_budget(summary, {"p95_ms": 120.0})["ok"] is True, "the limit itself passes (<=)"
    assert lt.compare_to_budget({"p95_ms": float("nan")}, {"p95_ms": 100.0})["ok"] is False
    assert lt.compare_to_budget({}, {"p95_ms": 100.0})["ok"] is False


def test_report_round_trips(lt, tmp_path):
    summary = lt.summarise([_rec(i, 0.02) for i in range(20)])
    runs = [{"target_rps": 10, "duration_s": 2, "summary": summary,
             "budget": lt.compare_to_budget(summary, {"p95_ms": 100.0})}]
    path = lt.write_report(tmp_path / "r" / "report.json", runs, {"workers": 1})
    data = json.loads(path.read_text())
    assert data["meta"]["workers"] == 1 and data["runs"][0]["summary"]["n_ok"] == 20
