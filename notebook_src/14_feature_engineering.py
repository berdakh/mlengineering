# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/14_feature_engineering.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 14 · Feature engineering, including time windows
#
# **Week 4 · lesson · about 100 minutes**
#
# A model learns from a table: one row per thing you predict for (here, a customer), one column per **feature**
# (a number the model can use). The database does not contain that table. It contains events: orders, items,
# tickets. **Feature engineering** is the work of turning events into one honest row per customer.
#
# **What you will learn in this notebook**
#
# - The classic customer features: **recency, frequency, monetary** value (RFM), tenure and rates.
# - **Time windows** that only look backwards from the cutoff, and how to test that a feature never sees the future.
# - Safe ratios, **one-hot encoding** of categories, **scaling**, and **missing-value** handling.
# - Why every "learned" number (a mean, a median, a category list) must come from the training rows only.
#
# **What you need:** notebook 13 (the churn label and the cutoff).
#
# **How grading works:** after each exercise there is a grader cell. Run it and it tells you immediately
# whether your answer works, and if not, what to look at.

# %%
# --- Setup: works in Google Colab AND on your own computer. Safe to re-run. ---
# In Colab this downloads the course (about 30 s) and installs what it needs (about a minute, once
# per session). On your computer it just finds the course folder.
import os, sys, subprocess
from pathlib import Path

if "google.colab" in sys.modules and not Path("/content/mlengineering").exists():
    subprocess.run(["git", "clone", "--depth", "1",
                    "https://github.com/berdakh/mlengineering.git", "/content/mlengineering"], check=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r",
                    "/content/mlengineering/requirements.txt"], check=True)
REPO_ROOT = Path("/content/mlengineering") if "google.colab" in sys.modules else next(
    p for p in [Path.cwd(), *Path.cwd().parents] if (p / "src" / "mlcourse").is_dir())
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT / "src"))
from mlcourse.grader import grade, quiz
print("Ready. Course folder:", REPO_ROOT)

# %% [markdown]
# The next cell loads the data and **gives** you three functions from notebook 13 that we build on (they are
# not graded here). As in notebook 13, `use(your_function, ...)` runs your function, or the course's reference
# version (with a note) if you have not written it yet.

# %%
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mlcourse.sql import sql
from mlcourse.graders.w04 import use

orders = sql("SELECT * FROM orders", "shop")
orders["order_date"] = pd.to_datetime(orders["order_date"])
items = sql("SELECT * FROM order_items", "shop")
customers = sql("SELECT * FROM customers", "shop")
customers["signup_date"] = pd.to_datetime(customers["signup_date"])

CUTOFF = pd.Timestamp("2025-09-30")


def order_values(items):
    line = items["quantity"] * items["unit_price"] * (1 - items["discount"])
    return line.groupby(items["order_id"]).sum().rename("order_value")


def active_customers(orders, cutoff):
    keep = (orders["status"] != "cancelled") & (orders["order_date"] <= cutoff)
    return sorted(orders.loc[keep, "customer_id"].unique())


def churn_labels(orders, cutoff, horizon_days=90):
    active = active_customers(orders, cutoff)
    end = cutoff + pd.Timedelta(days=horizon_days)
    window = orders[(orders["status"] != "cancelled") & (orders["order_date"] > cutoff) & (orders["order_date"] <= end)]
    came_back = set(window["customer_id"])
    return pd.DataFrame({"customer_id": active, "churned": [c not in came_back for c in active]})


values = order_values(items)
active = active_customers(orders, CUTOFF)
print(len(active), "active customers at", CUTOFF.date())

# %% [markdown]
# ## 1. Recency: one honest number per customer
#
# **Why.** In notebook 13, customers who had not bought for a long time churned far more. "Days since the last
# order" is usually the single strongest churn feature, and every retail or subscription team computes it.
#
# **Idea.** A feature for the cutoff day may only use events **on or before** the cutoff. So every feature function
# starts the same way: filter the events to `order_date <= cutoff` (and drop cancelled orders, as for the label),
# then aggregate per customer. **Recency** is `cutoff - last order date`, in days.
#
# Writing each feature as a function of `(events, cutoff)` has a big benefit: you can compute the same features
# for any cutoff (to make more training rows, or to score customers today) and you can **test** that a feature
# ignores the future: change the events after the cutoff and check that nothing moves.
#
# **See it.** Subtracting two dates gives a `Timedelta`; `.dt.days` turns a column of them into whole days.

# %%
example = pd.Series(pd.to_datetime(["2025-09-01", "2025-06-15"]))
print((CUTOFF - example).dt.days.tolist())

