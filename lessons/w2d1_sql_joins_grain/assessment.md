# W2D1 assessment

Write answers in your own words (2–6 sentences each unless stated) **before** opening
`solutions/lessons/w2d1_sql_joins_grain/assessment_answers.md`. Suggested location:
`progress/journal/w2d1_assessment.md`. Numbers refer to `data/maintenance.db` (SYNTHETIC).

## A. Reasoning questions

**A1.** A machine has `a` work orders and `b` downtime events. You `LEFT JOIN` both tables to
`machines` and compute `SUM(labor_hours)`, `SUM(hours)`, `COUNT(DISTINCT wo_id)` and
`COUNT(wo_id)` per machine. Give each of the four results in terms of the true values, for
(i) `a, b ≥ 1` and (ii) `a ≥ 1, b = 0`. Why does case (ii) make spot-checking dangerous?

**A2.** The broken dashboard query reports 838.8 labour hours in total; the true total is 633.8.
A colleague concludes "the query over-counts by 32 %, so divide by 1.32 until we fix it". Give two
separate reasons, with evidence from the data, why no single correction factor can be right.

**A3.** In the same broken query the `parts_cost` column is exactly correct. Explain why, using the
word *grain*. Then state the general rule that tells you, before running anything, which columns of
a joined result are safe to sum.

**A4.** `SELECT COUNT(*) FROM machines WHERE criticality = 'high'` returns 7 and
`… WHERE criticality <> 'high'` returns 12, but the table has 32 rows. Explain the missing 13 and
write a predicate that returns "all machines not known to be high" (25 rows).

**A5.** Someone writes `AVG(COALESCE(labor_hours, 0))` "to handle the NULLs". On this data the
mean changes from about 7.64 to about 6.82 hours. Which estimand does each expression compute, and
what would you need to know about *why* the hours are missing to decide which, if either, to report?

**A6.** You are handed this query and told it lists the technicians who have never worked on a
machine at site 3. It returns no rows, and the author says "so everyone has". Identify the two
independent defects.

```sql
SELECT tech_name FROM technicians
WHERE tech_id NOT IN (SELECT w.tech_id FROM work_orders w JOIN machines m USING (machine_id)
                      WHERE m.site_id <> 3);
```

## B. Design-choice explanation (one paragraph, about 150 words)

**B1.** You must build a training table with one row per machine for a "will this machine have a
corrective work order next quarter?" model, with features from `work_orders`, `parts_used` and
`downtime_events`. Compare two designs: (1) one query that joins everything and uses
`COUNT(DISTINCT …)` and `SUM(…)` with care; (2) one CTE per source table, each aggregated to the
machine grain, joined at the end. Choose one and defend it on correctness, reviewability, the ability
to test it, and cost. Say what would make you choose the other.

## C. Rubric for open answers

| Level | A-questions | B1 |
|---|---|---|
| **Meets** | Names the mechanism precisely (grain, cardinality, UNKNOWN), gives the right quantities, and ties them to evidence in the data | Chooses with reasons on at least three of the four dimensions, names an invariant that would be tested, and states a condition under which the other design wins |
| **Partial** | Right conclusion, mechanism vague ("duplicates", "NULLs are weird") or quantities missing | Chooses correctly but argues from style or habit; no test, no counter-condition |
| **Not yet** | Proposes `DISTINCT`, a correction factor or `COALESCE` everywhere as the fix | Treats the designs as equivalent, or picks (1) because it is shorter |

## D. Interview rep — SQL (15 minutes, timed)

**Conditions (weeks 1–2 of the fading schedule):** write your answer first, untimed reading of the
prompt allowed, then compare with the rubric and worked answer in the solutions file. Say your
reasoning aloud if you can; an interviewer hears the grain statement before they see the query.

> Tables: `users(user_id PK, country)` where `country` may be NULL;
> `sessions(session_id PK, user_id, started_at)`; `purchases(purchase_id PK, user_id, amount)`.
> A user may have any number of sessions and purchases, including none.
>
> Write one query returning, per country (NULL country reported as `'unknown'`): the number of
> users, the number of users with at least one purchase, total revenue, and the average number of
> sessions per user, where users with no sessions count as zero.
>
> Then answer: how would you convince a reviewer that the revenue column is right?

Log the rep in `progress/notes.md`: time taken, what went wrong, and the pattern behind the error.
