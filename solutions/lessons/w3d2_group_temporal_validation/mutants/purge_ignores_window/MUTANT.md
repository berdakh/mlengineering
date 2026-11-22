# Mutant `purge_ignores_window`

**Mistake.** `required_purge` returns the label horizon only and forgets the feature window.

**Why plausible.** Most write-ups of purging discuss overlapping *labels*. With `horizon = 0` (the label belongs to the row) this returns 0, i.e. no buffer at all, although rolling features of width `window` are shared across the boundary.

**Caught by.** `test_required_purge_counts_shared_raw_samples` and the shared-sample property test.
