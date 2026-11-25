# Mutant: per-bucket counts instead of cumulative

Prometheus `le` buckets are cumulative (count of observations <= upper). Writing the count of each interval breaks every quantile computed from them. Caught by `test_latency_histogram_is_cumulative_and_consistent`.
