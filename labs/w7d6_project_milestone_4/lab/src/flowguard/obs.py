"""Minimal observability: counters exposed at /metrics and JSON log events. GIVEN in the lab.

A small stand-in for what w7d1 builds properly (structured logs with request ids, golden signals).
"""
from __future__ import annotations

import json
import logging
import threading
import time

logger = logging.getLogger("flowguard")


class Metrics:
    """Thread-safe counters with labels, rendered in the Prometheus text format."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._values: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}

    def inc(self, name: str, amount: float = 1.0, **labels: str) -> None:
        key = (name, tuple(sorted((k, str(v)) for k, v in labels.items())))
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + amount

    def get(self, name: str, **labels: str) -> float:
        key = (name, tuple(sorted((k, str(v)) for k, v in labels.items())))
        with self._lock:
            return self._values.get(key, 0.0)

    def render(self) -> str:
        lines = []
        with self._lock:
            for (name, labels), value in sorted(self._values.items()):
                label_text = ",".join(f'{k}="{v}"' for k, v in labels)
                lines.append(f"{name}{{{label_text}}} {value:g}" if label_text else f"{name} {value:g}")
        return "\n".join(lines) + "\n"


def log_event(event: str, **fields) -> None:
    """One JSON object per line on the 'flowguard' logger: {"ts":..., "event":..., ...fields}."""
    logger.info(json.dumps({"ts": round(time.time(), 3), "event": event, **fields}, sort_keys=True, default=str))
