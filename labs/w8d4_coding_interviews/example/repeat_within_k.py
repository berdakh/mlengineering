"""Worked example for w8d4: from brute force to a hash map, with the talk-aloud steps and a timing check.

Problem (not one of the lab problems): a sensor stream sends integer readings. Flag every index whose
value already appeared among the previous k readings (a stuck or replaying sensor). Return the flagged
indices.

    python labs/w8d4_coding_interviews/example/repeat_within_k.py

The script runs both versions on the same inputs, checks they agree on 500 random cases, and times them on
growing n with k = n // 10 so the brute force's O(n k) shows. Timings depend on the machine.
"""
from __future__ import annotations

import random
import time


def flagged_brute(values: list[int], k: int) -> list[int]:
    """O(n k): look back over the previous k readings for every index."""
    return [i for i, v in enumerate(values) if v in values[max(0, i - k):i]]


def flagged_fast(values: list[int], k: int) -> list[int]:
    """O(n): remember the last index of each value; a repeat counts if it is at most k positions back."""
    last: dict[int, int] = {}
    out = []
    for i, v in enumerate(values):
        j = last.get(v)
        if j is not None and i - j <= k:
            out.append(i)
        last[v] = i
    return out


def own_tests() -> None:
    """The tests you would say out loud before running anything."""
    assert flagged_fast([], 3) == []
    assert flagged_fast([1, 2, 1], 2) == [2]          # repeat exactly k back counts
    assert flagged_fast([1, 2, 3, 1], 2) == []        # k + 1 back does not
    assert flagged_fast([5, 5, 5], 1) == [1, 2]       # consecutive repeats
    assert flagged_fast([1, 2, 1, 2], 0) == []        # k = 0 flags nothing


def main() -> list[tuple[int, float, float]]:
    own_tests()
    rng = random.Random(0)
    for _ in range(500):
        vals = [rng.randint(0, 9) for _ in range(rng.randint(0, 40))]
        k = rng.randint(0, 10)
        assert flagged_fast(vals, k) == flagged_brute(vals, k)
    print("own tests pass; brute force and hash map agree on 500 random cases")
    rows = []
    print(f"{'n':>8} {'k':>7} {'brute (s)':>10} {'hash map (s)':>13}")
    for n in (2_000, 4_000, 8_000, 16_000, 32_000):
        vals = [rng.randrange(1_000_000) for _ in range(n)]
        k = n // 10
        t0 = time.perf_counter(); a = flagged_brute(vals, k); t1 = time.perf_counter()
        b = flagged_fast(vals, k); t2 = time.perf_counter()
        assert a == b
        rows.append((n, t1 - t0, t2 - t1))
        print(f"{n:>8} {k:>7} {t1 - t0:>10.4f} {t2 - t1:>13.5f}")
    return rows


if __name__ == "__main__":
    main()
