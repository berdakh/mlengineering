# Mutant: windows_cross_experiments

Features are computed with one rolling pass over the whole tidy table, so the first `w-1` rows of every experiment are filled from the tail of the previous experiment (and gaps are ignored). Nothing crashes and there are fewer NaNs, which looks like an improvement. With a split by experiment this leaks rows of one experiment into another, possibly across the train/test boundary. Typical cause: `df[col].rolling(w)` without `groupby`. Caught by the contamination test, the warm-up test and the gap test.

Changed file: `src/flowguard/features.py`