# %% [markdown]
# **Try it.** Before running the cell above, predict the two numbers. (September has 30 days.)
#
# ### Exercise 1 · recency
#
# Write `recency_days(orders, cutoff)`: a Series indexed by `customer_id`, with the number of days between each
# active customer's **last non-cancelled order on or before the cutoff** and the cutoff. Customers who are not
# active at the cutoff must not appear.

# %%
def recency_days(orders, cutoff):
    ### BEGIN SOLUTION
    past = orders[(orders["status"] != "cancelled") & (orders["order_date"] <= cutoff)]
    return (cutoff - past.groupby("customer_id")["order_date"].max()).dt.days
    ### END SOLUTION


# %%
grade("w04.recency_days", recency_days)

# %% [markdown]
# ## 2. Windows that look backwards: frequency and monetary value
#
# **Why.** "Number of orders" over all time mixes customers who joined two years ago with customers who joined last
# month. A **time window** of fixed length makes customers comparable: "orders in the last 90 days" means the same
# thing for everyone.
#
# **Idea.** A backward window of `d` days ends at the cutoff: `cutoff - d days < order_date <= cutoff`. Use several
# lengths (30, 90, 365 days) to capture short- and long-term behaviour.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c14-01.svg" alt="Three backward windows of 365, 90 and 30 days all end at the cutoff; nothing after the cutoff is used" style="max-width:100%">
#
# * **Frequency**: number of non-cancelled orders in the window.
# * **Monetary**: total value of those orders.
#
# Customers with no orders in the window must still get a row, with **0** (not missing): "bought nothing" is real,
# useful information. `reindex(active, fill_value=0)` does exactly that: it lines the result up with the list of
# active customers and fills the gaps.
#
# **See it.** How the window filter looks for 30 days:

# %%
start = CUTOFF - pd.Timedelta(days=30)
in_window = orders[(orders["order_date"] > start) & (orders["order_date"] <= CUTOFF) & (orders["status"] != "cancelled")]
counts = in_window.groupby("customer_id").size()
print("customers with an order in the last 30 days:", len(counts))
print("after reindexing to all active customers:", len(counts.reindex(active, fill_value=0)))

# %% [markdown]
# **Try it.** Change 30 to 365 in the cell above. How many active customers bought at least once in the last year?
#
# ### Exercise 2 · orders in a window
#
# Write `orders_in_window(orders, cutoff, days)`: a Series indexed by `customer_id`, **one entry per active
# customer**, counting their non-cancelled orders with `cutoff - days < order_date <= cutoff` (0 if none). You may
# call `active_customers` (given above).

# %%
def orders_in_window(orders, cutoff, days):
    ### BEGIN SOLUTION
    kept = orders[orders["status"] != "cancelled"]
    start = cutoff - pd.Timedelta(days=days)
    window = kept[(kept["order_date"] > start) & (kept["order_date"] <= cutoff)]
    return window.groupby("customer_id").size().reindex(active_customers(orders, cutoff), fill_value=0)
    ### END SOLUTION


# %%
grade("w04.orders_in_window", orders_in_window)

# %% [markdown]
# ### Exercise 3 · spend in a window
#
# Write `spend_in_window(orders, values, cutoff, days)`: like exercise 2, but the **total order value** instead of
# the count. `values` is a Series of order values indexed by `order_id` (from `order_values`). Tip:
# `orders["order_id"].map(values)` looks up each order's value. Fill 0.0 for customers with no orders in the window.

# %%
def spend_in_window(orders, values, cutoff, days):
    ### BEGIN SOLUTION
    kept = orders[orders["status"] != "cancelled"].copy()
    kept["value"] = kept["order_id"].map(values)
    start = cutoff - pd.Timedelta(days=days)
    window = kept[(kept["order_date"] > start) & (kept["order_date"] <= cutoff)]
    return window.groupby("customer_id")["value"].sum().reindex(active_customers(orders, cutoff), fill_value=0.0)
    ### END SOLUTION


# %%
grade("w04.spend_in_window", spend_in_window)

# %% [markdown]
# ### What leakage looks like
#
# Here is a feature that *looks* reasonable: each customer's total number of orders, counted over the whole
# table. Compare it with the honest count (orders on or before the cutoff), separately for churned and retained
# customers:

# %%
labels = churn_labels(orders, CUTOFF)
kept = orders[orders["status"] != "cancelled"]
check = labels.set_index("customer_id")
check["orders_before_cutoff"] = kept[kept["order_date"] <= CUTOFF].groupby("customer_id").size()
check["orders_all_time"] = kept.groupby("customer_id").size()
check.groupby("churned")[["orders_before_cutoff", "orders_all_time"]].mean().round(2)

