# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/19_metrics_for_decisions.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 19 · Metrics and thresholds that match decisions
#
# **Week 5 · lesson · about 100 minutes**
#
# A classifier does not output "churn" or "stay". It outputs a **score**, and somebody chooses a **threshold** that
# turns scores into actions. That choice is where the model meets the business, and accuracy at a threshold of
# 0.5 is almost never the right way to make it.
#
# **What you will learn**
#
# - the confusion matrix, by hand, and the metrics built from it: precision, recall, F1;
# - ranking metrics: ROC-AUC and PR-AUC, and why they tell different stories when positives are rare;
# - choosing a threshold from a cost matrix, from a contact budget, and from both;
# - calibration: when a score of 0.7 really means "70% of these churn", in one picture.
#
# **What you need:** notebook 17 (costs of errors, break-even precision) and notebook 18 (the churn table and the
# logistic-regression pipeline).
#
# **How grading works:** most exercises are functions; the grader runs them on random inputs and edge cases and
# compares the results with scikit-learn.

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
# The same data and splits as notebook 18, and the logistic regression fitted on the training rows. All
# choices in this notebook are made on the **validation** rows; the test set stays locked for the lab.

# %%
from sklearn.compose import make_column_transformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from mlcourse.churn import build_churn_table, FEATURES, NUMERIC, CATEGORICAL

table = build_churn_table()
X, y = table[FEATURES], table["churned"]
X_rest, X_test, y_rest, y_test = train_test_split(X, y, test_size=0.25, random_state=0, stratify=y)
X_train, X_val, y_train, y_val = train_test_split(X_rest, y_rest, test_size=0.25, random_state=0,
                                                  stratify=y_rest)
preprocess = make_column_transformer((StandardScaler(), NUMERIC),
                                     (OneHotEncoder(handle_unknown="ignore"), CATEGORICAL))
model = make_pipeline(preprocess, LogisticRegression(max_iter=1000)).fit(X_train, y_train)
scores = model.predict_proba(X_val)[:, 1]          # P(churn) for each validation customer
y_val = y_val.to_numpy()
print(len(scores), "validation customers; first scores:", scores[:5].round(2))

# %% [markdown]
# ## 1 · The confusion matrix
#
# **Why.** "Accuracy 0.63" hides *which* mistakes the model makes. The retention team cares a lot about the
# difference between a wasted call and a missed churner (notebook 17), so you need them counted separately.
#
# **Idea.** Fix a threshold $t$ and predict 1 ("will churn") when the score is at least $t$. Every customer then
# falls into one of four cells:
#
# | | predicted 1 (contact) | predicted 0 (leave alone) |
# |---|---|---|
# | **actually churns (1)** | **TP** true positive | **FN** false negative: a missed churner |
# | **actually stays (0)** | **FP** false positive: a wasted call | **TN** true negative |
#
# Accuracy is $(TP + TN) / n$: it adds the two kinds of correct answers and treats both kinds of error alike.

# %%
from sklearn.metrics import confusion_matrix

y_pred = (scores >= 0.5).astype(int)
print(confusion_matrix(y_val, y_pred))      # rows: actual 0, 1; columns: predicted 0, 1

# %% [markdown]
# scikit-learn lays the matrix out with actual classes as rows and predicted classes as columns, **0 first**, so the
# top-left is TN and the bottom-right is TP. At $t = 0.5$ the model finds 31 of the 58 churners (TP = 31, FN = 27)
# and wrongly flags 18 of the 65 stayers (FP = 18). This layout trips everyone up at least once, which is why you
# will write your own, with named counts.
#
# **Try it.** Change the threshold to 0.3 and then 0.7. Which cells grow, which shrink? Before running, predict the
# direction of each.

