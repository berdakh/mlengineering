"""Challenge part 2a: CircuitBreaker (fake clock; no sleeping)."""
from __future__ import annotations

import pytest


def boom():
    raise ConnectionError("dependency down")


def ok():
    return "fine"


def fail_n(breaker, n):
    for _ in range(n):
        with pytest.raises(ConnectionError):
            breaker.call(boom)


def test_closed_passes_results_and_exceptions(res, clock):
    b = res.CircuitBreaker(failure_threshold=3, reset_timeout=10, clock=clock)
    assert b.state == "closed" and b.call(ok) == "fine"
    with pytest.raises(ConnectionError):
        b.call(boom)
    assert b.state == "closed"


def test_breaker_opens_after_consecutive_failures(res, clock):
    b = res.CircuitBreaker(failure_threshold=3, reset_timeout=10, clock=clock)
    fail_n(b, 3)
    assert b.state == "open"
    calls = []
    with pytest.raises(res.CircuitOpen):
        b.call(lambda: calls.append(1))
    assert calls == [], "an open circuit must not call the dependency"


def test_success_resets_the_consecutive_count(res, clock):
    b = res.CircuitBreaker(failure_threshold=3, reset_timeout=10, clock=clock)
    fail_n(b, 2)
    b.call(ok)
    fail_n(b, 2)
    assert b.state == "closed", "2 + success + 2 failures is not 3 consecutive failures"


def test_stays_open_until_timeout(res, clock):
    b = res.CircuitBreaker(failure_threshold=1, reset_timeout=10, clock=clock)
    fail_n(b, 1)
    clock.now = 9.9
    with pytest.raises(res.CircuitOpen):
        b.call(ok)


def test_half_open_allows_one_trial_and_success_closes(res, clock):
    b = res.CircuitBreaker(failure_threshold=1, reset_timeout=10, clock=clock)
    fail_n(b, 1)
    clock.now = 10.0
    assert b.state == "half_open"
    assert b.call(ok) == "fine"
    assert b.state == "closed"


def test_failed_trial_reopens_and_restarts_timeout(res, clock):
    b = res.CircuitBreaker(failure_threshold=1, reset_timeout=10, clock=clock)
    fail_n(b, 1)
    clock.now = 12.0
    fail_n(b, 1)                       # the trial call fails
    assert b.state == "open"
    clock.now = 21.0                   # 9 s after re-opening
    with pytest.raises(res.CircuitOpen):
        b.call(ok)
    clock.now = 22.0
    assert b.call(ok) == "fine"


def test_only_one_trial_in_flight(res, clock):
    b = res.CircuitBreaker(failure_threshold=1, reset_timeout=10, clock=clock)
    fail_n(b, 1)
    clock.now = 10.0
    seen = []

    def trial():
        with pytest.raises(res.CircuitOpen):
            b.call(lambda: seen.append("second"))
        return "trial done"
    assert b.call(trial) == "trial done"
    assert seen == [], "a second call during the half-open trial must be rejected"
