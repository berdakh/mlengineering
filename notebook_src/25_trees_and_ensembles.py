# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/25_trees_and_ensembles.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 25 · Trees and ensembles in practice
#
# **Week 7 · lesson · about 90 minutes**
#
# On tables of mixed business data (distances, counts, categories, flags), the models that win most often in
# industry are not neural networks but **ensembles of decision trees**: random forests and gradient boosting.
# This notebook shows how they work, how they overfit, how to read (and mis-read) their "feature importance",
# and when a plain linear model is the better choice.
#
# **What you will learn**
#
# - how a decision tree chooses a split (Gini impurity), and why depth is its complexity knob;
# - how a **random forest** averages many deep trees, and how **gradient boosting** adds small trees one by one;
# - how to configure both in scikit-learn so they do not overfit, including early stopping;
# - why the built-in `feature_importances_` can rank pure noise highly, and how **permutation importance** fixes it;
# - when a linear model is enough, and a rule for choosing the simpler model.
#
# **What you need:** Week 4 (scikit-learn pipelines), Week 5 (baselines, ROC AUC) and Week 6 (grouped splits).
#
# **How grading works:** most exercises are functions; the grader runs them on small hand-made arrays and on a
# freshly generated dataset. Model exercises are re-trained by the grader on new data, so a lucky seed will not pass.

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
# ## The data for this week: late deliveries
#
# A delivery company wants to know, when a parcel leaves the depot, whether it will arrive **late**, so that it
# can warn the customer or re-route. `make_deliveries()` generates a **synthetic** (computer-generated, not real)
# table of 6,000 deliveries by 80 couriers. Each row is one delivery:
#
# | Column | Meaning |
# |---|---|
# | `courier_id` | who delivered it (80 couriers) |
# | `region` | north, south, east or west |
# | `distance_km`, `weight_kg`, `n_items` | the trip and the parcel |
# | `hour` (8-21), `weekend` (0/1), `rain` (0/1) | when, and the weather |
# | `tracking_noise` | a random number with **no** relation to lateness (we planted it on purpose) |
# | `late` | the label: 1 if the delivery arrived late |
#
# Couriers differ in skill, and that skill is not a column, so rows of the same courier are related. As in
# Week 6, we therefore split **by courier**: every courier is in exactly one of train, valid or test.
# `to_matrix` turns a table into model inputs (numbers only; the region becomes four 0/1 columns).

# %%
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score
from mlcourse.datasets_w07 import make_deliveries, make_linear_world, split_by_courier, to_matrix

deliveries = make_deliveries()
train, valid, test = split_by_courier(deliveries)
X_train, X_valid, X_test = to_matrix(train), to_matrix(valid), to_matrix(test)
y_train, y_valid, y_test = train["late"], valid["late"], test["late"]
print(len(train), "train rows,", len(valid), "valid rows,", len(test), "test rows")
print("late rate in train:", round(y_train.mean(), 3))
deliveries.head()

# %% [markdown]
# Expected: 3,574 train, 1,209 valid and 1,217 test rows (48, 16 and 16 couriers); about a quarter of
# deliveries are late. Throughout this notebook we measure models with **ROC AUC** (Week 5): the probability that
# a random late delivery gets a higher score than a random on-time one. 0.5 is guessing, 1.0 is perfect.

