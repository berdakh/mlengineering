# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/20_lab_churn_model.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 20 · Lab: a churn model you can defend
#
# **Week 5 · lab · about 90 minutes**
#
# This lab introduces nothing new. A retention manager sends a request; you frame it, lock a test set, build
# baselines and a model, pick a threshold from the team's costs and call budget, measure the decision on the test
# set, and write a recommendation the manager can act on. Each step uses the previous one's result.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c20-01.svg" alt="The lab in seven steps: frame, split, baselines, model, threshold from costs and budget, decision summary on test, written recommendation" style="max-width:100%">
#
# **What you will practise**
#
# - turning a request into a framing worksheet with numbers (notebook 17);
# - honest baselines and a model in a pipeline (notebook 18);
# - choosing a threshold on validation data from costs and a budget, and reporting the decision once on the test
#   set (notebook 19).
#
# **What you need:** notebooks 17, 18 and 19. You may copy your own functions from them.
#
# **How grading works:** each exercise is graded on its own inputs, so a mistake in one step does not block the
# next: if a function is not finished, the cells that use it fall back to the course's version and say so.

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
from sklearn.model_selection import train_test_split
from mlcourse.churn import build_churn_table, FEATURES, NUMERIC, CATEGORICAL
from mlcourse.graders.w05 import use

# %% [markdown]
# ## The message
#
# > **From:** Aigerim, retention manager
# > **Subject:** who should we call next quarter?
# >
# > Hi! Next quarter we want to try calling customers who are about to leave. Some facts:
# >
# > - We score customers on the first morning of the quarter, from everything we know up to the day before.
# > - A customer counts as lost if they place no (non-cancelled) order in the **90 days** after that.
# > - A call costs us **12** (agent time and a small voucher). If the customer was going to leave, the call keeps
# >   them about **30%** of the time, and a kept customer is worth **60** in margin.
# > - The team can make calls to at most **15%** of our active customers. We call people in order of risk.
# >
# > Can you tell me how many people we should call, and what we can expect from it? And please tell me honestly
# > whether the model is better than what we do today: we call everyone who has not ordered for a long time.
#
# Notice how this differs from notebook 17's retention request: a call is more expensive and a saved customer
# brings less. Compute the break-even precision before going further (`12 / (0.3 × 60)`): it is 0.67, above the
# churn rate of 0.47, so calling at random **loses** money here.

# %%
table = build_churn_table(cutoff="2025-06-30", horizon_days=90)
VALUE_SAVED, CONTACT_COST, SUCCESS_RATE, BUDGET_SHARE = 60, 12, 0.30, 0.15
print(table.shape, "churn rate:", table["churned"].mean().round(3))
print("break-even precision:", CONTACT_COST / (SUCCESS_RATE * VALUE_SAVED))

# %% [markdown]
# ## Exercise 1 · the framing
#
# Fill in the worksheet from the message, as a dict:
#
# - `"unit"`: `"customer"`, `"order"` or `"call"`;
# - `"horizon_days"`: the label window, in days;
# - `"cost_fp"`: the cost of calling a customer who would have stayed;
# - `"cost_fn"`: the net value missed by not calling a customer who leaves (the call would have worked only some of
#   the time, and it would have cost money too);
# - `"budget_share"`: the largest fraction of customers the team can call, between 0 and 1;
# - `"decision"`: (a) call everyone the model flags at threshold 0.5, (b) call customers in order of risk,
#   stopping at the budget or earlier if calls stop paying off, (c) email every customer a voucher.

# %%
### BEGIN SOLUTION
framing = {"unit": "customer", "horizon_days": 90, "cost_fp": 12, "cost_fn": 6, "budget_share": 0.15,
           "decision": "b"}
### STARTER
framing = {"unit": "?", "horizon_days": None, "cost_fp": None, "cost_fn": None, "budget_share": None,
           "decision": "?"}
### END SOLUTION

# %%
grade("w05.lab_framing", framing)

# %%
COST_FP, COST_FN = 12, 6        # the values from your framing: a wasted call, and the net value of a save missed

