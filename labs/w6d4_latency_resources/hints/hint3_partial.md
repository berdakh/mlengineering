# Hint 3 — partial implementation

```python
def percentile(values, q):
    if not 0 <= q <= 100:
        raise ValueError(...)
    xs = sorted(values)
    if not xs:
        raise ValueError(...)
    h = (len(xs) - 1) * q / 100.0
    lo, hi = math.floor(h), math.ceil(h)
    return float(xs[lo] + (h - lo) * (xs[hi] - xs[lo]))


async def run_open_loop(send, rate, duration, clock=time.perf_counter):
    t0 = clock()

    async def one(intended):
        rec = {"intended": intended, "started": clock(), "status": None, "error": None}
        ...                                   # await send() inside try/except
        rec["finished"] = clock()
        rec["latency"] = ...                  # from which time?
        return rec

    tasks = []
    for offset in intended_schedule(rate, duration):
        delay = (t0 + offset) - clock()
        if delay > 0:
            await asyncio.sleep(delay)
        tasks.append(...)                     # start it, do not await it here
    return list(await asyncio.gather(*tasks))
```

`summarise` (sketch): `kept` by warm-up; `ok` = 2xx; `lat_ms` from `ok`; fill NaN for the latency keys
when `ok` is empty.
