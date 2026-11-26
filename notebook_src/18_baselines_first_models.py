# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/18_baselines_first_models.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 18 · Baselines and first models
#
# **Week 5 · lesson · about 90 minutes**
#
# Before anyone asks "how good is the model?", ask "compared with what?". This notebook builds a ladder of
# baselines on the churn table, from a model that always gives the same answer to a logistic regression and a
# decision tree, and reads the train/validation gap the way your theory course taught you to read
# $E_{in}$ and $E_{out}$.
#
# **What you will learn**
#
# - why every model needs baselines, and how to build the two that matter most: the majority class and a simple
#   one-feature rule;
# - a logistic regression and a decision tree in scikit-learn pipelines that survive messy production data;
# - learning curves and depth curves: the train/validation gap as the $E_{in}$/$E_{out}$ picture;
# - how to read logistic-regression coefficients without fooling yourself.
#
# **What you need:** notebook 15 (pipelines, `ColumnTransformer`) and notebook 17 (framing, the three-way split).
#
# **How grading works:** run the cell under each exercise; `grade(...)` fits your code on several datasets and
# explains what is wrong without giving the answer away.

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
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mlcourse.graders.w05 import use

# %% [markdown]
# ## 1 · The churn table and a locked test set
#
# **Why.** Every number in this notebook is a comparison. If the test set leaks into those comparisons, every
# number is optimistic (notebook 17, section 2). So we lock it away first.
#
# **Idea.** `mlcourse.churn.build_churn_table()` returns one row per customer who was active on the cutoff date
# (30 June 2025), with features computed only from data on or before that day and the label `churned` (no
# non-cancelled order in the next 90 days). It is the same table Week 4 builds step by step; here it is a ready
# helper so this week can focus on modelling. `FEATURES` lists the input columns: eight numeric (`NUMERIC`) and two
# categorical (`CATEGORICAL`).
#
# We split once: 25% **test**, locked until the end of the notebook; of the remaining rows, 25% become
# **validation**, for every comparison we make. `stratify=y` keeps the churn rate the same in each part.

# %%
from sklearn.model_selection import train_test_split
from mlcourse.churn import build_churn_table, FEATURES, NUMERIC, CATEGORICAL

table = build_churn_table()
X, y = table[FEATURES], table["churned"]
X_rest, X_test, y_rest, y_test = train_test_split(X, y, test_size=0.25, random_state=0, stratify=y)
X_train, X_val, y_train, y_val = train_test_split(X_rest, y_rest, test_size=0.25, random_state=0,
                                                  stratify=y_rest)
print("train", X_train.shape, " val", X_val.shape, " test", X_test.shape, "(locked)")
print("churn rate in train:", y_train.mean().round(3))
print("numeric:", NUMERIC)
print("categorical:", CATEGORICAL)
X_train.head()

# %% [markdown]
# 368 training rows, 123 validation rows, 164 test rows. The churn rate is about 0.47: the classes are almost
# balanced, which will matter in a moment.
#
# **Try it.** How many customers in `X_train` have a missing `city`? (`X_train["city"].isna().sum()`.) The
# pipelines below must cope with that.

# %%
X_train["city"].isna().sum()

# %% [markdown]
# ## 2 · Baselines: the bar every model must clear
#
# **Why.** "Our model is 70% accurate" sounds good until someone notices that predicting "nobody churns" is 53%
# accurate, or that one line of SQL gets 60%. A baseline turns a score into evidence.
#
# **Idea.** Climb a ladder and keep every rung in your report:
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c18-01.svg" alt="A ladder of baselines: majority class, a one-feature rule, logistic regression, a decision tree and beyond; each must beat the one before it" style="max-width:100%">
#
# 1. **Majority class**: always predict the most common label of the *training* set. scikit-learn calls it
#    `DummyClassifier`. It shows what accuracy you get for free.
# 2. **A simple rule** a domain expert would suggest: "a customer who has not ordered for more than 90 days will
#    churn". It shows how much a model adds over common sense.
# 3. **A simple model** (logistic regression), then a more flexible one (a decision tree).
#
# A model that does not beat rung 2 clearly is not worth deploying, however clever it is.

# %%
from sklearn.dummy import DummyClassifier

dummy = DummyClassifier(strategy="most_frequent").fit(X_train, y_train)
print("dummy predicts:", dummy.predict(X_val[:5]))
print("dummy validation accuracy:", round(dummy.score(X_val, y_val), 3))