# %% [markdown]
# ## Exercise 2 · lock the test set
#
# Write `lab_split(table, seed)` returning `X_train, X_test, y_train, y_test`: `X` holds exactly the `FEATURES`
# columns, `y` is `churned`, 25% of the rows go to the test set, stratified on the label, reproducible for `seed`.
# The cell after the grader also carves a **validation** set out of the training rows: you will choose the
# threshold there, and touch the test set only in Exercise 6.

# %%
def lab_split(table, seed):
    ### BEGIN SOLUTION
    return train_test_split(table[FEATURES], table["churned"], test_size=0.25, random_state=seed,
                            stratify=table["churned"])
    ### END SOLUTION


# %%
grade("w05.lab_split", lab_split)

# %%
X_train, X_test, y_train, y_test = use(lab_split, table, 42)
X_fit, X_val, y_fit, y_val = train_test_split(X_train, y_train, test_size=0.3, random_state=42, stratify=y_train)
print("fit", len(X_fit), " validation", len(X_val), " test", len(X_test), "(locked)")

# %% [markdown]
# ## Exercise 3 · baselines
#
# Aigerim's team today calls customers who have not ordered for a long time: the **recency baseline**. Write
# `lab_baselines(X_train, y_train, X_test, y_test)` returning a dict with
#
# - `"majority_accuracy"`: the accuracy on the test rows of always predicting the training set's most common class;
# - `"recency_auc"`: the ROC-AUC on the test rows when the raw `days_since_last_order` column is used as the
#   score (`sklearn.metrics.roc_auc_score`).

# %%
from sklearn.metrics import roc_auc_score


def lab_baselines(X_train, y_train, X_test, y_test):
    ### BEGIN SOLUTION
    values, counts = np.unique(np.asarray(y_train), return_counts=True)
    majority = values[np.argmax(counts)]
    return {"majority_accuracy": float(np.mean(np.asarray(y_test) == majority)),
            "recency_auc": float(roc_auc_score(y_test, X_test["days_since_last_order"]))}
    ### END SOLUTION


# %%
grade("w05.lab_baselines", lab_baselines)

# %% [markdown]
# ## Exercise 4 · the model
#
# Write `make_model()` returning a new, unfitted pipeline that scores churn risk. Start from notebook 18's
# `make_logreg`; you may change it if you can show on the validation set that the change helps. The grader fits it
# on its own split and requires a test ROC-AUC of at least 0.70 that also beats the recency baseline.

# %%
from sklearn.compose import make_column_transformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def make_model():
    ### BEGIN SOLUTION
    preprocess = make_column_transformer((StandardScaler(), NUMERIC),
                                         (OneHotEncoder(handle_unknown="ignore"), CATEGORICAL))
    return make_pipeline(preprocess, LogisticRegression(max_iter=1000))
    ### END SOLUTION


# %%
grade("w05.lab_model", make_model)

# %%
model = use(make_model).fit(X_fit, y_fit)
val_scores = model.predict_proba(X_val)[:, 1]
print("validation ROC-AUC, model  :", round(roc_auc_score(y_val, val_scores), 3))
print("validation ROC-AUC, recency:", round(roc_auc_score(y_val, X_val["days_since_last_order"]), 3))

# %% [markdown]
# ## Exercise 5 · the threshold
#
# Write `lab_choose_threshold(y_val, scores, cost_fp, cost_fn, budget_share)`: among the candidate thresholds
# (every distinct score, plus `float("inf")`) keep only those that contact at most
# `int(np.floor(budget_share * len(scores)))` customers (`score >= threshold`), and return the one with the lowest
# total cost `cost_fp * FP + cost_fn * FN`; on a tie, the highest. This is notebook 19's `best_threshold` with the
# budget as a constraint.

# %%
def lab_choose_threshold(y_val, scores, cost_fp, cost_fn, budget_share):
    ### BEGIN SOLUTION
    y = np.asarray(y_val).astype(int)
    s = np.asarray(scores, dtype=float)
    cap = int(np.floor(budget_share * len(s)))
    best_t, best_cost = None, None
    for t in sorted(set(s.tolist()), reverse=True) + [float("inf")]:
        pred = s >= t
        if pred.sum() > cap:
            continue
        cost = cost_fp * ((y == 0) & pred).sum() + cost_fn * ((y == 1) & ~pred).sum()
        if best_cost is None or cost < best_cost or (cost == best_cost and t > best_t):
            best_t, best_cost = t, cost
    return float(best_t)
    ### END SOLUTION


