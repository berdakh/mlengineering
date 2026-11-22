# Hint 3: partial implementation

Opening this hint means the lab counts as guided practice, not independent work.

```python
def _ecdfs(ref, cur):
    grid = np.sort(np.concatenate([ref, cur]))
    f_ref = np.searchsorted(np.sort(ref), grid, side="right") / ref.size
    f_cur = np.searchsorted(np.sort(cur), grid, side="right") / cur.size
    return grid, f_ref, f_cur

def wasserstein1(reference, current):
    ref, cur = _clean(reference), _clean(current)
    if ref.size == 0 or cur.size == 0:
        return float("nan")
    grid, f_ref, f_cur = _ecdfs(ref, cur)
    return float(np.sum(np.abs(f_ref - f_cur)[:-1] * np.diff(grid)))

def split_violations(frame, sensors, limits=SENSOR_LIMITS):
    bad = pd.Series(False, index=frame.index)
    for s in sensors:
        x = frame[s].astype(float)
        lo, hi = limits[s]
        bad |= np.isinf(x) | (x.notna() & ((x < lo) | (x > hi)))
    return frame.loc[~bad], bad
```

Challenge, the calendar part of the daily loop:

```python
in_settle = any(c <= day < c + settle for c in changes.get(f, []))
for c in changes.get(f, []):
    if day == c + settle:
        ref_days[f] = list(range(c, c + settle))
        thresholds[f] = calibrate(df, f, ref_days[f], margin)
```