# %% [markdown]
# The dummy always predicts 0 ("stays"), the more common class in training, and is right on about 53% of the
# validation customers.
#
# **Try it.** Replace `"most_frequent"` with `"stratified"` (random guesses in the training proportions) and run
# twice with different `random_state` values. Why does its accuracy hover around 0.5?

# %% [markdown]
# ### Exercise 1 · majority accuracy by hand
#
# Write `majority_accuracy(y_train, y_test)`: find the most common value in `y_train` (on a tie, take the smaller
# value, which is what `np.unique` + `np.argmax` give you), and return the share of `y_test` equal to it.

# %%
def majority_accuracy(y_train, y_test):
    ### BEGIN SOLUTION
    values, counts = np.unique(np.asarray(y_train), return_counts=True)
    majority = values[np.argmax(counts)]
    return float(np.mean(np.asarray(y_test) == majority))
    ### END SOLUTION


# %%
grade("w05.majority_accuracy", majority_accuracy)

# %% [markdown]
# ### Exercise 2 · the recency rule
#
# Write `recency_rule(X, threshold)`: predict 1 (churn) for customers whose `days_since_last_order` is
# **strictly greater** than `threshold`, else 0. Return a NumPy array of 0/1 integers, one per row of `X`.

# %%
def recency_rule(X, threshold):
    ### BEGIN SOLUTION
    return (X["days_since_last_order"].to_numpy() > threshold).astype(int)
    ### END SOLUTION


# %%
grade("w05.recency_rule", recency_rule)

# %% [markdown]
# ### Exercise 3 · fit the rule's threshold
#
# A rule has a "parameter" too: the threshold. Write `best_rule_threshold(X, y, candidates)`: return the candidate
# whose rule has the highest accuracy on `(X, y)`; on a tie, return the smallest such threshold. Then fit it on
# **train** and evaluate it on **validation**: choosing the threshold is learning, so it must not see the
# validation rows.

# %%
def best_rule_threshold(X, y, candidates):
    ### BEGIN SOLUTION
    y = np.asarray(y)
    accs = [np.mean(recency_rule(X, t) == y) for t in candidates]
    best = max(accs)
    return min(t for t, a in zip(candidates, accs) if a == best)
    ### END SOLUTION


# %%
grade("w05.best_rule_threshold", best_rule_threshold)

# %%
t_best = use(best_rule_threshold, X_train, y_train, list(range(0, 400, 15)))
rule_val = np.mean(use(recency_rule, X_val, t_best) == y_val)
print("best threshold on train:", t_best, "days;  rule accuracy on validation:", round(rule_val, 3))

# %% [markdown]
# The rule picks 120 days on the training rows and scores 0.577 on validation, 5 points above the dummy. That is
# the bar for a model.

# %% [markdown]
# ## 3 · First models in pipelines
#
# **Why.** On the scoring morning the model will meet customers from a city it never saw, or with no city at all.
# A notebook model that crashes on them is not a model the team can use.
#
# **Idea.** As in notebook 15, put the preprocessing *inside* a `Pipeline`, so that exactly the same steps run at
# fit time and at prediction time:
#
# - numeric columns: `StandardScaler` (subtract the training mean, divide by the training standard deviation);
# - categorical columns: `OneHotEncoder(handle_unknown="ignore")`: one 0/1 column per category seen in training;
#   an unknown category becomes all zeros instead of an error. A missing city is treated as its own category.
#
# Logistic regression in scikit-learn is **regularised** by default (a penalty on large weights, as in your theory
# course), which is one more reason to scale: the penalty treats all weights alike, so the features should be on
# comparable scales.

