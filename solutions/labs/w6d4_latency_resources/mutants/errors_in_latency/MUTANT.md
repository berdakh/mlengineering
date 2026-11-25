# Mutant: failed requests included in the latency percentiles
A fast 503 makes the service look quicker; a slow timeout makes it look slower. Either way the
percentiles no longer describe successful service. Caught by: test_errors_are_counted_and_kept_out_of_latency.
