"""P5 (medium, binary search on the answer): split work into contiguous batches. Reference solution."""
from __future__ import annotations


def min_max_batch_cost(costs: list[int], max_batches: int) -> int:
    """Smallest possible maximum batch cost when `costs` (positive ints, in order) are split into at most
    `max_batches` contiguous batches. O(n log(sum(costs))).
    """
    if max_batches < 1:
        raise ValueError("max_batches must be >= 1")
    if not costs:
        return 0

    def batches_needed(limit: int) -> int:
        count, running = 1, 0
        for c in costs:
            if running + c > limit:
                count += 1
                running = 0
            running += c
        return count

    target = max(max(costs), -(-sum(costs) // max_batches))
    while batches_needed(target) > max_batches:
        target += 1
    return target
