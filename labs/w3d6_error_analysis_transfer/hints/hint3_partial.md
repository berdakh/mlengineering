# Hint 3 - partial implementation

**Lab: the two helpers and the core of `error_segments`**

```python
def _runs(mask):
    padded = np.r_[False, mask.astype(bool), False]
    change = np.flatnonzero(padded[1:] != padded[:-1])
    return [(int(a), int(b) - 1) for a, b in zip(change[::2], change[1::2])]   # inclusive ends

# inside one experiment, with y (labels), f (flags), t sorted by time:
events = _runs(y == 1)
for start, end in events:
    hits = np.flatnonzero(f[start:end + 1])
    if len(hits) == 0:
        add("miss", start, end)
        continue
    first_hit = start + int(hits[0])
    for a, b in _runs(f[start:end + 1] == 0):
        a, b = a + start, b + start
        if a == start:
            ...   # late if (first_hit - start) > late_after, else boundary
        else:
            ...   # fragment
for a, b in _runs((y == 0) & (f == 1)):
    touches = any(b + 1 == start or a - 1 == end for start, end in events)
    ...           # no events -> false_alarm; touches and short -> boundary; else pre_onset / post_event / false_alarm
```

The bootstrap in `slice_metrics`:

```python
rng = np.random.default_rng(seed)
means = defined[rng.integers(0, len(defined), size=(n_boot, len(defined)))].mean(axis=1)
ci_low, ci_high = np.quantile(means, [0.025, 0.975])
```

**Challenge: split and metric**

```python
cutoff = pd.Timestamp(test_start)
test = df[df["issue_date"] >= cutoff]
label_known = df["due_date"] + pd.Timedelta(days=30) < cutoff
train = df[label_known & (df["issue_date"] < cutoff)]

frame = test.assign(_score=scores, _week=(test["issue_date"] - cutoff).dt.days // 7)
called = frame.sort_values("_score", ascending=False, kind="stable").groupby("_week").head(k)
```

What remains yours: which columns go into `FEATURES` and why, the baseline rule, the model, the
interval, the slice, and the report. The full reference is in
`solutions/labs/w3d6_error_analysis_transfer/`.
