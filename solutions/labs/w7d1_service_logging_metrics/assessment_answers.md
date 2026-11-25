# W7D1 assessment: model answers

## Reasoning questions

**1. 500s never counted.** In Starlette, a handler registered for `Exception` lives in
`ServerErrorMiddleware`, the outermost layer. When the endpoint raises, the exception propagates *out of*
`call_next` in your middleware; no response object comes back, so code placed after `call_next` never
runs. The fix is `try/finally` with `status = 500` set before the `try`; the bookkeeping in `finally` runs
on both paths and the exception continues outward to be turned into a 500. 422 and 404 are different:
their handlers live in the inner `ExceptionMiddleware`, so `call_next` returns a response for them.
*Common wrong answers:* "add `@app.exception_handler(Exception)` that increments the counter" (it works
for the counter but duplicates bookkeeping and still leaves in-flight and latency wrong unless repeated
there); "catch the exception and return a 500 yourself" (works, but swallows it before the outer handler
and its logging unless you re-raise).

**2. In-flight = 1.** The `/metrics` request is itself in flight while `render()` runs; the gauge was
incremented for it. Requiring 0 would make the check depend on whether the scrape counts itself (a
legitimate design choice either way); requiring <= 1 still catches a leak, because three crashed requests
leave it at >= 3. *Wrong answer:* "a background task is running" (there is none).

**3. Averaging p99s.** Instance A: 9,000 requests, p99 50 ms. Instance B: 1,000 requests, p99 1,008 ms.
Average 529 ms; true p99 588 ms (worked example). With a 250 ms SLO stated as "99 % under 250 ms", the
truth is that 6.7 % of all requests are slower than 250 ms, an SLO breach, while each instance's p99 and
any average of them cannot express that share. Correct: sum bucket counts across instances, then compute
the fraction above 250 ms (exact if 250 ms is a bucket edge) or estimate the quantile.
*Wrong answer:* "weight the p99s by traffic" (still not a percentile of the combined distribution).

**4. Validity.** Latency of failures measures nothing useful for the user and is often very short (fast
500s), so including them would improve the latency SLI during an outage. A 422 is the service correctly
rejecting a bad request: the client's fault, not evidence about availability; counting it as bad lets
one broken client burn your budget. A 503 means the service could not serve: the service's fault.

**5. Samples counter.** No. The client re-sends the run so far every 60 samples, so each sample is scored
up to ~19 times; the counter counts sample-scorings, not distinct seconds. To count distinct anomalous
time you would need the stateful streaming endpoint (each sample once), or an event-level count of alarm
episodes per machine computed downstream, or a log field with the timestamp range of the newly added
samples. Know what a counter counts before charting it.

**6. Not logged.** The sensor values (payload): data exposure, size, unreadability; summaries suffice to
debug. Request headers wholesale: they may contain credentials (Authorization, cookies). Also acceptable:
full tracebacks in responses (never), client IPs without a retention policy.

## Design-choice explanation (what a strong answer contains)

* A `machine_id` label creates up to 120,000 x routes x statuses series for the counter, and x 10 more
  for histogram buckets: millions of series, which the monitoring system will reject or charge for, and
  most of them empty most of the time.
* Instead: keep metrics at service level (route, status, model version) for alerting; put `machine_id` in
  the access/prediction log events and answer per-machine questions with a log query (top-N machines by
  5xx count in the last hour), or a periodic batch job that aggregates logs into a per-machine table.
* If a small fixed grouping matters operationally (site, product line, fleet segment with < ~20 values),
  that can be a label.
* Cost: log queries are slower and logs may be sampled; per-machine error accounting therefore needs
  errors to be logged unsampled.

## Rubric notes for the challenge (`SLO.md`)

"Meets" on every row requires: valid/good definitions that exclude 4xx and count 503; targets with a
window and a reason tied to the client's behaviour (re-sends every minute) and to measured latency; a
budget computed from a stated traffic assumption; a paging rule with two windows per rule; a ticket rule
for slow burns; and an explicit statement that model quality and input drift are outside these SLOs.
The reference `SLO.md` is in `challenge/`.

*Common weak answers:* 99.99 % "because it sounds professional" (4.3 minutes per 30 days, unachievable
for a single-container prototype); latency SLO on the mean; one paging threshold on a 5-minute window;
no traffic assumption, so the budget has no units.

## Interview rep: rubric and worked answer

| Area | Strong answer includes |
|---|---|
| Per-request log | request id (propagated end to end), model version, decision, score, latency, rule outcome; NO raw card data or PII; sampled INFO for successes, all errors; a separate access-controlled capture for later labelling, joined by transaction id |
| Metrics | request counter by route/status/model_version; latency histogram with a bucket edge at 80 ms; in-flight / queue depth; score histogram and decision rate (block share) per model version |
| Paging | multi-window burn-rate on availability and on the 80 ms latency SLI; a page on a sudden change of the block rate (a broken model or feature can block everyone with no 5xx at all) |
| Not knowable on day one | precision and recall (chargebacks 30-90 days late); use proxy metrics (block rate, score distribution, manual review outcomes) and plan delayed evaluation |
| Cardinality and cost | no merchant or card id labels; per-merchant views from logs |

*Worked answer, condensed.* "Each request carries an id from the payment gateway; I log one access event
and one decision event with id, model version, score, decision, latency and the rule that fired, no card
number. Metrics: requests by status and model version, an 80 ms-edged latency histogram, in-flight, and
a score histogram plus decision counter per model version. I page on SLO burn for availability and
latency with two windows, and separately on the block rate leaving a band derived from last week,
because the most damaging failure (blocking all payments) returns 200. What I cannot know for 30-90
days is whether decisions are right, so I track proxies and schedule a delayed evaluation job joined on
transaction id."
