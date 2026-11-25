# Mutant: configurations with missing parameters vanish

When two sweeps have different parameters, each sweep's rows are NaN in the other's columns. With
`groupby` (default `dropna=True` behaviour on NaN keys, and NaN != NaN) those configurations are
silently dropped from the table. Caught by: the mixed-sweeps aggregation check.
