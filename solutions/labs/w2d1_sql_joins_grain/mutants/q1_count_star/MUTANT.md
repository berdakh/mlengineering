# Mutant: q1_count_star

`COUNT(*)` counts the NULL-extended row of a site without machines, giving 1 machine instead of 0. The
`n_active` expression has the same flaw in a subtler form: on the NULL-extended row
`m.decommissioned_date IS NULL` is TRUE, so the phantom machine is also counted as active.

Changed file: `queries/q1_machines_per_site.sql`
