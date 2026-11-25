# Mutant: index-based percentile without interpolation
`xs[int(n * q / 100)]` - a common hand-written version. It differs from the documented (numpy linear)
definition. Caught by: test_percentile_matches_numpy_linear.
