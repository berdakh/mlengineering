# Mutant: one seed is accepted

A single run is summarised with sd = NaN (or 0) instead of being refused, so "one run" can enter a
comparison as if it had no seed variance. Caught by: the single-seed check.
