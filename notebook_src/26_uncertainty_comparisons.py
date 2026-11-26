# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/26_uncertainty_comparisons.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 26 · Uncertainty and fair model comparisons
#
# **Week 7 · lesson · about 90 minutes**
#
# "Model B scores 0.801, model A 0.798, so B is better." Sentences like this are written every day, and many of
# them are wrong: not because the arithmetic is wrong, but because 0.801 is a measurement made on one particular
# test set, and a different test set would have given a different number. This notebook teaches you to put an
# **interval** around every score, to compare two models **fairly** on the same rows, and to say "no detectable
# difference" when that is the truth.
#
# **What you will learn**
#
# - why a test score is an estimate with a standard error, and how big that error is;
# - the **bootstrap**: an interval for any metric by resampling the test set;
# - why rows that belong together (the same courier, customer or machine) must be resampled **as groups**;
# - **paired** comparisons: the interval of the *difference* between two models on the same resamples;
# - how to report "no detectable difference", and how much more data would be needed to detect one.
#
# **What you need:** notebook 25 (the delivery data and models), Week 5 (ROC AUC), Week 6 (grouped splits).
#
# **How grading works:** each exercise is a function. The grader runs it on small arrays with known answers and
# planted traps (for example, two identical models, or groups that must stay together).

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
# ## The models we will compare
#
# The cell below rebuilds the **synthetic** delivery data of notebook 25 (split by courier) and trains the three
# candidates from that notebook on the training couriers. It then scores the 1,217 **test** deliveries of the 16
# test couriers. This is the one-time final evaluation; we will not tune anything on it.

# %%
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score, accuracy_score
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from mlcourse.datasets_w07 import make_deliveries, split_by_courier, to_matrix

train, valid, test = split_by_courier(make_deliveries())
X_train, X_test = to_matrix(train), to_matrix(test)
y_train, y_test = train["late"].to_numpy(), test["late"].to_numpy()
couriers = test["courier_id"].to_numpy()

models = {
    "logistic": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
    "forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=20, random_state=0, n_jobs=-1),
    "boosting": HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=1000, early_stopping=True,
                                               validation_fraction=0.2, n_iter_no_change=20, random_state=0),
}
scores = {name: m.fit(X_train, y_train).predict_proba(X_test)[:, 1] for name, m in models.items()}
for name, s in scores.items():
    print(f"{name:9s} test AUC {roc_auc_score(y_test, s):.3f}   accuracy at 0.5: {accuracy_score(y_test, s >= 0.5):.3f}")

# %% [markdown]
# Expected: logistic 0.730, forest 0.801, boosting 0.798 (AUC). Is the forest better than boosting? Is either
# better than logistic regression? By the end of this notebook you will be able to answer both, honestly.

# %% [markdown]
# ## 1. A test score is an estimate
#
# **Why.** Your test set is one sample of the deliveries the model will meet. Draw another sample and the score
# moves. If you do not know by how much, you cannot tell a real improvement from luck.
#
# **Idea.** In *Learning from Data* terms, the test error is an unbiased estimate of $E_{out}$, and Hoeffding's
# inequality says it is close to $E_{out}$ *with high probability*, not exactly equal to it. In practice we
# quantify "close" with a **standard error** (SE). For accuracy, each test row is a coin flip that is right with
# probability $p$, so for $n$ independent rows
#
# $$SE = \sqrt{p(1-p)/n},$$
#
# and an approximate 95% interval is $p \pm 1.96 \cdot SE$.
#
# Because our data is generated, we can do what is impossible in real life: draw **100 brand-new test sets** of
# new couriers and see how much the forest's score really moves.

# %%
forest = models["forest"]
fresh = []
for seed in range(100, 200):
    d = make_deliveries(n=1200, n_couriers=16, seed=seed)       # 16 new couriers, like our test set
    p = forest.predict_proba(to_matrix(d))[:, 1]
    fresh.append({"auc": roc_auc_score(d["late"], p), "accuracy": accuracy_score(d["late"], p >= 0.5)})
fresh = pd.DataFrame(fresh)

