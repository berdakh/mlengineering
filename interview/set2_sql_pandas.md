# Interview set 2 - SQL and pandas

**Use on:** the Week 2 review day (`w2d7`). **Total time: 45 minutes, timer on.**
**Conditions (Weeks 1-2 level):** no hints, no solutions, no AI assistance. The SQLite and pandas
documentation are allowed. Rubrics and worked answers are in `solutions/interview/set2.md`: open
them only after all four answers are written.

Database: `diagnostic/data/streambox.db` (SQLite, **SYNTHETIC** subscription-service data; schema in
[`diagnostic/data/README.md`](../diagnostic/data/README.md)). Three tables: `customers` (one row per
customer), `invoices` (one row per charge attempt), `tickets` (one row per support ticket).
Being synthetic, the numbers mean nothing about a real business; only the correctness of your
queries is being exercised.

| # | Type | Time |
|---|---|---|
| S1 | SQL: join and aggregate with missing keys | 10 min |
| S2 | SQL: window functions | 10 min |
| S3 | SQL: month-over-month retention | 15 min |
| P4 | pandas: point-in-time feature | 10 min |

**For every SQL prompt, before writing the query, write one comment line stating the grain of the
result** ("one row per ..."). In an interview this sentence is worth as much as the query.

Write one `SELECT` statement per file (CTEs allowed) in `interview/work/set2/s1.sql`, `s2.sql`,
`s3.sql`, and the function in `interview/work/set2/p4.py`. Explore with
`python diagnostic/a2_sql/lab/explore.py "SELECT ..."`. When you consider an answer final:

```bash
python interview/set2_check.py            # all four
python interview/set2_check.py s2         # one prompt
```

Column names are not checked; column order is. Row order is checked only where the prompt asks for
an ordering. Numbers are compared after rounding as stated.

---

## S1 - Tickets by category and plan (10 min)

Support wants a breakdown of tickets by ticket `category` and by the `plan` of the customer who
opened them. Tickets opened without logging in have no customer; report their plan as `anonymous`.

Return: `category`, `plan`, `n_tickets`, `n_open` (tickets with no `resolved_at`),
`avg_resolution_hours` (mean hours from `opened_at` to `resolved_at` over resolved tickets, rounded
to 1 decimal; NULL if the group has no resolved ticket).

## S2 - Third paid invoice (10 min)

For every customer who has at least three `paid` invoices, return their **third** paid invoice in
time order (`invoice_date`, ties broken by `invoice_id`), with the cumulative amount they had paid
up to and including it.

Return: `customer_id`, `invoice_id`, `invoice_date`, `cumulative_paid` (rounded to 2 decimals).

## S3 - Monthly billing and retention, 2025 (15 min)

For each calendar month of 2025 return one row, **ordered by month ascending**:

* `month` as `YYYY-MM`
* `n_billed`: number of distinct customers with at least one invoice of any status in that month
* `n_paid`: number of distinct customers with at least one `paid` invoice in that month
* `n_retained`: number of distinct customers with a `paid` invoice in that month **and** a `paid`
  invoice in the immediately preceding calendar month

Look at the data before trusting a first draft: a customer can have more than one invoice in a
month, and the month before January 2025 exists in the table.

## P4 - Point-in-time ticket counts in pandas (10 min)

Implement in `interview/work/set2/p4.py`:

```python
def tickets_90d(tickets: pd.DataFrame, snapshots: pd.DataFrame) -> pd.Series:
    """tickets:   columns customer_id (may be missing), opened_at (datetime64)
    snapshots: columns customer_id, snapshot_date (datetime64); any index; a customer may appear
               in several rows with different snapshot dates.
    Returns an integer Series aligned to snapshots.index: the number of that customer's tickets with
        snapshot_date - 90 days <= opened_at < snapshot_date
    """
```

Requirements: no information from on or after `snapshot_date` may be counted; snapshot rows with no
matching ticket get 0; the result has exactly one value per snapshot row, in the same order and with
the same index, whatever that index is; the inputs are not modified. Avoid a Python loop over
snapshot rows.

After coding, answer in one sentence: why is the interval closed on the left and open on the right,
and which side matters for leakage?

---

## Log it

```bash
python wb.py note w2d7 "set2: S1 <t> <ok?>, S2 <t> <ok?>, S3 <t> <ok?>, P4 <t> <ok?>; error pattern: ..."
```
