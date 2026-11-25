# Hint 2 — approach

**`predict`, in order:**

1. `rid = request.state.request_id`, `model = request.app.state.model`.
2. `oos = out_of_support(body.values, settings.support_low, settings.support_high)`; if any: count and log.
3. Define `def degraded(reason): ...` inside `predict` (it can see `rid`, `model`, `oos`, `body`).
4. No model -> `return degraded("model_unavailable")`. Do this *before* taking a bulkhead slot.
5. `if not slots.acquire(blocking=False):` -> `JSONResponse(429, headers={"Retry-After": ...})`.
6. `future = executor.submit(_score, model, body.burn_in, body.values, faults)` then
   `future.add_done_callback(lambda _f: slots.release())`.
7. `try: scores = future.result(timeout=settings.deadline_s)` with `except FutureTimeout` -> deadline,
   `except Exception` -> count `flowguard_model_errors_total`, log, model_error.
8. `if not all_finite(scores): return degraded("invalid_scores")`.

**Client loop:** `for attempt in range(max_attempts)`: post; on `httpx.TransportError` remember the error;
on a response remember it and `return` it unless its status is in `RETRY_STATUSES`; if this was the last
attempt `break`; otherwise compute the delay (Retry-After capped, else `backoff(attempt)`) and
`self.sleep(delay)`. After the loop: return the last response or raise the last error.

**Your tests:** one test per broken service in `checks/broken/`, plus one for out-of-support values.
`tests/conftest.py` gives you `make_client(faults=..., settings=..., model_dir=...)` and `BODY`.