# %% [markdown]
# ## 1. How a tree splits
#
# **Why.** Before tuning a model you should know what it is doing. A tree is a sequence of yes/no questions such
# as "is the distance above 12 km?"; once you see how it picks those questions, its strengths (thresholds,
# interactions) and weaknesses (it memorises) follow.
#
# **Idea.** A **decision tree** starts with all training rows in one node. It tries every feature and every
# threshold, and keeps the question that makes the two resulting groups as **pure** as possible (mostly late, or
# mostly on time). Then it repeats inside each group. A node that is not split further is a **leaf**; its
# prediction is the fraction of late rows in it.
#
# Purity is measured with **Gini impurity**. If a fraction $p$ of the rows in a node are late,
#
# $$\text{Gini} = 1 - p^2 - (1-p)^2 = 2p(1-p).$$
#
# It is 0 for a pure node ($p = 0$ or $1$) and largest, 0.5, for a 50/50 node. A split is scored by the
# **weighted** Gini of its two children: each child's Gini times its share of the rows. Lower is better.
#
# Here is the real depth-2 tree for our training data:
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c25-01.svg" alt="A depth-2 tree: the first split is distance above 12.05 km, the second is hour above 17.5; the four leaves predict late rates 0.10, 0.30, 0.46 and 0.67" style="max-width:100%">
#
# Notice what the tree found without being told: a **threshold** on distance and an **interaction** (late hours
# matter more for long trips). A linear model would need you to engineer those by hand.

# %%
from sklearn.tree import DecisionTreeClassifier, export_text

stump = DecisionTreeClassifier(max_depth=2, random_state=0).fit(X_train, y_train)
print(export_text(stump, feature_names=list(X_train.columns), show_weights=True))

# %% [markdown]
# `weights: [1726, 189]` means 1,726 on-time and 189 late rows reached that leaf.
#
# **Try it.** Change `max_depth=2` to `3` and find the new questions. Predict first: will `tracking_noise`
# (pure noise) appear? Run and check.

# %%
stump = DecisionTreeClassifier(max_depth=2, random_state=0).fit(X_train, y_train)
print(export_text(stump, feature_names=list(X_train.columns)))

# %% [markdown]
# ### Exercise 1.1 · Gini impurity
#
# Write `gini(y)`: given an array of 0/1 labels, return the Gini impurity $2p(1-p)$ as a float. For an empty
# array return `0.0`.

# %%
def gini(y):
    y = np.asarray(y)
    ### BEGIN SOLUTION
    if len(y) == 0:
        return 0.0
    p = y.mean()
    return float(2 * p * (1 - p))
    ### END SOLUTION


gini([0, 0, 1, 1]), gini([1, 1, 1])

# %%
grade("w07.gini", gini)

# %% [markdown]
# ### Exercise 1.2 · The best threshold for one feature
#
# Write `best_split(x, y)`: try every threshold `t` from the **distinct values of `x`** (rows with `x <= t` go
# left, the others right; skip a threshold that leaves one side empty) and return `(best_t, best_score)` where
# `best_score` is the lowest weighted Gini. If no threshold is possible (all `x` equal), return `(None, gini(y))`.
# On ties keep the smallest threshold.
#
# This is exactly what a tree does at every node, for every feature.

# %%
def best_split(x, y):
    x, y = np.asarray(x, dtype=float), np.asarray(y)
    ### BEGIN SOLUTION
    best_t, best_score = None, gini(y)
    n = len(y)
    for t in np.unique(x)[:-1]:          # the largest value would leave the right side empty
        left = x <= t
        score = left.sum() / n * gini(y[left]) + (~left).sum() / n * gini(y[~left])
        if best_t is None or score < best_score - 1e-12:
            best_t, best_score = float(t), float(score)
    return best_t, best_score
    ### END SOLUTION


best_split([1, 2, 3, 10, 11, 12], [0, 0, 0, 1, 1, 1])

# %%
grade("w07.best_split", best_split)

# %% [markdown]
# ## 2. Depth is the complexity knob
#
# **Why.** A tree can keep splitting until every leaf holds one row. It is then perfect on training data and
# poor on new data. Choosing how far to grow it is the most important decision you make about a tree.
#
# **Idea.** Depth plays the role that polynomial degree played in your theory course. In *Learning from Data*
# terms, a deeper tree is a bigger hypothesis set: $E_{in}$ (training error) keeps going down, while $E_{out}$
# first improves and then gets worse once the tree starts fitting noise. We cannot see $E_{out}$, so we estimate
# it on the **validation** couriers and keep the test couriers locked away for the final check.
#
# The knobs scikit-learn gives you for this are `max_depth`, `min_samples_leaf` (a leaf must contain at least this
# many rows) and `max_leaf_nodes`. They all limit complexity.

