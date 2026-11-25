"""Structured logs and Prometheus-format metrics for the flowguard service. STARTER (w7d1): implement the TODOs (tasks 1 and 2).

Two halves, deliberately dependency-free so you can see every moving part:

* **Logs.** ``JsonFormatter`` turns each ``logging`` record into ONE line of JSON with stable keys.
  Call sites pass structured fields through ``extra={"fields": {...}}``; nothing is ever parsed out of
  a free-text message. ``configure_logging(stream)`` installs it on the ``flowguard`` logger tree.
* **Metrics.** ``Counter``, ``Gauge`` and ``Histogram`` keep values in memory per label set;
  ``Registry.render()`` writes the Prometheus text exposition format (version 0.0.4) that a Prometheus
  server scrapes from ``/metrics``. In production you would use the ``prometheus_client`` package; it
  produces the same format. Values live in one process: with several uvicorn workers each worker has
  its own registry (see the lesson, section 2.6).

Input summaries (``summarise_samples``) are what an ML service logs instead of raw payloads.
"""
from __future__ import annotations

import json
import logging
import math
import sys
import threading
import time
from datetime import datetime, timezone
from typing import IO, Iterable

LOGGER_ROOT = "flowguard"
ACCESS_LOGGER = "flowguard.access"
PREDICTION_LOGGER = "flowguard.prediction"

# Latency buckets in seconds. Chosen around the w6d4 measurements (p50 ~ 10 ms, p99 < 100 ms at the
# design load) with resolution where the SLO threshold (250 ms) sits; see the lesson, section 2.5.
LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5)
# Prediction-score buckets: |z| units. The operating threshold is 7.24.
SCORE_BUCKETS = (0.5, 1.0, 2.0, 3.0, 5.0, 7.244, 10.0, 20.0, 50.0)


# --------------------------------------------------------------------------------------------- logs
class JsonFormatter(logging.Formatter):
    """One JSON object per line: ts, level, logger, event, then the record's structured fields."""

    def format(self, record: logging.LogRecord) -> str:
        """Return ONE line of JSON (no embedded newlines) with keys ``ts`` (UTC ISO 8601), ``level``,
        ``logger``, ``event`` (= ``record.getMessage()``), then every key of ``record.fields`` (a dict
        passed as ``extra={"fields": {...}}``) that does not clash with those four. If the record has
        ``exc_info``, add ``exc_type`` (and, if you like, the formatted traceback).

        TODO w7d1 (task 1). Hint: json.dumps(..., default=str) handles datetimes; json.dumps never
        emits a raw newline, it escapes it.
        """
        raise NotImplementedError("TODO w7d1 task 1: JsonFormatter.format")


def configure_logging(stream: IO[str] | None = None, level: int = logging.INFO) -> logging.Handler:
    """Send every ``flowguard.*`` record to ``stream`` (default stdout) as JSON lines.

    Idempotent: a handler installed by an earlier call is replaced, so tests and reloads do not
    duplicate lines. Records do not propagate to the root logger (uvicorn's own handlers).
    """
    logger = logging.getLogger(LOGGER_ROOT)
    for handler in list(logger.handlers):
        if getattr(handler, "_flowguard_json", False):
            logger.removeHandler(handler)
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler._flowguard_json = True  # type: ignore[attr-defined]
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return handler


def log_event(logger: logging.Logger, event: str, level: int = logging.INFO, **fields) -> None:
    """Emit one structured event. ``event`` is a short constant name, never an interpolated sentence."""
    logger.log(level, event, extra={"fields": fields})


def summarise_samples(samples: Iterable) -> dict:
    """What we log about a request body: ``n_samples`` and the time span (``first_ts``, ``last_ts``,
    ``span_s``), NEVER the sensor values themselves. ``samples`` are the pydantic ``Sample`` objects.

    TODO w7d1 (task 1).
    """
    raise NotImplementedError("TODO w7d1 task 1: summarise_samples")


