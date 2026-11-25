"""Worked example: the same server, measured closed-loop and open-loop (SYNTHETIC, simulated time).

    python labs/w6d4_latency_resources/example/coordinated_omission.py

A single FIFO server takes exactly 10 ms per request, except that it freezes for 1 s once, at t = 30 s
(think: a garbage-collection pause, a log rotation, a noisy neighbour). We "load-test" it for 60 s at
about 50 requests/s in two ways, using a discrete-event simulation (no sleeping, fully deterministic):

* closed loop: one virtual user sends a request, waits for the response, thinks 10 ms, sends the next;
* open loop: requests are scheduled every 20 ms regardless of responses; latency = finish - scheduled.

Both see the same server. Only the measurement differs.
"""
from __future__ import annotations

SERVICE_S = 0.010
STALL_START, STALL_LEN = 30.0, 1.0
DURATION = 60.0


def serve(arrival: float, server_free_at: float) -> float:
    """Finish time for a request arriving at `arrival` to a FIFO server free from `server_free_at`."""
    start = max(arrival, server_free_at)
    if STALL_START <= start < STALL_START + STALL_LEN:
        start = STALL_START + STALL_LEN
    elif start < STALL_START < start + SERVICE_S:
        start = STALL_START + STALL_LEN
    return start + SERVICE_S


def closed_loop(think_s: float = 0.010) -> list[float]:
    t, free, latencies = 0.0, 0.0, []
    while t < DURATION:
        finish = serve(t, free)
        latencies.append(finish - t)
        free = finish
        t = finish + think_s
    return latencies


def open_loop(rate: float = 50.0) -> list[float]:
    free, latencies = 0.0, []
    for i in range(int(DURATION * rate)):
        scheduled = i / rate
        finish = serve(scheduled, free)
        latencies.append(finish - scheduled)
        free = finish
    return latencies


def pct(values: list[float], q: float) -> float:
    xs = sorted(values)
    h = (len(xs) - 1) * q / 100
    lo = int(h)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (h - lo) * (xs[hi] - xs[lo])


def report(name: str, lat: list[float]) -> dict:
    ms = [1000 * x for x in lat]
    row = {"method": name, "n": len(ms), "rate": len(ms) / DURATION, "p50": pct(ms, 50), "p95": pct(ms, 95),
           "p99": pct(ms, 99), "p99.9": pct(ms, 99.9), "max": max(ms),
           "share_over_100ms": sum(m > 100 for m in ms) / len(ms)}
    print(f"{name:<12} n={row['n']:5d} ({row['rate']:4.1f}/s)  p50={row['p50']:6.1f}  p95={row['p95']:6.1f}  "
          f"p99={row['p99']:7.1f}  p99.9={row['p99.9']:7.1f}  max={row['max']:7.1f} ms  "
          f">100 ms: {100 * row['share_over_100ms']:.2f}%")
    return row


if __name__ == "__main__":
    report("closed loop", closed_loop())
    report("open loop", open_loop())
