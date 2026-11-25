# Mutant: undefined ratios are 0.0

Precision with nothing flagged and recall with no anomalous rows return 0.0, the convention of
`flowguard.metrics` (and of scikit-learn's `zero_division=0`). In a per-experiment table that turns
'this experiment has no anomaly' into 'recall 0', and the slice mean is dragged down by experiments
that could not have been detected.

Rejected by `test_undefined_quantities_are_nan_not_zero` and `test_slice_where_the_metric_is_undefined_everywhere`.