# ------------------------------------------------------------------------------------------ metrics
def _escape(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _labels(names: tuple[str, ...], values: tuple[str, ...], extra: tuple[tuple[str, str], ...] = ()) -> str:
    pairs = list(zip(names, values)) + list(extra)
    if not pairs:
        return ""
    return "{" + ",".join(f'{k}="{_escape(v)}"' for k, v in pairs) + "}"


def _fmt(value: float) -> str:
    if math.isinf(value):
        return "+Inf" if value > 0 else "-Inf"
    if float(value).is_integer():
        return str(int(value))
    return repr(float(value))


class _Metric:
    kind = "untyped"

    def __init__(self, name: str, help_text: str, labelnames: tuple[str, ...] = ()):
        self.name, self.help, self.labelnames = name, help_text, tuple(labelnames)
        self._lock = threading.Lock()

    def _key(self, labels: dict) -> tuple[str, ...]:
        if set(labels) != set(self.labelnames):
            raise ValueError(f"{self.name}: labels {sorted(labels)} != {sorted(self.labelnames)}")
        return tuple(str(labels[n]) for n in self.labelnames)

    def header(self) -> list[str]:
        return [f"# HELP {self.name} {self.help}", f"# TYPE {self.name} {self.kind}"]


class Counter(_Metric):
    """Monotonically increasing count. Rates come from differences between scrapes."""

    kind = "counter"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._values: dict[tuple[str, ...], float] = {}

    def inc(self, amount: float = 1.0, **labels) -> None:
        if amount < 0:
            raise ValueError("a counter cannot decrease")
        key = self._key(labels)
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + amount

    def render(self) -> list[str]:
        with self._lock:
            items = sorted(self._values.items())
        return self.header() + [f"{self.name}{_labels(self.labelnames, k)} {_fmt(v)}" for k, v in items]


class Gauge(_Metric):
    """A value that goes up and down (requests in flight, model loaded)."""

    kind = "gauge"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._values: dict[tuple[str, ...], float] = {}

    def set(self, value: float, **labels) -> None:
        key = self._key(labels)
        with self._lock:
            self._values[key] = float(value)

    def inc(self, amount: float = 1.0, **labels) -> None:
        key = self._key(labels)
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + amount

    def dec(self, amount: float = 1.0, **labels) -> None:
        self.inc(-amount, **labels)

    def render(self) -> list[str]:
        with self._lock:
            items = sorted(self._values.items())
        return self.header() + [f"{self.name}{_labels(self.labelnames, k)} {_fmt(v)}" for k, v in items]


class Histogram(_Metric):
    """Counts of observations in CUMULATIVE buckets (``le`` = less than or equal), plus sum and count.

    Percentiles are estimated from buckets by the monitoring system; they cannot be averaged across
    instances or time windows, but bucket counts can be summed first (lesson, section 2.4).
    """

    kind = "histogram"

    def __init__(self, name: str, help_text: str, labelnames: tuple[str, ...] = (),
                 buckets: tuple[float, ...] = LATENCY_BUCKETS):
        super().__init__(name, help_text, labelnames)
        if list(buckets) != sorted(buckets) or len(set(buckets)) != len(buckets):
            raise ValueError("buckets must be strictly increasing")
        self.buckets = tuple(float(b) for b in buckets)
        self._counts: dict[tuple[str, ...], list[int]] = {}
        self._sum: dict[tuple[str, ...], float] = {}

    def observe(self, value: float, **labels) -> None:
        """Record one observation for this label set. TODO w7d1 (task 2).

        Keep, per label set, the count in each bucket and the running sum. Use ``self._key(labels)``
        and hold ``self._lock`` while updating.
        """
        raise NotImplementedError("TODO w7d1 task 2: Histogram.observe")

    def render(self) -> list[str]:
        """Prometheus text lines for this histogram. TODO w7d1 (task 2).

        For each label set, in this order: one ``<name>_bucket{<labels>,le="<upper>"} <count>`` line per
        bucket plus ``le="+Inf"``, where <count> is the number of observations <= upper (CUMULATIVE),
        then ``<name>_sum{<labels>} <sum>`` and ``<name>_count{<labels>} <count>``. Start with
        ``self.header()``. Helpers: ``_labels(self.labelnames, key, (("le", _fmt(upper)),))``, ``_fmt``.
        """
        raise NotImplementedError("TODO w7d1 task 2: Histogram.render")


class Registry:
    """The metrics of one service process."""

    def __init__(self):
        self._metrics: list[_Metric] = []

    def register(self, metric: _Metric) -> _Metric:
        if any(m.name == metric.name for m in self._metrics):
            raise ValueError(f"metric {metric.name} registered twice")
        self._metrics.append(metric)
        return metric

    def render(self) -> str:
        lines: list[str] = []
        for metric in self._metrics:
            lines.extend(metric.render())
        return "\n".join(lines) + "\n"


class ServiceMetrics:
    """The golden-signal metrics of the flowguard API (names are part of the lab's contract)."""

    def __init__(self):
        self.registry = Registry()
        r = self.registry
        self.requests = r.register(Counter(
            "flowguard_http_requests_total", "HTTP requests by method, route template and status code.",
            ("method", "route", "status")))
        self.latency = r.register(Histogram(
            "flowguard_http_request_duration_seconds", "Server-side request duration in seconds.",
            ("route",), LATENCY_BUCKETS))
        self.in_flight = r.register(Gauge(
            "flowguard_http_requests_in_flight", "Requests currently being processed."))
        self.model_info = r.register(Gauge(
            "flowguard_model_info", "1 for the loaded model version (0 series when no model is loaded).",
            ("model_version",)))
        self.scores = r.register(Histogram(
            "flowguard_prediction_score", "Anomaly scores returned (|z| units), warming-up samples excluded.",
            (), SCORE_BUCKETS))
        self.samples = r.register(Counter(
            "flowguard_predicted_samples_total", "Samples scored, by outcome.", ("outcome",)))

    def render(self) -> str:
        return self.registry.render()


def now() -> float:
    """Monotonic clock for durations (never wall-clock time)."""
    return time.perf_counter()