# %%
grade("w05.lab_choose_threshold", lab_choose_threshold)

# %%
threshold = use(lab_choose_threshold, y_val, val_scores, COST_FP, COST_FN, BUDGET_SHARE)
print("chosen threshold:", round(threshold, 3), " validation customers contacted:", int((val_scores >= threshold).sum()),
      "of", len(val_scores), "(budget", int(np.floor(BUDGET_SHARE * len(val_scores))), ")")

# %% [markdown]
# ## Exercise 6 · the decision, measured once on the test set
#
# Write `lab_decision_summary(y_true, scores, threshold, value_saved, contact_cost, success_rate)` returning a dict:
#
# - `"n_contacted"`: customers with `score >= threshold`;
# - `"precision"`, `"recall"`: of the contacted list (0.0 when a denominator is zero);
# - `"net_value"`: the expected net value of calling that list, as in notebook 17's `policy_value`.
#
# The cell after the grader refits the model on all training rows (fit + validation: more data, same choices),
# scores the locked test set **once**, and compares three call lists of the same size: the model's, the recency
# baseline's (the customers silent for longest), and a random one.

# %%
def lab_decision_summary(y_true, scores, threshold, value_saved, contact_cost, success_rate):
    ### BEGIN SOLUTION
    y = np.asarray(y_true).astype(int)
    contact = np.asarray(scores, dtype=float) >= threshold
    tp = int((contact & (y == 1)).sum())
    n = int(contact.sum())
    return {"n_contacted": n,
            "precision": tp / n if n else 0.0,
            "recall": tp / y.sum() if y.sum() else 0.0,
            "net_value": float((success_rate * value_saved * y[contact] - contact_cost).sum())}
    ### END SOLUTION


# %%
grade("w05.lab_decision_summary", lab_decision_summary)

# %%
final = use(make_model).fit(X_train, y_train)
test_scores = final.predict_proba(X_test)[:, 1]
n_calls = int((test_scores >= threshold).sum())
recency_scores = X_test["days_since_last_order"].to_numpy().astype(float)
recency_threshold = np.sort(recency_scores)[::-1][max(n_calls - 1, 0)] if n_calls else np.inf
random_scores = np.random.default_rng(0).random(len(X_test))
random_threshold = np.sort(random_scores)[::-1][max(n_calls - 1, 0)] if n_calls else np.inf
args = (VALUE_SAVED, CONTACT_COST, SUCCESS_RATE)
summary = pd.DataFrame({
    "model": use(lab_decision_summary, y_test, test_scores, threshold, *args),
    "recency baseline": use(lab_decision_summary, y_test, recency_scores, recency_threshold, *args),
    "random list": use(lab_decision_summary, y_test, random_scores, random_threshold, *args),
}).T
summary["test ROC-AUC"] = [roc_auc_score(y_test, test_scores), roc_auc_score(y_test, recency_scores), 0.5]
baselines = use(lab_baselines, X_train, y_train, X_test, y_test)
print("majority-class accuracy on test:", round(baselines["majority_accuracy"], 3))
summary.round(3)

# %% [markdown]
# Read the table before writing anything. How many customers does the model call (out of how many in the test
# set)? How does its precision compare with the break-even precision of 0.67? Is the expected net value positive,
# and how does it compare with a list of the same size chosen by the recency baseline? The recency list ties on
# `days_since_last_order` are broken by position, so its exact size can differ by one or two.
#
# The test set holds 164 customers, a quarter of the shop's active customers; multiply by about four for a
# rough quarterly figure, and say so if you do. With so few calls, replacing one churner on the list by a stayer
# changes the net value by 18: present the numbers as estimates, not promises.

