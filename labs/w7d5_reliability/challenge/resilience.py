"""Two mitigations from your failure-mode table. Implement both (challenge part 2); keep the interfaces."""
from __future__ import annotations

import time
from collections.abc import Callable


class CircuitOpen(Exception):
    """Raised instead of calling the protected function while the circuit is open."""


class CircuitBreaker:
    """See challenge/README.md for the required behaviour (closed / open / half_open)."""

    def __init__(self, failure_threshold: int = 5, reset_timeout: float = 30.0,
                 clock: Callable[[], float] = time.monotonic) -> None:
        raise NotImplementedError

    @property
    def state(self) -> str:
        raise NotImplementedError

    def call(self, fn: Callable, *args, **kwargs):
        raise NotImplementedError


class SampleOrderGuard:
    """See challenge/README.md for the required behaviour (ok / duplicate / out_of_order / gap)."""

    def __init__(self, max_gap_s: float) -> None:
        raise NotImplementedError

    def check(self, machine_id: str, timestamp: float) -> str:
        raise NotImplementedError
