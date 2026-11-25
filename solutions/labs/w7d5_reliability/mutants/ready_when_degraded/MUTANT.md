# Mutant: ready_when_degraded

`/readyz` returns 200 without a model, so a load balancer keeps sending traffic to an instance that can only answer with the fallback, and a bad rollout never trips the readiness gate.
