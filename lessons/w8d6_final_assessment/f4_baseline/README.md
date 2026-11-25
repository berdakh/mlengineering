# f4 - Problem framing and baselines on an unfamiliar tabular task (parallel form of b1)

**Time box: 35 minutes.** Sitting B, section 1 of 4. No hints; scikit-learn documentation is fine.

## Situation

Parcelo (a **synthetic** B2B parcel-shipping platform) loses accounts that quietly stop shipping. On
the 1st of every month its account managers can call **8% of active accounts**. They ask for a
monthly risk ranking.

The data team hands you two files, described in [`../data/README.md`](../data/README.md):
`lapse_train.csv` and `lapse_test.csv`. Each row is one account on one monthly snapshot date, with
features known on that date and the label `lapsed_30d` (1 if the account stopped shipping or closed
within the following 30 days). Use the split exactly as given in this section.

## Task

Implement the functions in `lab/baseline.py`:

1. `precision_recall_at_fraction(y_true, scores, fraction)` - precision and recall when the
   `k = ceil(fraction * n)` highest-scored rows are flagged.
2. `trivial_scores(train, test)` - the no-skill baseline: every row gets the training lapse rate.
3. `heuristic_scores(train, test)` - a rule an account manager could apply without ML. Your choice.
4. `model_scores(train, test)` - one simple, defensible first model. Your choice of model and features.
5. `run()` - evaluate all three on the test set (average precision, precision and recall at the 8%
   call budget) and return the dictionary described in the docstring.

Then answer the four questions in `lab/ANSWERS.md`.

Requirements that hold for any reasonable solution:

* Scores are one finite number per test row; higher means riskier.
* Nothing may depend on test labels: the functions must work when `test` has no `lapsed_30d` column.
* Two identical runs give identical scores.
* The data contains missing values and text categories; handle them.

## Check your work

```bash
python lessons/w8d6_final_assessment/f4_baseline/lab/baseline.py    # prints your report
python wb.py check lessons/w8d6_final_assessment/f4_baseline        # or:
python -m pytest lessons/w8d6_final_assessment/f4_baseline/checks -q
```

The starter raises `NotImplementedError`; all checks fail until you implement it.

## Acceptance criteria

* All checks pass.
* `ANSWERS.md` states the task precisely, justifies the metric with your own numbers, and translates
  the result into the account managers' terms.

The checks do not grade whether your model is *good*, only that it is a valid baseline that beats
no-skill. Model quality on synthetic data is not the point of this section.

## Submit

`lab/baseline.py`, `lab/ANSWERS.md`, the printed report, time used.
