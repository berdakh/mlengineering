# f2_sql - reviewer notes (parallel form of a2)

Same traps as a2, in a new schema, so a1/a2 and f1/f2 can be compared aspect by aspect.

| Query | Trap | What the plausible wrong query returns |
|---|---|---|
| q1 | grain: "how many accounts" is distinct accounts, not shipment rows; NULL region must be labelled | `COUNT(*)` gives shipment counts (several times larger); `GROUP BY region` alone puts NULL accounts in a NULL group the reader cannot interpret |
| q2 | `NOT IN` with a NULL in the subquery | zero rows, because 50 web-form complaints have `account_id` NULL |
| q3 | fan-out when joining two one-to-many tables | fees multiplied by the number of complaints, complaint counts multiplied by the number of shipments |
| q4 | ties on the latest date | accounts whose lost parcel was re-shipped the same day (the re-shipment has the higher id and was delivered) are wrongly listed |
| q5 | window over an aggregate | correct with `LAG` over a monthly CTE; a self-join on month strings works too |

## Rubric (assign per aspect)

| Aspect | Demonstrated independently | Partial | Not yet demonstrated |
|---|---|---|---|
| Joins and aggregation | q1, q3 correct; grain stated for each | correct only after check feedback, no grain statement | q1 or q3 wrong |
| NULL semantics | q2 with `NOT EXISTS` or `LEFT JOIN ... IS NULL`, and the NULL cause named | correct without explanation | `NOT IN` |
| Fan-out | q3 pre-aggregates, and SUBMISSION.md explains the multiplication | correct via `DISTINCT` patches that happen to work for counts but not sums | wrong totals |
| Window functions | q4 with `ROW_NUMBER` and the tie-break; q5 with `LAG` | one of the two | neither |
