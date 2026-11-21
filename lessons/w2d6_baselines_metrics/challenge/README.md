# w2d6 challenge - transfer exercise, part 1: who gets the retention offer?

**Independent work. About 60 minutes.** No hints unless you are stuck for more than 10 minutes; if you
open one, record the work as guided.

## Data note (read once)

The plan for this exercise was a public business dataset (UCI Bank Marketing). On 2026-11-21 the UCI
repository (`archive.ics.uci.edu`: dataset page, static zip and API) was unreachable from the authoring
environment, so **neither access nor licence terms could be verified, and the dataset is not used.**
The exercise runs on the course's **SYNTHETIC** StreamBox churn snapshots instead
(`diagnostic/data/churn_train.csv`, `churn_test.csv`; schema in
[`diagnostic/data/README.md`](../../../diagnostic/data/README.md)).

What this substitution costs: the data is simulated, so nothing you find is evidence about real
customers, realistic effect sizes, or which model family is better. What it keeps: the task is
unfamiliar relative to your research domain, the table has missing values, categories, repeated
customers and time order, and the decision logic is the real one. A real-data sitting replaces or
supplements this when the dataset's terms have been verified.

This is a different task from diagnostic b1 on the same files. There you ranked customers for a fixed
phone budget. Here there is no budget.

## Situation

StreamBox finance has approved a retention **discount offer**:

* Sending the offer to a customer costs **4.00 USD**, whether or not they would have churned.
* Past campaigns suggest the offer keeps **25 %** of customers who would otherwise have churned in the
  next 30 days. This is an assumption supplied by the business, not something in the data.
* A retained customer is worth **6 months** of their `monthly_price`.

On each snapshot date, decide per customer whether to send the offer. Finance wants to know the
expected net value per 1,000 active customers and how sure you are.

## Task

Implement the functions in `challenge/offer_policy.py` (signatures and return structures are fixed in
the docstrings) and write `challenge/DECISION.md` (template provided, one page).

1. `temporal_fit_validation_split` - carve validation months out of the training file.
2. `churn_probabilities` - a first, defensible probability model. Your choice of model and features.
3. `brier_score`, `reliability_table` - instruments to check that your probabilities mean something.
4. `offer_threshold` - the per-customer break-even churn probability implied by the costs above.
5. `policy_value` - the value of any offer policy under the stated assumptions.
6. `run` - compare four policies on the test months: nobody, everybody, a prevalence-only forecast, your model.

## Acceptance criteria

* `python wb.py check w2d6 --challenge` passes (11 checks).
* Your probabilities average to the churn rate on the data they were fitted on, and beat the
  prevalence forecast in Brier score on the test months.
* `DECISION.md` states: the recommendation in finance's terms; the evidence; whether calibration held
  on the *test* months and what you would do about it; the sensitivity of your policy's value to the
  assumed success rate (at least 0.125 and 0.5); what this analysis cannot establish and which
  experiment would.
* Nothing depends on test labels except the final evaluation. Thresholds come from costs, not from
  searching on test data.

## What is deliberately not specified

Which model; which features; how to handle missing values and categories; whether to recalibrate;
how to present uncertainty. Decide, and defend the decisions in the note.

## Submit

`challenge/offer_policy.py`, `challenge/DECISION.md`, time used, hints opened (if any).
