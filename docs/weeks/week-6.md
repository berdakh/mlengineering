---
title: "Week 6 · Validation and leakage"
parent: Weekly plan
nav_order: 6
---

# Week 6 · Validation and leakage

**Goal:** validate the way the model will be used and find leakage before it fools you.

In your ML course, a random validation set gave an honest estimate of $E_{out}$. With company data it often does
not: rows come in groups (many days per machine, many seats per customer), the world changes over time, and columns
sometimes contain the answer. This week you measure how much a wrong split or a leaky column inflates a score, using
synthetic data where the true answer is known, and you finish by reviewing a "99% accurate" churn model and reporting
its honest accuracy. Everything runs in Google Colab.

| # | Notebook | Kind | Time | Open |
|---|---|---|---|---|
| 21 | Validation done right: grouped and time-based splits | lesson | 100 min | [read](../notebooks/21_validation_done_right.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/21_validation_done_right.ipynb) |
| 22 | Leakage: how good models lie | lesson | 90 min | [read](../notebooks/22_leakage.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/22_leakage.ipynb) |
| 23 | Hyperparameter search without fooling yourself | lesson | 90 min | [read](../notebooks/23_hyperparameter_search.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/23_hyperparameter_search.ipynb) |
| 24 | Lab: find and fix the leaks | lab | 90 min | [read](../notebooks/24_lab_find_the_leaks.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/24_lab_find_the_leaks.ipynb) |

## Before you start

* Week 4: scikit-learn pipelines with `ColumnTransformer`, and `cross_val_score` (notebook 15).
* Week 5: baselines and ROC AUC (notebooks 18-19).
* From your ML course: training vs validation vs test error, $E_{in}$ and $E_{out}$, overfitting, cross-validation
  in principle.

## What you will be able to do

* build hold-out, k-fold and stratified splits by hand and with scikit-learn, and explain what each estimates;
* keep rows that belong together on one side with `GroupKFold`, and validate forward in time with `TimeSeriesSplit`
  and a gap;
* choose the splitter from how the model will be used, and hold out the final test set the same way;
* find leakage with single-feature probes, a data dictionary with `known_at` dates, duplicate counts and a leakage
  report on any split;
* prevent it with split-first discipline and pipelines (selection, target encoding and scaling inside the folds);
* run `GridSearchCV` and `RandomizedSearchCV` over a pipeline with the right splitter, explain and simulate why the
  best score is optimistic, and use a final test set, nested cross-validation and the one-standard-error rule.

## Suggested pacing (6-8 hours)

| Session | Work | Time |
|---|---|---|
| 1 | Notebook 21, sections 1-2 (hold-out, k-fold, stratified, GroupKFold) | 1 h |
| 2 | Notebook 21, sections 3-4 and quiz (time-based splits, choosing a splitter) | 45 min |
| 3 | Notebook 22, sections 1-3 (probes, target leakage, preprocessing on all rows) | 1 h |
| 4 | Notebook 22, sections 4-5 and quiz (duplicates, the leakage report) | 30 min |
| 5 | Notebook 23 (search with the right splitter, optimism, test set, nested CV) | 1.5 h |
| 6 | Notebook 24, the lab, without looking at the solutions | 1.5 h |
| 7 | Review: redo any exercise you needed a hint for; write the lab's model-review summary | 30 min |

The notebooks train random forests on a few thousand rows, so some cells take 5-20 seconds in Colab. If a session
runs long, stop at the end of a section: every notebook can be re-run from the top, and later cells still work if you
skipped an exercise (they say when they used the course's reference version).

## Tool guides

No new tool this week. The [scikit-learn](../tools/scikit-learn.html) guide from Week 4 covers the cross-validation
splitters, pipelines and the search classes used here; the [pandas](../tools/pandas.html) guide covers
`duplicated`, `merge` and dates.

Next week: [Week 7 · Models, uncertainty and error analysis](week-7.html).
