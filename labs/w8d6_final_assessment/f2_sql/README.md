# f2 - SQL: joins, aggregation, window functions (parallel form of a2)

**Time box: 35 minutes.** Sitting A, section 2 of 3. No hints; SQLite documentation is fine.

Database: `labs/w8d6_final_assessment/data/parcelo.db` (SQLite, **synthetic**). Schema and column
meanings are in [`../data/README.md`](../data/README.md). Dates are ISO-8601 text (`YYYY-MM-DD`), so
string comparison orders them correctly.

Write **one `SELECT` statement per file** (CTEs are fine) in `lab/q1.sql` ... `lab/q5.sql`. Return the
columns in the order given. Column names and row order are not checked; amounts are compared to 2 decimals.

| File | Question | Columns |
|---|---|---|
| `q1.sql` | For shipments dated in 2025 with status `delivered`: per account region, how many distinct accounts shipped and the total fee. Accounts with no recorded region are reported as `UNKNOWN`. | region, n_shipping_accounts, total_fee |
| `q2.sql` | Accounts that signed up in 2025 and have never filed a complaint. | account_id |
| `q3.sql` | For every account on the `enterprise` tier: total fee of their `delivered` shipments (all time) and number of complaints (all time). Accounts with none of either appear with 0. | account_id, total_delivered_fee, n_complaints |
| `q4.sql` | Accounts whose **most recent** shipment has status `lost`. Most recent = latest `ship_date`; if several share that date, the one with the highest `shipment_id`. | account_id, shipment_id, ship_date |
| `q5.sql` | Monthly `delivered` fee for 2025 and the change versus the previous month (NULL for the first month). | month (`YYYY-MM`), total_fee, change_vs_prev |

Before trusting a query, look at the data: at least two of these questions have an obvious query that
runs without error and returns a wrong answer.

## Work and check

```bash
python labs/w8d6_final_assessment/f2_sql/lab/explore.py                  # list tables
python labs/w8d6_final_assessment/f2_sql/lab/explore.py "SELECT * FROM complaints LIMIT 5"
python labs/w8d6_final_assessment/f2_sql/lab/explore.py q3.sql           # run your file

python wb.py check labs/w8d6_final_assessment/f2_sql     # or:
python -m pytest labs/w8d6_final_assessment/f2_sql/checks -q
```

The starter files fail every check.

## Acceptance criteria

* All five checks pass.
* In `../SUBMISSION.md`, one line per query: what a plausible wrong version would have returned, and why.

## Submit

`lab/q1.sql` ... `lab/q5.sql` and the time used.
