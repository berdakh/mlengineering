# Mutant: inclusive_threshold

`>=` instead of `>`. The specification says "strictly longer than". With 1 Hz data and the default
threshold the difference is invisible unless an interval is exactly 5 s, which happens in the real
data five times (three in `other/12`, two in `other/13`): this mutant reports 14 gaps where the
specification gives 9. The learner's tests avoid the boundary value, so they pass.

Rejected by `test_threshold_is_strictly_greater_than` and `test_gaps_command`.
