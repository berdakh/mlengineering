# Mutant: no_jitter

Plain exponential backoff without jitter (`backoff` returns the cap): every client that failed at the same moment retries at the same moment, a retry storm. See the worked example.