fig, ax = plt.subplots(figsize=(6, 3))
ax.hist(fresh["auc"], bins=20, color="tab:blue")
ax.axvline(roc_auc_score(y_test, scores["forest"]), color="k", ls="--", label="our test set")
ax.set_xlabel("forest AUC on a new test set"); ax.set_ylabel("count"); ax.legend()
plt.show()
fresh.describe().loc[["mean", "std", "min", "max"]].round(3)

# %% [markdown]
# The same fitted forest scores anywhere from about 0.75 to 0.83 depending on which 16 couriers happen to be in
# the test set; the standard deviation is about 0.019 (AUC) and 0.018 (accuracy). A difference of 0.003 between
# two models is far inside that noise.
#
# **Try it.** Change `n_couriers=16` to `n_couriers=64` (and `n=4800`): a test set four times bigger. Predict
# first: by how much should the standard deviation shrink? (Hint: $\sqrt{4} = 2$.)

# %%
print(fresh["accuracy"].std().round(4))

# %% [markdown]
# ### Exercise 1.1 · Standard error of an accuracy
#
# Write `binomial_se(p, n)`: the standard error $\sqrt{p(1-p)/n}$ of an accuracy `p` measured on `n` independent
# rows, as a float.

# %%
def binomial_se(p, n):
    ### BEGIN SOLUTION
    return float(np.sqrt(p * (1 - p) / n))
    ### END SOLUTION


binomial_se(0.805, 1217)

# %%
grade("w07.binomial_se", binomial_se)

# %% [markdown]
# ### Exercise 1.2 · A normal-approximation interval
#
# Write `normal_interval(p, n, z=1.96)` returning a tuple `(low, high)` = $p \pm z \cdot SE$, **clipped** to
# `[0, 1]` (an accuracy cannot be negative or above 1).

# %%
def normal_interval(p, n, z=1.96):
    ### BEGIN SOLUTION
    se = binomial_se(p, n)
    return max(0.0, p - z * se), min(1.0, p + z * se)
    ### END SOLUTION


normal_interval(0.805, 1217)

# %%
grade("w07.normal_interval", normal_interval)

# %% [markdown]
# Compare: the formula gives SE 0.011 for the forest's accuracy, but the 100 fresh test sets showed a standard
# deviation of 0.018. The formula is too optimistic. Its assumption, **independent rows**, is false here: rows of
# the same courier share that courier's skill. Section 3 fixes this.

# %% [markdown]
# ## 2. The bootstrap: an interval for any metric
#
# **Why.** There is no simple formula for the standard error of AUC, PR-AUC, recall at a threshold, or the
# revenue a model saves. You need one method that works for all of them.
#
# **Idea.** The **bootstrap** pretends the test set is the population. It draws a new test set of the same size
# from it **with replacement** (some rows twice, some not at all), computes the metric, and repeats this about
# 1,000 times. The spread of the 1,000 values approximates how much the metric would move on a new test set. The
# **percentile interval** takes the 2.5th and 97.5th percentiles of those values as a 95% interval.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c26-01.svg" alt="The test set is resampled with replacement 1,000 times; the metric is computed on each resample; the middle 95% of the 1,000 metrics is the interval" style="max-width:100%">
#
# To resample rows, draw random row positions: `rng.integers(0, n, n)` gives `n` positions between 0 and
# `n - 1`, with repeats. Always use a seeded generator, `rng = np.random.default_rng(seed)`, so the interval is
# reproducible.

# %%
rng = np.random.default_rng(0)
idx = rng.integers(0, 10, 10)
print("positions drawn:", idx)
print("how often each row was picked:", np.bincount(idx, minlength=10))

# %% [markdown]
# **Try it.** Run the cell a few times with different seeds. On average about 37% of rows are not picked at all
# (the chance a row is missed $n$ times is $(1 - 1/n)^n \approx e^{-1}$). Count the zeros.

# %%
np.bincount(np.random.default_rng(1).integers(0, 1000, 1000), minlength=1000).tolist().count(0)

