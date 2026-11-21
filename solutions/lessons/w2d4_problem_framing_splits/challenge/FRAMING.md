# Framing: StreamBox retention calls (reference answer)

SYNTHETIC scenario. Assumptions are marked **[assumed]**.

## Decision supported

Each month the retention team chooses **which 5 % of active subscribers to phone** with an offer.
Today they call by a rule of thumb **[assumed: lowest usage first]** or not at all. The model changes
the *ranking* of whom to call; capacity is fixed, so the decision is a top-k selection, not a yes/no
per customer.

## Unit of prediction

One score per **active customer per monthly snapshot**. The unit of generalisation is two-fold:
*future months* (always) and *customers not seen in training* (new sign-ups), which is why the split
reports `test_known` and `test_new` separately.

## Prediction time and horizon

Scored at the end of month *m* using only information available then; the target is cancellation
during months *m+1 ... m+3*. Three months because a call needs lead time and because one month gives
too few positives; the cost is that labels mature three months late, which delays every evaluation
and removes the three most recent months from training.

## Label definition

`churn_within_3m = 1` if a cancellation is recorded in the three months after the snapshot. Sources of
trouble: (1) **right-censoring** - positives are known as soon as they happen, negatives only after
three months, so recent rows with a known label are almost all positives; (2) involuntary churn
(failed payment) is mixed with voluntary churn unless billing data separates them **[assumed: not
separated]**; (3) once the team starts calling, the label is contaminated by the intervention -
customers who were saved look like model errors.

## Cost of errors

* **False positive** (call someone who would have stayed): the call **[assumed: about 4 currency
  units]** plus a discount given away unnecessarily.
* **False negative** (no call, customer leaves): lost margin over the remaining lifetime **[assumed:
  roughly 60]**, discounted by the chance a call would have worked **[assumed: 20-30 %]**.
* What is really wanted is *uplift* (who stays **because** of the call); churn probability is a proxy
  and can rank "lost causes" first. Stated as a limitation, to be tested with a hold-out group that is
  never called.

## Constraints

Monthly batch scoring, no latency pressure. Only features present in the month-end export. The team
needs a reason per call ("usage fell by half") to hold the conversation. Capacity of 5 % is fixed.
Offers must not depend on protected attributes.

## Success metrics

1. Business: retained margin net of call and discount cost, measured against a randomly selected
   **control group that is not called**.
2. Offline proxy matched to the decision: **precision and recall in the top 5 %** of each monthly
   snapshot (equivalently lift at 5 %), averaged over test months, reported separately for known and
   new customers.
3. Development metric: average precision. ROC-AUC is reported but not optimised; it weights the whole
   ranking equally and the team only acts on the top.

## Baseline

* No model: call 5 % at random; precision equals the base rate (about 16 % in this table).
* A rule: lowest `usage_hours` first, ties broken by `basic` plan. If a model does not beat this rule
  by more than month-to-month variation, ship the rule.

## Splits

Temporal and grouped. With `test_start = 2025-01` and a three-month horizon: **train** on snapshots up
to 2024-09 (the last month whose label window closed before 2025-01), **test** on 2025-01 to 2025-03
(the last months whose window is fully inside the data). 2024-10 to 2024-12 are unusable for either: a
purge gap equal to the horizon. 20 % of trainable customers are withheld from training; `test_new` also
contains everyone who joined too late to have a training row. On the supplied file: train 596 rows /
147 customers, test_known 266 rows / 94 customers, test_new 297 rows / 125 customers.

## Out of scope

Choosing the offer, estimating causal uplift (needs a randomised hold-out), price changes, and any
claim about real subscribers: the table is simulated.

## Part C: one number

Churn rate of the proper test rows (2025-01 to 2025-03): **0.163** (563 rows). "Rows from 2025-01 on
with a non-missing label": **0.199** (588 rows). The second set silently adds the 25 rows from
2025-04 and 2025-05 whose label is known *because* the customer already cancelled; all of them are
positives. Selecting rows by label availability selects on the outcome.
