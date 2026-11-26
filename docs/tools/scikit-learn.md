---
title: "scikit-learn"
parent: Tool guides
nav_order: 8
---

# scikit-learn

scikit-learn (imported as `sklearn`) is the standard Python library for classical machine learning: linear and
logistic models, trees and ensembles, nearest neighbours, clustering, and, just as important for an engineer,
everything around the model: splitting data, filling missing values, encoding categories, scaling, pipelines,
cross-validation and metrics. This guide covers the parts used from Week 4 onwards.

## What it is, and why teams use it

Your ML course taught you what a model *is*. In practice the model is a small part of the code; most of it prepares
data and evaluates results. scikit-learn gives all of these pieces **one shared interface**, so they can be swapped
and chained, and it is careful about correctness (for example, it makes it easy to learn preprocessing only from
training rows). Even teams that train deep networks use scikit-learn for baselines, preprocessing and metrics.

## Opening it

**In Google Colab** it is preinstalled. Import the pieces you need:

```python
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
```

**On your own computer**: `python -m pip install scikit-learn` (note the package name differs from the import name).
Check the version with `import sklearn; print(sklearn.__version__)`; this course was tested with 1.9.

## The estimator API: one pattern for everything

Every scikit-learn object is an **estimator**, used in three steps:

1. **Create** it with its settings (called *hyperparameters*): `model = LogisticRegression(C=1.0, max_iter=1000)`.
   Nothing is learned yet.
2. **Fit** it to data: `model.fit(X, y)` (or `fit(X)` for things that need no labels, like a scaler). Learned values
   are stored as attributes ending in an underscore: `model.coef_`, `scaler.mean_`, `encoder.categories_`.
3. **Use** it:
   * `transform(X)` for **transformers** (scalers, imputers, encoders): returns new features;
   * `predict(X)` for **models**: returns predicted labels; `predict_proba(X)` returns class probabilities, one
     column per class (for churn: column 0 = "stays", column 1 = "churns").

`fit_transform(X)` is `fit(X)` followed by `transform(X)` on the same rows. Use it on training data only.

Shapes: `X` is two-dimensional (rows × columns), a pandas DataFrame or a NumPy array. `y` is one-dimensional, one
label per row. A single column must stay two-dimensional: `X[["segment"]]` (a DataFrame), not `X["segment"]`.

```python
import numpy as np
from sklearn.preprocessing import StandardScaler

X = np.array([[1.0, 200.0], [2.0, 100.0], [3.0, 300.0]])
scaler = StandardScaler().fit(X)
print(scaler.mean_)          # [  2. 200.]
print(scaler.transform(X))   # each column now has mean 0, standard deviation 1
```

## Splitting data

```python
from sklearn.model_selection import train_test_split

X = table.drop(columns=["churned"])
y = table["churned"]
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=0, stratify=y)
```

* `test_size=0.25`: a quarter of the rows go to the test set.
* `random_state=0`: fixes the random shuffle so the split is the same every run. Any integer works; what matters is
  that it is fixed.
* `stratify=y`: the class balance is the same in both parts.
* The order of the four outputs is always `X_train, X_test, y_train, y_test`.

Split **before** fitting anything, and keep the test set for the final check. Week 6 covers splits that respect
time and groups, which real problems often need.

## Preprocessing

| Problem | Transformer | Learns in `fit` |
|---|---|---|
| missing numbers | `SimpleImputer(strategy="median")` | each column's median |
| missing categories | `SimpleImputer(strategy="most_frequent")` | each column's most common value |
| text categories | `OneHotEncoder(handle_unknown="ignore")` | the list of categories per column |
| different scales | `StandardScaler()` | each column's mean and standard deviation |
| missing-value flags | `SimpleImputer(..., add_indicator=True)` | which columns had missing values |

`OneHotEncoder(handle_unknown="ignore")` turns a category never seen during `fit` into all zeros. Without it,
`transform` raises `ValueError: Found unknown categories`, which in production means a failed prediction. The
encoder returns a **sparse matrix** (only non-zero values are stored); models accept it directly, and
`.toarray()` shows it as an ordinary array.

## Pipelines and ColumnTransformer

A **Pipeline** chains steps into one estimator. `fit` fits each step in turn on the output of the previous one;
`predict` runs the data through every fitted step and the model.

A **ColumnTransformer** applies different transformers to different columns and puts the results side by side.
Columns not listed are dropped (by default), which protects you from feeding an id or the label to the model.

```python
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

NUMERIC = ["recency_days", "orders_90d", "spend_90d", "tenure_days"]
CATEGORICAL = ["segment", "city"]

numeric = Pipeline([("impute", SimpleImputer(strategy="median")),
                    ("scale", StandardScaler())])
categorical = Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore"))])
preprocess = ColumnTransformer([("num", numeric, NUMERIC),
                                ("cat", categorical, CATEGORICAL)])
pipe = Pipeline([("prep", preprocess),
                 ("model", LogisticRegression(max_iter=1000))])

pipe.fit(X_train, y_train)              # every step learns from training rows only
test_accuracy = (pipe.predict(X_test) == y_test).mean()
```

