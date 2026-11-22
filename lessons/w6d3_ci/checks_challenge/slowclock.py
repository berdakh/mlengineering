"""pytest plugin used by the challenge checks: every read of the wall clock advances it by 0.5 s.

Loaded with ``-p slowclock``. Under this clock any test that asserts on elapsed time fails, which is
how the checks find wall-clock assertions in the per-push test run without reading your code.
``time.monotonic`` is left alone because the event loop inside TestClient depends on it.
"""
from __future__ import annotations

import time

_real_perf, _real_time = time.perf_counter, time.time
_state = {"offset": 0.0}


def _slow(real):
    def clock():
        _state["offset"] += 0.5
        return real() + _state["offset"]
    return clock


def pytest_configure(config):
    time.perf_counter = _slow(_real_perf)
    time.time = _slow(_real_time)


def pytest_unconfigure(config):
    time.perf_counter, time.time = _real_perf, _real_time