# %% [markdown]
# ### Exercise 1 · count the four cells
#
# Write `confusion_counts(y_true, y_pred)` returning a dict `{"tp": ..., "fp": ..., "fn": ..., "tn": ...}` of
# integers. Inputs are 0/1 (or True/False) lists or arrays of equal length; `np.asarray(...).astype(int)` makes
# them uniform.

# %%
def confusion_counts(y_true, y_pred):
    ### BEGIN SOLUTION
    t = np.asarray(y_true).astype(int)
    p = np.asarray(y_pred).astype(int)
    return {"tp": int(((t == 1) & (p == 1)).sum()), "fp": int(((t == 0) & (p == 1)).sum()),
            "fn": int(((t == 1) & (p == 0)).sum()), "tn": int(((t == 0) & (p == 0)).sum())}
    ### END SOLUTION


# %%
grade("w05.confusion_counts", confusion_counts)

# %% [markdown]
# ## 2 · Precision, recall and F1
#
# **Why.** The retention team asks two different questions: "of the people we call, how many were really
# leaving?" (is the call list worth the staff time?) and "of all the people who are leaving, how many do we
# reach?" (how much churn are we addressing?). Each has a name.
#
# **Idea.**
#
# - **precision** $= TP / (TP + FP)$: the share of contacted customers who were real churners. This is the number
#   the break-even precision from notebook 17 is compared with.
# - **recall** $= TP / (TP + FN)$: the share of all churners we contacted (also called sensitivity, or the true
#   positive rate).
# - **F1** $= 2PR / (P + R)$, their harmonic mean: high only when both are high. Useful as one summary when you have
#   no costs; when you do have costs, use them instead (section 4).
#
# Lowering the threshold contacts more people: recall goes up, precision usually goes down. There is no free
# lunch, only a trade-off that the costs should settle.
#
# When a denominator is 0 (nobody predicted positive, or no actual positives) the metric is undefined; the common
# convention, which scikit-learn's `zero_division=0` follows, is to report 0.0.

# %% [markdown]
# ### Exercise 2 · precision, recall, F1
#
# Write `precision_recall_f1(y_true, y_pred)` returning a tuple of three floats `(precision, recall, f1)`, with 0.0
# whenever a denominator is zero. You may call your `confusion_counts`.

# %%
def precision_recall_f1(y_true, y_pred):
    ### BEGIN SOLUTION
    c = confusion_counts(y_true, y_pred)
    p = c["tp"] / (c["tp"] + c["fp"]) if c["tp"] + c["fp"] else 0.0
    r = c["tp"] / (c["tp"] + c["fn"]) if c["tp"] + c["fn"] else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return float(p), float(r), float(f)
    ### END SOLUTION


# %%
grade("w05.precision_recall_f1", precision_recall_f1)

# %%
for t in [0.3, 0.4, 0.5, 0.6, 0.7]:
    p, r, f = use(precision_recall_f1, y_val, (scores >= t).astype(int))
    print(f"threshold {t:.1f}: contacted {int((scores >= t).sum()):3d}  precision {p:.2f}  recall {r:.2f}  F1 {f:.2f}")

# %% [markdown]
# As the threshold rises from 0.3 to 0.7 the list shrinks from 90 to 19 customers, precision rises from 0.51 to
# 0.84 and recall falls from 0.79 to 0.28. Every row is a different business policy; none is "the" right one until
# we bring in costs.

# %% [markdown]
# ## 3 · Ranking metrics: ROC-AUC and PR-AUC
#
# **Why.** Before you pick a threshold, you want to know whether the scores *rank* customers well at all. A
# threshold-free number is also how you compare models fairly.
#
# **Idea.** Sweep the threshold from high to low and plot what happens:
#
# - the **ROC curve** plots recall (true positive rate) against the false positive rate $FP / (FP + TN)$. Its area,
#   **ROC-AUC**, has a lovely meaning: the probability that a random churner gets a higher score than a random
#   stayer. 0.5 is a coin flip, 1.0 is a perfect ranking;
# - the **precision-recall curve** plots precision against recall. Its area, **PR-AUC** (scikit-learn's
#   `average_precision_score`), starts from the share of positives: a random ranking scores about the prevalence.
#
# When positives are **rare**, these two disagree. The false positive rate divides by the (huge) number of
# negatives, so thousands of false alarms barely move ROC-AUC; precision does not forgive them.

