# Mutant: q2_not_in_null

`NOT IN` over a subquery that contains NULL (`work_orders.tech_id` is NULL for unassigned orders). For a
technician not in the list the predicate evaluates to UNKNOWN, never TRUE, so the query returns zero rows
without any error.

Changed file: `queries/q2_unassigned_technicians.sql`
