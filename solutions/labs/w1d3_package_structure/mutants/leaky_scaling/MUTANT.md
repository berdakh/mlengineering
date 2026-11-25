# Mutant: refactored, but the scaler is still fitted on all rows

A faithful, behaviour-preserving port: the structure is right, the metrics match
the golden run to every printed digit - and the test-set leakage is still there.
This is the state the learner should be in after Task 6 and *before* Task 7.
It shows that "the numbers match" cannot detect this leak on this dataset.

Rejected by: `test_scaling_lives_inside_the_model` only. Every other check passes.
