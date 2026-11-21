# b1_baseline - reviewer notes

Reference: `lab/baseline.py`. Its report on the prepared split (executed; logistic regression, all
preprocessing inside the pipeline):

| | AP | precision@10% | recall@10% |
|---|---|---|---|
| trivial (constant) | 0.089 (= test prevalence) | 0.107* | 0.120* |
| heuristic (failed payments, then low usage) | 0.166 | 0.157 | 0.177 |
| logistic regression | 0.209 | 0.274 | 0.309 |

\* With constant scores the "top 10%" is an arbitrary set of rows; the expected precision is the
prevalence (0.089) and the expected recall is 0.10. The reference happens to pick the first rows. A
strong answer notices this instead of reporting 0.107 as if it were meaningful.

These numbers describe the simulation only.

## Model answers (ANSWERS.md)

1. **Framing.** Unit: one active customer on one snapshot date (the 1st of a month). Prediction made
   on that date with information up to it. Label: cancels within the next 30 days. Output: a ranking;
   action: the retention team calls the top 10%. Hence a ranking problem under a capacity
   constraint, not a classification-at-0.5 problem.
2. **Metric.** Precision and recall at the 10% budget are the operational quantities ("of 197 calls,
   54 reach a customer who would have churned; that is 31% of all churners"); AP summarises ranking
   quality across budgets. Accuracy is uninformative: predicting "nobody churns" scores 91% and helps nobody.
   ROC AUC is acceptable as a secondary number but hides how few positives there are.
3. **Reading.** At the same number of calls the model reaches about 2.6-3x as many churners as
   calling at random (0.274 vs 0.089 precision) and about 1.7x the analyst rule (0.274 vs 0.157). Whether a
   call *prevents* churn is a separate, causal question this data cannot answer.
4. **Before trusting.** Any of: how the split was made (it is temporal - verify that train dates
   precede test dates); whether every feature is known on the snapshot date; uncertainty of the
   estimate (175 positives in test; bootstrap or per-month scores); stability across months.

## Common incorrect answers and why they fail

* **Precision/recall at threshold 0.5** (mutant `threshold_not_topk`) - ignores the contact budget;
  with 9% prevalence almost no score exceeds 0.5.
* **`model.predict` output as scores** (mutant `hard_labels_as_scores`) - destroys the ranking.
* **Fitting on train+test, or computing imputation/scaling statistics on both** (mutant
  `fit_uses_test_rows`).
* **Using `customer_id` as a feature** (one-hot or ordinal) - memorises customers; not caught by the
  checks, look for it in review.
* **Reporting only accuracy or only ROC AUC**, no trivial baseline, no translation into calls.
* **Jumping to gradient boosting with a parameter search** as the "baseline" - a baseline is the
  simplest thing that could work, and here the simple model is not obviously beaten (in our runs a
  default random forest and default histogram gradient boosting scored *lower* AP than logistic
  regression on this split: 0.18 and 0.14).
* **Claiming the model "reduces churn by X%"** - prediction is not intervention.

## Rubric

| Aspect | Demonstrated independently | Partial | Not yet demonstrated |
|---|---|---|---|
| Framing | Unit, timing, label horizon and action all stated precisely | Task named ("binary classification") without timing/action | Framing missing or wrong unit |
| Baselines | Trivial + heuristic + simple model, compared on the same rows | Model only, or baselines without comparison | No baseline |
| Metric under imbalance | Budget-based metric implemented correctly and justified with numbers | Correct metric after check feedback; justification generic | Accuracy / threshold 0.5 |
| Leakage hygiene | Preprocessing inside the pipeline; no test labels touched; reproducible | Passes checks after fixes prompted by them | Fit on test rows |
| Communication | Result translated into calls and churners reached; prediction vs intervention distinguished | Numbers reported without interpretation | - |
