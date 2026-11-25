# f4_baseline - reviewer notes (parallel form of b1)

## Reference numbers (SYNTHETIC; executed 2026-11-22 with the reference `lab/baseline.py`)

Train 3,168 rows (Jan-Aug 2025 snapshots, lapse rate 11.2 %), test 1,065 rows (Sep-Dec 2025).

| Baseline | Average precision | Precision at 8 % | Recall at 8 % |
|---|---|---|---|
| trivial (constant train rate) | 0.129 (= prevalence) | 0.140 | 0.088 |
| heuristic (lost parcels + complaints, then few shipments) | 0.197 | 0.198 | 0.124 |
| logistic regression, preprocessing in a pipeline | 0.225 | 0.279 | 0.175 |

The trivial baseline's precision at 8 % is arbitrary (ties broken by row order); its AP equals the
prevalence by construction. 86 calls a month find about 24 lapsing accounts with the model, 17 with
the heuristic, 12 at random. Synthetic: says nothing about real accounts.

## Strong written answers contain

1. **Framing:** unit = active account on the 1st of the month; label = stops shipping or closes in
   the next 30 days; prediction made with information up to the snapshot; action = 8 % of accounts get
   a call. The horizon and the budget are explicit.
2. **Metric:** precision (and recall) at the 8 % budget is the decision metric; AP as a threshold-free
   summary; accuracy would be about 0.87 for "nobody lapses". Uses the candidate's own numbers.
3. **Reading:** "of the 86 calls, about 24 reach an account that would lapse, against 12 at random
   and 17 with the rule" - in calls, not in AUC.
4. **Before trusting:** the test months follow the training months (good), but check e.g. whether the
   September starter-tier fee increase shifts the test distribution, or uncertainty with 137 positives.

## Common incorrect answers and why they fail

* Accuracy or ROC AUC as the headline: not tied to the budget.
* A `predict()` (0/1) output used as the score: the ranking collapses (mutant `hard_labels_as_scores`).
* A threshold at 0.5 for "flagged": ignores the call budget (mutant `threshold_not_topk`).
* Fitting anything on test rows (mutant `fit_uses_test_rows`).

## Rubric (assign per aspect)

| Aspect | Demonstrated independently | Partial | Not yet demonstrated |
|---|---|---|---|
| Framing | unit, time of prediction, label horizon and action all stated | two of the four | vague |
| Baselines | trivial, rule and model, each fitted on train only | model without a rule or without no-skill | no comparison |
| Metric under imbalance | budget metric justified with own numbers; accuracy rejected with a reason | correct metric, no justification | accuracy |
| Communication | answer 3 readable by an account manager | correct but in ML jargon | unclear |
