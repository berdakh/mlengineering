---
title: "Week 7 · Models, uncertainty and error analysis"
parent: Weekly plan
nav_order: 7
---

# Week 7 · Models, uncertainty and error analysis

**Goal:** compare models fairly with uncertainty, analyse errors, and start the project.

Until now every model comparison in this course was a comparison of two numbers. This week you learn the models
that win most often on business tables (random forests and gradient boosting) and how to keep them from
overfitting; you learn to put an interval around every score and to compare two models with a paired interval, so
that "no detectable difference" becomes an answer you can give with confidence; and you learn error analysis:
slicing metrics, reading the worst mistakes and writing a decision memo. Lessons 25-27 use a **synthetic** delivery
dataset generated in the notebook. The week ends with the first milestone of the course project: fault detection on
real sensor recordings (SKAB), evaluated at point and event level with intervals over experiments. Everything runs
in Google Colab.

| # | Notebook | Kind | Time | Open |
|---|---|---|---|---|
| 25 | Trees and ensembles in practice | lesson | 90 min | [read](../notebooks/25_trees_and_ensembles.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/25_trees_and_ensembles.ipynb) |
| 26 | Uncertainty and fair model comparisons | lesson | 90 min | [read](../notebooks/26_uncertainty_comparisons.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/26_uncertainty_comparisons.ipynb) |
| 27 | Error analysis and choosing a model | lesson | 90 min | [read](../notebooks/27_error_analysis_model_choice.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/27_error_analysis_model_choice.ipynb) |
| 28 | Project milestone 1: fault detection on sensor data | project lab | 120 min | [read](../notebooks/28_project_m1_fault_detection.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/28_project_m1_fault_detection.ipynb) |

## Before you start

* Week 4: scikit-learn estimators and pipelines (`fit`, `predict_proba`).
* Week 5: baselines, ROC AUC, precision, recall, PR-AUC and choosing a threshold.
* Week 6: grouped splits (why rows of one customer or machine must stay together) and leakage.
* From your theory course: training vs test error, overfitting, the bias-variance idea, validation.

## What you will be able to do

* explain how a decision tree chooses a split, and control a tree's complexity with depth and leaf size;
* train random forests and gradient boosting (`HistGradientBoostingClassifier`) with early stopping, and know when
  a logistic regression is the better choice;
* tell impurity importance from permutation importance, and avoid reporting noise as a "driver";
* compute standard errors and bootstrap intervals, resample by group (courier, customer, experiment), and compare
  two models with a paired interval of their difference;
* slice metrics by segment, find the weakest slice that matters, read the most confident mistakes, and measure
  latency;
* choose a model with a rule fixed in advance and write a decision memo;
* evaluate an anomaly detector on real sensor data at point and event level, with persistence rules and intervals
  over experiments.

## Suggested pacing (6-8 hours)

| Session | Work | Time |
|---|---|---|
| 1 | Notebook 25, sections 1-3 (splits, depth, random forests) | 50 min |
| 2 | Notebook 25, sections 4-6 and quiz (boosting, importance, linear vs trees) | 50 min |
| 3 | Notebook 26, sections 1-3 (standard errors, bootstrap, group bootstrap) | 50 min |
| 4 | Notebook 26, sections 4-5 and quiz (paired differences, "no detectable difference") | 40 min |
| 5 | Notebook 27, sections 1-3 (slices, worst slice, worst mistakes) | 50 min |
| 6 | Notebook 27, sections 4-5 and quiz (latency, decision memo) | 40 min |
| 7 | Notebook 28, steps 1-5 (load, split check, burn-in features, PR-AUC, events) | 1 h |
| 8 | Notebook 28, steps 6-8 and reflection (persistence, intervals, findings) | 1 h |

If a session runs long, stop at the end of a section: every notebook can be re-run from the top.

## Tool guides

No new tool this week. The [scikit-learn](../tools/scikit-learn.html) and [pandas](../tools/pandas.html) guides
cover everything the notebooks use; [matplotlib](../tools/matplotlib.html) covers the plots.

## Data this week

* Notebooks 25-27: `make_deliveries()` in `src/mlcourse/datasets_w07.py` generates a **synthetic** table of 6,000
  deliveries by 80 couriers, split by courier into train, valid and test. It contains a planted noise column and a
  hidden per-courier effect, both used in the lessons. The graders use a freshly generated copy with another seed.
* Notebook 28: the **Skoltech Anomaly Benchmark (SKAB)**, real laboratory recordings (34 labelled experiments,
  about 4 MB, GPL-3.0). It is downloaded on first use by `python project/get_skab.py` and never committed to the
  repository. The frozen experiment-level split is `solutions/labs/w3d1_leakage/lab/splits/v2.json` (27 dev and 7
  test experiments). See the [project guide](../guides/project.html). The project is an educational research
  prototype.

Previous week: [Week 6 · Validation and leakage](week-6.html) · Next week: [Week 8 · Code you can trust](week-8.html).
