# W2D3 independent challenge — a checker and a quality report for an orders export

**Time:** 45 min (10 in the essential path to start, the rest in the optional extension).
**Data:** `challenge/data/orders_export.csv` — **SYNTHETIC**, an invented web shop. It demonstrates
the task; nothing about any real business follows from it.
**Conditions for the `independent` flag:** no hints, no solutions folder, pandas documentation allowed.

## Situation

The orders team sends a nightly export that will feed a demand model. They have given you this
data contract. Your job is the gate in front of the model, and a report they can act on.

### Data contract (as written by the orders team)

The file is CSV, comma-separated, UTF-8. Read it as text:
`pd.read_csv(path, dtype=str, keep_default_na=False)` (an empty string means "not provided").

| Column | Rule |
|---|---|
| `order_id` | Present on every row and unique. |
| `customer_id` | May be empty for guest checkout. Guest checkouts are normally 1–2 % of orders; **above 5 % something is wrong with login, not with a row**. |
| `order_ts` | UTC instant, exactly `YYYY-MM-DDTHH:MM:SSZ`. |
| `currency` | Exactly one of `USD`, `EUR`, `KZT`. |
| `amount` | A number greater than zero, decimal point. |
| `refunded_amount` | A number, at least zero and at most `amount`. |
| `status` | One of `placed`, `shipped`, `delivered`, `cancelled`. |
| `delivered_ts` | Same format as `order_ts`. Present **if and only if** `status` is `delivered`, and never earlier than `order_ts`. |

One more expectation from the team: the shop takes orders every day, so **a calendar day with no
orders inside the exported range means a lost batch**, not a quiet day.

## Task

1. Implement `run_checks(orders)` in `challenge/order_quality.py`. It returns a list of result
   objects, each with attributes `name`, `passed`, `severity` (`"error"` or `"warning"`) and
   `detail` (define your own class).
2. Decide the severity of every rule and be ready to defend it.
3. Run it on the export and write `challenge/QUALITY_REPORT.md` for the orders team (at most one
   page): what is wrong, how many rows, examples, what you need from them, and what you will do
   with tonight's file.

```bash
python lessons/w2d3_data_quality_ingestion/challenge/order_quality.py lessons/w2d3_data_quality_ingestion/challenge/data/orders_export.csv
python wb.py check w2d3 --challenge
```

## Acceptance criteria

Automated (22 checks, on freshly generated synthetic tables, not on the shipped file):

- A table that satisfies the contract passes every check.
- Each contract violation planted in one row fails an **error** check whose `detail` contains that
  row's `order_id`, and no failing detail names an unaffected order.
- An unusual guest share and a day without orders each fail a **warning** check and nothing else;
  the lost day is named.
- Several violations of different rules are all reported in one run.
- A missing column is reported, not raised; unparseable values and an empty table never raise.
- The input frame is not modified.

By rubric (see `assessment.md`, question 5):

- `QUALITY_REPORT.md` separates defects by rule with counts and example ids, distinguishes "your
  export is wrong" from "something upstream of you looks wrong", states one decision about tonight's
  file, and contains no repair that was applied silently.
