# Hint 3 - partial implementation

```python
def required_purge(window, horizon=0):
    return window - 1 + horizon


def purged_time_split(n, n_splits, purge=0, embargo=0):
    folds = []
    for block in np.array_split(np.arange(n), n_splits):
        start, end = int(block[0]), int(block[-1])
        keep = np.ones(n, dtype=bool)
        keep[max(0, start - purge): end + embargo + 1] = False
        folds.append((np.flatnonzero(keep), block))
    return folds


def leave_one_family_out(tidy, keep_together=None, ...):
    labelled = ...                                     # experiments with family != "anomaly-free"
    for family in sorted(...):
        val = [e for e in labelled if family_of[e] == family]
        blocked = set()                                # experiments sharing a group with val
        for group in keep_together or []:
            if group & set(val):
                blocked |= set(group)
        train = [e for e in labelled if e not in val and e not in blocked]
        ...
```

Challenge skeleton:

```python
for c in cutoffs:
    train = has_label & (week + label_weeks <= c)
    val = has_label & (week > c) & (week <= c + horizon_weeks)
    if not train.any() or not val.any():
        raise ValueError(...)
    known = np.isin(store, ...)                        # stores with at least one TRAINING row
    folds.append({"cutoff": int(c), "train": position[train],
                  "val_known": ..., "val_new": ...})
```
