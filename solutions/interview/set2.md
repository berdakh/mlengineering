# Interview set 2 - rubrics and model answers

Open after attempting. Reference answers: `solutions/interview/set2/` (`s1.sql`, `s2.sql`, `s3.sql`,
`p4.py`). Deliberately wrong answers that the checker rejects: `solutions/interview/set2_wrong/`.

Verified in the authoring session (Python 3.13.18, pandas 3.0.5, SQLite 3.53.1):
`python interview/set2_check.py --dir solutions/interview/set2` prints `[ok]` for all four prompts
(about 2 s). Every wrong answer below was run through the checker and rejected.

The data is **synthetic**; the result values quoted here are properties of the simulation only.

Evidence levels per prompt: **Demonstrated** (correct, grain stated first, within time, unaided),
**Partial**, **Not yet**.

## The habit being tested: say the grain first

For each query, the first thing written should be "one row per ...". Then every join is checked
against it: does this join multiply rows of my grain (fan-out) or drop them (inner join on a nullable key)?

## S1 - tickets by category and plan

Grain: one row per (category, plan), where plan includes the pseudo-value `anonymous`.
Reference result: 13 rows (12 category-plan pairs plus one anonymous group in the simulation).

Key decisions
* `LEFT JOIN customers`: `tickets.customer_id` is nullable, and an inner join drops those 60 tickets
  without any error.
* `COALESCE(c.plan, 'anonymous')` in both the select list and the `GROUP BY`.
* `AVG` ignores NULLs, so averaging the duration expression over all rows already restricts to resolved
  tickets; `n_open` needs an explicit count of NULLs (`SUM(resolved_at IS NULL)` or
  `COUNT(*) - COUNT(resolved_at)`).
* SQLite has no interval type: `(julianday(b) - julianday(a)) * 24` gives hours.

| Common incorrect answer | Why it fails |
|---|---|
| Inner join (`set2_wrong/s1_inner_join`) | 12 rows instead of 13; anonymous tickets vanish. The query "looks right" and the totals are only 6 % low, which is exactly why it survives review |
| `COUNT(resolved_at)` reported as `n_open` | Counts resolved, not open |
| Grouping by `c.plan` and renaming NULL afterwards in the client | Works by accident in some tools; the contract says the query returns `anonymous` |
| `WHERE t.resolved_at IS NOT NULL` to compute the average | Removes open tickets from `n_tickets` and `n_open` as well: a filter applies to the whole row set, not to one aggregate. Use `AVG(...)`'s NULL handling or `AVG(CASE ...)` / `FILTER` |

## S2 - third paid invoice

Grain: one row per customer with at least three paid invoices (832 customers in the simulation).

