# W2D1 assessment — model answers

Open after writing your own. Numbers were measured on `data/maintenance.db` (SYNTHETIC).
Reference queries: `lab/queries/`, `challenge/queries/`. Reference bug report: `lab/FANOUT_REPORT.md`.

## A. Reasoning questions

**A1.** Let `L` be the machine's true labour hours and `D` its true downtime hours.

| | `SUM(labor_hours)` | `SUM(hours)` | `COUNT(DISTINCT wo_id)` | `COUNT(wo_id)` |
|---|---|---|---|---|
| (i) `a, b ≥ 1` | `b·L` | `a·D` | `a` (correct) | `a·b` |
| (ii) `a ≥ 1, b = 0` | `L` (correct) | NULL | `a` (correct) | `a` (correct) |

With `b = 0` the LEFT JOIN adds one NULL-extended downtime row per work order, so nothing is
multiplied. A reviewer who spot-checks a machine without downtime (or with exactly one event) sees
correct labour and concludes the query is right. Machine 2 in the data is such a case (6 orders, no
downtime); machine 1 (4 orders, 5 events) shows 92.0 instead of 18.4. The error is proportional to
the *other* child's row count, so it is largest for the busiest, most important machines.

*Common incorrect answers.* "Both sums are multiplied by `a·b`" (each is multiplied by the other
child's count only). "`COUNT(DISTINCT)` shows the query is fine" (it repairs identifier counts and
nothing else). Forgetting that `SUM` over only NULLs is NULL, not 0.

**A2.** (1) The inflation is not uniform: each work order is repeated once per part line, so the
factor differs per order (1 to 6 here) and therefore per site. Per site the ratio of reported to true
labour is 1.07, 0.85, 1.46, 2.00 and 1.40. (2) The query also *drops* rows: the inner join to
`parts_used` removes the 36 work orders without parts (11, 5, 10, 4 and 6 per site) and the site with
no machines. Site 2 is under-reported (80.7 against 95.5) because it loses more through dropped
orders than it gains through duplication. Two opposing errors of different size per group cannot be
undone by one constant; 32 % is only their net effect on the grand total.

*Common incorrect answers.* "Divide by the average number of parts per order" (ignores dropped
orders and per-order variation). Stating only the over-count: the under-count is the part that makes
the tile misleading in both directions.

**A3.** After the join the rows are at the part-line grain, one row per `(wo_id, part_id)`.
`quantity * unit_cost` is defined at exactly that grain, and every part line appears once, so its sum
is right. `labor_hours` is defined at the coarser work-order grain and is repeated on every part
line. Rule: *in a joined result, a column may be summed only if the result's rows are at the grain
at which that column is defined, and no row of that grain was dropped.* Before running anything, find
the finest-grained table in the join chain; only its measures are safe. (The inner join did not drop
part lines, because every part line has a work order, a machine and a site.)

*Common incorrect answer.* "Because parts were joined correctly": the join is the same one that
breaks labour. Correctness is a property of the measure–grain pair, not of the join.

**A4.** For the 13 machines whose `criticality` is NULL both comparisons evaluate to UNKNOWN, and
`WHERE` keeps only TRUE. The two queries are not complements. "Not known to be high":
`WHERE criticality <> 'high' OR criticality IS NULL` (25 rows). Engine-specific null-safe forms exist
(`IS DISTINCT FROM 'high'` in PostgreSQL and DuckDB; `criticality IS NOT 'high'` in SQLite); the
portable version is the explicit `OR … IS NULL`. `COALESCE(criticality, 'unknown') <> 'high'` also
works and states the intent.

*Common incorrect answers.* "NULL is treated as false" (the predicate is UNKNOWN, which is why `NOT`
does not rescue it: `NOT (criticality = 'high')` still excludes the NULLs). "`!=` instead of `<>`"
(same operator).

**A5.** `AVG(labor_hours)` = 7.64 is the mean over the 83 orders with recorded hours.
`AVG(COALESCE(labor_hours, 0))` = 6.82 is the mean over all 93 orders *assuming the 10 unrecorded
ones took zero hours*, which is almost certainly false. Which to report depends on the missingness
mechanism. If hours are missing at random with respect to duration, 7.64 estimates the mean hours per
order. If they are missing because the order is still open, or because short jobs are not booked, the
recorded subset is biased and neither number is the population mean; you would report 7.64 with the
coverage (83 of 93) and investigate. Zero-filling is right only when NULL genuinely means "no work
done". Report the denominator with any average over a nullable column.

*Common incorrect answer.* "COALESCE is safer because it handles NULLs": it replaces a visible
unknown with an invisible wrong value.

