# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/22_leakage.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 22 · Leakage: how good models lie
#
# **Week 6 · lesson · about 90 minutes**
#
# **Leakage** is information that reaches the model during training or validation but will **not** be available when
# the model makes real predictions. A leaky model looks excellent in the notebook and disappoints in production, and
# nothing crashes to warn you. It is the most common reason a model's promised performance never materialises. This
# notebook gives you a field guide: what leakage looks like, five places it hides, cheap tests that find it, and the
# habits that prevent it.
#
# **What you will learn in this notebook**
#
# - The "too good to be true" check and single-feature probes that point at suspicious columns.
# - Target leakage: features computed after the outcome, and how a data dictionary with dates catches them.
# - Preprocessing fitted on all rows (selection, encoding, scaling), and why pipelines prevent it.
# - Duplicates across splits, and group and time leakage seen as one family.
# - Split-first discipline and a leakage report you can run on any split.
#
# **What you need:** notebook 21 (grouped and time-based splits), notebook 15 (pipelines) and notebook 19 (ROC AUC).
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
# Leakage comes in two families: **leaky features** (a column that secretly contains the answer) and **leaky
# evaluation** (the split or the preprocessing lets test information into training). The map for this notebook:
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c22-01.svg" alt="Leakage has two families. Leaky features: target leakage, a feature computed after the outcome. Leaky evaluation: preprocessing fitted on all rows, duplicates across splits, the same group on both sides, training on the future. Each has a test and a fix." style="max-width:100%">

# %%
import warnings

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler

from mlcourse.validation_data import make_churn_with_leak, make_noise
from mlcourse.graders.w06 import use

warnings.filterwarnings("ignore", category=UserWarning)

churn = make_churn_with_leak()      # synthetic: one row per customer of a subscription service
FEATURES = ["tenure_months", "orders_90d", "spend_90d", "tickets_90d", "discount_share", "retention_call"]
cv = StratifiedKFold(5, shuffle=True, random_state=0)
model = make_pipeline(StandardScaler(), LogisticRegression())
auc = cross_val_score(model, churn[FEATURES], churn["churned"], cv=cv, scoring="roc_auc").mean()
print(churn.shape, " churn rate:", churn["churned"].mean(), f" cross-validated AUC: {auc:.3f}")
churn.head()

# %% [markdown]
# 1,500 customers, a churn rate of 0.34, and a cross-validated AUC of **0.962** from a plain logistic regression. If
# your team's best churn model so far scored 0.70, this should worry you, not please you.
#
# ## 1. "Too good to be true" and single-feature probes
#
# **Why.** Leakage never announces itself. The first symptom is a score that is better than anything you have seen
# on a similar problem, and the cheapest reaction is to ask: *which column is doing the work?*
#
# **Idea.** Two habits:
#
# 1. **Compare with what is plausible**: an earlier model, a published benchmark, a colleague's intuition, a simple
#    baseline. A jump from 0.70 to 0.96 without a new data source is almost always leakage.
# 2. **Probe single features**: compute the ROC AUC of each column *on its own*, using its raw values as the score.
#    An AUC of 0.5 means the column alone ranks churners no better than a coin; 1.0 means it separates them
#    perfectly. A column that falls as churn rises gives an AUC below 0.5, so report $\max(AUC, 1 - AUC)$: the
#    strength regardless of direction. Real features rarely exceed 0.75 alone; a single column above 0.9 deserves
#    a hard look.
#
# **See it.**

# %%
for col in FEATURES:
    a = roc_auc_score(churn["churned"], churn[col])
    print(f"{col:16s} AUC alone: {max(a, 1 - a):.3f}")

# %% [markdown]
# Five columns score between 0.555 and 0.643 alone, which is typical. `retention_call` scores **0.941**. One column
# that almost replaces the whole model is the signature of a leak.
#
# **Try it.** Probe `customer_id` the same way. An ID should score about 0.5. When would an ID score high, and what
# would that tell you about how the table was built?

# %%
# your experiment here

# %% [markdown]
# ### Exercise 1 · the AUC of one feature
#
# Write `single_feature_auc(x, y)` for two pandas Series. Drop the rows where `x` is missing (`keep = x.notna()`).
# If the remaining `y` has fewer than two classes, return `0.5` (no ranking is possible). Otherwise compute
# `roc_auc_score(y, x)` on the kept rows and return `max(auc, 1 - auc)` as a float.

