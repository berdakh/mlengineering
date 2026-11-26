# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/15_sklearn_pipelines.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 15 · scikit-learn pipelines
#
# **Week 4 · lesson · about 90 minutes**
#
# In your ML course you probably wrote models by hand, or called a library function once. On the job, nearly every
# Python ML project uses **scikit-learn** (imported as `sklearn`) for the parts around the model: splitting data,
# filling missing values, encoding categories, scaling, cross-validation. This notebook teaches it from zero, with
# one goal: a **pipeline** that turns raw customer rows into predictions, and that can only ever learn from training
# rows.
#
# **What you will learn in this notebook**
#
# - The estimator API: `fit`, `transform`, `predict`, and why every scikit-learn object speaks it.
# - `train_test_split` with a seed and stratification.
# - `SimpleImputer`, `OneHotEncoder`, `StandardScaler`, combined with `ColumnTransformer` and `Pipeline`.
# - Fitting on training data only, and how train and test accuracy relate to $E_{in}$ and $E_{out}$.
# - A first look at cross-validation with `cross_val_score`.
#
# **What you need:** notebooks 13 and 14 (the churn label and the features).
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
# The next cell is **given**: it builds the labelled churn table from notebooks 13-14 in one function (read it; it
# is the same logic, written compactly). As before, `use(your_function, ...)` runs your function, or the course's
# reference version with a note if you have not written it yet.

# %%
import numpy as np
import pandas as pd
from mlcourse.sql import sql

orders = sql("SELECT * FROM orders", "shop")
orders["order_date"] = pd.to_datetime(orders["order_date"])
items = sql("SELECT * FROM order_items", "shop")
customers = sql("SELECT * FROM customers", "shop")
customers["signup_date"] = pd.to_datetime(customers["signup_date"])
CUTOFF = pd.Timestamp("2025-09-30")


def churn_table(orders, items, customers, cutoff):
    """One row per active customer: the features from notebook 14, segment and city, and the churn label."""
    kept = orders[orders["status"] != "cancelled"].copy()
    line = items["quantity"] * items["unit_price"] * (1 - items["discount"])
    kept["value"] = kept["order_id"].map(line.groupby(items["order_id"]).sum())
    past = kept[kept["order_date"] <= cutoff]
    recent = past[past["order_date"] > cutoff - pd.Timedelta(days=90)]
    future = kept[(kept["order_date"] > cutoff) & (kept["order_date"] <= cutoff + pd.Timedelta(days=90))]
    table = pd.DataFrame(index=pd.Index(sorted(past["customer_id"].unique()), name="customer_id"))
    table["recency_days"] = (cutoff - past.groupby("customer_id")["order_date"].max()).dt.days
    table["orders_90d"] = recent.groupby("customer_id").size().reindex(table.index, fill_value=0)
    table["spend_90d"] = recent.groupby("customer_id")["value"].sum().reindex(table.index, fill_value=0.0)
    info = customers.set_index("customer_id")
    table["tenure_days"] = (cutoff - info["signup_date"]).dt.days
    table["segment"] = info["segment"]
    table["city"] = info["city"]  # has missing values on purpose: the pipeline will deal with them
    table["churned"] = (~table.index.isin(future["customer_id"])).astype(int)
    return table


table = churn_table(orders, items, customers, CUTOFF)
NUMERIC = ["recency_days", "orders_90d", "spend_90d", "tenure_days"]
CATEGORICAL = ["segment", "city"]
print(table.shape, "churn rate:", round(table["churned"].mean(), 3))
from mlcourse.graders.w04 import use
table.head()

# %% [markdown]
# You should see 860 rows and a churn rate of 0.472. Note that `city` is text and has missing values (35 of them),
# and `segment` is text: a model cannot use either directly. That is what this notebook fixes.
#
# ## 1. The estimator API: fit, transform, predict
#
# **Why.** scikit-learn has hundreds of classes, but they all behave the same way. Learn the pattern once and you can
# use any of them, and chain them together.
#
# **Idea.** Every scikit-learn object is an **estimator**: you create it with its settings, then call
#
# * `fit(X)` or `fit(X, y)`: **learn** from data. The learned values are stored on the object in attributes ending in
#   an underscore, like `mean_` or `coef_`.
# * `transform(X)` (for **transformers**, like a scaler): apply what was learned to any rows, returning new values.
# * `predict(X)` (for **models**, like logistic regression): apply what was learned to make predictions.
#
# `fit_transform(X)` is a shortcut for `fit(X)` then `transform(X)` on the same rows. `X` is a table (a DataFrame or
# a 2-D NumPy array, rows by columns) and `y` the labels, one per row.
#
# **See it.** `StandardScaler` learns each column's mean and standard deviation, then standardises.

