# W2D4 independent challenge: frame and split a churn problem

**Time:** 40-50 min, unassisted. Hints exist ([1](../hints/hint1_concept.md), [2](../hints/hint2_approach.md),
[3](../hints/hint3_partial.md)); using one means the `independent` flag stays unset for this unit.
**Data:** `customer_months.csv` in this directory - SYNTHETIC (generator:
`../checks_challenge/customer_months.py`). It supports conclusions about your split logic only.

## The brief (as a product manager would write it)

> "StreamBox loses subscribers every month. Retention can phone about 5 % of active subscribers a
> month with an offer. Tell us who to call. We export a snapshot of every active subscriber at the end
> of each month; a model would be refreshed at month end and used during the following months.
> Marketing also wants to know whether it works for people who signed up recently."

## The table

One row per customer per month in which the customer was active (2,386 rows, 300 customers,
2024-01 to 2025-06).

| Column | Meaning |
|---|---|
| `customer_id` | subscriber |
| `month` | snapshot month, `YYYY-MM`; features describe the customer at the end of this month |
| `tenure_months`, `plan`, `usage_hours`, `support_tickets` | features known at the end of `month` |
| `churn_within_3m` | 1 if the customer cancels during one of the **three months after** `month`, else 0 |

Read this twice: a cancellation is recorded the moment it happens, so a `1` can be known long before
the three months are over; a `0` can only be known once all three months have passed. In the last
snapshots the label is therefore either `1` or missing.

## Part A - framing (written, rubric-graded)

Fill in `FRAMING.md` (same ten headings as the lab's problem statement). One page. Take positions:
what is the decision, what is the unit, when is the prediction made and about what period, what do
the two error types cost, what is the business metric and which offline metric stands in for it, what
is the baseline that needs no model, and what would make you refuse to ship.

## Part B - the split (automatically checked)

Implement in `churn_splits.py`:

```python
split_customer_months(df, test_start, horizon_months=3, new_customer_fraction=0.2, seed=0)
    -> {"train": [...], "test_known": [...], "test_new": [...]}     # labels from df.index
```

The situation to emulate: the model is trained at the end of the month before `test_start` and then
scores the monthly snapshots from `test_start` onwards.

Acceptance criteria

1. **Train** contains only rows whose outcome was fully known when the model was trained.
2. **Test** rows are snapshots from `test_start` onwards whose outcome is fully observable in the
   data; every such row is in exactly one of `test_known` / `test_new`. Rows must not be selected by
   whether the label happens to be filled in.
3. `new_customer_fraction` of the customers who *could* have been trained on are withheld from
   training entirely, chosen reproducibly from `seed`.
4. `test_known` = test rows of customers with at least one training row; `test_new` = test rows of
   customers with none (for whatever reason).
5. No usable training row of a training customer is discarded.
6. Deterministic for a given seed; the input frame is not modified; works for any `horizon_months`
   and for a frame whose index is not `0..n-1`.

```bash
python wb.py check w2d4 --challenge
```

## Part C - one number (put it at the end of `FRAMING.md`)

Compute the churn rate of your test rows, and the churn rate you would have reported had you built
the test set as "rows from `test_start` on where the label is not missing". Explain the difference
in two sentences.
