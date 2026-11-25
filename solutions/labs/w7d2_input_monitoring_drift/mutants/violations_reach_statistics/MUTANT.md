# Mutant: only infinities count as violations

A sentinel -9999 passes into the statistics, so a data-entry bug is reported as distribution drift (and the violation count is wrong). Caught by `test_schema_violations_are_counted_and_excluded`.