# %%
rows = []
for depth in [1, 2, 3, 4, 6, 8, 12, None]:
    tree = DecisionTreeClassifier(max_depth=depth, random_state=0).fit(X_train, y_train)
    rows.append({"depth": depth,
                 "train_auc": roc_auc_score(y_train, tree.predict_proba(X_train)[:, 1]),
                 "valid_auc": roc_auc_score(y_valid, tree.predict_proba(X_valid)[:, 1]),
                 "leaves": tree.get_n_leaves()})
pd.DataFrame(rows).round(3)

# %% [markdown]
# Training AUC climbs to 1.0 (669 leaves for 3,574 rows) while validation AUC peaks at depth 4 (about 0.78) and
# falls to about 0.63 for the unlimited tree. Same data, same algorithm: only complexity changed.
#
# **Try it.** Replace `max_depth=depth` by `max_depth=None, min_samples_leaf=depth or 1` and use values like
# `[1, 5, 20, 50, 100]`. Which direction now means "simpler"?

# %%
for leaf in [1, 5, 20, 50, 100]:
    tree = DecisionTreeClassifier(min_samples_leaf=leaf, random_state=0).fit(X_train, y_train)
    print(leaf, round(roc_auc_score(y_valid, tree.predict_proba(X_valid)[:, 1]), 3))

# %% [markdown]
# ### Exercise 2.1 · A complexity curve
#
# Write `depth_curve(X_tr, y_tr, X_va, y_va, depths)` that fits one `DecisionTreeClassifier(max_depth=d,
# random_state=0)` per value in `depths` and returns a DataFrame with **one row per depth, in the given order**, and
# the columns `depth`, `train_auc`, `valid_auc`.

# %%
def depth_curve(X_tr, y_tr, X_va, y_va, depths):
    ### BEGIN SOLUTION
    rows = []
    for d in depths:
        tree = DecisionTreeClassifier(max_depth=d, random_state=0).fit(X_tr, y_tr)
        rows.append({"depth": d,
                     "train_auc": roc_auc_score(y_tr, tree.predict_proba(X_tr)[:, 1]),
                     "valid_auc": roc_auc_score(y_va, tree.predict_proba(X_va)[:, 1])})
    return pd.DataFrame(rows, columns=["depth", "train_auc", "valid_auc"])
    ### END SOLUTION


depth_curve(X_train, y_train, X_valid, y_valid, [2, 4, 8])

# %%
grade("w07.depth_curve", depth_curve)

# %% [markdown]
# ### Exercise 2.2 · Pick the depth
#
# Write `pick_depth(curve)`: given a table like the one above, return the `depth` with the highest `valid_auc`.
# If several depths are within `0.005` of the best validation AUC, return the **smallest** of them (the simplest
# model that is as good). Treat a depth of `None` (unlimited) as the largest possible depth.

# %%
def pick_depth(curve):
    ### BEGIN SOLUTION
    best = curve["valid_auc"].max()
    ok = curve[curve["valid_auc"] >= best - 0.005]
    depths = [d for d in ok["depth"] if d is not None and not (isinstance(d, float) and np.isnan(d))]
    return min(depths) if depths else None
    ### END SOLUTION


pick_depth(pd.DataFrame(rows))

# %%
grade("w07.pick_depth", pick_depth)

