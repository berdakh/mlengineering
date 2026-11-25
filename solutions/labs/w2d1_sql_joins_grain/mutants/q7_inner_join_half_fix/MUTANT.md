# Mutant: q7_inner_join_half_fix

Fixes the duplication (parts are pre-aggregated to one row per work order) but keeps an INNER join to the
pre-aggregate, so the 36 work orders without parts, their labour hours, and the empty site are still
dropped. Typical of a fix that addresses the symptom finance reported ("too high") and stops there.
Rejected by the reconciliation invariants.

Changed file: `queries/q7_site_costs_fixed.sql`
