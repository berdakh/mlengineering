# Mutant: gaps_across_experiments

The sampling-gap check takes `tidy["datetime"].diff()` over the whole table instead of within each
experiment. The first row of every experiment is compared with the last row of the previous one, so
experiments recorded on different days are reported as having gaps.

Why it is plausible: it is one line shorter and gives the right answer on a single file, which is how
the check is usually developed. It is the tabular form of computing a feature across a subject
boundary. Why it is wrong: clean experiments are blamed, and the report becomes noise that people learn
to ignore.

Rejected by: `test_clean_data_passes_every_check`, the "clean experiment was blamed" assertion.