# %% [markdown]
# ## 3. Random forests: average many deep trees
#
# **Why.** One tree is unstable: change a few rows and the first split, and so the whole tree, can change. A
# model that changes a lot when the data changes a little has high **variance**. Averaging many such models
# cancels much of that variance.
#
# **Idea.** A **random forest** grows many deep trees, each on a different **bootstrap sample** of the training
# rows (rows drawn at random *with replacement*, so some appear twice and some not at all), and at each split it
# only considers a random subset of the features. The trees therefore make different mistakes, and the forest's
# prediction is the **average** of their predicted probabilities.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c25-02.svg" alt="Random forest: bootstrap samples train deep trees whose predictions are averaged. Gradient boosting: small trees are added one after another, each fitting what is still wrong, until validation stops improving" style="max-width:100%">
#
# In bias-variance terms: deep trees have low bias and high variance; averaging keeps the low bias and lowers the
# variance. More trees never make a forest overfit more; they only make it slower. The useful knobs are
# `n_estimators` (number of trees, 200-500 is typical), `min_samples_leaf` and `max_features`.

# %%
from sklearn.ensemble import RandomForestClassifier

for n in [1, 5, 20, 100, 300]:
    forest = RandomForestClassifier(n_estimators=n, random_state=0, n_jobs=-1).fit(X_train, y_train)
    print(f"{n:>3} trees: valid AUC {roc_auc_score(y_valid, forest.predict_proba(X_valid)[:, 1]):.3f}")

# %% [markdown]
# One unlimited tree scores 0.60 on validation, far below the depth-4 tree; 300 averaged trees reach 0.776.
#
# **Try it.** Add `min_samples_leaf=20` to the forest with 300 trees. Does validation AUC go up or down? Then look
# at its training AUC: it is no longer 1.0.

# %%
forest = RandomForestClassifier(n_estimators=300, random_state=0, n_jobs=-1).fit(X_train, y_train)
print("train", round(roc_auc_score(y_train, forest.predict_proba(X_train)[:, 1]), 3),
      "valid", round(roc_auc_score(y_valid, forest.predict_proba(X_valid)[:, 1]), 3))

# %% [markdown]
# ### Exercise 3.1 · A forest is an average
#
# A fitted forest keeps its trees in `forest.estimators_`. Write `forest_proba(forest, X)` that returns, as a 1-D
# NumPy array, the **average over all trees** of each tree's predicted probability of class 1
# (`tree.predict_proba(X)[:, 1]`). Pass `X` to the trees as a NumPy array (`np.asarray(X)`): the trees inside a
# forest were fitted without column names. Your result should equal `forest.predict_proba(X)[:, 1]`.

# %%
def forest_proba(forest, X):
    ### BEGIN SOLUTION
    X = np.asarray(X)
    return np.mean([tree.predict_proba(X)[:, 1] for tree in forest.estimators_], axis=0)
    ### END SOLUTION


forest_proba(forest, X_valid)[:5]

# %%
grade("w07.forest_proba", forest_proba)

# %% [markdown]
# ### Exercise 3.2 · Configure a forest that does not memorise
#
# Create `rf_model`, an **unfitted** `RandomForestClassifier` with `random_state=0`, at least 100 trees, and a
# setting that stops the trees from memorising single rows (for example `min_samples_leaf` or `max_depth`).
# The grader trains your configuration on a **new** delivery dataset and requires a validation AUC of at least
# 0.78 and a gap between training and validation AUC below 0.12.

# %%
### BEGIN SOLUTION
rf_model = RandomForestClassifier(n_estimators=300, min_samples_leaf=20, random_state=0, n_jobs=-1)
### STARTER
rf_model = None   # RandomForestClassifier(...)
### END SOLUTION
rf_model

# %%
grade("w07.rf_model", rf_model)

# %% [markdown]
# ## 4. Gradient boosting: small trees that fix mistakes
#
# **Why.** Gradient boosting is the model behind most winning solutions on tabular data, and scikit-learn's
# `HistGradientBoostingClassifier` trains it in seconds on hundreds of thousands of rows.
#
# **Idea.** Boosting builds trees **one after another**. It starts from a constant prediction (the base rate),
# then fits a *small* tree to what the current model still gets wrong (the **residuals**: the gap between the
# label and the current prediction), adds a fraction of that tree (the **learning rate**, e.g. 0.05) to the model,
# and repeats. Each round removes a bit of bias; too many rounds start fitting noise. **Early stopping** holds out
# part of the training data and stops adding trees when the score there stops improving.
#
# Main knobs: `learning_rate`, `max_iter` (maximum number of trees), `max_depth` or `max_leaf_nodes` (size of each
# tree), and `early_stopping=True` with `validation_fraction` and `n_iter_no_change`.

