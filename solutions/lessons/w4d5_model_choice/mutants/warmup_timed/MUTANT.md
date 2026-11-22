# Mutant: warm-up calls are timed

Times every call, including the warm-up ones, so first-call costs (lazy imports, cold caches) inflate
p99 and max. Caught by `test_latency_excludes_warmup`.
