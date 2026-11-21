# a2_sql - reviewer notes

Reference: `lab/q1.sql` ... `q5.sql`. The checks compute the expected rows with pandas from the same
tables, independently of the reference SQL; both agree
(`python tools/verify_checks.py diagnostic/a2_sql`).

## What each query probes, and the plausible wrong answer

| Query | Probe | Wrong-but-runs version | What it returns |
|---|---|---|---|
| q1 | join + GROUP BY, NULL group, distinct counting | `COUNT(*)` for customers (mutant `q1_count_rows`); `GROUP BY c.country` without `COALESCE` in the SELECT | invoice count instead of customer count; a NULL-labelled group instead of `UNKNOWN` |
| q2 | anti-join, NULL semantics | `NOT IN (SELECT customer_id FROM tickets)` (mutant `q2_not_in_null`) | **zero rows**: `x NOT IN (..., NULL)` is UNKNOWN, never TRUE. Expected: 138 customers |
| q3 | join fan-out | both child tables joined, then aggregated (mutant `q3_fanout_join`) | `total_paid` multiplied by the ticket count and `n_tickets` by the invoice count, for customers with >= 2 of either; customers with one ticket look correct, which is why spot checks miss it |
| q4 | window function, deterministic tie-break | join to `MAX(invoice_date)` (mutant `q4_tie_duplicates`); `ROW_NUMBER()` ordered by date only | includes customers whose failed charge was retried successfully the same day (402 customer-days have two invoices); or a non-deterministic pick |
| q5 | aggregate then window (`LAG`) | `LAG` applied before aggregation; self-join on month-1 with string arithmetic | wrong grain; or missing first month instead of NULL |

Other acceptable solutions: q2 with `LEFT JOIN ... WHERE t.customer_id IS NULL`, or `NOT IN` with an
explicit `WHERE customer_id IS NOT NULL` in the subquery; q3 with correlated scalar subqueries; q4 with
a correlated `NOT EXISTS` on (date, id) ordering.

## Rubric

| Aspect | Demonstrated independently | Partial | Not yet demonstrated |
|---|---|---|---|
| Joins and aggregation (q1) | Correct in time | Correct after check feedback pointed at the count | Not correct |
| NULL semantics (q2) | Correct first time, or diagnosed the empty result unaided and can explain three-valued logic | Fixed by trying alternatives without being able to say why `NOT IN` failed | Left returning zero/wrong rows |
| Fan-out (q3) | Pre-aggregates (or equivalent) and can state the row-multiplication mechanism | Reached a passing query via `COUNT(DISTINCT ...)` patches without naming the cause (note: `SUM(DISTINCT amount)` is wrong in general) | Fan-out result submitted |
| Window functions (q4, q5) | Both correct, tie-break handled | One correct, or written with self-joins only | Neither |
| Verification habit | Looked at the data before/after (counts, a hand-checked customer) | Relied on the checks only | - |

The written line per query in `SUBMISSION.md` distinguishes "passed" from "understood".