# %%
from sklearn.datasets import make_classification
from sklearn.metrics import average_precision_score, roc_auc_score

# A synthetic problem where only about 1% of cases are positive (think: fraud).
Xr, yr = make_classification(n_samples=10000, n_features=8, n_informative=3, weights=[0.99], flip_y=0,
                             class_sep=1.5, random_state=0)
Xr_tr, Xr_va, yr_tr, yr_va = train_test_split(Xr, yr, test_size=0.5, random_state=0, stratify=yr)
rare_scores = LogisticRegression(max_iter=1000).fit(Xr_tr, yr_tr).predict_proba(Xr_va)[:, 1]
random_scores = np.random.default_rng(0).random(len(yr_va))
print("positives:", yr_va.mean().round(3))
for name, s in [("model", rare_scores), ("random", random_scores)]:
    print(f"{name:7s} ROC-AUC {roc_auc_score(yr_va, s):.3f}   PR-AUC {average_precision_score(yr_va, s):.3f}")
print("churn model on validation: ROC-AUC", round(roc_auc_score(y_val, scores), 3),
      " PR-AUC", round(average_precision_score(y_val, scores), 3), " (prevalence", y_val.mean().round(3), ")")

# %% [markdown]
# On the rare-event problem the model's ROC-AUC is 0.91, which sounds excellent, while its PR-AUC is only 0.25:
# among the cases it ranks highest, false alarms still crowd out the real positives. Random scores give a ROC-AUC
# near 0.5 (0.54 here: with only 50 positives the estimate is noisy) and a PR-AUC near the prevalence (0.013), which
# is why a PR-AUC must always be read next to the share of positives. For the churn data, where almost half the
# customers churn, the two numbers are close (0.66 and 0.69 on validation) and tell a similar story.
#
# **Rule of thumb:** with balanced classes either works; with rare positives that you must act on, report PR-AUC
# (or precision at your budget) next to ROC-AUC.
#
# **Try it.** Change `weights=[0.97]` to `[0.5]` and rerun. What happens to the gap between the two AUCs?

# %% [markdown]
# ### Exercise 3 · ROC-AUC from its meaning
#
# Write `roc_auc_by_ranks(y_true, scores)`: compare every (positive, negative) pair; count 1 if the positive has
# the higher score and 0.5 for a tie; return the total divided by the number of pairs. If `y_true` has no positives
# or no negatives, `raise ValueError(...)`. (NumPy broadcasting helps: `pos[:, None] - neg[None, :]` is the table
# of all pairwise differences.)

# %%
def roc_auc_by_ranks(y_true, scores):
    ### BEGIN SOLUTION
    y = np.asarray(y_true).astype(int)
    s = np.asarray(scores, dtype=float)
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        raise ValueError("ROC-AUC needs at least one positive and one negative")
    diff = pos[:, None] - neg[None, :]
    return float(((diff > 0).sum() + 0.5 * (diff == 0).sum()) / diff.size)
    ### END SOLUTION


# %%
grade("w05.roc_auc_by_ranks", roc_auc_by_ranks)

# %% [markdown]
# ### Exercise 4 · precision at k
#
# The retention team does not use a threshold: it calls the top of a ranked list until the budget runs out. The
# matching metric is **precision@k**: the precision among the `k` highest-scored customers. Write
# `precision_at_k(y_true, scores, k)`. If `k` exceeds the number of rows, use all rows; if `k` is 0, return 0.0.
# (`np.argsort(-scores, kind="stable")[:k]` gives the positions of the `k` highest scores.)

