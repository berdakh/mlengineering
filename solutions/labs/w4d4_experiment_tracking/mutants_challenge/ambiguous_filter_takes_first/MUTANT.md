# Mutant: an under-specified filter silently picks one run per seed

If the filter matches several configurations, one run per seed is chosen arbitrarily and the
comparison is between whatever happened to come first. Caught by: the ambiguous-filter check.
