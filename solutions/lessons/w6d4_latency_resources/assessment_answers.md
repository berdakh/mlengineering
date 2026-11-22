# W6D4 assessment — model answers

## 1. Mean 35 ms, two distributions

(a) Every request takes 30-40 ms: mean 35, p99 about 40 ms, meets "p99 <= 100 ms".
(b) 97 % of requests take 10 ms and 3 % take 843 ms: mean 0.97 x 10 + 0.03 x 843 = 35 ms, p99 = 843 ms,
misses badly. (The lesson's open-loop simulation is this shape: p50 10 ms, p99 710 ms.) The dashboard
should show p50, p95 and p99 over a stated window, the request rate and the error rate, and ideally a
latency histogram or heat map, never the mean alone.

*Common wrong answer.* "Show the max": one request decides it; it is useful as an alarm, not a summary.

## 2. Closed loop and a 2 s pause every minute

Each of the 8 virtual users has at most one request outstanding. During the pause each user's request
waits, so 8 requests record about 2 s, and then the users resume; the requests that independent clients
would have sent during those 2 s were never sent, so they are never measured. Out of a minute's
requests (say 8 users x ~60 s / ~20 ms = ~24,000), 8 are slow: 0.03 %, invisible at p99. In an open-loop
test at the same average rate, every request scheduled during the pause is delayed (by up to 2 s, then
by the backlog draining), so at least 2/60 = 3.3 % of requests are delayed, which puts p99 inside the
pause. The closed loop's p99 is wrong by two orders of magnitude.

## 3. Little's law

L = 120 x 0.050 = 6 requests in the system on average. With W = 2 s: L = 240. Those 234 extra requests
are held somewhere (accept queue, event loop, thread pool, request bodies in memory), so memory grows in
proportion; with large payloads that is how a container is killed for exceeding its memory limit (the
lab's overloaded worker grew from 90 MB to 2.1-2.8 GB). Rising L at constant lambda is also a cheap
early warning: monitor in-flight requests.

## 4. Threads vs processes

Threads in one process share one interpreter and its GIL: only one thread runs Python bytecode at a
time, so CPU-bound endpoints gain nothing in throughput; threads help when requests wait on I/O (database,
another service), and they keep one slow request from blocking the event loop. Worker processes are
separate interpreters: up to one core each of Python work, so capacity scales with cores for CPU-bound
code, at the cost of memory per process (model, libraries) and of per-process state (caches,
connections). For this service, processes; threads only matter if the endpoint starts waiting on I/O.

## 5. Timing checks in CI

(1) The runner is a shared VM whose speed varies run to run, so the check fails on unchanged code
(w6d3 measured 0-3 failures in 40 runs as load changed). (2) A p95 needs many requests at a controlled,
realistic offered load, which a unit test does not create; a test-suite timing is a closed-loop,
cold-cache, tiny sample. Deterministic proxy for CI: "the model is loaded once at startup, not per
request" (count loads with a test double), or "the endpoint does not call X per sample".

## 6. Laptop measurement with a co-located generator

Overstates: service time and latency (generator and server compete for 4 cores; the lab's shared machine
made it worse); understates or ignores: network round trips, TLS, multiple client hosts and connection
counts, other tenants on production hosts, larger or varied payloads, long-run effects (memory growth,
GC pauses, log rotation). The biggest bias: CPU contention between generator and server; run the
generator on a separate machine (or at least pin it to separate cores) and measure on the production
host type.

## Design-choice explanation (model answer)

Overload must be turned into fast, visible rejection rather than slow collapse. Concretely: (1) a
concurrency limit per worker slightly above the number it can serve within budget (with 12 ms per request
and a 100 ms p95 budget, a handful in flight per worker); requests beyond it get an immediate 503 with
`Retry-After`, which costs microseconds and keeps memory bounded; (2) request time-outs on the server
shorter than the client's, so abandoned work is cancelled; (3) clients retry with jittered exponential
back-off, so a burst spreads out; (4) autoscaling on utilisation or in-flight requests for sustained
increases, accepting that it reacts in minutes, not seconds. For the reliability engineer this is better
than queueing: queued requests come back late (an alarm for a fault at 10:00 arriving at 10:03 is
worse than useless if the dashboard looks current), and an overload outage takes every machine's alarms
down with it, while explicit rejections show up as a measurable error rate on the service dashboard,
tell clients to retry, and keep the requests that are served on time. Scoring: strong answers name
bounded queues/limits, explicit rejection and why late answers are harmful for alerting; adequate answers
propose autoscaling only; weak answers "add more workers".

## Interview rep — what a strong answer contains (rubric, 1 point each)

1. **Work backwards from the user requirement**: 2 s, 99 % of the time, end to end; allocate the budget
   across ingestion, queueing, network, the model service and the dashboard (for example 300 ms p99
   for the model service), and say the allocation is a decision to revisit.
2. **Load**: 2,000 machines x 1 window per 60 s = about 33 requests/s on average; ask about
   synchronisation (all machines on the minute boundary gives a 2,000-request burst each minute) and
   propose client jitter.
3. **Size with Little's law and a utilisation target**: measure service time for a 60-sample request
   open loop on the target host; workers = ceil(lambda x S / 0.7); add N+1.
4. **Measure correctly**: open-loop load at and above the expected peak, percentiles, warm-up, generator
   on separate hosts, burst test of the minute-boundary pattern.
5. **Production**: server-side latency histogram per route, in-flight requests, error rate, end-to-end
   latency from window timestamp to dashboard update (the user's actual metric), alerts on SLO burn,
   overload protection (limits, 503s).

4-5 strong, 2-3 adequate, 0-1 weak. Deduct for quoting a mean, or for sizing from a closed-loop test.