# %%
import numpy as np
from sklearn.preprocessing import StandardScaler

X_small = np.array([[1.0, 200.0], [2.0, 100.0], [3.0, 300.0]])
scaler = StandardScaler()          # 1. create, with settings (here: the defaults)
scaler.fit(X_small)                # 2. learn
print("learned means:", scaler.mean_, " learned stds:", scaler.scale_.round(3))
print(scaler.transform(X_small).round(3))   # 3. apply

# %% [markdown]
# The learned means are `[2, 200]`; after `transform` every column has mean 0 and standard deviation 1.
#
# **Try it.** Call `scaler.transform(np.array([[10.0, 200.0]]))`. Predict the first number before you run it.

# %%
scaler.transform(np.array([[10.0, 200.0]]))

# %% [markdown]
# ### Exercise 1 · a fitted scaler
#
# Write `fitted_scaler(X)`: create a `StandardScaler`, fit it on `X`, and return the **fitted** scaler.

# %%
def fitted_scaler(X):
    ### BEGIN SOLUTION
    return StandardScaler().fit(X)
    ### END SOLUTION


# %%
grade("w04.fitted_scaler", fitted_scaler)

# %% [markdown]
# ### Exercise 2 · scale train and test correctly
#
# Write `scale_train_test(X_train, X_test)`: fit **one** scaler on `X_train` only, and return
# `(X_train_scaled, X_test_scaled)`, both transformed by that same scaler. (This is notebook 14's rule, done by
# scikit-learn.)

# %%
def scale_train_test(X_train, X_test):
    ### BEGIN SOLUTION
    scaler = StandardScaler().fit(X_train)
    return scaler.transform(X_train), scaler.transform(X_test)
    ### END SOLUTION


# %%
grade("w04.scale_train_test", scale_train_test)

# %% [markdown]
# ## 2. Splitting the data
#
# **Why.** You know from theory that the error on the data a model was trained on ($E_{in}$) is optimistic. To
# estimate the error on new customers ($E_{out}$) you need rows the model never saw: a **test set**, put aside
# before anything is fitted, and used once at the end.
#
# **Idea.** `train_test_split(X, y, test_size=0.25, random_state=0, stratify=y)` shuffles the rows and splits them:
#
# * `test_size=0.25` puts 25% of rows in the test set;
# * `random_state=0` fixes the shuffle, so you (and your colleagues) get the same split every run;
# * `stratify=y` keeps the churn rate the same in both parts, which matters for small or imbalanced data.
#
# It returns four things, in this order: `X_train, X_test, y_train, y_test`. The label column must **not** stay in
# `X`, or the model would simply read the answer.
#
# (Week 6 shows that a random split is not always right: for churn you will eventually train on an earlier cutoff
# and test on a later one. A random split is the standard starting point.)
#
# **See it.**

# %%
from sklearn.model_selection import train_test_split

X = table.drop(columns=["churned"])
y = table["churned"]
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, random_state=0, stratify=y)
print(len(X_tr), "train rows,", len(X_te), "test rows")
print("churn rate train / test:", round(y_tr.mean(), 3), round(y_te.mean(), 3))

# %% [markdown]
# You should see 645 train and 215 test rows, with churn rates 0.473 and 0.47.
#
# **Try it.** Remove `stratify=y` and change `random_state` a few times. How far apart do the two churn rates get?
#
# ### Exercise 3 · a reproducible, stratified split
#
# Write `split_train_test(df, label, test_size, seed)`: split the DataFrame `df` whose label column is named
# `label`. Return `X_train, X_test, y_train, y_test`, with the label removed from `X`, stratified on the label, and
# reproducible for a given `seed`.

# %%
def split_train_test(df, label, test_size, seed):
    ### BEGIN SOLUTION
    X = df.drop(columns=[label])
    y = df[label]
    return train_test_split(X, y, test_size=test_size, random_state=seed, stratify=y)
    ### END SOLUTION


# %%
grade("w04.split_train_test", split_train_test)

# %%
X_train, X_test, y_train, y_test = use(split_train_test, table, "churned", 0.25, 0)