# %%
def precision_at_k(y_true, scores, k):
    ### BEGIN SOLUTION
    y = np.asarray(y_true).astype(int)
    if k <= 0:
        return 0.0
    top = np.argsort(-np.asarray(scores, dtype=float), kind="stable")[:k]
    return float(y[top].mean())
    ### END SOLUTION


# %%
grade("w05.precision_at_k", precision_at_k)

# %% [markdown]
# ### Exercise 5 · recall at k
#
# Write `recall_at_k(y_true, scores, k)`: the share of **all** positives that are among the `k` highest-scored rows
# (0.0 if there are no positives or `k` is 0).

# %%
def recall_at_k(y_true, scores, k):
    ### BEGIN SOLUTION
    y = np.asarray(y_true).astype(int)
    if y.sum() == 0 or k <= 0:
        return 0.0
    top = np.argsort(-np.asarray(scores, dtype=float), kind="stable")[:k]
    return float(y[top].sum() / y.sum())
    ### END SOLUTION


# %%
grade("w05.recall_at_k", recall_at_k)

# %%
k = 18          # notebook 17's budget: 100 calls for 655 customers, about 15%; 15% of 123 is 18
print("precision@18:", round(use(precision_at_k, y_val, scores, k), 3),
      "  recall@18:", round(use(recall_at_k, y_val, scores, k), 3))

# %% [markdown]
# With the budget, 15 of the 18 top-ranked validation customers are churners (precision 0.83, far above the
# break-even precision of 0.33), but they cover only about a quarter of all churners (recall 0.26). A useful pair of numbers for the
# team: "the list is good; the budget, not the model, is what limits how much churn we can reach".

# %% [markdown]
# ## 4 · Choosing a threshold from costs and a budget
#
# **Why.** This is the decision. Everything before it was preparation.
#
# **Idea.** Write down the cost of each error (notebook 17: a false positive, a wasted call, costs `cost_fp`; a
# false negative, a missed churner, costs `cost_fn` in value not gained). For any threshold, the total cost is
#
# $$\text{cost}(t) = \text{cost\_fp} \cdot FP(t) + \text{cost\_fn} \cdot FN(t).$$
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c19-01.svg" alt="A score goes through a threshold test: above it, contact (a churner is a TP, a stayer an FP, a wasted call); below it, do nothing (a churner is an FN, a lost customer; a stayer a TN, no cost)" style="max-width:100%">
#
# Three ways to pick $t$, all on **validation** data:
#
# 1. **Minimise cost** over all candidate thresholds (every distinct score, plus "contact nobody").
# 2. **Respect the budget**: the lowest threshold that contacts at most the allowed number.
# 3. **Theory**: if the scores are calibrated probabilities (section 5), contacting a customer with churn
#    probability $p$ is worth it when $p \cdot \text{cost\_fn} \ge (1 - p) \cdot \text{cost\_fp}$, that is when
#    $p \ge \text{cost\_fp} / (\text{cost\_fp} + \text{cost\_fn})$. For notebook 17's numbers, $5 / 15 = 0.33$:
#    exactly the break-even precision, seen from the other side.
#
# In practice you use 1 and 2 together: the cheapest threshold that fits the budget (the lab does exactly that).

# %% [markdown]
# ### Exercise 6 · cost at a threshold
#
# Write `expected_cost(y_true, scores, threshold, cost_fp, cost_fn)`: predict 1 where `score >= threshold`, then
# return `cost_fp * FP + cost_fn * FN` as a float. A threshold of `float("inf")` means "contact nobody".

# %%
def expected_cost(y_true, scores, threshold, cost_fp, cost_fn):
    ### BEGIN SOLUTION
    y = np.asarray(y_true).astype(int)
    pred = np.asarray(scores, dtype=float) >= threshold
    return float(cost_fp * ((y == 0) & pred).sum() + cost_fn * ((y == 1) & ~pred).sum())
    ### END SOLUTION


