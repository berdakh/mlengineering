# Mutant: gap_as_timedelta

`gap_seconds` holds a pandas `Timedelta` (and the JSON a string such as `"0 days 00:00:11"`) instead
of a number of seconds. The column name promises a unit; downstream code that compares it with a
threshold or sums it gets a type error or, worse, a silently wrong comparison after a cast to
nanoseconds.

Rejected by `test_one_gap_is_reported_with_both_timestamps` and `test_gaps_command`.
