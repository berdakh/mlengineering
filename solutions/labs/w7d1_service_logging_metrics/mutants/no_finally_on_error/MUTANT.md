# Mutant: bookkeeping only on the success path

With no try/finally, an unhandled exception leaves `call_next` before the request is counted or logged: 500s are invisible in exactly the situation monitoring exists for, and in-flight leaks. Caught by the 500 cases in `test_exactly_one_access_line_per_request_for_every_outcome` and `test_request_counter_counts_every_outcome`.