# %%
grade("w05.expected_cost", expected_cost)

# %% [markdown]
# ### Exercise 7 · the cheapest threshold
#
# Write `best_threshold(y_true, scores, cost_fp, cost_fn)`: try every distinct score as a threshold, plus
# `float("inf")`, and return the one with the lowest `expected_cost`. If several tie, return the **highest** of them
# (the same cost with fewer calls is the safer policy).

# %%
def best_threshold(y_true, scores, cost_fp, cost_fn):
    ### BEGIN SOLUTION
    candidates = sorted(set(np.asarray(scores, dtype=float).tolist())) + [float("inf")]
    costs = [expected_cost(y_true, scores, t, cost_fp, cost_fn) for t in candidates]
    best = min(costs)
    return max(t for t, c in zip(candidates, costs) if c == best)
    ### END SOLUTION


# %%
grade("w05.best_threshold", best_threshold)

# %% [markdown]
# ### Exercise 8 · a threshold for a budget
#
# Write `budget_threshold(scores, budget)`: the **lowest** threshold such that at most `budget` customers have
# `score >= threshold`. Careful with ties: if the 18th and 19th scores are equal, a threshold at that value contacts
# both, so you may have to stop above it. Return `float("inf")` when `budget` is 0, and the smallest score when the
# budget covers everyone.

# %%
def budget_threshold(scores, budget):
    ### BEGIN SOLUTION
    s = np.asarray(scores, dtype=float)
    best = float("inf")
    for t in sorted(set(s.tolist()), reverse=True):
        if (s >= t).sum() <= budget:
            best = t
        else:
            break
    return float(best)
    ### END SOLUTION


# %%
grade("w05.budget_threshold", budget_threshold)

# %% [markdown]
# ### Exercise 9 · the threshold from theory
#
# Write `cost_threshold(cost_fp, cost_fn)`: the probability above which contacting is worth it, from the
# inequality in the Idea above.

# %%
def cost_threshold(cost_fp, cost_fn):
    ### BEGIN SOLUTION
    return cost_fp / (cost_fp + cost_fn)
    ### END SOLUTION


# %%
grade("w05.cost_threshold", cost_threshold)

# %% [markdown]
# **See it.** All three on the validation scores, with notebook 17's costs (`cost_fp = 5`, `cost_fn = 10`) and a
# budget of 18 calls:

# %%
thresholds = np.linspace(0.05, 0.95, 91)
costs = [use(expected_cost, y_val, scores, t, 5, 10) for t in thresholds]
t_cost = use(best_threshold, y_val, scores, 5, 10)
t_budget = use(budget_threshold, scores, 18)
t_theory = use(cost_threshold, 5, 10)
fig, ax = plt.subplots(figsize=(6, 3.5))
ax.plot(thresholds, costs)
for t, name, style in [(t_cost, "cheapest", "-"), (t_budget, "budget (18 calls)", "--"), (t_theory, "theory", ":")]:
    ax.axvline(t, color="gray", linestyle=style, label=f"{name}: {t:.2f}")
ax.set_xlabel("threshold")
ax.set_ylabel("total cost on validation")
ax.legend()
plt.show()
for name, t in [("cheapest", t_cost), ("budget", t_budget), ("theory", t_theory)]:
    print(f"{name:9s} t={t:.3f}  contacts {int((scores >= t).sum()):3d}  cost {use(expected_cost, y_val, scores, t, 5, 10):.0f}")

# %% [markdown]
# The cheapest threshold (0.25) contacts 101 of the 123 validation customers at a cost of 320; the theoretical
# 0.33 contacts 81 at 340; the budget threshold (0.72) contacts 18 and costs 445. The cost curve is low for small
# thresholds and climbs steeply above about 0.5: missing a churner (10) costs twice as much as a wasted call (5),
# so with these prices it pays to contact generously. The cheapest
# threshold and the theoretical one land close together and both want to call most of the validation customers;
# the budget of 18 forces a much higher threshold. In this case **the budget, not the model, decides**, and the
# right message to the team is "more call capacity would pay for itself".
#
# **Try it.** Make calls expensive: `cost_fp = 20`. Where do the cheapest and theoretical thresholds move now? Does
# the budget still bind?

