# flowguard service level objectives (reference answer)

## 1. Who depends on the service, and for what

The plant reliability engineer's monitoring client sends each machine's run to `/predict` every minute and
raises an alert when samples exceed the threshold for long enough (w4d5 operating point). If the service is
down or slow, faults go unseen; if it is wrong, w7d3's delayed-label evaluation is the only thing that will
show it. These SLOs cover the first two; they say nothing about model quality.

## 2. SLIs

| SLI | Good events | Valid events | Source |
|---|---|---|---|
| Availability | `/predict` responses with status < 500 | `/predict` requests except 4xx (client errors) | access log `status`, or `flowguard_http_requests_total` |
| Latency | status 200 with `duration_ms` <= 250 | `/predict` responses with status 200 | access log `duration_ms`, or the duration histogram bucket `le="0.25"` |

Why these exclusions: a 422 is the service correctly refusing bad input, so it is neither good nor bad for
availability; a 503 (model not loaded) is the service's fault and counts as bad. Errors are excluded from the
latency SLI so that fast failures cannot make latency look better. The 250 ms threshold is a histogram bucket
boundary, so the SLI can be computed exactly from metrics, not interpolated.

## 3. Objectives

* Availability: **99.5 %** of valid `/predict` requests over a rolling **30 days**.
* Latency: **99 %** of successful `/predict` requests within **250 ms** over 30 days.

Rationale: the client re-sends the whole run every minute, so a single failed request delays one update by a
minute but loses no data; 99.5 % allows about 3.6 hours of total outage per 30 days at constant traffic. w6d4
measured p95 of 12-15 ms up to 120 requests/s with the corrected server, so 250 ms leaves room for queueing
under bursts without being so loose that a real regression goes unnoticed.

## 4. Error budget, worked

Traffic: 40 machines x 1 request/minute = 57,600 requests/day = 1,728,000 per 30 days.
Availability budget: (1 - 0.995) x 1,728,000 = **8,640 bad requests per 30 days**.
A 2-hour total outage at that traffic = 4,800 bad requests = 56 % of the budget.

## 5. Alerting

Page when either rule holds (both windows of a rule must exceed the factor):

| Long window | Short window | Burn-rate factor | Budget spent in the long window |
|---|---|---|---|
| 1 h | 5 min | 14.4 | 2 % |
| 6 h | 30 min | 6 | 5 % |

Open a ticket (no page) at burn rate 1 over 3 days. The long window prevents paging on a 2-minute blip;
the short window makes the page clear soon after the problem is fixed. These factors are the SRE workbook's
values as recalled; they assume a 30-day window and should be re-derived if the window changes.

## 6. What these SLOs do not cover

* **Model quality.** A service can meet both SLOs while every score is wrong. Detection quality needs labels,
  which arrive late (maintenance records); see w7d3.
* **Input drift.** A fully available service can be fed out-of-distribution data; see w7d2.
* **Per-machine fairness of service.** Aggregate SLIs can hide one machine whose requests always fail
  (for example because its run exceeds the 5,000-sample cap); a per-machine error breakdown in the logs is
  the check.
