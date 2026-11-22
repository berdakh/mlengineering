# W7D5 assessment

Answer in writing before opening `solutions/lessons/w7d5_reliability/assessment_answers.md`.

## Reasoning questions

1. The drill's `units_bug` scenario produced the same 313 alarms as `normal`. Explain why, using the
   formula of the score, and name the guard that detects it. Would a model trained on raw values have been
   blind in the same way?
2. Why does `/healthz` stay 200 when the bundle is corrupt, while `/readyz` returns 503? Describe what
   happens under each of the two wrong choices in a cluster of 3 instances where one bad bundle was rolled
   out to all of them.
3. After a `deadline` answer, is the model call still running? What does that imply for when the bulkhead
   slot is released, and what would go wrong otherwise under a slow-dependency incident?
4. A client receives `429` with `Retry-After: 1`, then `503` without the header, then a read timeout.
   With base 0.2 s, cap 5 s and full jitter, what is the range of each delay it sleeps?
5. Which of these should the client retry: 400, 409, 413, 422, 429, 500, 502, 503, connection refused?
   Justify the two you find least obvious.
6. The fallback detects 2 of 7 test faults against 5 of 7 for the model, with zero false alarm events for
   both. A product manager asks you to "just use the fallback when the model is slow, nobody will notice".
   What do you answer, with which number?

## Design-choice explanation (write 150-250 words)

You chose to answer model failures with `200` and `degraded: true` rather than `503`. Argue for this
choice, give the strongest argument for `503` instead, and state the condition under which you would
switch.

## Rubric (for the design-choice answer and questions 2, 3, 6)

| Criterion | 0 | 1 | 2 |
|---|---|---|---|
| Correctness | wrong mechanism | right conclusion, vague mechanism | names the mechanism precisely (scale invariance, crash loop, threads cannot be killed) |
| Consequences | none | for the service only | for callers, operators and the decision the plant makes |
| Evidence | none | generic | uses a number from the drill or the fallback table |
| Trade-off | one-sided | mentions the alternative | states when the alternative wins |

## Interview rep (15 min, debugging: a cascading failure)

> "At 14:02 the scoring service's p99 latency went from 40 ms to 9 s. At 14:05 the checkout service
> started timing out. At 14:09 the feature store, which the scoring service calls, was at 100 % CPU. The
> feature store team says nothing changed on their side. At 14:30 someone restarted all scoring
> instances; it got worse for 10 minutes, then recovered. Walk me through what probably happened and what
> you would change."

Answer aloud or in writing in 15 minutes, then score yourself with the rubric in the answers file. Do not
look at the worked answer before scoring.
