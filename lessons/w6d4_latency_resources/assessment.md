# W6D4 assessment

Write your answers before opening `solutions/lessons/w6d4_latency_resources/assessment_answers.md`.

## Reasoning questions

1. A dashboard shows "mean latency 35 ms". Give two distributions of request latency with that mean,
   one of which meets "p99 <= 100 ms" and one of which badly misses it. What should the dashboard show?
2. A closed-loop load test with 8 virtual users reports p99 = 40 ms against a server that, for 2 s
   every minute, stops answering (a garbage-collection pause, say). Explain why the reported p99 is far
   too optimistic, and estimate the fraction of requests that an open-loop test at the same average rate
   would see delayed by the pause.
3. Little's law: a service receives 120 requests/s and the mean time in system is 50 ms. How many
   requests are in the system on average? If the arrival rate stays the same and the mean time rises to
   2 s because of queueing, how many? What happens to memory, and why does that matter?
4. Your service is CPU-bound Python. Explain what adding uvicorn *threads* (a larger thread pool for sync
   endpoints) buys you versus adding *worker processes*, and when each helps.
5. Two reasons why "p95 latency measured in a unit test" belongs in a scheduled job rather than in CI
   (lesson w6d3), and one deterministic proxy that may stay in CI.
6. You measured on a 4-core laptop with the load generator on the same machine. List what this setup
   over- or under-states compared with production, and one change that removes the biggest bias.

## Design-choice explanation (150-250 words)

The lab found the single-worker service collapses beyond its capacity: latency rose to seconds and
memory to gigabytes. Propose how the service should behave when offered more load than it can serve
(think: bounded queues, concurrency limits, `503` with `Retry-After`, timeouts, autoscaling), and argue
which response is better for the reliability engineer who consumes the alerts.

## Rubric (open answers)

| Criterion | Strong | Adequate | Weak |
|---|---|---|---|
| Distribution thinking | reasons with percentiles and tails, gives numbers | mentions tails | reasons with means |
| Measurement validity | names coordinated omission, warm-up, co-located generator, noisy host | one of these | trusts any number |
| Queueing | uses L = lambda W and utilisation correctly, links queues to memory | one link | none |
| Concurrency model | separates GIL-bound threads from processes | partly | "more threads = faster" |
| Evidence | cites the lab's own measurements | general | none |

## Interview rep (10-15 minutes, system design: latency budget; reduced assistance)

> "The product team wants anomaly scores shown on the operator dashboard 'in real time'. Each of 2,000
> machines sends a 60-sample window every minute. The dashboard must update within 2 seconds of a window
> arriving, 99% of the time. Walk me through how you would turn that into a latency budget for the model
> service, how you would size it, and how you would know you are meeting it in production."

Answer aloud or in writing in 12 minutes, then score yourself with the rubric in the answers file.
