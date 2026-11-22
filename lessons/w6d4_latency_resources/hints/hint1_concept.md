# Hint 1 — concepts

* **Open loop.** The generator decides *when* each request is sent (t0 + i / rate) before the test
  starts. It never waits for a response before sending the next request. Requests overlap.
* **Latency is measured from the intended start.** If the generator or the server stalls, the requests
  that should have gone out during the stall still count from when they *should* have been sent.
  Measuring from the actual send hides the stall ("coordinated omission").
* **Percentiles.** Sort, compute the fractional position h = (n - 1) q / 100, interpolate between the
  two neighbouring values. That is numpy's default ("linear") definition.
* **Errors are not latencies.** A fast 503 or a 10 s timeout tells you about failure, not about how
  long successful service takes. Count them in the error rate; keep them out of the percentiles.
* **Warm-up.** The first seconds include connection set-up and cold code paths. Exclude them by
  intended start time, not by count.
* **Capacity (challenge).** A Python worker serving CPU-bound requests handles about one at a time.
  Little's law: average number busy = arrival rate x time each takes.
