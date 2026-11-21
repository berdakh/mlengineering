# a2 - SQL: joins, aggregation, window functions

**Time box: 35 minutes.** Session A, section 2 of 3. No hints; SQLite documentation is fine.

Database: `diagnostic/data/streambox.db` (SQLite, **synthetic**). Schema and column meanings are in
[`../data/README.md`](../data/README.md). Dates are ISO-8601 text (`YYYY-MM-DD`), so string comparison
orders them correctly.

Write **one `SELECT` statement per file** (CTEs are fine) in `lab/q1.sql` ... `lab/q5.sql`. Return the
columns in the order given. Column names and row order are not checked; amounts are compared to 2 decimals.

| File | Question | Columns |
|---|---|---|
| `q1.sql` | For invoices dated in 2025 with status `paid`: per customer country, how many distinct customers paid and how much revenue. Customers with no recorded country are reported as `UNKNOWN`. | country, n_paying_customers, revenue |
| `q2.sql` | Customers who signed up in 2025 and have never opened a support ticket. | customer_id |
| `q3.sql` | For every customer on the `premium` plan: total amount of their `paid` invoices (all time) and number of support tickets (all time). Customers with none of either appear with 0. | customer_id, total_paid, n_tickets |
| `q4.sql` | Customers whose **most recent** invoice has status `failed`. Most recent = latest `invoice_date`; if several share that date, the one with the highest `invoice_id`. | customer_id, invoice_id, invoice_date |
| `q5.sql` | Monthly `paid` revenue for 2025 and the change versus the previous month (NULL for the first month). | month (`YYYY-MM`), revenue, change_vs_prev |

Before trusting a query, look at the data: at least two of these questions have an obvious query that
runs without error and returns a wrong answer.

## Work and check

```bash
python diagnostic/a2_sql/lab/explore.py                      # list tables
python diagnostic/a2_sql/lab/explore.py "SELECT * FROM tickets LIMIT 5"
python diagnostic/a2_sql/lab/explore.py q3.sql               # run your file, print first rows

python wb.py check diagnostic/a2_sql                         # or:
python -m pytest diagnostic/a2_sql/checks -q
```

The starter files fail all checks; that is expected.

## Acceptance criteria

* Each query returns exactly the expected set of rows.
* You can say, for each query, what a wrong-but-plausible version would have returned and why
  (one line each in `SUBMISSION.md`).

## Submit

The five `.sql` files and time used.
