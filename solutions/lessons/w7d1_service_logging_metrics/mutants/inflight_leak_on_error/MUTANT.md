# Mutant: in-flight gauge decremented only on success

The gauge counts up on every request but down only when `call_next` returns, so each unhandled error leaks one unit and the saturation signal drifts upward forever. Caught by `test_in_flight_returns_to_baseline_after_errors`.