# %%
from sklearn.ensemble import HistGradientBoostingClassifier

for name, model in {
    "default (100 trees, no early stopping here)": HistGradientBoostingClassifier(random_state=0),
    "small trees + early stopping": HistGradientBoostingClassifier(
        max_depth=3, learning_rate=0.05, max_iter=1000, early_stopping=True,
        validation_fraction=0.2, n_iter_no_change=20, random_state=0),
}.items():
    model.fit(X_train, y_train)
    print(f"{name}: {model.n_iter_} trees, train AUC "
          f"{roc_auc_score(y_train, model.predict_proba(X_train)[:, 1]):.3f}, valid AUC "
          f"{roc_auc_score(y_valid, model.predict_proba(X_valid)[:, 1]):.3f}")

# %% [markdown]
# The default model reaches a training AUC of about 0.98 and a validation AUC of about 0.77; the constrained one
# stops itself after about 105 trees, with training 0.84 and validation 0.79. (scikit-learn only turns early
# stopping on by default for more than 10,000 rows, so for small tables switch it on yourself.)
#
# **Try it.** Set `learning_rate=0.3` in the second model. How many trees does it use now, and why fewer?

# %%
model = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=1000, early_stopping=True,
                                       validation_fraction=0.2, n_iter_no_change=20, random_state=0)
model.fit(X_train, y_train).n_iter_

# %% [markdown]
# ### Exercise 4.1 · Boosting by hand
#
# Boosting is easiest to see on a regression problem. Write `boost_stumps(x, y, n_rounds, learning_rate)`:
#
# 1. start with `pred` = an array filled with the mean of `y`;
# 2. repeat `n_rounds` times: compute `residual = y - pred`, fit a `DecisionTreeRegressor(max_depth=1)` to
#    predict `residual` from `x` (use `x.reshape(-1, 1)` as the input), and add `learning_rate` times its
#    predictions to `pred`;
# 3. return `pred` (a 1-D array, same length as `y`).
#
# With `n_rounds=0` it returns the mean everywhere.

# %%
from sklearn.tree import DecisionTreeRegressor


def boost_stumps(x, y, n_rounds, learning_rate):
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    ### BEGIN SOLUTION
    pred = np.full(len(y), y.mean())
    for _ in range(n_rounds):
        stump = DecisionTreeRegressor(max_depth=1).fit(x.reshape(-1, 1), y - pred)
        pred = pred + learning_rate * stump.predict(x.reshape(-1, 1))
    return pred
    ### END SOLUTION


xs = np.linspace(0, 6, 60)
ys = np.sin(xs)
fig, ax = plt.subplots(figsize=(6, 3))
ax.plot(xs, ys, "k.", label="data")
for r in [1, 10, 100]:
    ax.plot(xs, boost_stumps(xs, ys, r, 0.3), label=f"{r} rounds")
ax.legend(); ax.set_title("Boosting stumps: each round fixes part of what is still wrong")
plt.show()

# %%
grade("w07.boost_stumps", boost_stumps)

# %% [markdown]
# ### Exercise 4.2 · Configure boosting with early stopping
#
# Create `hgb_model`, an **unfitted** `HistGradientBoostingClassifier` with `random_state=0` and early stopping
# switched on (`early_stopping=True`). The grader fits it on a new delivery dataset and requires: validation AUC
# at least 0.78, fewer trees used than `max_iter` (so early stopping really stopped it), and a train-validation
# gap below 0.12.

# %%
### BEGIN SOLUTION
hgb_model = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=1000, early_stopping=True,
                                           validation_fraction=0.2, n_iter_no_change=20, random_state=0)
