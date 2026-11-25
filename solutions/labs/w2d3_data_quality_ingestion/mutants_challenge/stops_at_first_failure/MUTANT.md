# Mutant: stops_at_first_failure

The checker returns as soon as an error-severity rule fails ("the table is bad anyway").

Why it is plausible: it mirrors `assert`-style validation and exceptions. Why it is wrong: a report is
for the person who has to fix the export. If they fix the one reported problem and resubmit, they meet
the next one, and so on; with several upstream teams this turns one round trip into five.

Rejected by: `test_all_violations_are_reported_together`.
