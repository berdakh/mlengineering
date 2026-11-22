# Mutant: threshold chosen on the test data

`frozen_threshold_evaluation` picks the threshold on the test scores and labels. The test F1 it
reports is then the best achievable on that sample, which no deployed threshold would reach, and the
"frozen" threshold changes whenever the test set does.

Rejected by: the two frozen-evaluation tests in `checks/test_threshold.py`.
