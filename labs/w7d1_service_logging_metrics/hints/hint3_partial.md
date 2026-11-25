# Hint 3: partial implementation

Opening this hint means the lab counts as guided practice, not independent work.

```python
# observability.py -- Histogram
def observe(self, value, **labels):
    key = self._key(labels)
    with self._lock:
        counts = self._counts.setdefault(key, [0] * (len(self.buckets) + 1))
        for i, upper in enumerate(self.buckets):
            if value <= upper:
                counts[i] += 1
                break
        else:
            counts[-1] += 1
        self._sum[key] = self._sum.get(key, 0.0) + float(value)

def render(self):
    lines = self.header()
    for key, counts in sorted(self._counts.items()):
        running = 0
        for upper, c in zip((*self.buckets, math.inf), counts):
            running += c
            lines.append(f"{self.name}_bucket{_labels(self.labelnames, key, (('le', _fmt(upper)),))} {running}")
        # ... then _sum and _count lines
    return lines
```

```python
# api.py -- the shape of the middleware
status = 500
start = now()
metrics.in_flight.inc()
try:
    response = await call_next(request)
    status = response.status_code
    response.headers[REQUEST_ID_HEADER] = request.state.request_id
    return response
finally:
    duration = now() - start
    route = _route_label(request)
    metrics.in_flight.dec()
    # requests.inc(...), latency.observe(...), log_event(access_logger, "access", level, ...)
```

```python
# challenge/slo.py
def burn_rate(bad, valid, target):
    if valid <= 0:
        return 0.0
    return (bad / valid) / (1.0 - target)
```