# %% [markdown]
# ### Exercise 2.1 · Bootstrap the rows
#
# Write `bootstrap_rows(y, s, metric, n_boot=1000, seed=0)`. `y` are labels, `s` scores (NumPy arrays of the same
# length `n`), and `metric(y, s)` returns a number (for example `roc_auc_score`). Use
# `rng = np.random.default_rng(seed)`; `n_boot` times, draw `n` row positions with replacement and compute
# `metric(y[idx], s[idx])`. Return the `n_boot` values as a NumPy array.

# %%
def bootstrap_rows(y, s, metric, n_boot=1000, seed=0):
    y, s = np.asarray(y), np.asarray(s)
    ### BEGIN SOLUTION
    rng = np.random.default_rng(seed)
    n = len(y)
    out = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, n, n)
        out[b] = metric(y[idx], s[idx])
    return out
    ### END SOLUTION


reps = bootstrap_rows(y_test, scores["forest"], roc_auc_score, n_boot=200)
reps[:5].round(3), reps.std().round(4)

# %%
grade("w07.bootstrap_rows", bootstrap_rows)

# %% [markdown]
# ### Exercise 2.2 · The percentile interval
#
# Write `percentile_interval(replicates, level=0.95)` returning `(low, high)`: the `(1 - level) / 2` and
# `(1 + level) / 2` quantiles of the replicates (use `np.percentile` with values in percent, e.g. 2.5 and 97.5).

# %%
def percentile_interval(replicates, level=0.95):
    ### BEGIN SOLUTION
    a = (1 - level) / 2 * 100
    low, high = np.percentile(np.asarray(replicates), [a, 100 - a])
    return float(low), float(high)
    ### END SOLUTION


percentile_interval(bootstrap_rows(y_test, scores["forest"], roc_auc_score))

# %%
grade("w07.percentile_interval", percentile_interval)

# %% [markdown]
# ## 3. Grouped data: resample whole groups
#
# **Why.** Rows from one courier (or one customer, one patient, one machine) are not independent: they share
# something the model does not see. If you resample single rows, the bootstrap believes it has 1,217 independent
# pieces of evidence, when the real evidence about "how well does it work for a *new* courier" comes from only 16
# couriers.
#
# **Idea.** Resample at the level of the unit you want to generalise to. The **group bootstrap** (also called the
# cluster bootstrap) draws **couriers** with replacement (16 of them, some twice) and takes **all** rows of each
# drawn courier. It is the same rule you used for splits in Week 6: the unit of splitting and the unit of
# resampling are the same.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c26-02.svg" alt="Row bootstrap draws rows of different couriers independently and gives intervals that are too narrow; group bootstrap draws whole couriers with all their rows and gives honest intervals for new couriers" style="max-width:100%">
#
# A useful trick: compute the row positions of each group once, with
# `positions = {g: np.flatnonzero(groups == g) for g in np.unique(groups)}`, then join the positions of the drawn
# groups with `np.concatenate`.

# %%
groups = np.array(["a", "a", "b", "c", "c", "c"])
positions = {str(g): np.flatnonzero(groups == g).tolist() for g in np.unique(groups)}
drawn = np.random.default_rng(0).choice(np.unique(groups), size=3, replace=True)
print("positions per group:", positions)
print("groups drawn:", drawn.tolist(), "-> rows", sum((positions[g] for g in drawn), []))

# %% [markdown]
# **Try it.** Draw again with `default_rng(1)`, `(2)`, ... Notice that the resampled test set has a different
# number of rows each time. That is expected: couriers have different numbers of deliveries.

# %%
np.random.default_rng(1).choice(np.unique(groups), size=3, replace=True)

# %% [markdown]
# ### Exercise 3.1 · Bootstrap the groups
#
# Write `bootstrap_groups(y, s, groups, metric, n_boot=1000, seed=0)`: like `bootstrap_rows`, but each replicate
# draws `k` group labels with replacement (`k` = number of distinct groups, using
# `rng.choice(unique_groups, size=k, replace=True)`) and evaluates `metric` on **all** rows of the drawn groups.
# Return the `n_boot` values as a NumPy array.

