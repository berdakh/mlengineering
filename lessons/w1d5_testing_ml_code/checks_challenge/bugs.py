"""Defects injected into the reference detect_events. SPOILER - see checks/bugs.py."""
from harness import Bug

F = "eventkit/events.py"
BUGS = [
    Bug("final_event_dropped", "a run that is still open at the end of the array is never emitted",
        ((F, "    if start is not None:\n        runs.append((start, len(s)))\n", ""),)),
    Bug("threshold_inclusive", "uses >= threshold instead of > threshold",
        ((F, "above = s > threshold", "above = s >= threshold"),)),
    Bug("stop_inclusive", "stop is the last sample of the event instead of one past it",
        ((F, "runs.append((start, i))", "runs.append((start, i - 1))"),
         (F, "runs.append((start, len(s)))", "runs.append((start, len(s) - 1))"))),
    Bug("min_samples_off_by_one", "events of exactly min_samples are discarded",
        ((F, "if b - a >= min_samples]", "if b - a > min_samples]"),)),
    Bug("filter_before_merge", "short runs are discarded before merging, so fragmented events vanish",
        ((F, "    for run in runs:\n", "    for run in [r for r in runs if r[1] - r[0] >= min_samples]:\n"),)),
    Bug("merge_gap_off_by_one", "gaps of exactly merge_gap samples are not merged",
        ((F, "run[0] - merged[-1][1] <= merge_gap", "run[0] - merged[-1][1] < merge_gap"),)),
    Bug("nan_counts_as_above", "NaN scores are treated as above threshold",
        ((F, "above = s > threshold", "above = ~(s <= threshold)"),)),
    Bug("no_parameter_validation", "min_samples < 1 and merge_gap < 0 are silently accepted",
        ((F, '    if min_samples < 1:\n        raise ValueError("min_samples must be >= 1")\n'
             '    if merge_gap < 0:\n        raise ValueError("merge_gap must be >= 0")\n', ""),)),
]
