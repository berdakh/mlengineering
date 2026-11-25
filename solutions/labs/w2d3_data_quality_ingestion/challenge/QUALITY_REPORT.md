# Quality report: `orders_export.csv` (reference; SYNTHETIC data)

To: orders team. From: demand-model pipeline. File: 579 rows, 576 distinct `order_id`,
order dates 2025-09-01 to 2025-09-30. Produced by `order_quality.py`; nothing was repaired.

**Decision for tonight:** the file is **not ingested**. Eight contract rules are violated, by 40
distinct order ids in total; the model keeps yesterday's table and that staleness is flagged on our side.

## Contract violations (errors)

| Rule | Rows | Examples | What we think happened / what we need |
|---|---|---|---|
| `order_id` unique | 6 rows, 3 ids | ORD-100153, ORD-100164, ORD-100424 | Exact duplicate rows: looks like a batch sent twice. Please confirm and re-export. |
| `order_ts` format | 3 | ORD-100450, ORD-100090, ORD-100023 | `DD/MM/YYYY HH:MM` instead of ISO UTC. Is a regional system bypassing the formatter? Are these local times? |
| `currency` allowed | 9 | ORD-100244, ORD-100545 | 6 lower-case codes (`usd`, `eur`, `kzt`) and 3 `GBP`. Is GBP a new market (contract change) or an error? |
| `amount` positive number | 9 | ORD-100374, ORD-100284 | 4 negative amounts; 5 with a decimal comma (`57,63`). Are negatives refunds booked as orders? |
| refund within amount | 8 | ORD-100065, ORD-100403 | 4 refunds larger than the order; the other 4 are the negative-amount rows again. |
| `status` allowed | 3 | ORD-100461, ORD-100053, ORD-100176 | `returned` is not in the contract. New status? |
| `delivered_ts` iff delivered | 8 | ORD-100000, ORD-100421 | 5 delivered orders without a timestamp; 3 are the `returned` rows carrying one. |
| delivery not before order | 4 | ORD-100439, ORD-100503 | Delivered about 7 hours before ordering: a time-zone conversion on one of the two columns? |

Full id lists are in the checker output. A row with an unparseable `amount` is reported under the
amount rule only; the refund rule is not evaluated for it.

## Batch-level signals (warnings; no single row is wrong)

- **Guest checkouts: 6.9 % of orders (40 of 579)**, against a contract expectation of 1–2 % and a
  limit of 5 %. This points at login or identity, not at the export. Who owns that?
- **No orders at all on 2025-09-17.** By your own statement the shop sells every day, so a batch
  appears to be missing. Can it be re-sent?

## What we will not do

We will not lower-case currencies, swap decimal marks, drop duplicates or shift timestamps on our
side. Each of those would make tonight's file load and hide the cause; several would guess wrongly
(for example, whether `DD/MM` timestamps are UTC).