# %%
def bootstrap_groups(y, s, groups, metric, n_boot=1000, seed=0):
    y, s, groups = np.asarray(y), np.asarray(s), np.asarray(groups)
    ### BEGIN SOLUTION
    rng = np.random.default_rng(seed)
    unique = np.unique(groups)
    positions = {g: np.flatnonzero(groups == g) for g in unique}
    out = np.empty(n_boot)
    for b in range(n_boot):
        idx = np.concatenate([positions[g] for g in rng.choice(unique, size=len(unique), replace=True)])
        out[b] = metric(y[idx], s[idx])
    return out
    ### END SOLUTION


for name in scores:
    row_iv = percentile_interval(bootstrap_rows(y_test, scores[name], roc_auc_score))
    grp_iv = percentile_interval(bootstrap_groups(y_test, scores[name], couriers, roc_auc_score))
    print(f"{name:9s} rows: [{row_iv[0]:.3f}, {row_iv[1]:.3f}]   couriers: [{grp_iv[0]:.3f}, {grp_iv[1]:.3f}]")

# %%
grade("w07.bootstrap_groups", bootstrap_groups)

# %% [markdown]
# For the forest the row interval is about [0.771, 0.831] and the courier interval about [0.757, 0.837]: a third
# wider, and closer to the 0.75-0.83 range we saw on 100 genuinely new test sets in section 1.
#
# ### Exercise 3.2 · An honest results table
#
# Write `results_table(y, scores, groups, n_boot=1000, seed=0)`: `scores` is a dict `{model name: score array}`.
# Return a DataFrame with **one row per model** (in the dict's order) and the columns `model`, `auc` (on the full
# test set), `low` and `high` (95% percentile interval from **your group bootstrap** with `roc_auc_score`).

# %%
def results_table(y, scores, groups, n_boot=1000, seed=0):
    ### BEGIN SOLUTION
    rows = []
    for name, s in scores.items():
        low, high = percentile_interval(bootstrap_groups(y, s, groups, roc_auc_score, n_boot, seed))
        rows.append({"model": name, "auc": roc_auc_score(y, s), "low": low, "high": high})
    return pd.DataFrame(rows, columns=["model", "auc", "low", "high"])
    ### END SOLUTION


results_table(y_test, scores, couriers).round(3)

# %%
grade("w07.results_table", results_table)

# %% [markdown]
# ## 4. Comparing two models: pair them
#
# **Why.** The forest's interval [0.757, 0.837] and boosting's [0.759, 0.832] overlap almost completely. Does that
# mean they are equal? And logistic regression's interval overlaps neither: is that enough to say it is worse?
# Comparing two separate intervals is the wrong test, in both directions.
#
# **Idea.** Both models were scored on the **same** test rows, and much of the variation (an easy courier, a hard
# courier) hits both models alike. A **paired** comparison uses that: on each resample compute *both* metrics and
# keep their **difference**. The interval of the difference is much narrower than either interval alone, because
# the shared noise cancels.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c26-03.svg" alt="One resample of the test couriers gives the metric of model A and model B and their difference; repeated 1,000 times this gives an interval of the difference: above 0 means B is better, below 0 means A is better, containing 0 means no detectable difference" style="max-width:100%">
#
# The verdict follows from where 0 lies: an interval entirely above 0 says B is better, entirely below 0 says A is
# better, and an interval that **contains 0** says the data cannot tell them apart.

# %% [markdown]
# ### Exercise 4.1 · Paired bootstrap of a difference
#
# Write `paired_difference(y, s_a, s_b, groups, metric, n_boot=1000, seed=0)`. Resample groups exactly as in
# `bootstrap_groups`; on **each** resample compute `metric(y[idx], s_b[idx]) - metric(y[idx], s_a[idx])`. Return
# the `n_boot` differences as a NumPy array. (Check yourself: if `s_a` and `s_b` are identical, every difference
# must be exactly 0.)