# %%
def single_feature_auc(x, y):
    ### BEGIN SOLUTION
    keep = x.notna()
    x, y = x[keep], y[keep]
    if y.nunique() < 2:
        return 0.5
    auc = roc_auc_score(y, x)
    return float(max(auc, 1 - auc))
    ### END SOLUTION


# %%
grade("w06.single_feature_auc", single_feature_auc)

# %% [markdown]
# ### Exercise 2 · probe every feature
#
# Write `probe_features(df, target)`: for every **numeric** column except `target`
# (`df.select_dtypes("number").columns`), compute `single_feature_auc(df[col], df[target])`. Return a pandas Series
# (index = column name, value = AUC) sorted from the highest AUC to the lowest.

# %%
def probe_features(df, target):
    ### BEGIN SOLUTION
    cols = [c for c in df.select_dtypes("number").columns if c != target]
    probe = pd.Series({c: single_feature_auc(df[c], df[target]) for c in cols})
    return probe.sort_values(ascending=False)
    ### END SOLUTION


# %%
grade("w06.probe_features", probe_features)

# %% [markdown]
# ### Exercise 3 · flag suspicious columns
#
# Write `suspicious_features(df, target, threshold)`: return a **list** of the column names whose probe AUC is
# `>= threshold`, most suspicious first. (Use your `probe_features`.)

# %%
def suspicious_features(df, target, threshold):
    ### BEGIN SOLUTION
    probe = probe_features(df, target)
    return list(probe[probe >= threshold].index)
    ### END SOLUTION


# %%
grade("w06.suspicious_features", suspicious_features)

# %%
use(probe_features, churn, "churned").round(3)

# %% [markdown]
# A probe only says *where to look*. A strong column may be perfectly legitimate (a fraud model's "amount"), and a
# leak may be spread over several weaker columns. The next step is always to ask **when** a column's value is known.
#
# ## 2. Target leakage: features computed after the outcome
#
# **Why.** A model is used at a **prediction time**: the day you score customers to decide whom to call. Any feature
# must be known at that moment. A column filled in later, because of the outcome, is called **target leakage**.
#
# **Idea.** Draw the timeline. Features must come from the left of the prediction time; the label comes from the
# label window on the right. In this table, `retention_call` is 1 when the retention team phoned the customer, which
# they do *after* the customer asks to cancel. It is a consequence of churn, not a cause, and on the scoring day it
# does not exist yet.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c22-02.svg" alt="A timeline: history before the prediction time gives safe features; the label window after it gives the label; a column recorded inside or after the label window, such as a retention call or a refund, is target leakage" style="max-width:100%">
#
# Typical examples: a refund flag in a fraud model (refunds follow confirmed fraud), "days since last login" measured
# on the export date in a churn model, a diagnosis code in a model meant to predict that diagnosis, an "account
# closed" date. The defence is a **data dictionary** with a `known_at` column for every feature, and a rule: only use
# features known on or before the prediction date.
#
# **See it.** Drop the leaky column and the score becomes believable.

# %%
honest = cross_val_score(model, churn[FEATURES[:-1]], churn["churned"], cv=cv, scoring="roc_auc").mean()
print(f"without retention_call: AUC {honest:.3f}")
pd.crosstab(churn["retention_call"], churn["churned"])

# %% [markdown]
# The AUC drops from 0.962 to 0.686, in line with what churn models usually achieve. The cross-table shows why: 466
# of the 510 churners got a retention call, against 31 of the 990 who stayed.
#
# ### Exercise 4 · features known at prediction time
#
# Write `available_features(data_dict, prediction_date)`. `data_dict` is a DataFrame with columns `feature` and
# `known_at` (a date string like `"2025-06-30"`, or missing when nobody knows). Return the list of features whose
# `known_at` is **on or before** `prediction_date`, in the order of the dictionary. A feature with a missing date is
# **not** available. Tip: `pd.to_datetime(data_dict["known_at"]) <= pd.Timestamp(prediction_date)` is `False` for
# missing dates.

# %%
def available_features(data_dict, prediction_date):
    ### BEGIN SOLUTION
    known = pd.to_datetime(data_dict["known_at"]) <= pd.Timestamp(prediction_date)
    return list(data_dict.loc[known, "feature"])
    ### END SOLUTION


