# Capacity plan: flowguard /predict for the 120,000-machine fleet (REFERENCE SOLUTION)

## Assumptions

* **Traffic.** 120,000 machines x 1 request / 600 s = **200 requests/s on average**. Peak = 3 x average =
  **600 requests/s**, the operator's estimate, not a measurement. Requests are 600 samples (about 138 KiB
  of JSON), the size measured.
* **Service time.** In `measured_curve.csv` the single worker kept up at 60 requests/s and saturated
  between 60 and 90 (at 90 it served only 82.9/s and the queue grew). Maximum throughput of about
  83/s means about **12 ms of worker time per request**; the client-observed mean at 20/s was 11.5 ms,
  consistent. I use S = 12 ms. The model itself is a small part of that: the lab's profile put about
  4 ms in parsing, scoring and building the response, the rest in the framework and HTTP.
* **Utilisation target 0.7.** A worker serves one CPU-bound request at a time (GIL), so queueing delay
  grows sharply as utilisation approaches 1 (at rho = 0.7 a simple M/M/1 queue already waits 2.3 x the
  service time on average; tails are worse). The measurement agrees: p95 met the 100 ms SLO at 60/s
  (rho about 0.72) and missed it at 90/s. 0.7 leaves room for bursts within the peak minute.
* **Measurement bias.** One 4-core machine ran both the load generator and the server, shared with other
  jobs: the service time is probably overstated (generator competes for CPU) and network is absent
  (understated). Production hosts, network and TLS will differ; this plan must be re-measured there.
* **Multi-worker latency floor.** With `uvicorn --workers N` the lab measured a ~40 ms Nagle/delayed-ACK
  floor; this plan assumes the TCP_NODELAY launcher (`serve.py`), with which 2 workers kept p95 at
  12-15 ms up to 120/s.

## Calculation

* Little's law at peak, with W = 11.5 ms mean time in system: L = 600 x 0.0115 = **6.9 requests in the
  service on average**. Busy workers (offered load): a = lambda x S = 600 x 0.012 = 7.2.
* Workers at rho <= 0.7: n = ceil(7.2 / 0.7) = ceil(10.3) = **11 workers**. Cross-check from the curve:
  `max_rate_within_slo(curve, 100)` = 60 requests/s per worker, so 600 / 60 = 10 workers; 11 is
  consistent and slightly more conservative.
* Hosts: one worker per vCPU, but leave one vCPU per host for the OS, logging and the event loop: 3
  workers per 4-vCPU host, so ceil(11 / 3) = **4 hosts**, plus **1 spare** so that losing a host during
  the peak does not break the SLO (N+1): **5 hosts, 15 workers installed, 11 needed at peak.**
* Average load (200/s) needs ceil(2.4 / 0.7) = 4 workers: most of the day the fleet is 70 % idle, which
  is the argument for autoscaling on request rate if the platform supports it.

## Sensitivity

| Assumption changed | Workers needed |
|---|---|
| Peak traffic 0.5x (300/s) | 6 |
| Peak as estimated (600/s) | 11 |
| Peak 1.5x (900/s) | 16 |
| Peak 2x (1,200/s) | 21 |
| Service time = p95 at low load (15.9 ms) instead of 12 ms | 14 |
| Utilisation target 0.6 instead of 0.7 | 12 |

The peak factor dominates: it is an estimate and moves the answer by 5 workers per 0.5x. The service
time and utilisation target move it by 1-3. So the first thing to measure is the real arrival pattern
(requests per second at 1 s resolution over a few shift changes), not a better benchmark.

## Risks

1. **Peak higher than 3x** (synchronised flushes after an outage). Measure: arrival histogram per second
   in production logs. Mitigate: clients add random jitter before flushing; the service rejects excess
   load quickly with 503 + `Retry-After` instead of queueing.
2. **Overload collapse.** The lab showed a single worker at 120/s serving 3.5/s with 95 % errors and
   2.3 GB of resident memory: an unbounded queue turns overload into an outage. Measure: queue depth and
   RSS under a 2x-peak open-loop test. Mitigate: a concurrency limit per worker and request timeouts.
3. **Service time differs in production** (larger requests, TLS, slower CPUs). Measure: server-side
   duration per request (w7d1 metrics) and re-run the load test on the production host type.
4. **Latency floor returns** after an upgrade of uvicorn or a change of launcher. Measure: a scheduled
   perf check of p50 at low load on 2 workers (the floor shows up as p50 of about 50 ms).
