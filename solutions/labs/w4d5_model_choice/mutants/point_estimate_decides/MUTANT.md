# Mutant: the point estimate decides

`classify_difference` compares the midpoint of the interval with the MPID instead of the whole
interval, so +0.07 [0.02, 0.13] is called "better". The interval is the evidence; its centre is not.
Caught by the parametrised `test_classify_difference` and `test_recommend_prefers_simple_when_nothing_is_better`.