# %% [markdown]
# Retained customers average 4.14 orders before the cutoff but 6.26 "all time"; churned customers have 2.51 in both
# columns. Of course: by definition, churned customers bought nothing in the 90 days after the cutoff, and the
# all-time count includes those 90 days. The all-time feature contains the answer. A model trained with it would
# look excellent in testing and fail on the day you use it, when the future has not happened yet.
#
# ## 3. Tenure and ratios
#
# **Why.** Some of the most useful features compare two quantities: average order value (spend per order), the
# share of orders that were cancelled. Ratios also make customers of different ages comparable.
#
# **Idea.** **Tenure** is how long someone has been a customer at the cutoff: `cutoff - signup_date` in days.
# Customers who signed up after the cutoff do not exist yet on the cutoff day, so they are left out.
#
# A ratio has a trap: **division by zero**. pandas does not crash; it silently produces `NaN` (0/0) or `inf`
# (5/0), which later break models. A **safe ratio** decides explicitly what an undefined ratio means; for
# "average order value when there were no orders", 0.0 is a sensible choice.
#
# **See it.**

# %%
num = pd.Series([10.0, 5.0, 0.0])
den = pd.Series([2.0, 0.0, 0.0])
print((num / den).tolist())

# %% [markdown]
# You should see `[5.0, inf, nan]`. Neither `inf` nor `nan` is a number a model can use.
#
# ### Exercise 4 · tenure
#
# Write `tenure_days(customers, cutoff)`: a Series indexed by `customer_id` with the days from `signup_date` to the
# cutoff, for customers who signed up **on or before** the cutoff only.

# %%
def tenure_days(customers, cutoff):
    ### BEGIN SOLUTION
    known = customers[customers["signup_date"] <= cutoff].set_index("customer_id")
    return (cutoff - known["signup_date"]).dt.days
    ### END SOLUTION


# %%
grade("w04.tenure_days", tenure_days)

# %% [markdown]
# ### Exercise 5 · a safe ratio
#
# Write `safe_ratio(numerator, denominator)`: element-wise division of two Series with the same index, giving
# **0.0 wherever the denominator is 0**. No `NaN` or `inf` may come out. Tip: `den.where(den != 0)` replaces zeros
# by NaN; dividing by NaN gives NaN, which `.fillna(0.0)` then replaces.

# %%
def safe_ratio(numerator, denominator):
    ### BEGIN SOLUTION
    return (numerator / denominator.where(denominator != 0)).fillna(0.0)
    ### END SOLUTION


# %%
grade("w04.safe_ratio", safe_ratio)

# %% [markdown]
# ### Exercise 6 · cancellation rate
#
# Write `cancel_rate(orders, cutoff)`: for each customer with at least one order (**any status**) on or before the
# cutoff, the share of those orders whose status is `"cancelled"`. A Series indexed by `customer_id`.

# %%
def cancel_rate(orders, cutoff):
    ### BEGIN SOLUTION
    past = orders[orders["order_date"] <= cutoff]
    return (past["status"] == "cancelled").groupby(past["customer_id"]).mean()
    ### END SOLUTION


# %%
grade("w04.cancel_rate", cancel_rate)

# %% [markdown]
# ## 4. Categories: one-hot encoding
#
# **Why.** Models do arithmetic. `"student"` is not a number, and replacing categories by 1, 2, 3 invents an order
# ("small_business is three times a consumer") that does not exist.
#
# **Idea.** **One-hot encoding** makes one 0/1 column per category: `segment=student` is 1 for students and 0
# otherwise. The list of categories is **learned from the training data and then fixed**. That matters in
# production: if tomorrow a customer arrives with a category never seen before, or with a missing value, the encoder
# must still produce exactly the same columns (all zeros for the unknown), or the model receives inputs of the wrong
# shape.
#
# **See it.** `pd.get_dummies` is handy for exploring, but its columns depend on the data it is given:

# %%
print(pd.get_dummies(pd.Series(["web", "mobile_app"], name="channel")).columns.tolist())
print(pd.get_dummies(pd.Series(["web", "fax"], name="channel")).columns.tolist())

# %% [markdown]
# Two batches, two different sets of columns: a model trained on the first could not even read the second.
#
# ### Exercise 7 · one-hot with a fixed category list
#
# Write `one_hot(series, categories)`: a DataFrame with **one column per entry of `categories`, in that order**,
# named `f"{series.name}={category}"`, containing 1 where the value equals that category and 0 otherwise. Unknown
# categories and missing values become rows of zeros. Keep the input's index.