**A6.** Defect 1 (NULL): `work_orders.tech_id` is NULL for unassigned orders, so the subquery
contains NULL and `NOT IN` can never be TRUE; the query returns no rows whatever the data says.
Defect 2 (logic): the subquery lists technicians who worked at a site *other than* 3. Excluding them
answers "technicians who worked only at site 3, or nowhere", not "never worked at site 3". The
negation belongs outside, the positive condition inside:

```sql
SELECT t.tech_name FROM technicians t
WHERE NOT EXISTS (SELECT 1 FROM work_orders w JOIN machines m USING (machine_id)
                  WHERE w.tech_id = t.tech_id AND m.site_id = 3);
```

This returns four technicians (ids 1, 10, 11, 12). "No rows" was read as an answer when it was a
symptom; an anti-join that returns nothing deserves the check `SELECT COUNT(*) - COUNT(col)` on the
subquery column.

*Common incorrect answer.* Fixing only the NULL (`WHERE w.tech_id IS NOT NULL` in the subquery) and
keeping `<> 3`: the query then runs, returns rows, and answers the wrong question.

## B. Design choice

**B1 (model answer).** I would use design (2): one CTE per source, each aggregated to the machine
grain, left-joined to `machines`. Correctness: each join is one-to-at-most-one, so the row count is
fixed at the number of machines by construction, and no measure can be multiplied by a sibling
table's row count. Design (1) is correct only while every aggregate happens to be fan-out-safe;
adding one `SUM` later breaks it silently. Reviewability: each CTE can be read and run alone, and its
grain is one `GROUP BY` line. Testability: I can assert `COUNT(*) = (SELECT COUNT(*) FROM machines)`,
uniqueness of `machine_id`, and that each feature total reconciles with its source table; in design
(1) there is no intermediate to test. Cost: (2) scans each child once and joins small aggregates,
usually cheaper than building the multiplied intermediate. I would accept (1) only for a single
child table, where no sibling exists to multiply against. Either way the feature windows must end
before the label period starts, which is a separate (temporal) leakage question.

*Common incorrect answers.* "(1), with DISTINCT where needed": works today, has no protection
against the next edit. "They are equivalent if written carefully": true of results, false of
failure modes. Ignoring that machines with no activity must be present with zeros (they are likely
negatives).

## D. Interview rep — worked answer and rubric

Executed reference: `python solutions/labs/w2d1_sql_joins_grain/interview_rep/country_summary.py`
(prints the model answer and the usual wrong answer on a six-user toy table).

```sql
WITH s AS (SELECT user_id, COUNT(*) AS n_sessions FROM sessions GROUP BY user_id),
     p AS (SELECT user_id, SUM(amount) AS revenue FROM purchases GROUP BY user_id)
SELECT COALESCE(u.country, 'unknown')                  AS country,
       COUNT(*)                                        AS n_users,
       COUNT(p.user_id)                                AS n_buyers,
       COALESCE(SUM(p.revenue), 0)                     AS revenue,
       1.0 * COALESCE(SUM(s.n_sessions), 0) / COUNT(*) AS sessions_per_user
FROM users AS u
LEFT JOIN s ON s.user_id = u.user_id
LEFT JOIN p ON p.user_id = u.user_id
GROUP BY COALESCE(u.country, 'unknown');
```

Reasoning to say aloud: result grain is country; users is the driving table; sessions and purchases
are two independent children of user, so each is reduced to one row per user first; after the joins
the rows are still one per user, so `COUNT(*)` is users and `COUNT(p.user_id)` is buyers.
`AVG(s.n_sessions)` would be wrong: it skips users with no sessions. Convincing the reviewer:
the revenue column must sum to `SELECT SUM(amount) FROM purchases`, and `n_users` to
`SELECT COUNT(*) FROM users`; both are one-line checks.

On the toy data the naive two-join query reports revenue 120 for KZ (true 40) and 3.5 sessions per
user (true 2.0), while its `n_users` and `n_buyers`, protected by `DISTINCT`, are right.

| Criterion | Meets | Not yet |
|---|---|---|
| Grain stated before writing | Says "one row per country; one row per user before grouping" | Starts typing joins |
| Fan-out avoided | Pre-aggregates both children, or uses correlated subqueries | Joins both children and sums |
| NULL handling | `unknown` group; zero-session users in the denominator; revenue 0 not NULL | `AVG` over joined sessions; NULL country row left as NULL |
| Integer division | `1.0 *` or a cast | integer result |
| Verification | Names at least one reconciliation total unprompted | "I would look at the output" |
| Time | Working answer within 15 minutes | — |

*Common incorrect answers.* `COUNT(DISTINCT …)` for the counts and plain `SUM(amount)` for revenue
(the classic); `AVG(n_sessions)` after the left join (drops zero-session users from the mean); leaving the
NULL country as a NULL group when the prompt asks for `'unknown'`; integer division in the average.