### STARTER
hgb_model = None   # HistGradientBoostingClassifier(...)
### END SOLUTION
hgb_model

# %%
grade("w07.hgb_model", hgb_model)

# %% [markdown]
# ## 5. Feature importance and its traps
#
# **Why.** The first question a manager asks about a model is "what drives it?". Answering with the wrong tool
# sends a team to work on the wrong thing.
#
# **Idea.** Tree models offer `feature_importances_` (**impurity importance**): how much each feature reduced
# Gini across all splits, measured **on the training data**. It has two well-known traps:
#
# - it favours features with **many distinct values** (continuous numbers, IDs), because they offer many
#   thresholds to try, and some of those split training noise well;
# - it measures what helped the model fit the training rows, not what helps it predict new rows.
#
# **Permutation importance** asks the question you actually care about: shuffle one column of the
# **validation** data (destroying its relation to the label, keeping its distribution), and measure how much the
# validation score drops. A useless feature drops it by about 0. Both methods measure what the *model* uses, not
# what *causes* lateness.

# %%
from sklearn.inspection import permutation_importance

forest = RandomForestClassifier(n_estimators=300, random_state=0, n_jobs=-1).fit(X_train, y_train)
impurity = pd.Series(forest.feature_importances_, index=X_train.columns)
perm = permutation_importance(forest, X_valid, y_valid, scoring="roc_auc", n_repeats=10, random_state=0)
table = pd.DataFrame({"impurity": impurity, "permutation": perm.importances_mean}).round(3)
table.sort_values("impurity", ascending=False)

# %% [markdown]
# `tracking_noise` is pure noise, yet impurity importance ranks it **second** (about 0.18). Permutation
# importance gives it about 0.004, which is noise level, and instead shows that `hour` and `rain` matter.
#
# **Try it.** Re-run the cell with `RandomForestClassifier(n_estimators=300, min_samples_leaf=20, ...)`. Does the
# noise feature's impurity importance shrink? Why would bigger leaves help?

# %%
table.sort_values("permutation", ascending=False)

# %% [markdown]
# ### Exercise 5.1 · Permutation importance by hand
#
# Write `permutation_drop(model, X, y, column, seed=0)`: compute the AUC of `model.predict_proba(X)[:, 1]`, then
# make a **copy** of `X` in which `column` is shuffled with `np.random.default_rng(seed).permutation`, and return
# `baseline_auc - shuffled_auc` (a float). Do not change `X` itself.

# %%
def permutation_drop(model, X, y, column, seed=0):
    ### BEGIN SOLUTION
    base = roc_auc_score(y, model.predict_proba(X)[:, 1])
    X_shuffled = X.copy()
    X_shuffled[column] = np.random.default_rng(seed).permutation(X_shuffled[column].to_numpy())
    return float(base - roc_auc_score(y, model.predict_proba(X_shuffled)[:, 1]))
    ### END SOLUTION


permutation_drop(forest, X_valid, y_valid, "distance_km"), permutation_drop(forest, X_valid, y_valid, "tracking_noise")

# %%
grade("w07.permutation_drop", permutation_drop)

# %% [markdown]
# ### Exercise 5.2 · Spot the misleading features
#
# Write `misleading_features(table, high=0.05, useless=0.005)`: given a DataFrame indexed by feature name with
# columns `impurity` and `permutation` (like `table` above), return a **sorted list** of the features whose
# impurity importance is at least `high` but whose permutation importance is at most `useless`. These are the
# features you must not report as "drivers".

# %%
def misleading_features(table, high=0.05, useless=0.005):
    ### BEGIN SOLUTION
    mask = (table["impurity"] >= high) & (table["permutation"] <= useless)
    return sorted(table.index[mask])
    ### END SOLUTION


misleading_features(table)

# %%
grade("w07.misleading_features", misleading_features)

# %% [markdown]
# On our forest the list is `n_items`, `tracking_noise` and `weight_kg`. `weight_kg` does have a small real effect
# in the generator, but this forest does not use it in a way that helps on new couriers; "the model relies on
# weight" would still be a wrong statement about *this* model.

