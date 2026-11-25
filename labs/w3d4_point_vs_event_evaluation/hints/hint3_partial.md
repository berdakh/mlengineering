# Hint 3 - partial implementation (w3d4)

```python
def extract_events(binary, min_duration=1, merge_gap=0):
    b = np.asarray(binary, dtype=int)
    d = np.diff(np.concatenate([[0], b, [0]]))
    runs = list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)))
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] <= merge_gap:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return [(int(s), int(e)) for s, e in merged if e - s >= min_duration]


def match_events(true_events, pred_events, early_tolerance=0):
    starts = np.array([s for s, _ in true_events])
    first_detection = [None] * len(true_events)
    labels = [None] * len(pred_events)              # one label per alarm, in the order given
    for j in sorted(range(len(pred_events)), key=lambda j: pred_events[j][0]):   # earliest first
        a_start = pred_events[j][0]
        k = int(np.searchsorted(starts, a_start + early_tolerance, side="right")) - 1
        inside = k >= 0 and true_events[k][0] - early_tolerance <= a_start < true_events[k][1]
        if not inside:
            labels[j] = "false_alarm"
        elif first_detection[k] is None:
            first_detection[k] = ...                # what does detection_delay need to know?
            labels[j] = "hit"
        else:
            labels[j] = "redundant"
    return {"first_detection": first_detection, "pred_label": labels}
```

Still yours: the return structure of `match_events`, the NaN conventions, `detection_delay` with the
confirmation wait, `delay_summary` with infinite delays, `normal_hours` from timestamps with gaps.
