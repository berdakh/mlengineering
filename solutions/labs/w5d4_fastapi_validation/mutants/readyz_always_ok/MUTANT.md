# Mutant: readyz_always_ok

`/readyz` returns 200 like `/healthz`. A load balancer then sends traffic to an instance that
answers every prediction with 503, instead of waiting for it or replacing it.
