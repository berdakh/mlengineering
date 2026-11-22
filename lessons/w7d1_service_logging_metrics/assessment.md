# W7D1 assessment

Answer in writing before opening `solutions/lessons/w7d1_service_logging_metrics/assessment_answers.md`.

## Reasoning questions

1. Your middleware increments `flowguard_http_requests_total` after `await call_next(request)` returns.
   In production the 500 count stays at zero during an incident in which users see 500s. Explain the
   mechanism and the fix.
2. The replay shows `flowguard_http_requests_in_flight 1` although no prediction is running. Why, and
   why does the check accept 0 or 1 rather than requiring 0?
3. A dashboard shows "p99 latency = average over instances of each instance's p99". Give a concrete case
   where this hides a breach of a 250 ms SLO, and the correct computation.
4. Why is the latency SLI computed over status-200 requests only, while the availability SLI counts 503
   as bad and excludes 422?
5. `flowguard_predicted_samples_total{outcome="exceeding"}` reached 2,624 in the replay. Can you conclude
   that 2,624 seconds of the two runs were above the threshold? What would you need to log or count
   instead?
6. Name two fields you deliberately do NOT log in the prediction event, and the reason for each.

## Design-choice explanation (write 150-250 words)

You need per-machine visibility for a fleet of 120,000 pumps: which machines get errors, which get slow
responses. A colleague proposes a `machine_id` label on the request counter and latency histogram.
Explain what you would do instead, what each piece answers, and what it costs.

## Rubric (open-ended answers)

| Criterion | Does not meet | Meets | Exceeds |
|---|---|---|---|
| Mechanism | Names a symptom ("errors not counted") | Explains that the exception propagates out of `call_next` because the `Exception` handler sits in the outermost middleware | Also explains why 422/404 behave differently and what the in-flight gauge does |
| Metrics reasoning | Treats percentiles as averageable or labels as free | Correctly separates bucket sums from percentile averages and bounded from unbounded labels | Quantifies cardinality or uses the bucket-edge argument for exact SLIs |
| Logging judgement | Logs payloads or relies on log-line counts for rates | Summaries in logs, counts from metrics, correlation by request id | Adds sampling, retention or access-control considerations |
| SLO (challenge) | Targets without rationale; 4xx counted against the service | SLIs with valid/good definitions, numeric targets and budget, two-window paging | Derives factors from budget fractions; states what the SLO cannot see and how that is covered |

## Interview rep (15 minutes, system design: observability)

*Prompt (say your answer aloud or write it, then compare with the rubric in the answers file).*
You are about to put a real-time card-fraud scoring API into production: about 2,000 requests per
second, p99 budget 80 ms, scores consumed by a rules engine that blocks or allows payments. Labels
(chargebacks) arrive 30-90 days later. Design the logs, metrics and alerts for the first release. What
do you log per request, what are your metrics and their labels, what pages a human at 3 a.m., and what
can you NOT know from any of this on day one?
