# Mutant: ignores_retry_after

The client ignores the server's `Retry-After` and uses its own jitter. Under load shedding the server asked for a specific pause; ignoring it brings the retries back too early.