# %% [markdown]
# ## 5 · Calibration in one picture
#
# **Why.** The theory threshold above, "contact when $p \ge 0.33$", only works if a score of 0.33 really means a
# one-in-three chance. Teams also turn scores into money forecasts ("expected churners in this list"), which needs
# the same property.
#
# **Idea.** A model is **calibrated** if, among all customers given a score near $p$, about a fraction $p$ actually
# churn. Check it with a **reliability diagram**: cut $[0, 1]$ into equal-width bins, and for each non-empty bin
# plot the mean predicted probability against the observed churn rate. A calibrated model hugs the diagonal.
# Logistic regression is usually close to calibrated (its loss rewards honest probabilities); a deep decision tree
# is not (its leaves are tiny, so its "probabilities" are mostly 0 or 1).
#
# The **Brier score**, the mean of $(p - y)^2$, summarises probability quality in one number (lower is better; it
# rewards both good ranking and good calibration).

# %% [markdown]
# ### Exercise 10 · a calibration table
#
# Write `calibration_table(y_true, probs, n_bins)`: cut $[0, 1]$ into `n_bins` equal-width bins (a probability of
# exactly 1.0 belongs to the last bin), drop empty bins, and return a DataFrame with columns `mean_predicted`,
# `observed_rate`, `n`, one row per non-empty bin from low to high. One way to find each row's bin:
# `np.minimum((probs * n_bins).astype(int), n_bins - 1)`.

# %%
def calibration_table(y_true, probs, n_bins):
    ### BEGIN SOLUTION
    p = np.asarray(probs, dtype=float)
    df = pd.DataFrame({"bin": np.minimum((p * n_bins).astype(int), n_bins - 1), "p": p,
                       "y": np.asarray(y_true, dtype=float)})
    g = df.groupby("bin").agg(mean_predicted=("p", "mean"), observed_rate=("y", "mean"), n=("y", "size"))
    return g.reset_index(drop=True)
    ### END SOLUTION


# %%
grade("w05.calibration_table", calibration_table)

# %% [markdown]
# ### Exercise 11 · the Brier score
#
# Write `brier_score(y_true, probs)`: the mean of `(probs - y_true) ** 2`.

# %%
def brier_score(y_true, probs):
    ### BEGIN SOLUTION
    return float(np.mean((np.asarray(probs, dtype=float) - np.asarray(y_true, dtype=float)) ** 2))
    ### END SOLUTION


# %%
grade("w05.brier_score", brier_score)

# %%
from sklearn.tree import DecisionTreeClassifier

tree = make_pipeline(preprocess, DecisionTreeClassifier(max_depth=8, random_state=0)).fit(X_train, y_train)
tree_scores = tree.predict_proba(X_val)[:, 1]
fig, ax = plt.subplots(figsize=(4.5, 4.5))
ax.plot([0, 1], [0, 1], color="gray", linestyle=":", label="perfectly calibrated")
for name, s in [("logistic regression", scores), ("tree, depth 8", tree_scores)]:
    t = use(calibration_table, y_val, s, 5)
    ax.plot(t["mean_predicted"], t["observed_rate"], marker="o",
            label=f"{name} (Brier {use(brier_score, y_val, s):.3f})")
ax.set_xlabel("mean predicted probability")
ax.set_ylabel("observed churn rate")
ax.legend(fontsize=8)
plt.show()

