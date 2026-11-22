"""C2 reference: a generic retry wrapper with capped exponential backoff and full jitter.

Specification: interview/set7_system_design.md, prompt C2. Standard library only.
"""
from __future__ import annotations

import random
import time
from typing import Callable, Optional, TypeVar

T = TypeVar("T")


class TransientError(Exception):
    """A failure that a later attempt may not repeat. ``retry_after`` (seconds) is the server's hint."""

    def __init__(self, message: str = "", retry_after: Optional[float] = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


def default_is_retryable(exc: Exception) -> bool:
    return isinstance(exc, TransientError)


def retry_call(
    fn: Callable[[], T],
    *,
    max_attempts: int = 5,
    base: float = 0.1,
    cap: float = 5.0,
    deadline: Optional[float] = None,
    is_retryable: Optional[Callable[[Exception], bool]] = None,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.monotonic,
    rand: Callable[[], float] = random.random,
) -> T:
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    if base < 0 or cap < 0:
        raise ValueError("base and cap must be >= 0")
    if deadline is not None and deadline < 0:
        raise ValueError("deadline must be >= 0")

    if is_retryable is None:
        is_retryable = default_is_retryable
    start = now()
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as exc:                 # BaseException (KeyboardInterrupt, SystemExit) propagates
            if not is_retryable(exc):
                raise
            if attempt == max_attempts:
                raise RuntimeError(f"gave up after {attempt} attempts") from exc
            hint = getattr(exc, "retry_after", None)
            if hint is not None:
                delay = min(max(float(hint), 0.0), cap)
            else:
                delay = rand() * min(cap, base * 2 ** (attempt - 1))
            if deadline is not None and (now() - start) + delay > deadline:
                raise
            sleep(delay)
    raise AssertionError("unreachable")       # the loop always returns or raises
