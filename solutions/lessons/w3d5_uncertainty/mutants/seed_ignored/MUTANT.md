# Mutant: seed accepted but ignored

The generator is created without the seed, so every call gives a different interval. The intervals
are statistically valid; the report is not reproducible, and two people running the same command
get different numbers in the third decimal.

Why it is tempting: `default_rng()` works, and the `seed` parameter is easy to forget to pass on.

Rejected by: `test_same_seed_same_interval_different_seed_different`, `test_paired_is_reproducible`.
