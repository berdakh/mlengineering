# Mutant: one global top-k instead of k per week

Ranks the whole test quarter at once and takes the top 15 x weeks. The collections team cannot do
that: they have 15 calls each week and choose among that week's invoices. A global ranking rewards
scores that drift with time (late rates were rising) and concentrates calls in the last weeks.

Rejected by `test_metric_ranks_within_each_week`, `test_metric_is_not_a_global_top_k` and
`test_metric_agrees_with_reference_on_real_shape`.
