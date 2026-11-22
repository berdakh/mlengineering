"""C2: retry_call with capped exponential backoff and full jitter.

Specification: interview/set7_system_design.md, prompt C2. Standard library only.
Keep the names TransientError and retry_call; add helpers as you like.
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
    raise NotImplementedError
