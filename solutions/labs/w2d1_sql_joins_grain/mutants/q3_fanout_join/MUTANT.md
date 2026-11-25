# Mutant: q3_fanout_join

Joins both one-to-many children (`work_orders`, `downtime_events`) to `machines` and then sums. A machine with
a work orders and b downtime events yields a*b rows, so labour is multiplied by b and downtime by a.
`COUNT(DISTINCT w.wo_id)` hides the problem for the count, which makes the query look verified. The most
common real-world form of the fan-out bug.

Changed file: `queries/q3_machine_hours.sql`
