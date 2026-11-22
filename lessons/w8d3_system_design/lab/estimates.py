"""Back-of-envelope estimates for ML system design (starter, w8d3 - fill in the bodies).

Every function turns stated assumptions into one number. The point in an interview is not precision
but showing the arithmetic, the units and which assumption dominates. Each function validates its
inputs and raises ValueError for values that make the estimate meaningless.
"""
from __future__ import annotations

import math

SECONDS_PER_DAY = 86_400


def _positive(**values: float) -> None:
    for name, v in values.items():
        if not (isinstance(v, (int, float)) and math.isfinite(v) and v > 0):
            raise ValueError(f"{name} must be a finite number > 0, got {v!r}")


def _fraction(**values: float) -> None:
    for name, v in values.items():
        if not (isinstance(v, (int, float)) and 0 < v <= 1):
            raise ValueError(f"{name} must be in (0, 1], got {v!r}")


def peak_qps(requests_per_day: float, peak_to_mean: float) -> float:
    """Peak requests per second = mean rate over the day x peak-to-mean ratio."""
    raise NotImplementedError("w8d3 lab: implement this estimate")


def storage_bytes(events_per_day: float, bytes_per_event: float, retention_days: float,
                  replication: int = 1) -> float:
    """Bytes held at steady state: daily volume x retention x number of copies."""
    raise NotImplementedError("w8d3 lab: implement this estimate")


def labels_available(predictions_per_day: float, label_rate: float, label_delay_days: float,
                     window_days: float) -> float:
    """Labelled examples usable today from the predictions of the last `window_days` days.

    A prediction made `a` days ago has its label only if a >= label_delay_days and it is one of the
    `label_rate` fraction that ever gets a label. Predictions are spread evenly over the window, so the
    usable share of the window is max(0, window_days - label_delay_days).
    """
    raise NotImplementedError("w8d3 lab: implement this estimate")


def latency_remaining_ms(budget_ms: float, components_ms: dict[str, float]) -> float:
    """Budget left for the model after the other components of the request path (can be negative)."""
    raise NotImplementedError("w8d3 lab: implement this estimate")


def replicas_needed(peak_qps_value: float, service_ms: float, cores_per_replica: int,
                    target_utilisation: float) -> int:
    """Replicas to serve the peak with headroom (Little's law: busy cores = rate x service time)."""
    raise NotImplementedError("w8d3 lab: implement this estimate")


def labels_for_precision(p: float, half_width: float, z: float = 1.96) -> int:
    """Labelled examples needed so a proportion near `p` has a normal-approximation CI of +/- half_width.

    n = z^2 p (1 - p) / half_width^2, rounded up. (For p near 0 or 1 use Wilson; this is a planning number.)
    """
    raise NotImplementedError("w8d3 lab: implement this estimate")