# %% [markdown]
# With only 123 validation customers and 5 bins each point is a rough estimate, but the shapes differ. The
# logistic regression stays near the diagonal except in its lowest bin (18 customers scored about 0.13, of whom 39%
# churned). The tree is far off at both ends: 43 customers it scored 0.00 churned at a rate of 30%, and 24 it scored
# 0.98 churned at 67%. Its leaves are small, so its "probabilities" are over-confident. Brier scores: 0.237 for the
# logistic regression, 0.278 for the tree. If you need
# probabilities from a model like that, scikit-learn's `CalibratedClassifierCV` can recalibrate it on held-out data;
# for ranking and budget decisions, calibration matters less.

# %% [markdown]
# ## Quiz
#
# **Q1.** At threshold 0.5 a model has precision 0.80 and recall 0.20. What happens, typically, when you lower the
# threshold to 0.3? (a) both go up (b) recall goes up, precision usually goes down (c) precision goes up, recall
# goes down (d) neither changes, because the model is the same

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w05.19_q1", answer)

# %% [markdown]
# **Q2.** 1% of transactions are fraud. Model A has ROC-AUC 0.95 and PR-AUC 0.20. What does the PR-AUC tell you that
# the ROC-AUC hides? (a) nothing: ROC-AUC is the better metric (b) among the transactions it flags, false alarms
# still far outnumber fraud for most thresholds (c) the model is badly calibrated (d) the model is overfitting

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w05.19_q2", answer)

# %% [markdown]
# **Q3.** A false positive costs 2 and a false negative costs 18. For calibrated probabilities, above which
# probability should you act? (a) 0.5 (b) 0.9 (c) 0.1 (d) 0.18

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w05.19_q3", answer)

# %% [markdown]
# **Q4.** The team can call 50 customers a week, whatever the scores. Which single number best describes how useful
# the model is to them? (a) accuracy at threshold 0.5 (b) ROC-AUC (c) precision among the 50 highest-scored
# customers (precision@50) (d) the F1 score at threshold 0.5

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w05.19_q4", answer)

# %% [markdown]
# **Q5.** Among customers scored around 0.8 by a model, only 45% churn. What is true? (a) the model ranks badly
# (b) the model is over-confident (poorly calibrated) in that range; its ranking may still be fine (c) the
# threshold should be 0.45 (d) the model is perfectly calibrated

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w05.19_q5", answer)

# %% [markdown]
# ## Recap
#
# - A classifier gives scores; a threshold turns them into actions. 0.5 is a default, not a decision.
# - The confusion matrix counts TP, FP, FN, TN; scikit-learn puts actual classes in rows, class 0 first.
# - Precision: how good the contact list is. Recall: how much of the problem it reaches. F1 combines them when you
#   have no costs.
# - ROC-AUC is the chance a random positive outranks a random negative; with rare positives read PR-AUC (against
#   the prevalence) or precision at your budget.
# - Choose the threshold on validation data: minimise `cost_fp · FP + cost_fn · FN`, within the budget; for
#   calibrated probabilities the cost-optimal threshold is `cost_fp / (cost_fp + cost_fn)`.
# - Calibration: a score of $p$ should mean "a fraction $p$ of these are positive". Check with a reliability
#   diagram and the Brier score.
#
# **On the job.** Picking the threshold is often done in a meeting, not in a notebook. Bring a small table
# (threshold, people contacted, precision, recall, expected cost) for a few candidate thresholds, and let the team
# choose with the numbers in front of them; then write the chosen threshold and the reason into the model's
# documentation.
#
# **Going further.** scikit-learn's `precision_recall_curve`, `roc_curve` and `TunedThresholdClassifierCV` automate
# parts of this notebook; the handbook chapters on metrics from decisions and on thresholds, imbalance and
# calibration go deeper. Next: notebook 20, the lab, where you put the whole week together.

# %%
# Record your progress (optional; stored in progress/progress.json):
from mlcourse.progress import mark
# mark("19", "reading")
# mark("19", "guided")
