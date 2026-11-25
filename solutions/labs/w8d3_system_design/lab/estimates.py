"""Back-of-envelope estimates for ML system design (reference solution, w8d3).

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
    _positive(requests_per_day=requests_per_day, peak_to_mean=peak_to_mean)
    if peak_to_mean < 1:
        raise ValueError("peak_to_mean must be >= 1 (a peak is not below the mean)")
    return requests_per_day / SECONDS_PER_DAY * peak_to_mean


def storage_bytes(events_per_day: float, bytes_per_event: float, retention_days: float,
                  replication: int = 1) -> float:
    """Bytes held at steady state: daily volume x retention x number of copies."""
    _positive(events_per_day=events_per_day, bytes_per_event=bytes_per_event,
              retention_days=retention_days)
    if not (isinstance(replication, int) and replication >= 1):
        raise ValueError(f"replication must be an integer >= 1, got {replication!r}")
    return events_per_day * bytes_per_event * retention_days * replication


def labels_available(predictions_per_day: float, label_rate: float, label_delay_days: float,
                     window_days: float) -> float:
    """Labelled examples usable today from the predictions of the last `window_days` days.

    A prediction made `a` days ago has its label only if a >= label_delay_days and it is one of the
    `label_rate` fraction that ever gets a label. Predictions are spread evenly over the window, so the
    usable share of the window is max(0, window_days - label_delay_days).
    """
    _positive(predictions_per_day=predictions_per_day, window_days=window_days)
    _fraction(label_rate=label_rate)
    if not (isinstance(label_delay_days, (int, float)) and label_delay_days >= 0):
        raise ValueError(f"label_delay_days must be >= 0, got {label_delay_days!r}")
    return predictions_per_day * label_rate * max(0.0, window_days - label_delay_days)


def latency_remaining_ms(budget_ms: float, components_ms: dict[str, float]) -> float:
    """Budget left for the model after the other components of the request path (can be negative)."""
    _positive(budget_ms=budget_ms)
    for name, v in components_ms.items():
        if not (isinstance(v, (int, float)) and math.isfinite(v) and v >= 0):
            raise ValueError(f"component {name!r} must be >= 0 ms, got {v!r}")
    return budget_ms - sum(components_ms.values())


def replicas_needed(peak_qps_value: float, service_ms: float, cores_per_replica: int,
                    target_utilisation: float) -> int:
    """Replicas to serve the peak with headroom (Little's law: busy cores = rate x service time)."""
    _positive(peak_qps_value=peak_qps_value, service_ms=service_ms)
    _fraction(target_utilisation=target_utilisation)
    if not (isinstance(cores_per_replica, int) and cores_per_replica >= 1):
        raise ValueError("cores_per_replica must be an integer >= 1")
    busy_cores = peak_qps_value * service_ms / 1000.0
    return max(1, math.ceil(busy_cores / (cores_per_replica * target_utilisation) - 1e-12))


def labels_for_precision(p: float, half_width: float, z: float = 1.96) -> int:
    """Labelled examples needed so a proportion near `p` has a normal-approximation CI of +/- half_width.

    n = z^2 p (1 - p) / half_width^2, rounded up. (For p near 0 or 1 use Wilson; this is a planning number.)
    """
    _fraction(p=p)
    if p >= 1:
        raise ValueError("p must be < 1")
    _positive(half_width=half_width, z=z)
    if half_width >= 0.5:
        raise ValueError("half_width must be < 0.5")
    return math.ceil(z * z * p * (1 - p) / (half_width * half_width) - 1e-12)
