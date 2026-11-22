# Interview set 3 - validation, leakage and ML fundamentals (spoken)

**Use on:** the Week 3 review day (`w3d7`). **Total time: 45 minutes, timer on.**
**Conditions (Weeks 3-5 level):** timed; answers are **spoken aloud** (record yourself, or write
bullet notes while speaking); no hints, no solutions, no AI assistance. After the first attempt you
may open the **rubrics only** (`solutions/interview/set3.md`, part A). The worked answers (part B of
the same file) stay closed until you have made a second attempt at every prompt you scored below
"Demonstrated".

| # | Type | Time |
|---|---|---|
| S1-S5 | Scenario: spot the flaw in a described experiment, then fix it | 4 min each (20) |
| F6-F8 | Fundamentals: explain or derive | 4 min each (12) |
| C9 | Coding: grouped K-fold from scratch | 13 min |

On a short day do S1, S3, S5, F7 and C9 (about 30 minutes).

**How to answer a scenario.** An interviewer is listening for four things, in this order: (1) name
the flaw precisely; (2) say the *mechanism* by which it biases the number, and in which direction;
(3) give the corrected procedure; (4) say what you would expect to happen to the number, and how you
would confirm the flaw was the cause. "That's leakage" without (2) is a label, not an answer.

---

## S1 - The churn model that got worse in production (4 min)

A team predicts whether a subscriber will cancel in the next 30 days. They take all customers with
their features as of today, label each by whether they cancelled at any point in the past year,
split rows 80/20 at random, and report ROC AUC 0.93. Among the top features are
`n_support_tickets_last_30d` and `days_since_last_login`. Six weeks after launch the weekly AUC on
fresh outcomes is 0.71.

What is wrong with the experiment, and how should the dataset have been built?

## S2 - Feature selection before cross-validation (4 min)

A genomics-style table has 120 samples and 20,000 features. A colleague selects the 50 features
most correlated with the label using all 120 samples, then runs 5-fold cross-validation of a
logistic regression on those 50 features and reports 88 % accuracy. The classes are balanced.

What accuracy would you expect this procedure to report if the labels were random? Explain why, and
restructure the experiment. How would you *demonstrate* the problem to a sceptical colleague in ten
lines of code?

## S3 - Overlapping windows (4 min)

Vibration recordings from 40 machines are cut into 10 s windows with 90 % overlap. Each window is
labelled faulty or healthy. Windows are shuffled and split 70/15/15; a CNN reaches 99.2 % test
accuracy. On three machines installed later it reaches 81 %.

Name every source of optimism in the original number. Give a validation design that would have
predicted the 81 %, and say what remains uncertain even then.

## S4 - Forty configurations and one test set (4 min)

A researcher evaluates 40 hyperparameter configurations directly on the test set of 9 experiments,
reports the best one (event recall 9/9, F1 0.91), and notes that the second best has F1 0.90.

What does the reported 0.91 estimate? What is the size of the problem likely to be here, and what
does the procedure need to look like? If no data can be spared for a separate validation set, what
do you do?

## S5 - The detector that reads the clock (4 min)

On a benchmark of 34 recordings, each containing one fault, a gradient-boosted model on rolling
features reaches point-level F1 0.88 with experiment-wise splits, no look-ahead, and thresholds
chosen on validation experiments. Feature importance is dominated by `rolling_mean_temperature_600`
and a cumulative-energy feature.

The splits are correct. Why might the result still be worthless, how would you test that suspicion
in under an hour, and what would you change? (This one is from your own project.)

---

## F6 - Ridge and correlated features (4 min)

Two features are almost perfectly correlated and both predict the target. Explain what ordinary
least squares, ridge (L2) and lasso (L1) each do with their coefficients, and *why*. For ridge,
give the argument for two identical columns precisely. What does this imply for reading feature
importance from coefficients?

## F7 - PR versus ROC under a prevalence change (4 min)

A detector is evaluated at 35 % positive prevalence: ROC AUC 0.90, and at its operating threshold
recall 0.80, false-positive rate 0.10. It is deployed where the prevalence is 1 %. Assume the
score distributions within each class do not change.

Which of ROC AUC, recall, false-positive rate and precision change? Compute the precision at both
prevalences. What does this say about quoting average precision from a benchmark?

## F8 - The best of many is biased (4 min)

You evaluate `K` models whose true performance is identical, each measured with independent noise
of standard deviation `s`. Roughly how far above the truth is the best observed score, as a
function of `K`? Give numbers for `K = 10` and `K = 100`. Name three places in an ordinary ML
project where this effect appears, and the structural remedy for each.

---

## C9 - Grouped K-fold from scratch (13 min)

Implement in `interview/set3_work/c9.py`, standard library only:

```python
def group_kfold(groups, k, seed=0):
    """groups: sequence of hashable group ids, one per row (rows of a group need not be adjacent).
    Yield k pairs (train_indices, test_indices) of row indices such that:
      * no group has rows in both train and test of the same pair;
      * every row is a test row in exactly one pair;
      * fold sizes are balanced in ROWS as far as whole groups allow;
      * the same seed gives the same folds; different seeds can give different folds;
      * ValueError if k < 2 or k exceeds the number of distinct groups."""
```

Before coding, say in two sentences how you will balance folds when group sizes differ a lot, and
whether your method is optimal (it need not be). After coding, state the complexity, and say what
in scikit-learn this corresponds to and one way yours differs.

```bash
python -m pytest interview/set3_tests -q
```

Passing the tests is not the whole rubric: the interviewer also scores the balancing argument and
whether you asked what "balanced" should mean (rows, groups, or positives).