Key decisions
* Filter `status = 'paid'` **before** the window function (in the CTE's `WHERE`), because the ordinal
  and the running total are both defined over paid invoices.
* Deterministic ordering: `ORDER BY invoice_date, invoice_id`. Without the tie-breaker `ROW_NUMBER`
  is arbitrary among equal dates.
* Explicit frame `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`. The default frame with `ORDER BY`
  is `RANGE ... CURRENT ROW`, which includes all *peers* (rows with equal sort keys); with a unique
  sort key the two agree, but stating `ROWS` removes the dependency on that.
* A window function cannot be referenced in `WHERE` of the same query level, hence the CTE.

| Common incorrect answer | Why it fails |
|---|---|
| Number all invoices, then `WHERE rn = 3 AND status = 'paid'` (`set2_wrong/s2_rank_all_invoices`) | Returns the third invoice *if it is paid*: 778 rows instead of 832, and the running sum includes failed and refunded amounts |
| `ORDER BY invoice_date` only | Non-deterministic under ties; passes on this data only if no customer has two paid invoices on one date, which is a property of the data you did not check |
| `GROUP BY customer_id HAVING COUNT(*) >= 3` with `MIN`/`MAX` tricks | Cannot return "the third" row |
| `RANK()` instead of `ROW_NUMBER()` | With ties, rank 3 may be missing or duplicated |

## S3 - monthly billing and retention

Grain: one row per month of 2025 (12 rows). Reference first row: `('2025-01', 651, 629, 562)`.

Structure of a correct answer
1. Reduce to **one row per (customer, month)** first, with a flag "had a paid invoice". This removes the
   fan-out from same-day retries (402 customer-days have more than one invoice).
2. Compute "paid in the previous calendar month" **before** restricting to 2025, so January 2025 can see
   December 2024.
3. Aggregate to months and order.

Equivalent formulations: a self-join of the customer-month table on the previous month; or
`LAG(month) OVER (PARTITION BY customer_id ORDER BY month)` on paid customer-months compared with the
expected previous month (not merely "the previous row", since a customer can skip a month).

| Common incorrect answer | Why it fails |
|---|---|
| `COUNT(*)` on invoice rows (`set2_wrong/s3_count_invoice_rows`) | `n_billed` for January is 670 instead of 651: retries are counted as customers. `COUNT(DISTINCT customer_id)` or the pre-aggregation fixes it |
| Filtering to 2025 before the look-back (`set2_wrong/s3_filter_before_lookback`) | January `n_retained` = 0 instead of 562. The filter-then-window order is the single most common window-function error |
| `LAG` over paid months, treating the previous *row* as the previous *month* | A customer who paid in March and May is counted as retained in May |
| Computing the previous month by string arithmetic on `YYYY-MM` | Breaks at year boundaries (`2025-01` minus 1) |
| Joining invoices to invoices on customer and "previous month" without de-duplicating | Fan-out on both sides; `COUNT(*)` then counts pairs of invoices |

Interview note: state aloud that "retained" needs a definition (paid in consecutive calendar months
here); real definitions vary (active on a day, any activity in a trailing window) and the difference
changes the number materially.

## P4 - point-in-time ticket counts

Model answer: merge snapshots (with a positional row id) to tickets on `customer_id`, filter pairs by
the half-open window, count per row id, reindex to all rows with 0, restore the caller's index.
See `set2/p4.py`.

**Must**
* `opened_at < snapshot_date` strictly. A ticket opened at or after the snapshot instant is not
  available when the prediction is made; including it is temporal leakage. The left edge only
  determines the window length; the right edge determines whether the feature can be computed in production.
* One value per snapshot row, same order, same index, zeros filled.
* Robust to a non-unique, unordered index (do not `groupby` on the index; create a row id).
* Tickets without a customer are ignored; inputs are not mutated.

**Should**
* Mentions cost: the merge materialises all (snapshot, ticket) pairs per customer; fine here, but for
  large tables one would sort and use two `searchsorted` calls per customer or `pd.merge_asof` on
  cumulative counts.
* One-sentence answer: closed left / open right makes consecutive windows tile without overlap or gaps;
  the open right edge is the one that prevents leakage.

| Common incorrect answer | Why it fails |
|---|---|
| `<=` on the snapshot side (`set2_wrong/p4_includes_snapshot_day`) | Counts a ticket opened exactly at the snapshot instant: 3 instead of 2 in the boundary case. With date-only snapshots this silently includes the whole snapshot day in systems that truncate timestamps |
| `groupby(['customer_id', 'snapshot_date']).size()` returned directly (`set2_wrong/p4_drops_zero_rows`) | Rows with zero tickets disappear, duplicate snapshot rows collapse, index no longer aligned; a later `df['f'] = result` then misaligns or yields NaN |
| `snapshots.apply(lambda row: ..., axis=1)` | Correct but O(rows x tickets) in Python; the prompt asks to avoid it. Acceptable as a first draft if you say so and then vectorise |
| Filtering tickets to "before the latest snapshot" globally | Uses one cut-off for all rows; early snapshots then see later tickets |
| Modifying `snapshots` in place (adding a helper column) | Violates "inputs are not modified"; the caller's frame changes shape |

Connection to the course: this is the same construction as the `tickets_90d` column of the
diagnostic's churn snapshots and as causal rolling features on sensor data (w2d5): a feature for time
`t` may use only data strictly before `t` (or up to and including `t` when the current sample is
legitimately available, which must be decided and written down per feature).