# %%
grade("w06.available_features", available_features)

# %% [markdown]
# ## 3. Preprocessing fitted on all rows
#
# **Why.** Week 4 taught "fit on training rows only" for scalers and imputers. The rule matters most for steps that
# look at the **labels**: choosing features, encoding categories with label means, picking thresholds. Fitted on all
# rows, they quietly use the validation labels.
#
# **Idea.** Here is pure noise: 200 rows, 2,000 random features, a random label. Nothing can be predicted, so an
# honest estimate is about 0.5. A common shortcut is "keep the 20 features most related to the label, then
# cross-validate". With 2,000 noise columns, some are related to the label *by chance in these 200 rows*, including
# the validation rows. Selecting them on all rows bakes that chance into every fold.
#
# **See it.**

# %%
from sklearn.feature_selection import SelectKBest, f_classif

X_noise, y_noise = make_noise()
selected = SelectKBest(f_classif, k=20).fit(X_noise, y_noise)        # LEAKY: selection saw every row's label
leaky = cross_val_score(LogisticRegression(max_iter=1000), selected.transform(X_noise), y_noise, cv=cv).mean()
inside = Pipeline([("select", SelectKBest(f_classif, k=20)), ("model", LogisticRegression(max_iter=1000))])
honest_noise = cross_val_score(inside, X_noise, y_noise, cv=cv).mean()     # selection refitted in every fold
print(f"selection on all rows: accuracy {leaky:.3f}    selection inside the pipeline: {honest_noise:.3f}")

# %% [markdown]
# 0.765 accuracy on pure noise, against 0.520 when selection happens inside each fold. Same code, same data, one line
# moved. With a `Pipeline`, `cross_val_score` refits **every** step on the training part of each fold, so the
# validation rows are never seen by anything.
#
# Scaling and imputing on all rows leak too, but usually only a little, because they ignore the labels. It is still
# worth the habit: inside a pipeline the question disappears.
#
# ### Exercise 5 · selection inside the pipeline
#
# Write `make_selection_pipeline(k)`: return an **unfitted** `Pipeline` with a step `SelectKBest(f_classif, k=k)`
# followed by `LogisticRegression(max_iter=1000)`. The grader cross-validates it on noise and on real signal.

# %%
def make_selection_pipeline(k):
    ### BEGIN SOLUTION
    return Pipeline([("select", SelectKBest(f_classif, k=k)), ("model", LogisticRegression(max_iter=1000))])
    ### END SOLUTION


# %%
grade("w06.selection_pipeline", make_selection_pipeline)

# %% [markdown]
# ### Exercise 6 · target encoding, the safe way
#
# **Target encoding** replaces a category (a city, a product) by the mean label of that category: a compact way to use
# columns with hundreds of values. Fitted on all rows, it hands each row its own label. Write
# `target_encode(train_cat, train_y, test_cat)`:
#
# 1. `means = train_y.groupby(train_cat).mean()` (training rows only; missing categories are skipped);
# 2. `overall = train_y.mean()`;
# 3. encode with `train_cat.map(means)` and `test_cat.map(means)`, then `.fillna(overall)` for categories that are
#    missing or never seen in training;
# 4. return `(train_encoded, test_encoded)`.

# %%
def target_encode(train_cat, train_y, test_cat):
    ### BEGIN SOLUTION
    means = train_y.groupby(train_cat).mean()
    overall = train_y.mean()
    return train_cat.map(means).fillna(overall), test_cat.map(means).fillna(overall)
    ### END SOLUTION


# %%
grade("w06.target_encode", target_encode)

# %% [markdown]
# (The training rows are still encoded with means that include their own label, a milder leak. Production code uses
# out-of-fold means or scikit-learn's `TargetEncoder`, which does this for you inside a pipeline.)
#
# ## 4. Duplicates across splits
#
# **Why.** Exports get appended twice, events are logged by two systems, a customer signs up again with the same
# details. Duplicate rows are common, and a random split sends one copy to training and the other to test.
#
# **Idea.** A flexible model memorises training rows. Scored on exact copies of them, it looks brilliant. The fix is
# boring and effective: **de-duplicate first, then split**, and count rows shared between train and test as a check.
#
# **See it.** The churn table without the leaky column, then the same table with 30% of its rows appended again; a
# random forest (which can memorise) scored on a random 25% test set.

