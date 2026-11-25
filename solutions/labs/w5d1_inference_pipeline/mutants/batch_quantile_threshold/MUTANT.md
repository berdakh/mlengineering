# Mutant: the threshold is re-derived from the batch

`alarm_mask` alarms on the top 1 % of the scores in the batch (`np.quantile(scores, 0.99)`) instead of
the configured threshold: a fit-time decision recomputed at predict time. A batch with no fault still
alarms; a batch that is all fault mostly does not. Caught by `test_threshold_comes_from_the_configuration`
and `test_alarms_match_the_evaluated_post_processing`.
