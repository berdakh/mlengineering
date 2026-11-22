# Point-level versus event-level results for `flowguard` - my reading

Fill this in after running `event_table.py` (three post-processing settings) and `tradeoff_curve.py`.
Keep it to one page. Numbers must be copied from your own runs.

## 1. Table (test experiments, threshold from dev)

Paste the default table and the table for one post-processing setting of your choice.

## 2. Where the two families of metrics disagree

Name the detector whose rank changes most between point F1 and the event columns, and say which
property of the data or of the metric produces the change.

## 3. The clock

How many events does elapsed time "detect", with what delay, under the lab's rule? What would the
any-overlap rule have reported? What does that tell you about using event recall alone?

## 4. Post-processing

What did `min_duration` and `merge_gap` buy and what did they cost? Which data are you allowed to
tune them on?

## 5. What cannot be claimed

With 9 test events and under two hours of normal operation, which statements about this detector
are not supported? Give one number that shows it.

## 6. Decision

The operating-point metrics the project will report from now on, and the matching rule (one sentence each).