# %%
def paired_difference(y, s_a, s_b, groups, metric, n_boot=1000, seed=0):
    y, s_a, s_b, groups = np.asarray(y), np.asarray(s_a), np.asarray(s_b), np.asarray(groups)
    ### BEGIN SOLUTION
    rng = np.random.default_rng(seed)
    unique = np.unique(groups)
    positions = {g: np.flatnonzero(groups == g) for g in unique}
    out = np.empty(n_boot)
    for b in range(n_boot):
        idx = np.concatenate([positions[g] for g in rng.choice(unique, size=len(unique), replace=True)])
        out[b] = metric(y[idx], s_b[idx]) - metric(y[idx], s_a[idx])
    return out
    ### END SOLUTION


for a, b in [("logistic", "forest"), ("boosting", "forest")]:
    diffs = paired_difference(y_test, scores[a], scores[b], couriers, roc_auc_score)
    observed = roc_auc_score(y_test, scores[b]) - roc_auc_score(y_test, scores[a])
    low, high = percentile_interval(diffs)
    print(f"{b} - {a}: {observed:+.4f}, 95% interval [{low:+.3f}, {high:+.3f}]")

# %%
grade("w07.paired_difference", paired_difference)

# %% [markdown]
# Forest minus logistic is about +0.071 with an interval of about [+0.054, +0.088]: clearly above 0. Forest minus
# boosting is +0.003 with an interval of about [-0.010, +0.014]: it contains 0.
#
# ### Exercise 4.2 · The verdict
#
# Write `verdict(low, high, name_a, name_b)` for an interval of the difference **B - A**. Return exactly
# `f"{name_b} is better"` if `low > 0`, `f"{name_a} is better"` if `high < 0`, and otherwise
# `"no detectable difference"`.

# %%
def verdict(low, high, name_a, name_b):
    ### BEGIN SOLUTION
    if low > 0:
        return f"{name_b} is better"
    if high < 0:
        return f"{name_a} is better"
    return "no detectable difference"
    ### END SOLUTION


verdict(-0.010, 0.014, "boosting", "forest")

# %%
grade("w07.verdict", verdict)

# %% [markdown]
# ## 5. "No detectable difference" is a real answer
#
# **Why.** Managers and reviewers want a winner. Declaring one when the data cannot show it leads to churn:
# next month's evaluation "reverses" the decision, and nobody trusts the numbers any more.
#
# **Idea.** When the paired interval contains 0, write exactly that, with the interval: "the forest and boosting
# models score the same within our measurement precision (difference +0.003, 95% interval -0.010 to +0.014, 16
# test couriers)". Then choose on **other** grounds (simplicity, speed, cost; notebook 27). If the decision really
# needs a finer answer, estimate how much more data you need. Interval widths shrink like $1/\sqrt{\text{number of
# groups}}$, so halving the width needs **four times** as many test couriers.
#
# **Try it.** Re-run the paired comparison with `n_boot=200` and `seed=1`, `2`, `3`. The interval moves a little
# between seeds, but the verdict should not. If it flips, the evidence is borderline; say so.

# %%
low, high = percentile_interval(paired_difference(y_test, scores["boosting"], scores["forest"], couriers,
                                                  roc_auc_score, n_boot=200, seed=1))
round(low, 3), round(high, 3)

# %% [markdown]
# ### Exercise 5.1 · How many groups would we need?
#
# Write `groups_needed(width_now, n_groups_now, target_width)`: using width $\propto 1/\sqrt{n}$, return the
# number of groups needed for the interval to shrink to `target_width`, **rounded up** to a whole number (an int).
# If the current width is already at or below the target, return `n_groups_now`.

# %%
import math


def groups_needed(width_now, n_groups_now, target_width):
    ### BEGIN SOLUTION
    if width_now <= target_width:
        return int(n_groups_now)
    return int(math.ceil(n_groups_now * (width_now / target_width) ** 2 - 1e-9))
    ### END SOLUTION


groups_needed(0.024, 16, 0.006)

# %%
grade("w07.groups_needed", groups_needed)

# %% [markdown]
# To narrow the forest-vs-boosting interval (width about 0.024) to 0.006, which would be needed to detect a
# difference of about 0.003, we would need about 256 test couriers instead of 16. That is a business question
# ("is a 0.003 AUC difference worth collecting that data?"), and usually the answer is no.

