# Mutant: nan_passthrough

Non-finite scores are not detected (`all_finite` always says True). NaN reaches the JSON encoder and becomes a 500 instead of a degraded answer.
