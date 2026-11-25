# W7D5 assessment: model answers

## 1. The units bug the model cannot see

The score is `|x − mean(b)| / sd(b)` where `b` is the experiment's burn-in. Multiplying every value by
`c > 0` multiplies the numerator and the denominator by `c`, so every score is unchanged:
`|c·x − c·mean(b)| / (c·sd(b)) = |x − mean(b)| / sd(b)`. Same scores means the same 313 alarms. Only the
training-support guard (`out_of_support`, 1,140 of 1,140 values flagged, counter
`flowguard_out_of_support_total 1140`) sees it, because it compares raw values with the 0.56 to 133.69 L/min
range of development data. A model on raw values (a fixed threshold, a tree on absolute features) would
*not* be blind. It would fire everywhere, which is loud but just as wrong, and support checks are still the
cleaner signal.

*Common wrong answers.* "The model is robust to units, so no problem": the plant's decision may be fine
today, but every downstream consumer of the raw values (dashboards, the fallback rule, drift monitors) is
wrong, and the next model may not be scale invariant. "Validation would catch it": the values are
finite, in schema and plausible-looking numbers. Only knowledge of the training distribution catches them.

## 2. Liveness vs readiness with a bad bundle

Restarting reloads the same bad bundle, so a failing liveness probe cannot fix it. If `/healthz` failed
on the bundle, the orchestrator would restart all 3 instances in a loop: a crash loop with no answers at
all, not even the fallback. If `/readyz` returned 200 without a model, the load balancer would keep
routing to instances that can only give fallback answers, and the rollout gate (w6d6) would never stop the
bad release. With the lesson's choice, all 3 instances report not-ready, so the rollout halts or
rolls back. Callers that still reach an instance get explicit `degraded` answers. The alert on readiness
is the signal to roll back.

*Common wrong answer.* "Both should fail, the service is broken". This loses the fallback and creates the
crash loop.

## 3. Deadlines and the bulkhead

Yes. Python threads cannot be killed, so the model call keeps running after the deadline answer.
The slot must be released when the *work* ends (the future's done-callback), not when the response is
sent. Otherwise, during a slow-dependency incident each request gets a fast deadline answer and frees
its slot while its model call keeps running. In-flight work grows without bound, CPU contention makes
every call slower, and the bulkhead protects nothing (mutant `slot_released_on_response`).

## 4. Delays

* After the `429` with `Retry-After: 1`: exactly 1.0 s (below the 5 s cap).
* After the `503` without the header (retry index 1): uniform in [0, min(5, 0.2·2¹)] = [0, 0.4] s.
* After the read timeout (retry index 2): uniform in [0, 0.8] s.

*Common wrong answer.* Using the Retry-After value for later retries, or starting the exponential at
index 1 for the first retry. The contract counts the first retry as index 0.

## 5. What to retry

Retry: 429, 502, 503, connection refused (and 504). Do not retry: 400, 409, 413, 422, 500.

* **409 Conflict**: it means the request conflicts with the current state (for example the same
  idempotency key with a different body). The same request will conflict again.
* **500**: for this service a 500 means a bug. The known failure modes are answered with explicit
  degradation, so a 500 is deterministic for that input, and retrying multiplies the damage. Some
  systems retry 500 once. If you do, make it part of a bounded, jittered policy and only for idempotent
  calls.

## 6. "Just use the fallback"

The fallback is a safety net with a measured cost. On the 7 frozen test experiments it detected 2 faults
against the model's 5, so it would have missed 3 of the 5 faults the model caught. Point recall drops from
0.270 to 0.234. Zero false alarms for both means it is not noisier, only blinder. Nobody would notice,
which is the problem: a quiet stretch would be read as "healthy". So the answer is to keep the fallback,
always flag it, alert when the degraded rate exceeds a small threshold, and fix the slow model
(w6d4: threads, deadlines), not the flag.

## Design-choice explanation: model answer (about 200 words)

A model failure in flowguard is a *known* state with a defined answer: the envelope rule. Returning `200`
with `degraded: true` and a reason gives the caller something to act on (show "monitoring degraded" on
the plant dashboard, apply a stricter manual check) instead of an error page. It keeps the caller's own
error handling for real errors, and it does not provoke retries: clients retry 503s, and retrying a
failing model only adds load. The degraded counter and log event keep it visible to operators, and
readiness 503 handles routing.

The strongest argument for `503`: a 200 can be consumed by a caller that ignores the new field. That
caller treats the fallback's silence as health, which is exactly the silent wrong answer we wanted to
avoid. A status code is much harder to ignore than a JSON field.

I would switch to `503` (or a dedicated status) when callers cannot be relied on to read `degraded`:
third-party integrations, or a consumer that automatically acts on `above_threshold`. Then failure must be
loud. The same applies if the fallback's cost becomes unacceptable for the decision. A fallback catching 2
of 7 faults may be too weak for a safety function.

## Interview rep: worked answer and rubric

**Likely story.** Something made the feature store slightly slower at 14:02, perhaps a heavy query or a
noisy neighbour. "Nothing changed" is common and not evidence. The scoring service had no deadline on
the feature call, so its threads blocked and p99 rose to 9 s. Checkout timed out and retried, probably
immediately and several times, so traffic to scoring multiplied, and so did traffic to the feature store,
which reached 100 % CPU: a positive feedback loop. The 14:30 restart dropped the in-flight work, but every
instance came back cold at the same moment, all clients retried in lock-step, and the cold caches added
load. That explains "worse for 10 minutes". It recovered once retry budgets ran out and the feature
store caught up.

**Changes, by priority.**
1. Deadline on the feature call, with a bulkhead around it, and explicit degraded answers.
2. Clients: bounded retries with full jitter, honouring `Retry-After`; retry only 429/503/transport errors.
3. Load shedding with 429 so overload is visible and cheap.
4. A circuit breaker around the feature store.
5. Rolling restarts, not all at once, with readiness gating.
6. Alerts on shed rate, degraded rate and dependency latency, and a runbook entry.

| Criterion | 0 | 1 | 2 |
|---|---|---|---|
| Identifies the feedback loop (timeouts → retries → more load) | missing | mentions retries | explains amplification with the timeline |
| Explains why the restart made it worse | missing | "restarts are risky" | synchronised retries plus cold start |
| Deadlines and bulkheads | missing | one of them | both, and why a deadline alone is not enough |
| Retry discipline | missing | "add backoff" | bounded, jittered, honours Retry-After, idempotency |
| Prioritises and verifies | list only | some order | ordered, with how to test each (fault injection) |

8-10: strong; 5-7: adequate, review 2.4-2.5; below 5: redo the lab's task 2 and the worked example.
