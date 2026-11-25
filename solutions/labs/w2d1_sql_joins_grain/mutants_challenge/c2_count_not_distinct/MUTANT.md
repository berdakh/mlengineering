# Mutant: c2_count_not_distinct

Counts part lines instead of distinct parts: the same part used on two work orders of one machine is
counted twice. `(wo_id, part_id)` is unique in `parts_used`, but `part_id` is not unique per machine.

Changed file: `queries/c2_machine_parts.sql`