# %% [markdown]
# ## Exercise 7 · the recommendation
#
# Write `recommendation`: a short message to Aigerim (60-250 words) that she can act on. It must contain, using
# **your** numbers from the table above:
#
# 1. a comparison with the **baseline** (the word "baseline" must appear);
# 2. the action: how many customers to **call** or **contact**, and how they are chosen;
# 3. the expected money result: a net **value** (or cost/profit);
# 4. at least one **risk** or **limitation** (for example, the costs and the 30% are assumptions, or the test set is
#    small);
# 5. a **next** step (for example, a pilot with a control group, or monitoring the real success rate).
#
# The grader checks that these elements and at least three numbers are present; whether the message is *good* is
# up to you. Read it aloud: would a busy manager understand it in one pass?

# %%
### BEGIN SOLUTION
recommendation = """
Recommendation: next quarter, call the customers the model ranks as most at risk, up to the full budget of 15%:
on our held-out test set that was 23 of 164 customers, so about 90 calls for the whole shop.

Why: the model ranks churn risk better than what we do today. Its test ROC-AUC is 0.72, against 0.61 for the
recency baseline (calling the customers who have been silent longest). Of the 23 customers it would call, 17
really left: a precision of 0.74, above the 0.67 a call needs to pay for itself. That list has an expected net
value of about +30 per 164 customers (roughly +120 a quarter). A recency list of the same size has a precision
of 0.61 and an expected net value of -24, and a random list loses 60.

Risks and limitations: the call cost (12), the value of a kept customer (60) and especially the 30% success rate
are assumptions; the test set is small, so the value could be much lower; and one quarter may not represent the
next.

Next step: run a one-quarter pilot with a random control group, monitor the real success rate of calls, and
re-check the threshold once we know it.
"""
### STARTER
recommendation = ""  # write your message here (60-250 words)
### END SOLUTION

# %%
grade("w05.lab_recommendation", recommendation)

# %% [markdown]
# ## Quiz
#
# **Q1.** With Aigerim's costs the chosen threshold uses the whole budget. Suppose calls become more expensive and
# the cost-based threshold now contacts fewer customers than the budget allows. Why can that be right? (a) it cannot: always use the whole budget (b) below some score, a call's expected gain no longer covers
# its cost, so extra calls lose money (c) the validation set is too small to use the budget (d) the model is
# overfitting

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w05.20_q1", answer)

# %% [markdown]
# **Q2.** After seeing the test-set table you are tempted to lower the threshold a little, because the test value
# would be higher. What should you do? (a) lower it and report the new test value (b) keep the validation choice
# for the report; if you change it, the test value is no longer an honest estimate (c) average the two thresholds
# (d) retrain on the test set

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w05.20_q2", answer)

# %% [markdown]
# **Q3.** Why compare the model's call list with a recency list *of the same size*, rather than comparing AUCs only?
# (a) AUC cannot be computed for the recency rule (b) the team's decision is a list of a given size, so the value
# of that list is what matters; AUC averages over thresholds the team will never use (c) lists of different sizes
# cannot be compared at all (d) it is required by scikit-learn

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w05.20_q3", answer)

# %% [markdown]
# **Q4.** Aigerim asks: "So we will make exactly 30 profit per 164 customers?" What is the honest answer? (a) yes,
# the test set proves it (b) it is an estimate from a small test set under assumed costs; a pilot with a control
# group will measure the real number (c) no, it will be 0 because models never work in production (d) it will
# be higher, because the model will learn from the calls

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # your letter here
### END SOLUTION
quiz("w05.20_q4", answer)

# %% [markdown]
# ## Reflection
#
# Write three or four sentences in a text cell or in your notes: Which number in your recommendation are you least
# sure of, and what would make you more sure? What would change in your analysis if the success rate of a call
# were 50% instead of 30%? What would you check first if, after a pilot quarter, the called customers churned as
# often as the uncalled ones?
#
# ## What to show in your portfolio
#
# A one-page write-up: the framing worksheet, the baseline-vs-model table, the cost-vs-threshold plot from
# notebook 19 redrawn with Aigerim's costs, and your recommendation. This is what an ML engineer's work looks like
# from the outside: not "I trained a model", but "here is what to do, why, and how sure we are".
#
# **Next week:** Week 6 asks whether our validation was honest: time-based splits (training on one quarter and
# testing on the next) and leakage.

# %%
# Record your progress (optional; stored in progress/progress.json):
from mlcourse.progress import mark
# mark("20", "guided")
# mark("20", "independent")
