# Mutant: returns the last sufficient candidate instead of the smallest

Every candidate is evaluated and the last one that reaches the target is returned. With an
ascending candidate list that is the largest, so the answer to "how many experiments do we need"
is inflated to whatever the top of the grid was.

Rejected by `test_required_experiments_is_the_smallest_sufficient_candidate`.