# %% [markdown]
# ## 6. When a linear model is enough
#
# **Why.** Trees are not free: they are larger, slower to score, harder to explain and to check. If a logistic
# regression is as good, it is usually the better product.
#
# **Idea.** Trees win when the label depends on **thresholds and interactions** that you have not engineered
# (our deliveries). A linear model wins, or ties, when the relation really is close to linear, or when data is
# scarce. The only way to know is to try both on the same validation rows. Then apply a rule written down
# *before* you look: "take the simplest model whose score is within a small tolerance of the best".

# %%
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def valid_auc(model, Xtr, ytr, Xva, yva):
    return roc_auc_score(yva, model.fit(Xtr, ytr).predict_proba(Xva)[:, 1])


world = make_linear_world()
lw_train, lw_valid = world.iloc[:2000], world.iloc[2000:]
features = ["x1", "x2", "x3", "x4", "x5"]
candidates = {
    "logistic": lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
    "forest": lambda: RandomForestClassifier(n_estimators=300, min_samples_leaf=20, random_state=0, n_jobs=-1),
    "boosting": lambda: HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=1000,
                                                       early_stopping=True, n_iter_no_change=20, random_state=0),
}
for name, make in candidates.items():
    print(f"{name:9s} deliveries: {valid_auc(make(), X_train, y_train, X_valid, y_valid):.3f}   "
          f"linear world: {valid_auc(make(), lw_train[features], lw_train['y'], lw_valid[features], lw_valid['y']):.3f}")

# %% [markdown]
# On the deliveries the tree ensembles beat logistic regression clearly (0.793 and 0.790 against 0.749). On the
# linear world it is the other way round: logistic regression is slightly ahead (0.826 against 0.819 and 0.818),
# and the trees bring nothing but cost. Neither family wins everywhere.
#
# **Try it.** Give logistic regression the two features it cannot build itself: add columns
# `long_trip = distance_km > 12` and `north_rain = rain * region_north` to copies of `X_train` and `X_valid`, and
# re-run it. How much of the gap closes?

# %%
Xtr2, Xva2 = X_train.copy(), X_valid.copy()
# Xtr2["long_trip"] = ...
print(round(valid_auc(candidates["logistic"](), Xtr2, y_train, Xva2, y_valid), 3))

# %% [markdown]
# ### Exercise 6.1 · The simplest model that is good enough
#
# Write `simplest_good_enough(scores, order, tolerance=0.01)`. `scores` is a dict `{model_name: validation
# score}` (higher is better); `order` is a list of the same names from **simplest to most complex**. Return the
# first name in `order` whose score is at least `best - tolerance`, where `best` is the highest score.

# %%
def simplest_good_enough(scores, order, tolerance=0.01):
    ### BEGIN SOLUTION
    best = max(scores.values())
    return next(name for name in order if scores[name] >= best - tolerance)
    ### END SOLUTION


simplest_good_enough({"logistic": 0.749, "forest": 0.793, "boosting": 0.790}, ["logistic", "forest", "boosting"])

# %%
grade("w07.simplest_good_enough", simplest_good_enough)

# %% [markdown]
# A tolerance of 0.01 is a choice, and notebook 26 shows how to set it from the data: a difference smaller than
# the uncertainty of your measurement is not a difference you can claim.

# %% [markdown]
# ## Quiz

# %% [markdown]
# **Q1.** A decision tree reaches training AUC 1.0 and validation AUC 0.63. What is the best next step?
#
# - a) Add more trees to make it a forest and keep the depth unlimited, because forests never overfit.
# - b) Limit its complexity (`max_depth`, `min_samples_leaf`) and choose the limit on validation data.
# - c) Report the training AUC; the validation set is probably unlucky.
# - d) Tune the limit on the test set, which is the most honest data.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"
### END SOLUTION
quiz("w07.25_q1", answer)