# %%
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

clean = churn.drop(columns=["customer_id", "retention_call"])
copies = pd.concat([clean, clean.sample(frac=0.3, random_state=0)]).reset_index(drop=True)
forest = RandomForestClassifier(n_estimators=200, random_state=0, n_jobs=-1)
for name, table in [("unique rows", clean), ("with 30% copies", copies)]:
    tr, te = train_test_split(table, test_size=0.25, random_state=0)
    forest.fit(tr[FEATURES[:-1]], tr["churned"])
    score = roc_auc_score(te["churned"], forest.predict_proba(te[FEATURES[:-1]])[:, 1])
    shared = len(te.merge(tr.drop_duplicates(), how="inner"))
    print(f"{name:16s} rows {len(table):5d}   test AUC {score:.3f}   test rows copied in train: {shared}")

# %% [markdown]
# Unique rows: test AUC 0.596. With copies: 0.895, because 224 test rows have an exact copy in training. Nothing
# about the model changed; only the test set got easier.
#
# **Try it.** Replace the forest with `make_pipeline(StandardScaler(), LogisticRegression())`. Does the duplicate
# effect shrink? Why would a simpler model be less affected?

# %%
# your experiment here

# %% [markdown]
# ### Exercise 7 · count rows shared between train and test
#
# Write `count_shared_rows(train_df, test_df)`: the number of **test** rows that have an exact copy (all columns
# equal) somewhere in `train_df`. A test row that appears twice counts twice; a train row that appears twice must not
# double-count. Tip: `test_df.merge(train_df.drop_duplicates(), how="inner")` keeps exactly the test rows with a copy.

# %%
def count_shared_rows(train_df, test_df):
    ### BEGIN SOLUTION
    return len(test_df.merge(train_df.drop_duplicates(), how="inner"))
    ### END SOLUTION


# %%
grade("w06.count_shared_rows", count_shared_rows)

# %% [markdown]
# ### Exercise 8 · de-duplicate, then split
#
# Write `dedupe_then_split(df, test_fraction, seed)`: drop exact duplicate rows, then
# `train_test_split(..., test_size=test_fraction, random_state=seed)`. Return `(train_df, test_df)`.

# %%
def dedupe_then_split(df, test_fraction, seed):
    ### BEGIN SOLUTION
    unique = df.drop_duplicates()
    return train_test_split(unique, test_size=test_fraction, random_state=seed)
    ### END SOLUTION


# %%
grade("w06.dedupe_then_split", dedupe_then_split)

# %% [markdown]
# ## 5. One family, one discipline
#
# **Why.** Notebook 21's grouped and time leaks are the same disease as duplicates: test rows that are not really
# new. You now have five kinds of leakage; you need one routine that catches them all.
#
# **Idea.** Leakage of every kind means the validation rows are not like the rows of prediction day. Four habits
# prevent nearly all of it:
#
# 1. **Write down the prediction time** and give every feature a `known_at`; drop what comes later.
# 2. **Split first.** Decide the split (grouped, forward in time, de-duplicated) before any exploration that uses the
#    labels, and lock the test set away.
# 3. **Put every fitted step in the pipeline**: imputing, scaling, encoding, selecting, and the model.
# 4. **Check the split** with a small report: groups on both sides, training rows dated after the test period, copies.
#
# | leak | quick test | fix |
# |---|---|---|
# | feature known after the outcome | probe AUC, `known_at` vs prediction time | drop it |
# | preprocessing on all rows | compare with the step inside a pipeline | pipeline |
# | duplicates | count shared rows | de-duplicate, then split |
# | same group on both sides | groups on both sides | `GroupKFold` |
# | training on the future | training dates after the first test date | forward-in-time split |
#
# ### Exercise 9 · a leakage report for any split
#
# Write `leakage_report(df, train_idx, test_idx, group_col, date_col)` (positions, as in notebook 21). Return a dict
# with three integer counts:
#
# - `"shared_groups"`: the number of distinct values of `group_col` that appear in both train and test;
# - `"train_rows_after_test_start"`: the number of training rows whose `date_col` is **after** the earliest test date;
# - `"duplicated_rows"`: the number of test rows with an exact copy in train (your `count_shared_rows`).

