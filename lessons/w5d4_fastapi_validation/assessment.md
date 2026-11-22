# Assessment - w5d4 FastAPI and input validation

Answer before opening `solutions/lessons/w5d4_fastapi_validation/assessment_answers.md`. 20-25 minutes.

## Reasoning questions

1. A request arrives with `"flow_rate": NaN`. Trace what happens in your service, step by step, from
   bytes to response. What would happen if you had no range limits and no `allow_inf_nan=False`?
2. Why is a non-increasing timestamp sequence a 400 and not a 422 in this design? Name a design in
   which it would legitimately be a 422.
3. `/healthz` returns 200 and `/readyz` returns 503. What should an orchestrator do with this instance,
   and what would go wrong if it used `/healthz` for both decisions?
4. Your colleague changes `/predict` to `async def` "for performance". Under load, latency of `/healthz`
   rises to seconds. Explain.
5. The sanity limit for `flow_rate` is [0, 500] L/min, while training data never exceeded 134. A client
   sends 300. What does the API do, what does the detector do, and is that the right division of labour?
6. Where does the `request_id` help, concretely, when a customer reports "your API returned 500 at
   14:02"? What must the server do for it to help?

## Explain a design choice (150-250 words)

The model is loaded in the lifespan and a failed load leaves the process running but not ready, instead
of crashing at startup. Argue for this choice, then give the strongest argument for the alternative
("fail fast: exit if the model cannot be loaded") and say when you would choose it.

## Rubric for the open-ended answers

| Criterion | Strong | Adequate | Weak |
|---|---|---|---|
| Request lifecycle (Q1) | parser accepts the token, pydantic rejects with `finite_number`, handler builds 422 with loc; without constraints NaN reaches the model, `score_batch` raises, 500 | knows it is rejected | "JSON cannot contain NaN" |
| Status-code reasoning (Q2, Q3) | ties each code to what the client or orchestrator does next | right codes, no consequence | codes from memory only |
| Concurrency model (Q4) | event loop blocked by CPU-bound code in `async def`; `def` runs in the thread pool | "async is not always faster" | no mechanism |
| Validation vs detection (Q5) | sanity limits reject impossible inputs; unusual-but-possible is the detector's and monitoring's job | partial | conflates the two |
| Operations (Q6) | id in response, header and every log line; logs searchable | id in response only | no link to logs |
| Design choice | weighs availability, observability and orchestrator behaviour; names when fail-fast wins | one side argued | assertion |

## Interview rep (12 minutes, API concepts, reduced assistance)

Answer aloud or in writing, timed, without notes:

> You are asked to design the request and response of a prediction endpoint for a fraud model that
> scores card transactions. (a) What goes in the request and why; what do you reject at the schema
> level? (b) What goes in every response besides the score? (c) Which status codes can it return, and
> what should the client do for each? (d) The same transaction may be sent twice after a timeout.
> What do you do?

The rubric and a model answer are in the answers file.