# %% [markdown]
# ## 3. Transformers for each kind of column
#
# **Why.** Numeric and categorical columns need different treatment, and both may contain missing values today or
# tomorrow. scikit-learn has a transformer for each step, all with the same fit/transform API.
#
# **Idea.**
#
# * `SimpleImputer(strategy="median")` learns each column's median in `fit` and fills missing values with it in
#   `transform`. For text columns use `strategy="most_frequent"`.
# * `OneHotEncoder(handle_unknown="ignore")` learns the category list in `fit` and makes one 0/1 column per category in
#   `transform`. `handle_unknown="ignore"` turns a category never seen in training into all zeros. Without it, an
#   unseen category raises an error, and in production that means a crashed prediction job.
# * A `Pipeline([("name1", step1), ("name2", step2)])` chains steps: `fit` fits each step on the output of the
#   previous one. The whole pipeline is itself an estimator.
#
# **See it.** What happens with an unseen segment, without and with `handle_unknown="ignore"`:

# %%
import pandas as pd
from sklearn.preprocessing import OneHotEncoder

new_rows = pd.DataFrame({"segment": ["student", "enterprise"]})
try:
    OneHotEncoder().fit(X_train[["segment"]]).transform(new_rows)
except ValueError as err:
    print("ValueError:", err)

encoder = OneHotEncoder(handle_unknown="ignore").fit(X_train[["segment"]])
print("learned categories:", encoder.categories_[0].tolist())
print(encoder.transform(new_rows).toarray())

# %% [markdown]
# The second encoder turns the student into `[0, 0, 1]` and the unknown "enterprise" into `[0, 0, 0]`. (The
# encoder returns a *sparse* matrix, which stores only the non-zero values; `.toarray()` shows it as a normal
# array.)
#
# ### Exercise 4 · the numeric transformer
#
# Write `numeric_transformer()`: return a new, **unfitted** `Pipeline` that first imputes missing values with the
# median, then standardises.

# %%
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline


def numeric_transformer():
    ### BEGIN SOLUTION
    return Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
    ### END SOLUTION


# %%
grade("w04.numeric_transformer", numeric_transformer)

# %% [markdown]
# ### Exercise 5 · the categorical transformer
#
# Write `categorical_transformer()`: return a new, unfitted `Pipeline` that imputes missing values with the most
# frequent category, then one-hot encodes, ignoring unknown categories.

# %%
def categorical_transformer():
    ### BEGIN SOLUTION
    return Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                     ("onehot", OneHotEncoder(handle_unknown="ignore"))])
    ### END SOLUTION


# %%
grade("w04.categorical_transformer", categorical_transformer)

# %% [markdown]
# ## 4. ColumnTransformer and the full pipeline
#
# **Why.** You want *one* object that takes the raw table (numbers, text, gaps) and returns predictions, so that
# training, testing and production all run exactly the same steps.
#
# **Idea.** A `ColumnTransformer` sends each group of columns through its own transformer and puts the results side
# by side: `ColumnTransformer([("num", numeric_transformer(), NUMERIC), ("cat", categorical_transformer(),
# CATEGORICAL)])`. Columns you do not list are **dropped**, which also protects you from accidentally feeding an id
# or the label to the model. Then a `Pipeline` puts the preprocessor and a model in sequence.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c15-01.svg" alt="A ColumnTransformer sends numeric columns through an imputer and scaler, categorical columns through an imputer and one-hot encoder, and feeds the combined numbers to logistic regression" style="max-width:100%">
#
# ### Exercise 6 · the preprocessor
#
# Write `make_preprocessor(numeric_cols, categorical_cols)`: return an unfitted `ColumnTransformer` that applies
# your numeric transformer to `numeric_cols` and your categorical transformer to `categorical_cols`.

# %%
from sklearn.compose import ColumnTransformer


def make_preprocessor(numeric_cols, categorical_cols):
    ### BEGIN SOLUTION
    return ColumnTransformer([("num", numeric_transformer(), numeric_cols),
                              ("cat", categorical_transformer(), categorical_cols)])
    ### END SOLUTION


# %%
grade("w04.make_preprocessor", make_preprocessor)

# %%
prep = use(make_preprocessor, NUMERIC, CATEGORICAL)
prep.fit(X_train)
print(prep.transform(X_test).shape)
print(prep.get_feature_names_out().tolist())

# %% [markdown]
# 4 numeric columns plus 3 segment columns plus 8 city columns: 15 columns, no text, no gaps.
#
# ### Exercise 7 · the model pipeline
#
# Write `make_model_pipeline(numeric_cols, categorical_cols)`: a `Pipeline` with two steps, your preprocessor and
# then `LogisticRegression(max_iter=1000)` (`max_iter` gives the solver enough iterations to converge).

