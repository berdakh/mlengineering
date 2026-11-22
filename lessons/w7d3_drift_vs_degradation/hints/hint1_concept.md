# Hint 1 (concept): two clocks and one rule

Every label has two times. **Event time** (when the alarm or the fault happened) decides which window
the label belongs to. **Label time** (when the label reached you) decides whether it exists yet. A
function that answers "as of day d" filters on label time first and only then groups by event time.

The second idea: a number computed from too few labels is not a small number, it is no number. Your
functions return a status next to every estimate, and NaN when the status is `insufficient_data`.

The third: `monitor_report` holds two independent verdicts. Write it so that changing
`drift_result["drift"]` can change `input_changed` and the action text, and nothing else.
