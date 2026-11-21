# Mutant: q4_where_filter

The conditions on the right-hand table are in `WHERE` instead of `ON`. NULL-extended rows fail the
comparison, so the LEFT JOINs behave as INNER JOINs and sites with no corrective order in 2025 vanish
instead of showing 0. Counts for the remaining sites are correct, which is why it survives a glance.

Changed file: `queries/q4_corrective_2025_per_site.sql`
