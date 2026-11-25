# Mutant: slice value pooled over rows

`slice_metrics` weights each experiment by its number of rows, which is what you get by
summing counts over a slice before dividing. One long, easy experiment then outvotes several short
failing ones: in the planted data the `other` family reads 0.64 instead of 0.25 and stops being the
worst slice. Plausible because row-pooled metrics are what `sklearn.metrics` gives by default.

Rejected by `test_value_is_the_mean_over_experiments` and `test_the_planted_failing_slice_is_the_worst`.
