# Mutant: an empty slice reports 0.0

`np.nansum(values) / max(n, 1)` avoids a division warning and returns 0.0 for a slice with no
experiments or with the metric undefined everywhere. In a table sorted by value that slice is now the
'worst', with a measured-looking 0.000. Plausible: it is the standard way to silence a RuntimeWarning.

Rejected by `test_requested_level_with_no_experiments_is_reported_as_empty` and
`test_slice_where_the_metric_is_undefined_everywhere`.
