"""Worked example (SYNTHETIC): why retries need jitter. A discrete-time simulation, no network.

200 clients send one request each at t = 0. The service is down for the first 2.0 s (every request
fails), then serves at most 20 requests per 100 ms bucket and rejects the rest with 503 (load shedding).
A rejected client retries according to its policy, up to 10 attempts. We count requests per bucket and
how long it takes until every client has been served.

    python labs/w7d5_reliability/example/retry_storm.py
"""
from __future__ import annotations

import heapq
import random

N_CLIENTS, OUTAGE_S, CAPACITY, BUCKET_S, MAX_ATTEMPTS = 200, 2.0, 20, 0.1, 10
BASE, CAP = 0.1, 6.4


def policy_delay(name: str, retry_index: int, rng: random.Random) -> float:
    if name == "immediate":
        return 0.0
    exp = min(CAP, BASE * 2 ** retry_index)
    if name == "exponential":
        return exp
    if name == "full_jitter":
        return rng.uniform(0, exp)
    raise ValueError(name)


def simulate(name: str, seed: int = 0) -> dict:
    rng = random.Random(seed)
    queue = [(0.0, c, 0) for c in range(N_CLIENTS)]     # (time, client, attempt index)
    heapq.heapify(queue)
    load: dict[int, int] = {}
    served_at: dict[int, float] = {}
    gave_up = requests = 0
    while queue:
        t, client, attempt = heapq.heappop(queue)
        requests += 1
        bucket = int(round(t / BUCKET_S, 9))
        load[bucket] = load.get(bucket, 0) + 1
        ok = t >= OUTAGE_S and load[bucket] <= CAPACITY
        if ok:
            served_at[client] = t
        elif attempt + 1 < MAX_ATTEMPTS:
            heapq.heappush(queue, (t + policy_delay(name, attempt, rng), client, attempt + 1))
        else:
            gave_up += 1
    after = [v for b, v in load.items() if b * BUCKET_S >= OUTAGE_S]
    return {"policy": name, "requests": requests, "served": len(served_at), "gave_up": gave_up,
            "peak_per_bucket_after_recovery": max(after) if after else 0,
            "all_served_by_s": max(served_at.values()) if len(served_at) == N_CLIENTS else None,
            "load": load}


def main() -> None:
    print(f"{N_CLIENTS} clients, outage {OUTAGE_S} s, capacity {CAPACITY} per {BUCKET_S * 1000:.0f} ms, "
          f"max {MAX_ATTEMPTS} attempts, base {BASE} s, cap {CAP} s (SYNTHETIC)")
    print(f"{'policy':12s} {'requests':>8s} {'served':>6s} {'gave up':>7s} {'peak/bucket':>11s} {'all served by':>13s}")
    for name in ("immediate", "exponential", "full_jitter"):
        r = simulate(name)
        done = f"{r['all_served_by_s']:.2f} s" if r["all_served_by_s"] is not None else "never"
        print(f"{name:12s} {r['requests']:8d} {r['served']:6d} {r['gave_up']:7d} "
              f"{r['peak_per_bucket_after_recovery']:11d} {done:>13s}")


if __name__ == "__main__":
    main()