# %% [markdown]
# ## Quiz

# %% [markdown]
# **Q1.** Model B has test accuracy 0.812 and model A 0.806 on 1,000 test rows. What can you conclude?
#
# - a) B is better, because 0.812 > 0.806.
# - b) Nothing yet: a difference of 0.006 is well inside the noise of a 1,000-row test set (SE about 0.012); compute
#   a paired interval of the difference.
# - c) A is better, because smaller numbers are more stable.
# - d) The test set is too small to compute any interval.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"
### END SOLUTION
quiz("w07.26_q1", answer)

# %% [markdown]
# **Q2.** Your test set has 5,000 rows from 40 customers. Why is a row bootstrap interval misleading?
#
# - a) Row bootstrap only works for accuracy, not AUC.
# - b) It is too wide, because it counts every row.
# - c) The bootstrap needs at least 10,000 rows.
# - d) Rows of one customer are correlated; resampling rows treats them as 5,000 independent pieces of evidence
#   and gives an interval that is too narrow for new customers.

# %%
### BEGIN SOLUTION
answer = "d"
### STARTER
answer = "?"
### END SOLUTION
quiz("w07.26_q2", answer)

# %% [markdown]
# **Q3.** The 95% intervals of two models overlap. What is the right next step?
#
# - a) Conclude they are equal.
# - b) Compute the paired interval of their difference on the same resamples; overlap of separate intervals is not
#   the right test.
# - c) Conclude the one with the higher point estimate is better.
# - d) Use a larger level, such as 99%, so the intervals separate.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"
### END SOLUTION
quiz("w07.26_q3", answer)

# %% [markdown]
# **Q4.** A paired interval of B - A is [-0.008, +0.015]. Which report is correct?
#
# - a) "B is better by +0.004."
# - b) "A is better."
# - c) "No detectable difference between A and B on this test set (difference interval -0.008 to +0.015); we choose
#   on simplicity and cost."
# - d) "The models are identical."

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"
### END SOLUTION
quiz("w07.26_q4", answer)

# %% [markdown]
# **Q5.** With 16 test couriers your interval is 0.08 wide. Roughly how many test couriers would make it 0.04 wide?
#
# - a) 32
# - b) 24
# - c) 64
# - d) 160

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"
### END SOLUTION
quiz("w07.26_q5", answer)

# %% [markdown]
# ## Recap
#
# - A test score estimates $E_{out}$; report it with an interval. For independent rows, accuracy has
#   $SE = \sqrt{p(1-p)/n}$.
# - The bootstrap gives an interval for any metric: resample the test set with replacement ~1,000 times, take the
#   2.5th and 97.5th percentiles.
# - Resample the unit you generalise to: whole couriers, customers, machines or experiments, not rows. Row
#   intervals on grouped data are too narrow.
# - Compare models with a **paired** interval of the difference on the same resamples, not by checking whether two
#   separate intervals overlap.
# - An interval of the difference that contains 0 means "no detectable difference": say so, and choose on other
#   grounds.
# - Interval width shrinks like $1/\sqrt{n}$: half the width needs four times the groups.
#
# ## On the job
#
# Every model comparison an ML engineer writes up (in a pull request, an experiment log, a decision memo) should
# carry intervals and the number of independent units behind them. Reviewers at good companies will ask "how many
# customers is that?" and "is the difference outside the noise?". The functions you wrote today are short enough
# to keep in the project's evaluation module and run on every comparison.
#
# ## Going further
#
# - Handbook and advanced track: [17 · Uncertainty](../advanced/notebooks/17_uncertainty.ipynb) goes further
#   (permutation tests, power analysis) on the project data.
# - Efron and Tibshirani's *An Introduction to the Bootstrap* is the classic reference.
# - Next: [27 · Error analysis and choosing a model](27_error_analysis_model_choice.ipynb).

# %% [markdown]
# ## Record your progress
#
# Flags: `reading`, `guided` (you passed the graded exercises), `independent` (you solved them without hints or
# solutions), `review` (come back to this).

# %%
from mlcourse.progress import mark

# mark("26", "reading")
# mark("26", "guided")