# %%
from sklearn.linear_model import LogisticRegression


def make_model_pipeline(numeric_cols, categorical_cols):
    ### BEGIN SOLUTION
    return Pipeline([("prep", make_preprocessor(numeric_cols, categorical_cols)),
                     ("model", LogisticRegression(max_iter=1000))])
    ### END SOLUTION


# %%
grade("w04.make_model_pipeline", make_model_pipeline)

# %% [markdown]
# ## 5. Fit on training rows only: E_in and E_out
#
# **Why.** The single most important habit in applied ML: nothing learns from the test rows. Not the model, not the
# scaler, not the imputer, not the category list. A pipeline makes this easy, because one `fit` call fits every step,
# and you only ever call it on training data.
#
# **Idea.** Call `pipe.fit(X_train, y_train)` once. Then `pipe.predict(X_train)` gives the training accuracy, an
# estimate of $1 - E_{in}$, and `pipe.predict(X_test)` the test accuracy, an estimate of $1 - E_{out}$. Expect the
# training number to be higher: in *Learning from Data* terms, the gap between them is the generalisation gap, and a
# large one signals overfitting. **Accuracy** is the share of correct predictions: `(predictions == truth).mean()`.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c15-02.svg" alt="Split first; fit the pipeline on train rows only; score on train gives E_in, score on the locked-away test rows estimates E_out" style="max-width:100%">
#
# ### Exercise 8 · train and test accuracy
#
# Write `train_test_accuracy(pipe, X_train, y_train, X_test, y_test)`: fit `pipe` on the training data, and return
# `(train_accuracy, test_accuracy)`. Afterwards, `pipe` must be the pipeline fitted on the training data.

# %%
def train_test_accuracy(pipe, X_train, y_train, X_test, y_test):
    ### BEGIN SOLUTION
    pipe.fit(X_train, y_train)
    train_acc = (pipe.predict(X_train) == y_train).mean()
    test_acc = (pipe.predict(X_test) == y_test).mean()
    return float(train_acc), float(test_acc)
    ### END SOLUTION


# %%
grade("w04.train_test_accuracy", train_test_accuracy)

# %%
pipe = use(make_model_pipeline, NUMERIC, CATEGORICAL)
train_acc, test_acc = use(train_test_accuracy, pipe, X_train, y_train, X_test, y_test)
baseline = (y_test == y_train.mode()[0]).mean()
print(f"train accuracy {train_acc:.3f} | test accuracy {test_acc:.3f} | always-'stays' baseline {baseline:.3f}")

# %% [markdown]
# You should see a training accuracy of 0.678, a test accuracy of 0.647 and a baseline of 0.530. The model beats the
# baseline, and the train number is higher than the test number, as theory predicts. With 215 test rows, one
# customer is worth about half a percentage point, so these numbers are rough (Week 7 measures that uncertainty).
#
# **Try it.** The pipeline handles rows it has never seen, even with an unknown segment and a missing city:

# %%
odd = X_test.head(2).copy()
odd["segment"] = ["enterprise", "student"]
odd["city"] = [None, "Atlantis"]
pipe.predict_proba(odd).round(3)

# %% [markdown]
# Each row gets two probabilities (stays, churns) that add up to 1, without an error.
#
# ## 6. A preview of cross-validation
#
# **Why.** One test split gives one number, and with a few hundred rows that number moves a lot depending on which
# rows happened to land in the test set. Before touching the test set, you often want a more stable estimate from
# the training data alone, for example to compare two pipelines.
#
# **Idea.** **k-fold cross-validation** cuts the training rows into $k$ parts (folds). It fits the pipeline $k$ times,
# each time on $k-1$ folds, and scores on the fold left out. `cross_val_score(pipe, X, y, cv=..., scoring="accuracy")`
# returns the $k$ scores. `StratifiedKFold(n_splits=5, shuffle=True, random_state=0)` keeps the churn rate the same in
# every fold and makes the folds reproducible. Because the whole pipeline is refitted in each fold, the imputer and
# scaler never see the fold they are scored on. Week 6 covers validation in depth.
#
# ### Exercise 9 · cross-validated accuracy
#
# Write `cv_accuracy(estimator, X, y, k, seed)`: return the array of $k$ accuracy scores from stratified, shuffled
# k-fold cross-validation with `random_state=seed`.

# %%
from sklearn.model_selection import StratifiedKFold, cross_val_score


