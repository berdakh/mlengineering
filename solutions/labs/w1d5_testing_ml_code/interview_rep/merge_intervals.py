"""Reference answer for the w1d5 interview rep."""


def merge_intervals(intervals):
    """Merge half-open intervals that overlap or touch. O(n log n) for the sort.

    The input is not modified. Raises ValueError on an empty or reversed interval.
    """
    merged = []
    for start, stop in sorted(intervals):
        if start >= stop:
            raise ValueError(f"invalid interval ({start}, {stop})")
        if merged and start <= merged[-1][1]:          # overlap or touch
            merged[-1] = (merged[-1][0], max(merged[-1][1], stop))
        else:
            merged.append((start, stop))
    return merged
