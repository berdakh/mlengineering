# Mutant: NaN treated as a schema violation

Missingness and malformed input have different causes and owners; merging them hides a sensor that is dropping out. Caught by `test_missing_values_are_missingness_not_violations`.
