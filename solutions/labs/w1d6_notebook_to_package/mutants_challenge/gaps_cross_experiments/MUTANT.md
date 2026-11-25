# Mutant: gaps_cross_experiments

`datetime.diff()` over the whole table, exactly as in the notebook cell that printed "n gaps > 5 s: 19".
The first row of each experiment is compared with the last row of the previous one, so every boundary
between recordings is reported as a gap (and a boundary where the next recording starts *earlier*
yields a negative interval that means nothing). The notebook counted 19 "gaps" this way; computed
per experiment on the real data there are 9.

The learner's own tests use a single experiment, or two that happen to be adjacent in time, so they pass.
Rejected by `test_experiment_boundaries_are_not_gaps` and the two `gaps` command tests.