Useful details:

* Step names (`"prep"`, `"model"`) are yours to choose; they let you reach inside:
  `pipe.named_steps["model"].coef_`.
* `pipe.named_steps["prep"].get_feature_names_out()` lists the output columns, e.g. `num__recency_days`,
  `cat__segment_student`.
* `make_pipeline(StandardScaler(), LogisticRegression())` builds a pipeline with automatic step names.
* The fitted pipeline is the object you save and deploy (Week 9), so training and serving run identical
  preprocessing.

### Why "fit on training rows only" matters

Means, medians, category lists and model weights are all **learned parameters**. If any of them is computed with
test rows, the test set has influenced the model, and the test score stops being an honest estimate of performance
on new data ($E_{out}$). Putting preprocessing inside the pipeline and calling `fit` only on training data makes
this automatic, including inside cross-validation.

## Scoring and cross-validation

Accuracy by hand is `(pipe.predict(X_test) == y_test).mean()`. `pipe.score(X_test, y_test)` gives the same for
classifiers. Week 5 introduces better metrics for decisions (precision, recall, ROC AUC, costs) from
`sklearn.metrics`.

**Cross-validation** fits and scores the pipeline $k$ times, each time holding out a different fold of the
training data:

```python
from sklearn.model_selection import StratifiedKFold, cross_val_score

folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
scores = cross_val_score(pipe, X_train, y_train, cv=folds, scoring="accuracy")
print(scores.mean(), scores.std())
```

The spread of the scores shows how much a single split can mislead. Because the whole pipeline is refitted inside
each fold, no preprocessing step ever sees the fold it is scored on.

## Common errors and how to read them

| Message | What it means | Fix |
|---|---|---|
| `ValueError: could not convert string to float: 'consumer'` | a text column reached a step that needs numbers | route it through a `OneHotEncoder` in the `ColumnTransformer` |
| `ValueError: Input X contains NaN` | missing values reached a scaler or model | add a `SimpleImputer` before it |
| `ValueError: Found unknown categories [...] during transform` | a category not seen in `fit` | `OneHotEncoder(handle_unknown="ignore")` |
| `ValueError: Expected 2D array, got 1D array instead` | you passed one column as a Series or 1-D array | use `X[["col"]]` or `array.reshape(-1, 1)` |
| `NotFittedError: This StandardScaler instance is not fitted yet` | `transform`/`predict` before `fit` | call `fit` on training data first |
| `ConvergenceWarning: lbfgs failed to converge` | the solver ran out of iterations | scale the features and/or raise `max_iter=1000` |
| `ValueError: A given column is not a column of the dataframe` | a name in the `ColumnTransformer` list does not exist | check spelling against `X.columns` |
| `ValueError: The least populated class in y has only 1 member` | `stratify` with a class too rare to split | check your labels; you may have the wrong column |

Warnings are not errors, but read them: a `ConvergenceWarning` means the model you are evaluating is not the one
you think you trained.

## Cheat sheet

```python
# split
from sklearn.model_selection import train_test_split
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, random_state=0, stratify=y)

# estimator API
est = Something(setting=...)     # create
est.fit(X_tr, y_tr)              # learn  (attributes ending in _ appear)
est.transform(X)                 # transformers
est.predict(X); est.predict_proba(X)   # models

# preprocessing
from sklearn.impute import SimpleImputer            # strategy="median" | "most_frequent", add_indicator=True
from sklearn.preprocessing import StandardScaler, OneHotEncoder   # OneHotEncoder(handle_unknown="ignore")

# composition
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline, make_pipeline
prep = ColumnTransformer([("num", num_pipe, NUMERIC), ("cat", cat_pipe, CATEGORICAL)])
pipe = Pipeline([("prep", prep), ("model", LogisticRegression(max_iter=1000))])
pipe.fit(X_tr, y_tr); pipe.predict(X_te)
pipe.named_steps["prep"].get_feature_names_out()

# evaluation
(pipe.predict(X_te) == y_te).mean()
from sklearn.model_selection import StratifiedKFold, cross_val_score
cross_val_score(pipe, X_tr, y_tr, cv=StratifiedKFold(5, shuffle=True, random_state=0), scoring="accuracy")
```

**Rules of thumb:** split first; put every learned step inside the pipeline; fit only on training rows; fix
`random_state`; always handle unknown categories and missing values; compare with a baseline.

## Where to go next

* The official [getting started guide](https://scikit-learn.org/stable/getting_started.html) and
  [user guide](https://scikit-learn.org/stable/user_guide.html), especially "Pipelines and composite estimators" and
  "Cross-validation".
* [Common pitfalls and recommended practices](https://scikit-learn.org/stable/common_pitfalls.html): a short page
  on leakage and inconsistent preprocessing that every ML engineer should read once.
* Used in: [15 · scikit-learn pipelines](../notebooks/15_sklearn_pipelines.html),
  [16 · Lab: a feature pipeline for churn](../notebooks/16_lab_feature_pipeline.html), and every modelling notebook
  after them.
