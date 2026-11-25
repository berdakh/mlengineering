# Hint 3: partial implementation

```python
def _oriented(df, objectives):
    cols = []
    for col, direction in objectives.items():
        if direction not in ("max", "min"):
            raise ValueError(...)
        if col not in df.columns:
            raise ValueError(...)
        values = df[col].to_numpy(dtype=float)
        if np.isnan(values).any():
            raise ValueError(...)
        cols.append(values if direction == "max" else -values)
    return np.column_stack(cols)


def classify_difference(lo, hi, mpid):
    if not mpid > 0 or np.isnan(lo) or np.isnan(hi) or lo > hi:
        raise ValueError("...")
    if lo > mpid:
        return "better"
    if hi < -mpid:
        return "worse"
    if -mpid < lo and hi < mpid:
        return "equivalent"
    return "inconclusive"
```

`model_size_bytes` with a temporary file:

```python
fd, tmp = tempfile.mkstemp(suffix=".pkl")
try:
    with os.fdopen(fd, "wb") as fh:
        pickle.dump(model, fh, protocol=5)
    return Path(tmp).stat().st_size
finally:
    Path(tmp).unlink(missing_ok=True)
```

The rest (latency loop, `recommend`) follows hint 2 line by line.
