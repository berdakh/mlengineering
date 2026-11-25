# Assessment answers - w5d4 FastAPI and input validation

## 1. `"flow_rate": NaN`, from bytes to response

Uvicorn passes the body to FastAPI, which parses it with Python's `json` module; that module accepts
the non-standard token `NaN` and produces `float("nan")`. Pydantic validates the `Sample`: with
`allow_inf_nan=False` it records an error of type `finite_number` at `["body", "samples", i,
"flow_rate"]`. FastAPI raises `RequestValidationError`; the handler builds the 422 body with
`code="validation_error"` and the details; the middleware adds the request id header. The endpoint
never runs.

Without range limits and without `allow_inf_nan=False`, NaN passes validation, `score_batch` raises
`ValueError("flow_rate contains missing or non-finite values")` (the detector's own guard), and the
client gets a 500 for what is the client's error. Without that guard in the detector, a NaN in the
burn-in would make `mu` NaN and every score of the run NaN, and serialising a NaN score fails (JSON
has no NaN): a 500 again, or a silently wrong answer in other stacks. Each layer protects the next.

*Common wrong answers.* "JSON cannot contain NaN, so it cannot happen": the standard forbids it, the
parser accepts it. "The range check already rejects it": it does, but with the misleading type
`less_than_equal`, and only for fields that have a range.

## 2. Non-increasing timestamps: 400 or 422?

In this design the schema describes one sample at a time; ordering is a property of the list as a
whole, checked by the endpoint after validation, so it is reported as a domain error (400,
`invalid_sequence`) with the offending indices. It would legitimately be a 422 if the ordering rule
were part of the schema, e.g. a pydantic `model_validator` on `PredictRequest`: then it is one more
schema constraint, appears in the same error list as field errors, and arguably documents itself
better. Both are defensible; what matters is consistency and that the client can find the offending
sample from the response.

## 3. `/healthz` 200, `/readyz` 503

The process is alive but cannot serve: the orchestrator should **not route traffic** to it (take it out
of the load balancer) and **not restart** it immediately (the model may still be loading, or the
problem is the bundle, which a restart does not fix; repeated restarts just hide the cause). If
`/healthz` were used for readiness, traffic would go to an instance that answers 503 to every
prediction; if `/readyz` were used for liveness, a missing bundle would cause a restart loop.

## 4. `async def` and a slow `/healthz`

An `async def` endpoint runs on the event loop. `score_batch` is CPU-bound and never awaits, so while
it runs no other request on that worker is served, `/healthz` included; under load the loop is busy
most of the time and every request queues. A plain `def` endpoint is run in a thread pool, so the
loop stays free (the GIL still limits parallel CPU work within one process; more workers or processes
scale that). The FastAPI documentation states the thread-pool behaviour for `def` path operations.

## 5. `flow_rate = 300`

The API accepts it: 300 L/min is physically possible for some pump, so it is not a broken input. The
detector scores it: with a burn-in mean near 32 and SD near 0.5, the |z| is in the hundreds, far above
the threshold, so it alarms. That is the right division: the API rejects impossible or mis-scaled
values (negative flow, 9,999, NaN), the detector judges plausible values, and monitoring (week 7)
notices that inputs have moved outside the training range. Putting the training range into the schema
would turn every real fault into a 422 and hide it from the detector.

## 6. Request ids

The customer quotes the request id from the response body or header; the server logs every request and
every exception with the same id (`logger.exception(..., request_id)`), so one search finds the
traceback, the input size, the model version and the timing. For it to work the id must be in the
response (body and header), in every log line of that request, and logs must be kept and searchable.
Accepting a client-provided id (validated) lets the id span several services.

## Design choice: start without a model rather than fail fast (model answer)

Starting without a model keeps the process observable: `/healthz` answers, `/readyz` explains (503 and
a log line naming the bundle problem), and `/version` shows what is deployed, so an operator can see
*why* the instance is useless instead of watching it crash-loop. It also supports deployments where
the model arrives after the process (mounted later, downloaded on start) and keeps the readiness
semantics honest: not ready, not dead. Its risk is an instance that never becomes ready and nobody
notices; readiness probes and alerts on "not ready for N minutes" cover that.

The strongest argument for fail fast: a service without a model has no purpose, and an immediate,
loud failure at deploy time (the new version never becomes healthy, the rollout stops) is the safest
signal, with no chance of partially serving. Choose fail fast when the model is baked into the image,
there is no legitimate "loading later" state, and the deployment system treats a crashing new version
as a failed rollout and keeps the old one. In this course the model lives next to the code in a
bundle, so either works; the lab uses the observable variant because it teaches readiness.

## Interview rep: rubric and model answer

| Level | Evidence |
|---|---|
| Strong | (a) request: transaction id, amount + currency, merchant and card identifiers (tokenised), timestamp with timezone, channel; schema rejects missing, non-finite, negative amounts, unknown currencies, extra fields, oversize batches. (b) response: score, decision or threshold version, model version, request id, possibly reason codes. (c) 200; 422 schema; 400 domain (e.g. timestamp in the future beyond tolerance); 409 for a transaction id already scored with different content; 429 rate limit with Retry-After; 503 not ready, retry elsewhere; 500 report with request id. (d) idempotency key = transaction id: same content -> return the stored previous answer; different content -> 409 |
| Adequate | sensible fields and codes, idempotency mentioned without a mechanism |
| Weak | "return the score"; status codes 200/500 only; duplicates scored twice (and possibly counted twice in velocity features) |

Model answer, (d) in particular: a retried transaction must not be scored as a new one, because
velocity features ("transactions in the last hour") would count it twice and raise the next score.
Store `(transaction_id -> content hash, response)` for a retention window; a retry with the same hash
gets the stored response; a different hash gets 409.
