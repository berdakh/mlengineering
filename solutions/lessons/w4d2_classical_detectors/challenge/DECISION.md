# Fraud scoring under label scarcity — decision (w4d2 challenge) — REFERENCE

Numbers from the authoring run on the shipped data (generator seed 20261122; SYNTHETIC).

## Features

amount, hour, distance_km, merchant_risk, online, n_tx_24h, card_age_days. Excluded: `customer_id`,
`tx_id` (identifiers, meaningless for new customers) and `label`. card_age_days is kept because it is
available at authorisation time, but it is constant per customer, which turns it into an account
identifier for a flexible model: the GBT fitted on the labelled rows puts most of its permutation
importance on it (0.50 of AP on the training rows, against 0.14 for distance and 0.11 for velocity).

## Validation scheme

Labels come from reviewing whole accounts: 81 of 1,500 customers, 2,907 rows, 39 frauds from only
5 customers. Next quarter's customers are new. So every estimate is out-of-fold with folds grouped by
customer (5-fold GroupKFold), on the labelled rows. The isolation forest is fitted on all rows of the
training-fold customers (it needs no labels); the GBT on their labelled rows.

| estimate of AP on new customers | isolation forest | GBT |
|---|---|---|
| grouped by customer (used) | 0.276 | 0.042 |
| random row folds (not used) | 0.290 | 0.685 |
| in-sample (not used) | 0.265 | 1.000 |
| actual, `transactions_test.csv` (looked at once, at the end) | 0.282 | 0.159 |

## Choice

Isolation forest (0.276 against 0.042). The GBT has five fraudulent accounts to learn from; with
customer-grouped folds most folds hold one or two of them, and what it learns about those accounts
(their card age, above all) does not transfer to new customers. Random row folds put each fraudulent
account on both sides of the split and report 0.685 for a model whose real AP is 0.159 — the
cross-subject lesson in a payments setting. The grouped estimate is pessimistic for the GBT (0.042 vs
0.159), because each fold trains on fewer fraudulent accounts than the final model; it is still the
right ranking.

## Next quarter

Expected AP about 0.28 at a fraud prevalence of about 3% (a precision-recall curve about nine times the
no-skill level), with the uncertainty of an estimate built on 5 fraudulent accounts: on four other
generator seeds the same procedure's estimate and the new-customer AP differed by 0.01-0.06. It would be
wrong if fraud patterns shift (the forest flags unusual transactions, not fraud; a new pattern that
looks ordinary is invisible), if the population of genuine customers changes (travel season raises
`distance_km` for everyone), or once many more accounts are reviewed — at that point the supervised
model should be re-evaluated, with the same grouped scheme.
