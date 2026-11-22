"""C3: per-endpoint p95 latency and error rate over a sliding window of JSON log lines.

Specification: interview/set6_debugging.md, prompt C3. Implement window_summary; add helpers as you like.
Standard library only.
"""
from __future__ import annotations

from typing import Iterable


def window_summary(lines: Iterable[str], end: str, window_s: float = 300.0) -> dict:
    raise NotImplementedError
