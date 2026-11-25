# Independent challenge: fraud scores with scarce, account-level labels

No walkthrough. Hints are in [`../hints/`](../hints/); try without them first.

## Situation

A payments team has a year of card transactions for 1,500 customers. Fraud review is expensive: an
analyst reviews whole *accounts*, and about 5% of the accounts have been reviewed, so about 5% of the
training rows carry a label (`label` = 1 fraud, 0 genuine, NaN unreviewed). Next quarter the model will
score transactions of **new customers**. The team wants to know whether an unsupervised isolation forest
or a supervised gradient-boosted model is the better choice, and how good the chosen one will be.

Generate the data (SYNTHETIC; read the generator's docstring):

```bash
python labs/w4d2_classical_detectors/challenge/data/make_transactions.py
```

This writes `transactions_train.csv` (labels mostly missing) and `transactions_test.csv` (new customers,
fully labelled). Treat the test file as next quarter: look at it once, at the end.

## Task

Implement `run(train, seed=0)` in `fraud.py`. It returns the choice, an estimate of next quarter's
average precision for **each** method, and the chosen model fitted on the training data. Every decision
(features, validation scheme, which rows each model may use) is yours; defend them in `DECISION.md`.

## Acceptance criteria

Automated (`python wb.py check w4d2 --challenge`), on data the checks generate with an unseen seed:

* the returned structure is as documented and the choice follows your estimates;
* your estimate for the chosen method is within 0.12 of its average precision on new customers;
* scores do not depend on `customer_id` or `tx_id`; `score` works on frames without `label`;
* the procedure is deterministic given `seed`;
* the chosen model's average precision on new customers is at least 0.2 (prevalence is about 0.03).

Rubric for `DECISION.md` (self-scored against the reference after you finish): the validation scheme is
justified from how labels were produced; the gap between the two methods is explained, not just
reported; the claim about next quarter states its uncertainty and the conditions under which it fails.

## Time

60-90 minutes.
