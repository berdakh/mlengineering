# replicas_rounded
Rounds to the nearest integer instead of up, so 2.1 busy cores get 2 replicas. Caught by:
test_replicas_is_little_law_rounded_up, test_replicas_exact_boundary_and_minimum.
