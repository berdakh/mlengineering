# LedgerLine late-payment ranking: evaluation report - reference

Numbers from `evaluate.py` in this directory, run 2026-11-21 on the committed SYNTHETIC table.

## 1. Framing

Each week the collections team calls 15 of the invoices issued that week. The unit of prediction is
the invoice, scored on its issue date, using only what the billing system knows that day. The label
`late` (unpaid 30 days after the due date) is decided 44 to 90 days after issue, so labels arrive
with a delay of up to three months. A call on a would-be-late invoice is useful; any other call is
wasted, and capacity is fixed, so the decision is a ranking *within each week* and the metric is the
share of called invoices that go late (precision among the weekly top 15). Probabilities need not be
calibrated for this decision; only the within-week order matters.

## 2. Leak audit

| Column | Known at issue time? | Reason | Used |
|---|---|---|---|
| `segment`, `industry`, `country` | yes | customer attributes | yes |
| `payment_terms_days`, `amount`, `issue_date`, `due_date` | yes | printed on the invoice | terms and amount yes; dates only for splitting |
| `prior_invoices` | yes | count of earlier invoices | no (adds nothing beyond the two below) |
| `prior_resolved_invoices`, `prior_late_invoices` | yes | by definition only outcomes decided before the issue date | yes, as a shrunk rate |
| `customer_late_rate` | **no** | master-table value at export (2025-03-15): the customer's late share over *all* invoices, including this one and later ones | no |
| `account_status` | **no** | master-table value at export; `on_hold` reflects late payments in the second half of 2024 | no |
| `reminders_sent` | **no** | reminders are sent after the due date | no |
| `days_to_payment` | **no** | the outcome itself; empty when unpaid | no |
| `invoice_id`, `customer_id` | yes, but | identifiers; `customer_id` as a feature would memorise customers and say nothing about new ones | no |

Evidence beyond the dictionary: `customer_late_rate` is constant within a customer across two years,
which a point-in-time rate cannot be; no invoice with zero reminders is late, and 2,341 of the 2,362
invoices with four or more reminders are.

## 3. Split

Test: the 1,844 invoices issued from 2024-10-01 (14 weekly blocks, the last one partial).
Train: the 8,032 invoices issued earlier **whose label was already decided on 2024-09-30**
(`due_date + 30 days < 2024-10-01`). The 1,212 invoices issued before October whose outcome was still
open are excluded: on the training day their labels did not exist. No customer-level grouping: the
model will be used on existing customers' new invoices, so customers on both sides is the deployment.
10.5 % of test invoices (193) come from customers absent from training.

## 4. Results

| Policy | Share of calls landing on late invoices | Interval |
|---|---|---|
| Calling at random (test prevalence) | 0.274 | - |
| Largest invoices first | 0.263 | - |
| Rule without a model: highest prior late rate `(late + 0.5) / (resolved + 2)` | 0.727 | - |
| Model: logistic regression on the usable columns | 0.722 | 0.651 to 0.783 |

209 calls on 80 distinct customers (one customer was called 12 times). The interval is a percentile
bootstrap resampling **customers**, because one customer's calls share that customer's payment habit
and are not independent; a row bootstrap gives 0.660 to 0.780, slightly narrower. It reflects which
customers happened to be called in this one quarter. It does not cover quarter-to-quarter change.

**The model does not beat the rule.** 0.722 against 0.727 is no difference. Both are far above
random. For reference, ranking by the generator's own probabilities gives 0.751 on this quarter, so
there is little room above the rule.

## 5. One error slice

Invoices with no resolved payment history (`prior_resolved_invoices == 0`): 135 of 1,844 test
invoices. Among them the model's ranking is worse than chance (AUC 0.37 on 135 invoices, against 0.78
on the rest), and **none** was ever among the weekly 15. New customers are invisible to this
policy. Next check: what share of late amount comes from first-quarter customers, and whether a small
reserved number of calls for new accounts is worth more than the 15th call on a known bad payer.
(One slice, chosen in advance because the main feature is undefined there; no slice search was run.)

## 6. Limitations and recommendation

* Synthetic data: effect sizes and the model-versus-rule tie say nothing about a real ledger.
* One test quarter, during a period when the late rate was rising (0.17 early 2023 to 0.27 in the test
  quarter). The interval does not cover that drift; a second, earlier cut-off would show stability.
* The evaluation measures *who goes late*, not *whether a call changes payment*. Calling the customers
  most certain to be late may be the least effective use of a call. Only a randomised hold-out of calls
  measures the effect.
* Calls concentrate on few customers (80). Twelve calls to one account in a quarter may be undesirable;
  a per-customer cap changes the metric.

Recommendation: adopt the prior-late-rate rule now; it needs no model and no maintenance. Do not
deploy the model on this evidence. Run a four-week randomised hold-out to learn whether calls change
payment at all, and decide what to do about accounts with no history.
