# Hint 2 — approach

**`run_open_loop`.** Record `t0 = clock()`. For each offset in `intended_schedule(rate, duration)`:
`await asyncio.sleep(...)` until `t0 + offset`, then *start a task* for the request
(`asyncio.create_task(one(intended))`) and move on without awaiting it. At the end,
`await asyncio.gather(*tasks)`. Inside `one`: record `started`, `await send()` in a `try` (an exception
means status None and an `error` string), record `finished`, set `latency = finished - intended`.
`gather` returns results in the order the tasks were given, which is schedule order.

**`summarise`.** Filter by `intended >= first_intended + warmup_s`. Split successful (2xx) from the rest.
Percentiles over successful latencies in milliseconds. Window = last `finished` - first `intended` of the
kept records. Late starts: `started - intended > late_threshold_s`.

**`compare_to_budget`.** Loop over the budget's keys; treat missing and NaN as failing; `<=` passes.

**Measuring.** Run `measure_service.py` with `--workers 1` at a low, medium and high rate, then with 2
workers. Read where p95 leaves the budget and what the throughput column does at the same time.

**Challenge.** `workers_needed`: offered load in busy workers is rate x service time (in seconds);
divide by the target utilisation and round *up*. `max_rate_within_slo`: sort rows by rate and stop at
the first row that violates the SLO.
