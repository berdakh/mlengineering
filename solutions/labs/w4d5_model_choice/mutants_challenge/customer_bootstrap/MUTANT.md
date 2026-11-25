# Mutant: customers resampled as if independent

Bootstraps individual customers. The interval for B - A becomes [+0.001, +0.022]: it excludes zero
and looks like evidence for B. Caught by `test_interval_resamples_regions_not_customers`.
