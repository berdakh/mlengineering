---
title: "Week 5 · From theory to practice: framing, baselines, metrics"
parent: Weekly plan
nav_order: 5
---

# Week 5 · From theory to practice: framing, baselines, metrics

**Goal:** frame a business problem as an ML task, beat honest baselines, and pick metrics and thresholds from costs.

Your theory course gave you a dataset and asked for a good hypothesis. This week starts one step earlier, where
real projects start: with a decision someone has to make. You write down who is scored, when, and what happens
next; you put a price on each kind of mistake; you build the baselines a model must beat; and you choose a
threshold from the team's costs and call budget. Everything runs in Google Colab on the churn table from the
synthetic shop database (Week 4 builds it step by step; this week uses a ready helper, `mlcourse.churn`).

| # | Notebook | Kind | Time | Open |
|---|---|---|---|---|
| 17 | From Learning from Data to real problems: framing | lesson | 90 min | [read](../notebooks/17_theory_to_practice_framing.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/17_theory_to_practice_framing.ipynb) |
| 18 | Baselines and first models | lesson | 90 min | [read](../notebooks/18_baselines_first_models.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/18_baselines_first_models.ipynb) |
| 19 | Metrics and thresholds that match decisions | lesson | 100 min | [read](../notebooks/19_metrics_for_decisions.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/19_metrics_for_decisions.ipynb) |
| 20 | Lab: a churn model you can defend | lab | 90 min | [read](../notebooks/20_lab_churn_model.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/20_lab_churn_model.ipynb) |

## Before you start

* Week 4, especially notebook 15 (scikit-learn pipelines and `ColumnTransformer`) and the churn definition from
  notebooks 14 and 16. If you skipped Week 4, this week still works: the churn table comes ready-made.
* From your introductory ML course: training vs test error, overfitting, validation, logistic regression.

## What you will be able to do

* fill in a framing worksheet (unit, label, prediction time, decision, cost of each error, constraints) for a
  vague request, and say when a rule or a report is a better answer than a model;
* explain why the test set is a one-time budget, and keep features to what exists at prediction time;
* build a majority-class baseline, a one-feature rule, a logistic regression and a decision tree in pipelines, and
  read learning and complexity curves as the $E_{in}$/$E_{out}$ picture;
* read logistic-regression coefficients without mistaking them for causes;
* compute a confusion matrix, precision, recall, F1, ROC-AUC, PR-AUC and precision@k, and know which one fits
  which decision;
* choose a threshold from a cost matrix and a contact budget, check calibration, and write a recommendation a
  manager can act on.

## Suggested pacing (6-8 hours)

| Session | Work | Time |
|---|---|---|
| 1 | Notebook 17, sections 1-3 (textbook vs job, the test set as a budget, the deployment question) | 50 min |
| 2 | Notebook 17, sections 4-5 and quiz (costs of errors, the framing worksheet) | 45 min |
| 3 | Notebook 18, sections 1-3 (locked test set, baselines, first pipelines) | 50 min |
| 4 | Notebook 18, sections 4-6 and quiz (learning curves, coefficients, the final report) | 50 min |
| 5 | Notebook 19, sections 1-3 (confusion matrix, precision and recall, ROC-AUC vs PR-AUC) | 50 min |
| 6 | Notebook 19, sections 4-5 and quiz (thresholds from costs and budget, calibration) | 55 min |
| 7 | Notebook 20, the lab, without looking at the solutions | 1.5 h |
| 8 | Review: redo any exercise you needed a hint for; rewrite your lab recommendation for your portfolio | 30 min |

If a session runs long, stop at the end of a section: every notebook can be re-run from the top.

## Tool guides

No new tool this week. Keep these at hand:

* [scikit-learn](../tools/scikit-learn.html): pipelines, `DummyClassifier`, metrics.
* [pandas](../tools/pandas.html) and [Plotting with matplotlib](../tools/matplotlib.html) for the tables and
  curves.

Previous week: [Week 4 · From data to features](week-4.html). Next week:
[Week 6 · Validation and leakage](week-6.html).
