# Hint 1 — concept

* Every failure branch in `/predict` should end in the **same** helper: "answer with the fallback, say
  `degraded: true`, give the reason, count it, log it with the request id". If you find yourself writing
  the response body four times, the four copies will drift apart and one will forget the flag.
* There are two clocks in a deadline: the caller's (how long the HTTP request waits) and the worker's
  (how long the model call runs). `future.result(timeout=...)` controls the first only. The bulkhead must
  follow the second.
* Readiness answers "send me traffic?"; liveness answers "restart me?". Ask what a restart would fix.
* For the client, write down the decision table first: which outcomes end the loop, which sleep and retry,
  and what is returned or raised when attempts run out.
* For your own tests: a drill that does not inject the fault cannot fail when the handling is broken.
