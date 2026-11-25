# Latency report: flowguard /predict (REFERENCE, authoring machine, 2026-11-22)

## Set-up
4-core Linux container shared with other jobs; Python 3.13, uvicorn 0.54.0 (h11, asyncio loop; httptools
and uvloop not installed), FastAPI 0.165. Each request: the first 600 samples of real SKAB test
experiment valve1/13, 138 KiB of JSON. Open-loop generator (`loadtest.run_open_loop`) with httpx on the
same machine, 127.0.0.1, rates 20/60/90/120 per second, 15 s measured after 3 s warm-up, two
repetitions in interleaved order (`figures/measure.py`). Co-locating generator and server overstates
service time a little (they compete for 4 cores) and leaves out the network entirely.

## Budget
p95 <= 100 ms, p99 <= 250 ms, error rate <= 0.1 % at the service, per `budget.toml`.

## Results (means of two repetitions)

| Configuration | Offered/s | p50 ms | p95 ms | p99 ms | errors | served/s | RSS after run |
|---|---|---|---|---|---|---|---|
| `uvicorn --workers 1` | 20 | 10.8 | 15.9 | 19.7 | 0 | 20.1 | |
| | 60 | 10.5 | 32.6 | 91.8 | 0 | 60.0 | |
| | 90 | 638.8 | 2027.8 | 2357.4 | 0 | 82.9 | |
| | 120 | 6767.4 | 10028.9 | 10457.1 | 0.951 | 3.5 | 2.1-2.5 GB |
| `uvicorn --workers 2` | 20 | 11.6 | 54.9 | 60.1 | 0 | 20.0 | |
| | 60 | 52.8 | 60.1 | 71.3 | 0 | 59.9 | |
| | 120 | 54.7 | 85.5 | 135.8 | 0 | 119.6 | 245 MB |
| `uvicorn --workers 4` | 120 | 55.7 | 87.8 | 136.7 | 0 | 119.6 | 434 MB |
| `serve.py --workers 2` (TCP_NODELAY) | 20 | 10.0 | 14.8 | 19.3 | 0 | 20.1 | |
| | 60 | 8.7 | 11.7 | 17.8 | 0 | 60.0 | |
| | 90 | 8.9 | 14.1 | 35.3 | 0 | 90.0 | |
| | 120 | 8.1 | 13.7 | 43.9 | 0 | 120.0 | 239 MB |

Idle server memory: 90 MB (1 worker), 220 MB (2), 395-399 MB (4).

## Bottleneck
1. **One worker saturates at about 83 requests/s.** Each request costs about 12 ms of CPU in one Python
   process (the GIL serialises it), so capacity is about 1/0.012 per second. At 90/s the queue grew for
   the whole run (p50 0.6 s); at 120/s requests waited until the client's 10 s timeout, 95 % failed, the
   server served only 3.5/s, and its memory grew to 2.1-2.8 GB holding queued request bodies.
   `profile_predict.py`: parsing, scoring and response building take about 3.8 ms of the ~11 ms; the rest
   is framework and HTTP work, so making the model faster would not have moved the knee much.
2. **With `--workers 2` or `4`, a 40 ms floor.** Capacity was fine up to 120/s, but p50 jumped to about
   52 ms at every rate from 60/s and p95 to 55 ms even at 20/s. Latency that does not depend on load
   is not queueing. 52 - 11 = ~41 ms matches the Linux delayed-ACK timer: Nagle's algorithm was on.
   Cause: uvicorn 0.54 creates the multi-worker listening socket with protocol number 0, and asyncio
   only sets TCP_NODELAY on sockets whose protocol is IPPROTO_TCP (read in the installed source).
   Confirmed by forcing TCP_NODELAY in the workers: p50 at 60/s fell from 52 ms to 9.5 ms.

## Fix and effect
`serve.py` creates the listening socket with `IPPROTO_TCP` and starts the same app with 2 workers.
Same method, same rates: p95 11.7-14.8 ms and p99 17.8-43.9 ms from 20 to 120/s, no errors, all within
budget, at 239 MB. Recommended configuration: `serve.py --workers 2` on this 4-core host.

## What this does not show
* Production: different CPUs, real network and TLS, many clients; the generator shared the cores.
* Rates above 120/s for 2 workers, and long-run behaviour (memory over hours, GC pauses).
* Behaviour with other request sizes; latency is roughly proportional to samples per request.
* The fix relies on uvicorn's internal `Multiprocess` supervisor; re-measure after upgrades.
