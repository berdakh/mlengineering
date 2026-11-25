# Hint 3 - partial implementation (w5d3)

**Lab: the calibration part of `update`.**

```python
if self.mu is None:                                # still calibrating
    self.count += 1
    delta = value - self.mean
    self.mean += delta / self.count
    self.m2 += delta * (value - self.mean)         # new mean on purpose
    if self.count == self.detector.n_burn:
        self.mu = self.mean
        sd = math.sqrt(self.m2 / self.count)       # population SD, like np.std
        self.sigma = sd if sd > 0 else 1.0
    score, status, exceeds = None, "warming_up", None
else:
    score = abs(value - self.mu) / self.sigma
    status, exceeds = "ok", score >= self.detector.threshold
```

The duplicate branch, placed before any assignment:

```python
if ts == self.last_ts:
    if value == self.last_value:
        return dataclasses.replace(self.last_result, duplicate=True)
    raise ConflictingDuplicateError(...)
```

**Challenge: the core of `update`.**

```python
if exceeds is None:
    self._run_hi = self._run_lo = 0
elif exceeds:
    self._run_hi, self._run_lo = self._run_hi + 1, 0
    if not self._alarm and self._run_hi >= self.k_raise:
        self._alarm = True
else:
    ...  # the mirror image with m_clear
return self._alarm
```
