---
title: "Week 4 · From data to features"
parent: Weekly plan
nav_order: 4
---

# Week 4 · From data to features

**Goal:** explore a dataset with purpose and turn it into features with scikit-learn pipelines.

This week starts the problem that runs through the rest of the course: **predicting customer churn** in the
synthetic shop database. You define churn precisely (a customer active before a cutoff date who places no order
in the 90 days after it), explore the data with questions instead of random plots, turn raw orders into honest
features that never look past the cutoff, and wrap the preprocessing and a model in a scikit-learn pipeline that
only ever learns from training rows. Everything runs in Google Colab.

| # | Notebook | Kind | Time | Open |
|---|---|---|---|---|
| 13 | Exploratory analysis with a purpose | lesson | 90 min | [read](../notebooks/13_eda_with_purpose.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/13_eda_with_purpose.ipynb) |
| 14 | Feature engineering, including time windows | lesson | 100 min | [read](../notebooks/14_feature_engineering.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/14_feature_engineering.ipynb) |
| 15 | scikit-learn pipelines | lesson | 90 min | [read](../notebooks/15_sklearn_pipelines.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/15_sklearn_pipelines.ipynb) |
| 16 | Lab: a feature pipeline for churn | lab | 90 min | [read](../notebooks/16_lab_feature_pipeline.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/16_lab_feature_pipeline.ipynb) |

## Before you start

* Weeks 2 and 3: you can filter, group and join in SQL and in pandas (`groupby`, `merge`, boolean filters).
* From your ML course: training vs test error, overfitting, logistic regression. No scikit-learn or matplotlib
  experience is assumed.

## What you will be able to do

* turn a vague business question into a precise label with a cutoff date and a horizon;
* explain why features may only use data from on or before the cutoff (your first look at leakage);
* explore with questions: distributions, groups, relationships, class balance and time, with labelled matplotlib
  plots;
* build recency, frequency, monetary, tenure and ratio features in backward time windows, and test that they ignore
  the future;
* one-hot encode, scale and impute with numbers learned from training rows only;
* build a `Pipeline` with a `ColumnTransformer`, `SimpleImputer`, `OneHotEncoder` and `StandardScaler`, fit it on
  training data, and compare train accuracy, test accuracy and a baseline.

## Suggested pacing (6-8 hours)

| Session | Work | Time |
|---|---|---|
| 1 | Notebook 13, sections 1-3 (questions, the churn label, class balance) | 45 min |
| 2 | Notebook 13, sections 4-6 and quiz (matplotlib: distributions, groups, relationships, time) | 1 h |
| 3 | Notebook 14, sections 1-3 (recency, backward windows, leakage, ratios) | 1 h |
| 4 | Notebook 14, sections 4-6 and quiz (one-hot, scaling, missing values, the feature table) | 1 h |
| 5 | Notebook 15 (estimator API, split, transformers, pipeline, cross-validation preview) | 1.5 h |
| 6 | Notebook 16, the lab, without looking at the solutions | 1.5 h |
| 7 | Review: redo any exercise you needed a hint for; skim both tool guides' cheat sheets | 30 min |

If a session runs long, stop at the end of a section: every notebook can be re-run from the top, and later cells
still work if you skipped an exercise (they say when they used the course's reference version).

## Tool guides

* [Plotting with matplotlib](../tools/matplotlib.html): figures and axes, the five plots you will use most,
  labelling, saving, common errors and a cheat sheet.
* [scikit-learn](../tools/scikit-learn.html): the estimator API, splitting, preprocessing, pipelines,
  cross-validation, common errors and a cheat sheet.
* [pandas](../tools/pandas.html), from Week 3, for `groupby`, `merge` and dates.

Next week: [Week 5 · From theory to practice: framing, baselines, metrics](week-5.html).
