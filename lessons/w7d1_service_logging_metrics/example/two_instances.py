"""Worked example (SYNTHETIC): why logs should be JSON, and why you sum buckets instead of averaging p99s.

    python lessons/w7d1_service_logging_metrics/example/two_instances.py

A recommendation service runs on two instances behind a load balancer. Instance A is healthy and
busy (9,000 requests); instance B is degraded and quiet (1,000 requests). Self-contained: it uses
only the standard library and NumPy, not the flowguard package.
"""
from __future__ import annotations

import json
import re

import numpy as np

BUCKETS = (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, float("inf"))


def cumulative_buckets(latencies: np.ndarray) -> np.ndarray:
    """Prometheus-style cumulative counts: number of observations <= each upper bound."""
    return np.array([(latencies <= b).sum() for b in BUCKETS])


def quantile_from_buckets(cum: np.ndarray, q: float) -> float:
    """Linear interpolation inside the bucket that contains the q-quantile (what histogram_quantile does)."""
    rank = q * cum[-1]
    i = int(np.searchsorted(cum, rank))
    lo = 0.0 if i == 0 else BUCKETS[i - 1]
    hi = BUCKETS[i] if np.isfinite(BUCKETS[i]) else BUCKETS[i - 1]
    below = 0 if i == 0 else cum[i - 1]
    inside = cum[i] - below
    return lo + (hi - lo) * ((rank - below) / inside if inside else 1.0)


def main() -> None:
    rng = np.random.default_rng(7)
    a = rng.lognormal(mean=np.log(0.02), sigma=0.4, size=9000)    # healthy: ~20 ms
    b = rng.lognormal(mean=np.log(0.30), sigma=0.5, size=1000)    # degraded: ~300 ms
    both = np.concatenate([a, b])

    print("1) Two log lines for the same request")
    text = "2026-03-01 10:00:01 INFO request abc123 for user 42 took 312ms (status=200) model=v3"
    js = json.dumps({"ts": "2026-03-01T10:00:01Z", "event": "access", "request_id": "abc123",
                     "status": 200, "duration_ms": 312, "model_version": "v3"})
    print("   text:", text)
    print("   json:", js)
    m = re.search(r"took (\d+)ms", text)
    print(f"   regex on text -> {m.group(1)} ms (breaks the day someone writes 'took 0.3s');"
          f" json -> {json.loads(js)['duration_ms']} ms, by key")
    print("   (the text line also leaked a user id; structured logging makes such fields explicit and reviewable)")

    print("\n2) Latency across two instances")
    p99_a, p99_b, p99_true = (float(np.quantile(x, 0.99)) for x in (a, b, both))
    print(f"   p99 instance A: {p99_a * 1000:7.1f} ms   (9,000 requests)")
    print(f"   p99 instance B: {p99_b * 1000:7.1f} ms   (1,000 requests)")
    print(f"   mean of the two p99s:              {(p99_a + p99_b) / 2 * 1000:7.1f} ms   <- not a percentile of anything")
    print(f"   true p99 of all 10,000 requests:   {p99_true * 1000:7.1f} ms")
    merged = cumulative_buckets(a) + cumulative_buckets(b)        # bucket counts CAN be summed
    print(f"   p99 from summed histogram buckets: {quantile_from_buckets(merged, 0.99) * 1000:7.1f} ms"
          "   <- lands in the right bucket (500-1000 ms); the position inside it is interpolated")
    print(f"   share of all requests slower than 250 ms: {(both > 0.25).mean():.1%}"
          f" (from buckets: {1 - merged[BUCKETS.index(0.25)] / merged[-1]:.1%}, exact because 250 ms is a bucket edge)")


if __name__ == "__main__":
    main()
