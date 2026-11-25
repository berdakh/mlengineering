# Hint 2: approach

**Formatter.** Start the payload with the four fixed keys, then copy `getattr(record, "fields", {})`
without overwriting them. Add `exc_type` from `record.exc_info[0].__name__` when `exc_info` is set.

**Histogram.** Internally, a list of `len(buckets) + 1` counts per label key (the last one for +Inf) and
a running sum. `observe` increments the first bucket whose bound is >= value. `render` walks the list
with a running total.

**Middleware.** Set `status = 500` before `try`. Inside `try`, `response = await call_next(request)`,
take `response.status_code`, set the header, `return response`. Put all bookkeeping in `finally`. The
route label is `_route_label(request)`, read in `finally` (routing has happened by then).

**Prediction event.** Count while you build `results`; call `summarise_samples(body.samples)` and spread
its dict into `log_event(...)`.

**Log query.** `json.loads` inside `try`; count failures and non-dicts; filter by `request_id`.

**Challenge.** Filter to `/predict` access events first. Availability: drop 4xx from valid, good is
`< 500`. Latency: valid is status 200 only. Burn rate: divide by `1 - target`. Paging: loop over rules,
both windows `>=` factor.
