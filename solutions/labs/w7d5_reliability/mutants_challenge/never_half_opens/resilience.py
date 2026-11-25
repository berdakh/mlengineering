"""Two mitigations from the flowguard failure-mode table: a circuit breaker and a per-machine ordering guard."""
from __future__ import annotations

import threading
import time
from collections.abc import Callable


class CircuitOpen(Exception):
    """Raised instead of calling the protected function while the circuit is open."""


class CircuitBreaker:
    """Stop calling a failing dependency for a while, then probe it with one trial call.

    closed     -> calls pass; ``failure_threshold`` CONSECUTIVE failures open the circuit.
    open       -> calls raise CircuitOpen without touching the dependency, until ``reset_timeout``
                  seconds (by ``clock``) have passed since the circuit opened.
    half_open  -> exactly one trial call is let through; success closes the circuit, failure re-opens it
                  (and restarts the timeout). Other calls during the trial raise CircuitOpen.
    """

    def __init__(self, failure_threshold: int = 5, reset_timeout: float = 30.0,
                 clock: Callable[[], float] = time.monotonic) -> None:
        if failure_threshold < 1 or reset_timeout <= 0:
            raise ValueError("failure_threshold >= 1 and reset_timeout > 0 are required")
        self.failure_threshold, self.reset_timeout, self.clock = failure_threshold, reset_timeout, clock
        self._state, self._failures, self._opened_at, self._trial = "closed", 0, 0.0, False
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._state == "open" and self.clock() - self._opened_at >= self.reset_timeout:
                self._state = "half_open"
            return self._state

    def call(self, fn: Callable, *args, **kwargs):
        with self._lock:
            if self._state == "open" or (self._state == "half_open" and self._trial):
                raise CircuitOpen(f"circuit open; retry after {self.reset_timeout:g} s")
            if self._state == "half_open":
                self._trial = True
        try:
            result = fn(*args, **kwargs)
        except Exception:
            with self._lock:
                self._trial = False
                if self._state == "half_open":
                    self._state, self._opened_at = "open", self.clock()
                else:
                    self._failures += 1
                    if self._failures >= self.failure_threshold:
                        self._state, self._opened_at = "open", self.clock()
            raise
        with self._lock:
            self._trial, self._failures, self._state = False, 0, "closed"
        return result


class SampleOrderGuard:
    """Classify each streamed sample per machine before it reaches the stateful scorer.

    "ok"            in order, accepted (state updated)
    "duplicate"     same timestamp as the last accepted sample: drop it (state unchanged)
    "out_of_order"  older than the last accepted sample: reject it (state unchanged)
    "gap"           more than ``max_gap_s`` after the last accepted sample: accepted (state updated);
                    the caller should restart that machine's burn-in, because the window is broken
    The first sample of a machine is "ok". Machines never affect each other.
    """

    def __init__(self, max_gap_s: float) -> None:
        if max_gap_s <= 0:
            raise ValueError("max_gap_s must be positive")
        self.max_gap_s = max_gap_s
        self._last: dict[str, float] = {}

    def check(self, machine_id: str, timestamp: float) -> str:
        last = self._last.get(machine_id)
        if last is None:
            self._last[machine_id] = timestamp
            return "ok"
        if timestamp == last:
            return "duplicate"
        if timestamp < last:
            return "out_of_order"
        self._last[machine_id] = timestamp
        return "gap" if timestamp - last > self.max_gap_s else "ok"
