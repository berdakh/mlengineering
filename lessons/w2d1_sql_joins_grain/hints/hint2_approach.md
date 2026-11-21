# Hint 2 — approach

A routine that prevents most mistakes:

1. **Write the grain of the result** and its key. Count how many rows that implies
   (`SELECT COUNT(*) FROM <driving table>`).
2. **List the measures and the grain at which each is defined.**
   `labor_hours` → work order. `quantity`, cost → part line. `hours` → downtime event.
3. **One CTE per measure source**, each grouped to the result's grain (or to the grain of the join
   key you will use). Join tables *upwards* (towards the "one" side) inside the CTE to obtain the
   grouping column; that direction never duplicates rows.
4. **Start the final `SELECT` from the driving table and `LEFT JOIN` each CTE.** Each CTE has at most
   one row per key, so the row count stays at the number from step 1.
5. **`COALESCE(…, 0)`** the measures that come from an outer-joined CTE.
6. **Verify:** row count equals step 1; grand totals equal single-table totals.

Which trap each lab or challenge question hides:

| Question | Trap |
|---|---|
| q1 | `COUNT(*)` and `IS NULL` tests on a NULL-extended row |
| q2, c5 | `NOT IN` with NULLs; for c5 the "corrective" condition belongs *inside* the anti-join |
| q3, c4 | several independent children under one parent |
| q4 | condition on the outer-joined table placed in `WHERE` |
| q5 | which rows the average is over; counting NULLs |
| q6 | row filter versus group filter; here the child grain is the right one |
| q7 | parent measure summed at child grain, plus rows lost to an inner join |
| c1 | counting orders after joining part lines |
| c2 | part lines versus distinct parts across a machine's orders |
| c3 | "every technician", including those who never appear in `work_orders` |

For the challenge key: a set of columns that is unique is not automatically the key you want.
Remove columns while it stays unique; what remains should read like the grain sentence.
