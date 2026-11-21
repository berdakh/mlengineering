# Mutant: c3_inner_join

INNER join drops the technicians who were never assigned, although the task says "every technician".
Also leaves `labor_hours` NULL instead of 0 where no hours were recorded.

Changed file: `queries/c3_technician_load.sql`
