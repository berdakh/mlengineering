# Mutant: correlation between candidates ignored

`simulate_max` accepts `rho` and does nothing with it: the errors are always independent. The
simulation then overstates the optimism for any realistic search, where all candidates are scored on
the same folds and share most of their error.

Rejected by: the `rho` tests in `checks_challenge/test_optimism.py`.