# %% [markdown]
# **Q2.** Why does a random forest usually generalise better than one deep tree?
#
# - a) Its trees are shallower, so each one has lower variance.
# - b) It uses the test set to pick its trees.
# - c) Averaging many decorrelated deep trees keeps their low bias and cancels much of their variance.
# - d) It removes noise features automatically.

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"
### END SOLUTION
quiz("w07.25_q2", answer)

# %% [markdown]
# **Q3.** In gradient boosting, what does lowering the learning rate from 0.3 to 0.05 usually do?
#
# - a) Each tree contributes less, so more trees are needed; with early stopping the result is often slightly better.
# - b) It makes every tree deeper.
# - c) It has no effect when early stopping is on.
# - d) It turns boosting into a random forest.

# %%
### BEGIN SOLUTION
answer = "a"
### STARTER
answer = "?"
### END SOLUTION
quiz("w07.25_q3", answer)

# %% [markdown]
# **Q4.** `feature_importances_` of a forest ranks `customer_id` third. What do you conclude?
#
# - a) Customer identity is a major driver; report it to the business.
# - b) Nothing yet: impurity importance favours high-cardinality columns. Check permutation importance on
#   validation data, and ask whether an ID should be a feature at all.
# - c) The model is broken and must be retrained without random_state.
# - d) Permutation importance will rank it even higher, so it must matter.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"
### END SOLUTION
quiz("w07.25_q4", answer)

# %% [markdown]
# **Q5.** Logistic regression scores 0.801 and gradient boosting 0.806 on validation. Your team agreed on a
# tolerance of 0.01. Which model do you ship, by the rule from section 6?
#
# - a) Boosting, because it has the higher number.
# - b) Neither; collect more data first.
# - c) Logistic regression: it is within the tolerance of the best and is simpler to run and explain.
# - d) Whichever does better on the test set after trying both there.

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"
### END SOLUTION
quiz("w07.25_q5", answer)

# %% [markdown]
# ## Recap
#
# - A tree splits on the feature and threshold that minimise the weighted Gini impurity of the two children; it
#   finds thresholds and interactions by itself.
# - Depth (or `min_samples_leaf`) is a tree's complexity knob: training AUC always rises with depth, validation
#   AUC peaks and then falls. Choose it on validation data.
# - A random forest averages many deep, decorrelated trees: same low bias, much lower variance. More trees never
#   hurt accuracy, only speed.
# - Gradient boosting adds small trees one at a time, each fitting the remaining errors; use a small learning rate
#   and early stopping.
# - Impurity importance can rank pure noise highly; use permutation importance on validation data, and remember
#   that importance describes the model, not causes.
# - Try a linear model on the same split. Ship the simplest model within an agreed tolerance of the best.
#
# ## On the job
#
# On a typical tabular problem (churn, fraud, delivery times, demand), an ML engineer trains a logistic regression
# and a gradient-boosting model in the first days, on a split that matches how the model will be used, and spends
# most of the remaining effort on data and features rather than on exotic models. When stakeholders ask what the
# model "looks at", the answer comes from permutation importance on held-out data, with a sentence on its limits.
#
# ## Going further
#
# - Tool guide: [scikit-learn](../docs/tools/scikit-learn.md) (estimators, `fit`/`predict_proba`, pipelines).
# - scikit-learn user guide: ensembles <https://scikit-learn.org/stable/modules/ensemble.html> and permutation
#   importance <https://scikit-learn.org/stable/modules/permutation_importance.html>.
# - Advanced track: [23 · Model choice](../advanced/notebooks/23_model_choice.ipynb).
# - Next: [26 · Uncertainty and fair model comparisons](26_uncertainty_comparisons.ipynb).

# %% [markdown]
# ## Record your progress
#
# Flags: `reading`, `guided` (you passed the graded exercises), `independent` (you solved them without hints or
# solutions), `review` (come back to this).

# %%
from mlcourse.progress import mark

# mark("25", "reading")
# mark("25", "guided")