# %%
def one_hot(series, categories):
    ### BEGIN SOLUTION
    return pd.DataFrame({f"{series.name}={c}": (series == c).astype(int) for c in categories}, index=series.index)
    ### END SOLUTION


# %%
grade("w04.one_hot", one_hot)

# %% [markdown]
# ## 5. Scaling and missing values, learned from training rows only
#
# **Why.** Recency is measured in hundreds of days, the cancellation rate between 0 and 1. Many models (logistic
# regression with regularisation, k-nearest neighbours, anything trained by gradient descent) treat a feature's size
# as its importance, or converge badly when features live on different scales.
#
# **Idea.** **Standardising** a feature means $z = (x - \mu) / \sigma$: subtract the mean and divide by the
# standard deviation, so the feature has mean 0 and standard deviation 1. Two rules:
#
# 1. $\mu$ and $\sigma$ are **learned from the training rows only**, then applied unchanged to any other rows
#    (validation, test, tomorrow's customers). They are parameters of the model, like weights.
# 2. A constant feature has $\sigma = 0$; return zeros rather than dividing by zero.
#
# **Missing values** follow the same logic. To **impute** (fill in) a missing number, use a value learned from
# training rows; the **median** is robust to the skewed amounts we saw in notebook 13. Often it also helps to add a
# 0/1 **missing indicator** column, because "unknown" can itself carry information.
#
# In *Learning from Data* terms: the test set gives an unbiased estimate of $E_{out}$ only if nothing about it
# influenced the hypothesis. A mean computed on train + test is a tiny piece of the test set inside your model.
#
# **See it.**

# %%
train = pd.Series([1.0, 2.0, 3.0, 4.0])
test = pd.Series([10.0])
mu, sigma = train.mean(), train.std(ddof=0)
print("train standardised:", ((train - mu) / sigma).round(2).tolist())
print("test standardised with TRAIN numbers:", ((test - mu) / sigma).round(2).tolist())

# %% [markdown]
# The test value comes out as 6.71: far outside what the model saw in training, which is exactly the truth. Had we
# standardised the test row with its own numbers, it would have become 0 (or `nan`), hiding that it is unusual.
# (`ddof=0` divides by n, which is what scikit-learn's scaler does; pandas' default `ddof=1` divides by n - 1.)
#
# **Try it.** Change `test` to `pd.Series([2.5])`. What do you expect?
#
# ### Exercise 8 · standardise with training numbers
#
# Write `standardize(train, other)`: returns `(train_scaled, other_scaled)`, both computed with the mean and
# standard deviation (`ddof=0`) of `train`. If that standard deviation is 0, return all zeros for both.

# %%
def standardize(train, other):
    ### BEGIN SOLUTION
    mu, sigma = train.mean(), train.std(ddof=0)
    if sigma == 0:
        return train * 0.0, other * 0.0
    return (train - mu) / sigma, (other - mu) / sigma
    ### END SOLUTION


# %%
grade("w04.standardize", standardize)

# %% [markdown]
# ### Exercise 9 · fill missing values with the training median
#
# Write `fill_with_train_median(train, other)`: returns `(train_filled, other_filled, median)` where `median` is the
# median of `train` (pandas ignores NaN when computing it) and both Series have their missing values replaced by it.

# %%
def fill_with_train_median(train, other):
    ### BEGIN SOLUTION
    median = train.median()
    return train.fillna(median), other.fillna(median), median
    ### END SOLUTION


# %%
grade("w04.fill_with_train_median", fill_with_train_median)

# %% [markdown]
# ## 6. Putting it together: a feature table
#
# **Why.** A model needs all features side by side, one row per customer, computed for the same cutoff.
#
# **Idea.** Start from an empty DataFrame indexed by the active customers, then add one column per feature.
# pandas aligns each Series on the index, so customers line up automatically. Scaling, imputation and one-hot
# encoding are *not* part of this table: they learn from training rows, so they happen after the split, inside a
# scikit-learn pipeline (notebook 15).
#
# ### Exercise 10 · the customer feature table
#
# Write `customer_features(orders, values, customers, cutoff)`: a DataFrame indexed by `customer_id` with **one row
# per active customer** and these columns: `recency_days`, `orders_90d`, `spend_90d`, `tenure_days`, `cancel_rate`.
# Use your functions from exercises 1-6. No missing values should remain.