# %%
def leakage_report(df, train_idx, test_idx, group_col, date_col):
    ### BEGIN SOLUTION
    train, test = df.iloc[train_idx], df.iloc[test_idx]
    return {
        "shared_groups": len(set(train[group_col]) & set(test[group_col])),
        "train_rows_after_test_start": int((train[date_col] > test[date_col].min()).sum()),
        "duplicated_rows": count_shared_rows(train, test),
    }
    ### END SOLUTION


# %%
grade("w06.leakage_report", leakage_report)

# %% [markdown]
# **Try it.** Build a tiny table with a `store`, a `date` and a value, split it with `train_test_split`, and run your
# report. Then split it by date instead and run it again.

# %%
# your experiment here

# %% [markdown]
# ## Quiz
#
# **Q1.** Your new churn model scores AUC 0.99; the team's best ever was 0.75. What do you do first?
#
# - a) Ship it: the new features clearly work.
# - b) Probe single features and check when each top feature becomes known.
# - c) Tune the hyperparameters to see if it goes even higher.
# - d) Add more features to make it robust.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w06.22_q1", answer)

# %% [markdown]
# **Q2.** Which column is target leakage in a model that flags fraudulent transactions at the moment they happen?
#
# - a) The age of the customer's account.
# - b) The number of transactions on the card in the previous 24 hours.
# - c) Whether the transaction was later refunded.
# - d) The country where the transaction took place.

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w06.22_q2", answer)

# %% [markdown]
# **Q3.** You keep the 20 features (of 2,000) most related to the label using all rows, then cross-validate, and get
# 0.77 accuracy on data that is pure noise. Why?
#
# - a) Selection used every row's label, so it picked features that fit the noise in the validation rows too.
# - b) Logistic regression overfits with 20 features.
# - c) Five folds are too few.
# - d) The data must contain some real signal after all.

# %%
### BEGIN SOLUTION
answer = "a"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w06.22_q3", answer)

# %% [markdown]
# **Q4.** A colleague standardises all rows with `StandardScaler` before splitting. What is the best description?
#
# - a) No leak at all, because the scaler never sees the labels.
# - b) A serious leak that makes all results meaningless.
# - c) It makes the estimate pessimistic.
# - d) Usually a small leak (test-row statistics reach training); in a pipeline it costs nothing, so fix it anyway.

# %%
### BEGIN SOLUTION
answer = "d"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w06.22_q4", answer)

# %% [markdown]
# **Q5.** 15% of the rows are exact duplicates and you split at random. What happens to the test score?
#
# - a) Nothing: duplicates do not affect evaluation.
# - b) It is optimistic: copies of training rows sit in the test set, most of all for models that can memorise.
# - c) It is pessimistic, because the model is confused by repeated rows.
# - d) Only the training time changes.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w06.22_q5", answer)

# %% [markdown]
# ## Recap
#
# - Leakage is information during training or validation that will not exist at prediction time; it makes scores lie.
# - A score far above what is plausible is the first symptom; single-feature probes point at the culprit.
# - Target leakage is a feature recorded after the outcome; a data dictionary with `known_at` dates catches it.
# - Any step fitted on all rows (selection, target encoding, scaling) leaks; inside a `Pipeline` it cannot.
# - Duplicates, shared groups and training on the future all make test rows "not really new".
# - Discipline: prediction time first, split first, everything fitted in the pipeline, and a leakage report on the split.
#
# ## On the job
#
# Leakage reviews are routine before a model ships: a teammate reads the feature list with the data dictionary, asks
# for the single-feature probe, and checks how the split was made. Many teams keep a "suspiciously good" threshold:
# any result that beats the current model by a wide margin needs a written explanation before anyone celebrates.
# Finding a leak before launch is a win; explaining one after launch is a much harder conversation.
#
# ## Going further
#
# - Tool guide: [scikit-learn](../docs/tools/scikit-learn.md): pipelines and `TargetEncoder`.
# - scikit-learn's page on [common pitfalls](https://scikit-learn.org/stable/common_pitfalls.html), with more leakage
#   examples.
# - Next: [23 · Hyperparameter search without fooling yourself](23_hyperparameter_search.ipynb).

# %% [markdown]
# ## Record your progress

# %%
from mlcourse.progress import mark

# mark("22", "reading")
# mark("22", "guided")
