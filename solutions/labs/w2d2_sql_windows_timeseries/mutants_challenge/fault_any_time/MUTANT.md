# Mutant: fault_any_time

`seconds_since_fault` uses the closest `fault` event at any time, including faults logged after the
label. Since a failure is followed by a `fault` status within minutes, a small value of this feature
is the label itself in disguise.

Changed file: `features.sql`