# %%
def customer_features(orders, values, customers, cutoff):
    ### BEGIN SOLUTION
    features = pd.DataFrame(index=pd.Index(active_customers(orders, cutoff), name="customer_id"))
    features["recency_days"] = recency_days(orders, cutoff)
    features["orders_90d"] = orders_in_window(orders, cutoff, 90)
    features["spend_90d"] = spend_in_window(orders, values, cutoff, 90)
    features["tenure_days"] = tenure_days(customers, cutoff)
    features["cancel_rate"] = cancel_rate(orders, cutoff)
    return features
    ### END SOLUTION


# %%
grade("w04.customer_features", customer_features)

# %%
features = use(customer_features, orders, values, customers, CUTOFF)
features["avg_order_value_90d"] = use(safe_ratio, features["spend_90d"], features["orders_90d"])
print(features.shape)
features.describe().T.round(2)

# %% [markdown]
# You should see 860 rows. The numeric columns live on very different scales (recency up to 598 days, the
# cancellation rate at most 0.75), which is why the pipeline in notebook 15 standardises them.
#
# **Try it.** Join the labels and compare feature means between churned and retained customers:
# `features.join(labels.set_index("customer_id")).groupby("churned").mean().T`. Which features differ most?

# %%
features.join(labels.set_index("customer_id")).groupby("churned").mean().T.round(2)

# %% [markdown]
# ## Quiz
#
# **Q1.** Why must a feature for the cutoff day use only events on or before the cutoff?
#
# - a) Because computing it is faster.
# - b) Because on the day you use the model, later events do not exist yet; a feature that uses them cannot be
#   computed in production, and the test score would be a lie.
# - c) Because future data adds useful extra signal that the model should not get too easily.
# - d) It only matters for the label, not for features.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w04.14_q1", answer)

# %% [markdown]
# **Q2.** You standardise a feature using the mean and standard deviation of *all* rows (train and test together),
# then split. What is wrong?
#
# - a) Nothing: scaling does not change the information in the data.
# - b) Test rows should not be scaled at all.
# - c) The scaler's numbers are learned parameters; computing them with test rows lets the test set influence the
#   model, so the test score is no longer a clean estimate of E_out.
# - d) It is wrong only for very large datasets.

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w04.14_q2", answer)

# %% [markdown]
# **Q3.** Why fix the one-hot category list at training time?
#
# - a) So that new data always produces exactly the same columns, whatever categories it contains.
# - b) Because `pd.get_dummies` is slow.
# - c) So that rows with new categories can be dropped.
# - d) Because columns must be in alphabetical order.

# %%
### BEGIN SOLUTION
answer = "a"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w04.14_q3", answer)

# %% [markdown]
# **Q4.** Spend values are strongly right-skewed. Which fill value for missing spend is the most sensible default?
#
# - a) The mean of the training rows.
# - b) Zero.
# - c) Drop customers with missing spend.
# - d) The median of the training rows.

# %%
### BEGIN SOLUTION
answer = "d"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w04.14_q4", answer)

# %% [markdown]
# **Q5.** What does a 0/1 "missing indicator" column add?
#
# - a) It removes rows with missing values.
# - b) It lets the model learn whether "the value was unknown" itself predicts the label.
# - c) It replaces the need to fill in the missing value.
# - d) It lets scikit-learn models read NaN directly.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w04.14_q5", answer)

# %% [markdown]
# ## Recap
#
# - Every feature is a function of `(events, cutoff)` that only looks at events on or before the cutoff.
# - Recency, frequency and monetary value in backward windows of fixed length make customers comparable.
# - Customers with no events in a window get 0, not a missing value.
# - Ratios need an explicit rule for a zero denominator; `NaN` and `inf` must never reach a model.
# - One-hot encoding uses a category list fixed at training time; unknown or missing values become zeros.
# - Scaling and imputation learn numbers (mean, std, median): learn them from training rows only.
# - A feature that uses data from after the cutoff (like an all-time count) leaks the label.
#
# ## On the job
#
# Feature code is the part of an ML system that changes most and breaks most quietly. Teams keep feature
# definitions in functions with a cutoff parameter (or in a "feature store") so the same code builds training data
# and scores live customers, and they write tests like the graders here: edit the future, check nothing moves. When
# a churn model is suspiciously good, the first thing an experienced engineer checks is which feature can see the
# future.
#
# ## Going further
#
# - Tool guide: [scikit-learn](../docs/tools/scikit-learn.md) (scaling, imputation and encoding done for you).
# - Week 6 goes deep on leakage: [22 · Leakage](22_leakage.ipynb).
# - Next: [15 · scikit-learn pipelines](15_sklearn_pipelines.ipynb).

# %% [markdown]
# ## Record your progress

# %%
from mlcourse.progress import mark

# mark("14", "reading")
# mark("14", "guided")