# %%
from sklearn.compose import make_column_transformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def make_preprocessor():
    return make_column_transformer(
        (StandardScaler(), NUMERIC),
        (OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
    )


logreg = make_pipeline(make_preprocessor(), LogisticRegression(max_iter=1000)).fit(X_train, y_train)
print("logistic regression: train", round(logreg.score(X_train, y_train), 3),
      " validation", round(logreg.score(X_val, y_val), 3))
new_customer = X_val.head(1).assign(city="Atyrau")       # a city not in the training data
print("score for an unseen city:", logreg.predict_proba(new_customer)[:, 1].round(3))

# %% [markdown]
# 0.704 on training and 0.634 on validation: 11 points above the dummy and 6 above the rule, with a modest gap
# between training and validation. The unseen city gets a probability (0.25) instead of an error.
#
# **Try it.** Remove `handle_unknown="ignore"` and run the cell again. Read the error message: this is what a
# production job would print at 6 a.m. Then put it back.

# %% [markdown]
# ### Exercise 4 · a reusable logistic-regression builder
#
# Write `make_logreg()` that **returns a new, unfitted** pipeline: the preprocessor above followed by
# `LogisticRegression(max_iter=1000)`. The grader fits it on the churn table, checks the validation ROC-AUC (a
# ranking score explained in notebook 19), customers with unseen or missing categories, and that changing the unit
# of a numeric column (for example spending in thousands) does not change the predictions.

# %%
def make_logreg():
    ### BEGIN SOLUTION
    return make_pipeline(make_preprocessor(), LogisticRegression(max_iter=1000))
    ### END SOLUTION


# %%
grade("w05.make_logreg", make_logreg)

# %% [markdown]
# ### Exercise 5 · a decision-tree builder
#
# Write `make_tree(max_depth)` returning a new, unfitted pipeline: the same preprocessor followed by
# `DecisionTreeClassifier(max_depth=max_depth, random_state=0)`. `max_depth=None` means "grow until every leaf is
# pure". (Trees do not need scaling, but keeping one preprocessor for every model is simpler and harmless.)

# %%
from sklearn.tree import DecisionTreeClassifier


def make_tree(max_depth):
    ### BEGIN SOLUTION
    return make_pipeline(make_preprocessor(), DecisionTreeClassifier(max_depth=max_depth, random_state=0))
    ### END SOLUTION


# %%
grade("w05.make_tree", make_tree)

# %% [markdown]
# ## 4 · The train/validation gap: $E_{in}$ and $E_{out}$ in practice
#
# **Why.** A model that is perfect on training data and mediocre on new data will disappoint in production. You
# need to see that *before* deployment, and know which way to move: more flexibility, or less.
#
# **Idea.** In *Learning from Data* terms, the training accuracy plays the role of $1 - E_{in}$ and the validation
# accuracy estimates $1 - E_{out}$. Two pictures tell you almost everything:
#
# - a **complexity curve**: training and validation scores as model flexibility grows (here: tree depth). Training
#   always improves; validation improves, peaks, then falls as the model starts fitting noise (overfitting);
# - a **learning curve**: both scores as the number of training rows grows. A big gap that shrinks with more data
#   means variance (more data will help); two low curves that meet early mean bias (a more flexible model or better
#   features will help, more rows will not).

# %%
full_tree = use(make_tree, None).fit(X_train, y_train)
print("unlimited tree: train", round(full_tree.score(X_train, y_train), 3),
      " validation", round(full_tree.score(X_val, y_val), 3))

# %% [markdown]
# The unlimited tree memorises the training set (accuracy 1.0) and drops to 0.618 on validation: a 38-point gap,
# the textbook picture of a small $E_{in}$ and a much larger $E_{out}$.

# %% [markdown]
# ### Exercise 6 · measure the gap
#
# Write `train_val_gap(model, X_tr, y_tr, X_val, y_val)`: fit `model` on the training rows, then return a dict
# `{"train": ..., "val": ..., "gap": ...}` with both accuracies (`model.score`) and `gap = train - val`.

# %%
def train_val_gap(model, X_tr, y_tr, X_val, y_val):
    ### BEGIN SOLUTION
    model.fit(X_tr, y_tr)
    train = float(model.score(X_tr, y_tr))
    val = float(model.score(X_val, y_val))
    return {"train": train, "val": val, "gap": train - val}
    ### END SOLUTION


# %%
grade("w05.train_val_gap", train_val_gap)

# %% [markdown]
# ### Exercise 7 · a depth curve
#
# Write `depth_curve(make_model, depths, X_tr, y_tr, X_val, y_val)`: for each depth in `depths` (in order), build
# a fresh model with `make_model(depth)`, fit it on the training rows and record the training and validation
# accuracy. Return a DataFrame with columns `depth`, `train_acc`, `val_acc`, one row per depth.

# %%
def depth_curve(make_model, depths, X_tr, y_tr, X_val, y_val):
    ### BEGIN SOLUTION
    rows = []
    for d in depths:
        m = make_model(d).fit(X_tr, y_tr)
        rows.append({"depth": d, "train_acc": m.score(X_tr, y_tr), "val_acc": m.score(X_val, y_val)})
    return pd.DataFrame(rows)
    ### END SOLUTION


# %%
grade("w05.depth_curve", depth_curve)

# %%
curve = use(depth_curve, make_tree, [1, 2, 3, 4, 5, 6, 8, 10, 15], X_train, y_train, X_val, y_val)
fig, ax = plt.subplots(figsize=(6, 3.5))
ax.plot(curve["depth"], curve["train_acc"], marker="o", label="training (1 - E_in)")
ax.plot(curve["depth"], curve["val_acc"], marker="o", label="validation (estimates 1 - E_out)")
ax.axhline(rule_val, color="gray", linestyle="--", label="recency rule (validation)")
ax.set_xlabel("max_depth")
ax.set_ylabel("accuracy")
ax.legend()
plt.show()
curve.round(3)

# %% [markdown]
# Training accuracy climbs steadily from 0.61 (depth 1) to 0.99 (depth 15). Validation accuracy rises to about
# 0.66 at depths 4-5 and then drifts back to 0.62 while the gap keeps growing. Note how small the validation set is
# (123 rows): one customer is almost a full point of accuracy, so do not over-read the wiggles (0.650 at depth 2,
# 0.626 at depth 3). Week 7 shows how to put error bars on numbers like these.
#
# **Try it.** Pass `[2, 4, 8]` and the *test* set instead of the validation set. Then explain to yourself why you
# must not use the result to choose the depth.

# %% [markdown]
# ### Exercise 8 · a learning curve
#
# Write `learning_curve_points(make_model, sizes, X_tr, y_tr, X_val, y_val)`: for each `n` in `sizes`, fit a fresh
# `make_model()` on the **first `n`** training rows (`.iloc[:n]`), and record its accuracy on those same `n` rows
# and on the full validation set. Return a DataFrame with columns `n_train`, `train_acc`, `val_acc`.

# %%
def learning_curve_points(make_model, sizes, X_tr, y_tr, X_val, y_val):
    ### BEGIN SOLUTION
    rows = []
    for n in sizes:
        Xn, yn = X_tr.iloc[:n], y_tr.iloc[:n]
        m = make_model().fit(Xn, yn)
        rows.append({"n_train": n, "train_acc": m.score(Xn, yn), "val_acc": m.score(X_val, y_val)})
    return pd.DataFrame(rows)
    ### END SOLUTION


# %%
grade("w05.learning_curve_points", learning_curve_points)

# %%
sizes = [30, 60, 100, 150, 200, 250, 300, 368]
lc_lr = use(learning_curve_points, make_logreg, sizes, X_train, y_train, X_val, y_val)
lc_tree = use(learning_curve_points, lambda: make_tree(None), sizes, X_train, y_train, X_val, y_val)
fig, axes = plt.subplots(1, 2, figsize=(10, 3.5), sharey=True)
for ax, lc, title in [(axes[0], lc_lr, "logistic regression"), (axes[1], lc_tree, "unlimited tree")]:
    ax.plot(lc["n_train"], lc["train_acc"], marker="o", label="training")
    ax.plot(lc["n_train"], lc["val_acc"], marker="o", label="validation")
    ax.set_title(title)
    ax.set_xlabel("training rows")
axes[0].set_ylabel("accuracy")
axes[0].legend()
plt.show()

# %% [markdown]
# Two different stories. For the logistic regression, training accuracy falls from 0.93 (30 rows are easy to fit)
# to 0.70, while validation wanders between 0.56 and 0.63: the curves approach each other, and the remaining gap is
# small. More rows of the *same* features would help a little; better features would help more. The unlimited
# tree stays at 1.0 on training at every size, with validation between 0.55 and 0.62: a wide gap that does not
# close, which is variance. This is the bias-variance picture from your theory course, drawn from real, noisy
# data: the validation points jump around by several points because the validation set is small.

# %% [markdown]
# ### Exercise 9 · diagnose
#
# From the numbers above, diagnose three models. Values: `"underfit"` (both scores low, close together, no better
# than the baselines), `"overfit"` (training much better than validation) or `"good_fit"` (validation clearly above
# the baselines, with a modest gap). Keys: `"dummy"`, `"full_tree"`, `"logreg"`.

# %%
### BEGIN SOLUTION
diagnosis = {"dummy": "underfit", "full_tree": "overfit", "logreg": "good_fit"}
### STARTER
diagnosis = {"dummy": "?", "full_tree": "?", "logreg": "?"}
### END SOLUTION

# %%
grade("w05.diagnosis", diagnosis)

# %% [markdown]
# ## 5 · Reading coefficients carefully
#
# **Why.** The first question after "does it work?" is "what drives churn?". Coefficients look like an answer,
# and are easy to misread in ways that lead a business into the wrong action.
#
# **Idea.** A logistic regression scores $\text{logit}(p) = w_0 + \sum_j w_j x_j$. After standardising, $w_j$ is
# the change in log-odds of churn for a **one standard deviation** increase in feature $j$, **holding the other
# features fixed**. Three cautions:
#
# 1. **Scale.** Without standardisation a coefficient's size depends on the feature's unit (days vs years), so
#    sizes are not comparable.
# 2. **Correlated features share credit.** `n_orders` and `total_spent` carry overlapping information; the model
#    can split the weight between them in many ways, and one may even get the "wrong" sign.
# 3. **Prediction is not causation.** A feature that predicts churn does not cause it. Customers with many tickets
#    may churn more, but closing tickets faster is not guaranteed to keep them: only an experiment can tell.
#
# For one-hot columns, each coefficient is relative to the others in its group (the encoder makes one column per
# category, so only differences between categories are meaningful).

# %% [markdown]
# ### Exercise 10 · a coefficient table
#
# Write `coef_table(pipeline)` for a **fitted** pipeline whose last step is a logistic regression. Return a DataFrame
# with columns `feature` and `coef`, one row per model input after preprocessing, sorted by the **absolute** value
# of `coef`, largest first, with a fresh index 0, 1, 2, ... The names come from
# `pipeline[:-1].get_feature_names_out()` (everything but the last step) and the weights from
# `pipeline[-1].coef_[0]`.

# %%
def coef_table(pipeline):
    ### BEGIN SOLUTION
    names = pipeline[:-1].get_feature_names_out()
    coef = pipeline[-1].coef_[0]
    t = pd.DataFrame({"feature": names, "coef": coef})
    return t.reindex(t["coef"].abs().sort_values(ascending=False).index).reset_index(drop=True)
    ### END SOLUTION


# %%
grade("w05.coef_table", coef_table)

# %%
use(coef_table, logreg).round(3).head(10)

# %% [markdown]
# Read it slowly; it is full of traps. (The prefixes `standardscaler__` and `onehotencoder__` say which part of the
# preprocessor produced each column.)
#
# - `n_orders` has the largest weight, negative: more orders, less risk. Plausible.
# - `tenure_days` is positive: *for the same number of orders*, a longer-standing customer buys less often.
# - `days_since_last_order`, the feature behind our recency rule, is near the bottom with a weight of about -0.06.
#   It is clearly predictive on its own, but it is correlated with `tenure_days` (0.43) and `n_orders` (-0.32), and
#   those two absorb its credit. Correlated features share credit (caution 2).
# - Several **cities** have large weights. Each city has only about 40 training customers; these weights are
#   mostly noise the model fitted. Before telling anyone "Shymkent customers are loyal", refit on another split and
#   see whether the weight survives.
#
# **Try it.** Fit the same pipeline *without* the `StandardScaler` (use `"passthrough"` instead) and print the table
# again. Which features jump to the top, and why does that say nothing about their importance?

# %% [markdown]
# ### Exercise 11 · true or false?
#
# Answer with a dict `{number: True or False}`.
#
# 1. Without scaling, the feature with the largest coefficient is the most important one.
# 2. A coefficient describes the change in log-odds for that feature while the other features are held fixed.
# 3. Because `n_tickets` has a positive coefficient, resolving tickets faster will reduce churn.
# 4. When two features carry almost the same information, their coefficients can be unstable and even have
#    surprising signs.
# 5. A positive coefficient for `segment_student` means students are more likely to churn than every other
#    customer, whatever the other one-hot coefficients are.

# %%
### BEGIN SOLUTION
coef_truths = {1: False, 2: True, 3: False, 4: True, 5: False}
### STARTER
coef_truths = {1: None, 2: None, 3: None, 4: None, 5: None}
### END SOLUTION

# %%
grade("w05.coef_statements", coef_truths)

# %% [markdown]
# ## 6 · Open the test set, once
#
# We chose the logistic regression on validation. Now, and only now, we report it on the locked test set,
# refitting on train + validation (more data, same choices), next to the baselines.

# %%
final = make_pipeline(make_preprocessor(), LogisticRegression(max_iter=1000)).fit(X_rest, y_rest)
t_final = use(best_rule_threshold, X_rest, y_rest, list(range(0, 400, 15)))
report = pd.Series({
    "majority class": use(majority_accuracy, y_rest, y_test),
    f"recency rule (> {t_final} days)": np.mean(use(recency_rule, X_test, t_final) == y_test),
    "logistic regression": final.score(X_test, y_test),
}, name="test accuracy")
report.round(3)

# %% [markdown]
# On the test set the logistic regression reaches 0.701, against 0.530 for the majority class and 0.573 for the
# recency rule. This is the number you would report, together with the two baselines: without them nobody could
# tell whether 0.70 is good. Notebook 19 asks whether accuracy is even the right number.

# %% [markdown]
# ## Quiz
#
# **Q1.** A fraud model has 99.2% accuracy. Only 0.8% of transactions are fraud. What do you conclude? (a) the
# model is excellent (b) nothing yet: predicting "never fraud" also scores 99.2%; compare with that baseline and
# use a better metric (c) the model is overfitting (d) accuracy above 99% proves the features are leaking

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w05.18_q1", answer)

# %% [markdown]
# **Q2.** Training accuracy 0.99, validation accuracy 0.61, and the learning curve shows the gap staying wide as rows
# are added. What is the most promising next step? (a) a more flexible model (b) a simpler or more regularised
# model, e.g. limit the depth (c) evaluate on the test set to be sure (d) remove the validation set and train on
# everything

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w05.18_q2", answer)

# %% [markdown]
# **Q3.** Training and validation accuracy are both 0.62, almost identical, and barely above the majority baseline.
# More rows of the same data would most likely... (a) help a lot, because the gap is small (b) help little: the
# model underfits, so better features or a more flexible model are needed (c) cause overfitting (d) make the
# validation score drop

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w05.18_q3", answer)

# %% [markdown]
# **Q4.** Why is the recency rule's threshold chosen on the training rows and not on the validation rows?
# (a) the validation set is too small (b) choosing the threshold is fitting; doing it on validation would make the
# rule's validation score optimistic, just like tuning on the test set (c) scikit-learn requires it (d) it makes no
# difference

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w05.18_q4", answer)

# %% [markdown]
# **Q5.** Why does the pipeline use `OneHotEncoder(handle_unknown="ignore")`? (a) it makes training faster (b) so
# that a category never seen in training (a new city) produces all-zero columns instead of an error at prediction
# time (c) it drops rare categories (d) it fills missing numeric values

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w05.18_q5", answer)

# %% [markdown]
# ## Recap
#
# - Report every model next to baselines: the majority class (`DummyClassifier`) and a simple rule.
# - Fitting a rule's threshold is learning: do it on training data, evaluate on validation.
# - Put preprocessing inside a pipeline; `handle_unknown="ignore"` keeps the model alive on new categories.
# - Training vs validation accuracy is $E_{in}$ vs an estimate of $E_{out}$: a complexity curve shows where
#   flexibility stops helping; a learning curve tells variance (wide gap) from bias (two low, close curves).
# - Coefficients: standardise first, read them "holding the rest fixed", expect correlated features to share
#   credit, and never read them as causes.
# - Choose on validation, then report once on the test set, with the baselines beside the model.
#
# **On the job.** A results table with a "majority class" row and a "simple rule" row is one of the clearest
# signs of an experienced ML engineer. It is also a safety net: when a new model suddenly beats the rule by 30
# points, the first suspect is leakage (Week 6), not genius.
#
# **Going further.** The [scikit-learn tool guide](../docs/tools/scikit-learn.md) covers pipelines and
# `DummyClassifier`. scikit-learn's own `learning_curve` and `validation_curve` functions compute the curves
# from this notebook with cross-validation. Next: notebook 19, metrics and thresholds that match decisions.

# %%
# Record your progress (optional; stored in progress/progress.json):
from mlcourse.progress import mark
# mark("18", "reading")
# mark("18", "guided")