def cv_accuracy(estimator, X, y, k, seed):
    ### BEGIN SOLUTION
    folds = StratifiedKFold(n_splits=k, shuffle=True, random_state=seed)
    return cross_val_score(estimator, X, y, cv=folds, scoring="accuracy")
    ### END SOLUTION


# %%
grade("w04.cv_accuracy", cv_accuracy)

# %%
scores = use(cv_accuracy, use(make_model_pipeline, NUMERIC, CATEGORICAL), X_train, y_train, 5, 0)
print("fold accuracies:", scores.round(3), " mean:", round(scores.mean(), 3), " std:", round(scores.std(), 3))

# %% [markdown]
# You should see five accuracies between 0.636 and 0.698. A spread of six points between folds is a useful
# reminder of how noisy a single small test set is.
#
# ## Quiz
#
# **Q1.** Which description of the estimator API is right?
#
# - a) `fit` learns parameters from data, `transform` applies them to any rows, `predict` uses a fitted model.
# - b) `transform` learns new parameters every time it is called.
# - c) `predict` re-fits the model on the rows it is given.
# - d) `fit_transform` does something different from `fit` followed by `transform`.

# %%
### BEGIN SOLUTION
answer = "a"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w04.15_q1", answer)

# %% [markdown]
# **Q2.** Your pipeline has a training accuracy of 0.68 and a test accuracy of 0.65. Which statement is right?
#
# - a) The training number is the better measure of the model, because it uses more rows.
# - b) Any gap between the two numbers is a bug.
# - c) Training accuracy estimates $1 - E_{in}$ and is optimistic; the test accuracy estimates performance on new
#   customers ($1 - E_{out}$).
# - d) Only one of them should ever be computed.

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w04.15_q2", answer)

# %% [markdown]
# **Q3.** Why put the imputer and scaler *inside* the pipeline instead of applying them to the whole table first?
#
# - a) Pipelines make models more accurate.
# - b) Then every `fit` (including each cross-validation fold) learns them from training rows only, so validation
#   rows never leak into preprocessing.
# - c) Then you no longer need a test set.
# - d) Because only linear models accept pipelines.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w04.15_q3", answer)

# %% [markdown]
# **Q4.** What does `OneHotEncoder(handle_unknown="ignore")` do with a city that never appeared in training?
#
# - a) It learns the new city and adds a column.
# - b) It drops the row.
# - c) It maps it to the most common city.
# - d) It encodes it as all zeros in the city columns, instead of raising an error.

# %%
### BEGIN SOLUTION
answer = "d"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w04.15_q4", answer)

# %% [markdown]
# **Q5.** Five-fold cross-validation gave accuracies from 0.64 to 0.70. What is the main thing it tells you that one
# split does not?
#
# - a) It makes the model better.
# - b) How much the score depends on which rows are held out: one split hides this variability.
# - c) The score on the test set.
# - d) The training accuracy.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w04.15_q5", answer)

# %% [markdown]
# ## Recap
#
# - Every scikit-learn object is an estimator: create with settings, `fit` to learn, `transform` or `predict` to apply.
# - `train_test_split(..., random_state=seed, stratify=y)` gives a reproducible split with equal class balance.
# - `SimpleImputer`, `StandardScaler` and `OneHotEncoder(handle_unknown="ignore")` cover missing values, scale and
#   categories.
# - `ColumnTransformer` routes columns to the right transformer and drops the rest; `Pipeline` chains steps into one
#   estimator.
# - Fit the pipeline on training rows only; train accuracy relates to $E_{in}$, test accuracy estimates $E_{out}$.
# - `cross_val_score` with `StratifiedKFold` gives $k$ scores and shows how noisy one split is.
#
# ## On the job
#
# A fitted pipeline is the unit that gets saved, tested and deployed (Weeks 8-9): the same object that was scored on
# the test set is loaded by the prediction service, so preprocessing cannot drift between training and production.
# Code reviewers look for exactly two things in modelling code: is anything fitted before the split, and does the
# pipeline survive unexpected input? You now know how to make both answers "yes, it is safe".
#
# ## Going further
#
# - Tool guide: [scikit-learn](../docs/tools/scikit-learn.md).
# - Week 6 goes deeper: notebook 21 · Validation done right.
# - Next: [16 · Lab: a feature pipeline for churn](16_lab_feature_pipeline.ipynb).

# %% [markdown]
# ## Record your progress

# %%
from mlcourse.progress import mark

# mark("15", "reading")
# mark("15", "guided")
