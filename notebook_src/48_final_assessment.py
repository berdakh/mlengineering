# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/48_final_assessment.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 48 · Final assessment
#
# **Week 12 · lab · about 120 minutes**
#
# Eight graded exercises, one from each part of the course: SQL, pandas, validation without leakage, a threshold
# from costs, a test that catches bugs, input validation for an API, a drift check, and a short written judgement.
# There are **no new concepts** here; every exercise names the notebooks to revisit if you get stuck.
#
# **How to take it.** Treat it like an exam: set aside two hours, work top to bottom, do not open the solutions, and
# use the course notebooks and tool guides as your open book. Grader messages tell you *what* is wrong, never the
# answer; a hint appears after a failed attempt. When you finish, fill in the self-assessment at the end honestly:
# it is the most useful output of this notebook.
#
# **What this assessment can and cannot tell you.** Passing every grader shows you can do each of these tasks on a
# clean, well-specified problem in a notebook. It does not certify job readiness: real work adds vague requirements,
# messy systems and other people. The self-assessment helps you decide what to practise next.
#
# **How grading works:** as in every lab, each exercise is followed by a grader cell. The written judgement
# (exercise 8) is checked for structure only.

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

# %%
import math
import numpy as np
import pandas as pd
from mlcourse.sql import sql
started = pd.Timestamp.now()

# %% [markdown]
# ## Exercise 1 · SQL: revenue share by category  (Weeks 2-3; notebooks 06, 07, 09)
#
# For each product category return `category`, `revenue` and `share` (the category's fraction of total revenue,
# between 0 and 1), highest revenue first. Revenue is `quantity * unit_price * (1 - discount)` per order line, from
# orders with status `delivered` or `shipped`. Do not round.

# %%
### BEGIN SOLUTION
query = """
WITH per_category AS (
  SELECT p.category, SUM(oi.quantity * oi.unit_price * (1 - oi.discount)) AS revenue
  FROM order_items AS oi
  JOIN orders   AS o ON o.order_id = oi.order_id
  JOIN products AS p ON p.product_id = oi.product_id
  WHERE o.status IN ('delivered', 'shipped')
  GROUP BY p.category
)
SELECT category, revenue, revenue / SUM(revenue) OVER () AS share
FROM per_category
ORDER BY revenue DESC
"""
### STARTER
query = """
YOUR QUERY HERE
"""
### END SOLUTION
grade("w12.final_sql", query)

# %% [markdown]
# ## Exercise 2 · pandas: a customer summary as of a date  (Weeks 3-4; notebooks 10, 14)
#
# Write `customer_summary(orders, cutoff)`. `orders` is a DataFrame with columns `order_id`, `customer_id`,
# `order_date` (text, `YYYY-MM-DD`) and `status`; `cutoff` is a date string. Count only orders that are **not
# cancelled** and dated **on or before** the cutoff. Return a DataFrame indexed by `customer_id` with two columns:
#
# - `n_orders`: the number of such orders;
# - `days_since_last`: days from the customer's latest such order to the cutoff (an integer).
#
# Customers with no such order do not appear. Do not modify `orders`.

# %%
def customer_summary(orders, cutoff):
    ### BEGIN SOLUTION
    cutoff = pd.Timestamp(cutoff)
    o = orders.assign(order_date=pd.to_datetime(orders["order_date"]))
    o = o[(o["status"] != "cancelled") & (o["order_date"] <= cutoff)]
    by_customer = o.groupby("customer_id")["order_date"]
    return pd.DataFrame({"n_orders": by_customer.size(),
                         "days_since_last": (cutoff - by_customer.max()).dt.days})
    ### END SOLUTION
    ### STARTER
    # YOUR CODE HERE
    raise NotImplementedError


# %%
grade("w12.final_pandas", customer_summary)

# %% [markdown]
# On the real shop (one way to check your function makes sense):

# %%
from mlcourse.graders.w12 import use   # use(): runs your function, or the course's version if yours is unfinished

orders = sql("SELECT order_id, customer_id, order_date, status FROM orders")
use(customer_summary, orders, "2025-09-30").describe().round(1)

# %% [markdown]
# ## Exercise 3 · validation without leakage  (Week 6; notebooks 21, 22)
#
# Sensor rows come from 40 machines, 10 rows each. Every machine has its own characteristic readings in the first
# three columns, and the label is a property of the machine. A model will be used on **new machines**.
#
# Write `honest_score(X, y, groups)` returning the mean accuracy of
# `make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))` under 5-fold cross-validation that keeps
# each machine's rows together (`GroupKFold(n_splits=5)` and `groups=groups`). The scaler must be inside the
# pipeline.

# %%
rng = np.random.default_rng(42)
machine = np.repeat(np.arange(40), 10)
machine_label = rng.integers(0, 2, 40)
y_machines = machine_label[machine]
X_machines = np.hstack([
    rng.normal(0, 1, (40, 3))[machine] + rng.normal(0, 0.05, (400, 3)),   # machine "fingerprint"
    rng.normal(0, 1, (400, 2)) + np.c_[1.2 * (2 * y_machines - 1), np.zeros(400)],   # real signal + noise
])

# %%
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold, KFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def honest_score(X, y, groups):
    ### BEGIN SOLUTION
    pipe = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    return float(cross_val_score(pipe, X, y, groups=groups, cv=GroupKFold(n_splits=5)).mean())
    ### END SOLUTION
    ### STARTER
    # YOUR CODE HERE
    raise NotImplementedError


# %%
grade("w12.final_grouped_cv", honest_score)

# %% [markdown]
# **Compare** (ungraded): the same pipeline with ordinary shuffled folds, which put rows of one machine on both sides.

# %%
naive = cross_val_score(make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
                        X_machines, y_machines, cv=KFold(5, shuffle=True, random_state=0)).mean()
print(f"grouped: {use(honest_score, X_machines, y_machines, machine):.3f} | shuffled rows: {naive:.3f}")

# %% [markdown]
# With the reference solution: 0.868 grouped, 0.885 with shuffled rows. The gap is small here because a linear model
# cannot memorise machine fingerprints well; a flexible model (try `KNeighborsClassifier(1)` in place of the
# pipeline) shows a much larger gap: 0.78 grouped against 0.93 shuffled. Write one sentence for yourself: which number would you report for new
# machines, and why?
#
# ## Exercise 4 · a threshold from costs  (Week 5; notebook 19)
#
# Write `best_threshold(y, scores, cost_fp, cost_fn)`. A row is flagged positive when `score >= t`. Try every
# distinct score as `t`, plus `math.inf` (flag nobody). Cost = `cost_fp * FP + cost_fn * FN`. Return the cheapest
# `t`; on a tie, the **larger** `t` (fewer people flagged).

# %%
def best_threshold(y, scores, cost_fp, cost_fn):
    ### BEGIN SOLUTION
    y = np.asarray(y)
    scores = np.asarray(scores, dtype=float)
    best_t, best_cost = None, None
    for t in sorted(set(scores.tolist())) + [math.inf]:
        flagged = scores >= t
        cost = cost_fp * int((flagged & (y == 0)).sum()) + cost_fn * int((~flagged & (y == 1)).sum())
        if best_cost is None or cost < best_cost or (cost == best_cost and t > best_t):
            best_t, best_cost = t, cost
    return best_t
    ### END SOLUTION
    ### STARTER
    # YOUR CODE HERE
    raise NotImplementedError


# %%
grade("w12.final_threshold", best_threshold)

# %% [markdown]
# ## Exercise 5 · tests that catch bugs  (Week 8; notebook 30)
#
# `rolling_mean(xs, k)` should return, for each position `i`, the mean of the last `k` values up to and including
# `xs[i]` (fewer at the start). Write test functions that each take the function under test as their argument
# (`def test_something(rolling_mean): ...`) and put them in the list `TESTS`. The grader runs them against a correct
# implementation (all must pass) and three buggy ones (each must be caught by at least one test): one that looks
# into the future, one that leaves out the current value, and one that always divides by `k`.

# %%
def rolling_mean(xs, k):
    """A correct implementation, so you can run your tests on it."""
    return [sum(xs[max(0, i - k + 1): i + 1]) / len(xs[max(0, i - k + 1): i + 1]) for i in range(len(xs))]


### BEGIN SOLUTION
def test_known_values(rolling_mean):
    assert rolling_mean([2, 4, 6, 8], 2) == [2.0, 3.0, 5.0, 7.0]


def test_start_uses_available_values(rolling_mean):
    assert rolling_mean([3, 5, 7], 3)[:2] == [3.0, 4.0]


def test_does_not_look_ahead(rolling_mean):
    a = rolling_mean([1, 1, 1, 100], 3)
    assert a[:3] == [1.0, 1.0, 1.0]


TESTS = [test_known_values, test_start_uses_available_values, test_does_not_look_ahead]
### STARTER
# YOUR CODE HERE: write your test functions, then list them (without parentheses)
TESTS = []
### END SOLUTION

# %%
for test in TESTS:
    test(rolling_mean)          # every test should pass on the correct version
grade("w12.final_tests", TESTS)

# %% [markdown]
# ## Exercise 6 · validate API input  (Week 9; notebooks 34, 35)
#
# Write a pydantic model `ChurnRequest` for the churn API with these fields, **all required**:
#
# - `recency_days`, `orders_90d`, `tenure_days`: integers, 0 or more;
# - `spend_90d`: a finite float (`FiniteFloat`), 0 or more;
# - `segment`: one of `"consumer"`, `"small_business"`, `"student"` (`Literal[...]`);
#
# and reject any extra field (`model_config = ConfigDict(extra="forbid")`). FastAPI turns every violation into a 422
# response automatically.

# %%
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, ValidationError

### BEGIN SOLUTION
class ChurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recency_days: int = Field(ge=0)
    orders_90d: int = Field(ge=0)
    spend_90d: FiniteFloat = Field(ge=0)
    tenure_days: int = Field(ge=0)
    segment: Literal["consumer", "small_business", "student"]
### STARTER
# YOUR CODE HERE: define the class ChurnRequest
ChurnRequest = None
### END SOLUTION

# %%
grade("w12.final_request_model", ChurnRequest)

# %% [markdown]
# ## Exercise 7 · a drift check  (Week 11; notebook 43)
#
# Write `psi(reference, current, bins=10)`, the population stability index:
#
# 1. inner bin edges from the **reference**: `np.quantile(reference, np.linspace(0, 1, bins + 1))[1:-1]`;
# 2. the share of reference values and of current values in each bin, using `np.digitize(values, edges)` (bin
#    numbers 0 to `bins - 1`) and `np.bincount(..., minlength=bins)`;
# 3. clip both shares at `1e-4` from below (so empty bins do not give `log(0)`);
# 4. return $\sum (c - r) \ln(c / r)$ as a float.

# %%
def psi(reference, current, bins=10):
    ### BEGIN SOLUTION
    reference = np.asarray(reference, dtype=float)
    current = np.asarray(current, dtype=float)
    edges = np.quantile(reference, np.linspace(0, 1, bins + 1))[1:-1]
    r = np.bincount(np.digitize(reference, edges), minlength=bins) / len(reference)
    c = np.bincount(np.digitize(current, edges), minlength=bins) / len(current)
    r, c = np.clip(r, 1e-4, None), np.clip(c, 1e-4, None)
    return float(np.sum((c - r) * np.log(c / r)))
    ### END SOLUTION
    ### STARTER
    # YOUR CODE HERE
    raise NotImplementedError


# %%
grade("w12.final_psi", psi)

# %% [markdown]
# On the shop: did the customers' order spend shift between the first and second half of 2025? (A common rule of
# thumb reads PSI below 0.1 as little change and above 0.25 as a large shift; treat these as conventions, not laws.)

# %%
spend = sql("""
SELECT o.order_date, SUM(oi.quantity * oi.unit_price * (1 - oi.discount)) AS value
FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.status <> 'cancelled' AND o.order_date LIKE '2025-%'
GROUP BY o.order_id
""")
first_half = spend.loc[spend["order_date"] < "2025-07-01", "value"]
second_half = spend.loc[spend["order_date"] >= "2025-07-01", "value"]
print(f"orders: {len(first_half)} then {len(second_half)} | PSI of order value: "
      f"{use(psi, first_half, second_half):.3f}")

# %% [markdown]
# With the reference solution: 1,163 orders in the first half and 2,514 in the second, and a PSI of 0.012. The shop
# sold many more orders later in the year, but the *distribution* of order values barely moved: volume and
# distribution are different questions.

# %% [markdown]
# ## Exercise 8 · a written judgement  (Weeks 7 and 12; notebooks 26, 27, 46)
#
# A **hypothetical** scenario (the numbers are made up for this exercise): a team compares two churn models on the
# same test customers. The product needs answers within 50 ms at the 95th percentile.
#
# | Model | PR-AUC (95% CI, bootstrap by customer) | p95 latency |
# |---|---|---|
# | Logistic regression | 0.61 (0.55 to 0.67) | 3 ms |
# | Boosted trees | 0.64 (0.57 to 0.70) | 45 ms |
#
# Write `JUDGEMENT`, a short Markdown memo (80-400 words) with three headings: **Recommendation**, **Evidence** and
# **Risks** (at least one risk as a bullet). Name both models, use the intervals, and weigh the latency. The grader
# checks the structure; compare your reasoning with the reference solution afterwards.

# %%
### BEGIN SOLUTION
JUDGEMENT = """
## Recommendation

Ship the logistic regression now, and keep the boosted trees as a candidate to re-test when more labelled data is
available.

## Evidence

- The boosted trees score higher (PR-AUC 0.64 against 0.61), but the two 95% intervals overlap almost entirely
  (0.57 to 0.70 and 0.55 to 0.67), so this test set cannot tell the models apart.
- The logistic regression answers in 3 ms at the 95th percentile; the boosted trees take 45 ms, close to the 50 ms
  budget, leaving little room for load spikes or slower inputs.
- The simpler model is easier to explain to the retention team and cheaper to monitor and retrain.

## Risks

- If the boosted trees really are better, we leave a small gain unused; a paired comparison on a larger or later
  test period would settle it.
- Both models were compared on one test period; performance may change as customer behaviour drifts, so monitor
  input drift and precision once labels arrive.
"""
### STARTER
JUDGEMENT = """YOUR MEMO HERE"""
### END SOLUTION

# %%
grade("w12.final_judgement", JUDGEMENT)

# %%
print(f"Time spent: about {(pd.Timestamp.now() - started).total_seconds() / 60:.0f} minutes")

# %% [markdown]
# ## Quiz
#
# **Q1.** Two models' 95% intervals overlap heavily, and the more complex one has the higher point estimate. What
# is the sound conclusion?
#
# - a) The complex model is better; ship it.
# - b) The data cannot tell them apart; prefer the simpler, cheaper one unless something else decides.
# - c) Re-run the evaluation with different seeds until one wins clearly.
# - d) Evaluate both again on the test set after tuning.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w12.48_q1", answer)

# %% [markdown]
# **Q2.** A drift alarm fires on one input feature. What do you do first?
#
# - a) Retrain immediately on the latest data.
# - b) Conclude the model has degraded and roll back.
# - c) Silence the alarm; models are robust.
# - d) Investigate the cause (a real change, or a sensor or pipeline fault?) and check performance when labels arrive.

# %%
### BEGIN SOLUTION
answer = "d"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w12.48_q2", answer)

# %% [markdown]
# **Q3.** What makes a unit test valuable?
#
# - a) It fails on the bug it was written to catch, and passes on correct code.
# - b) It increases line coverage.
# - c) It runs in under a millisecond.
# - d) It checks the model's accuracy.

# %%
### BEGIN SOLUTION
answer = "a"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w12.48_q3", answer)

# %% [markdown]
# **Q4.** A request arrives with `segment: "enterprise"`. What should the API return?
#
# - a) 200 with a prediction for the closest segment.
# - b) 200, after silently replacing the value with "consumer".
# - c) 422, saying which field is invalid and what is allowed.
# - d) 500.

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w12.48_q4", answer)

# %% [markdown]
# ## Self-assessment
#
# Graders check one clean task each. Use this table to judge yourself across the whole course. For each row, pick
# the level that is honestly true **today**, and write it in your notes (or in the cell below):
#
# - **1, seen it**: I recognise it and can follow a worked example.
# - **2, guided**: I can do it with the notebook or guide open next to me.
# - **3, independent**: I can do it on a new problem, without looking it up, and explain why.
#
# | Area | Can I ... | Course |
# |---|---|---|
# | Workbench | use the terminal, Git branches and commits, and a virtual environment on my own computer? | 01-03, 37 |
# | SQL | answer a business question with joins, GROUP BY, CTEs and window functions, and check the grain? | 05-09 |
# | pandas and data quality | load, clean and validate a messy file, and report its quality? | 10-12 |
# | Features and pipelines | build features as of a date and a scikit-learn pipeline without leakage? | 13-16 |
# | Framing and metrics | turn a business goal into a target, a baseline, a metric and a threshold from costs? | 17-20 |
# | Validation | choose grouped or time-based splits, spot leakage, and tune without touching the test set? | 21-24 |
# | Models and uncertainty | compare models with intervals, and analyse errors by segment? | 25-28 |
# | Code quality | package code, write pytest tests that catch bugs, configure and log a run? | 29-32 |
# | Serving | save a model safely, build and test a FastAPI service with input validation? | 33-36 |
# | Containers and CI | write a Dockerfile and a GitHub Actions workflow that runs the tests? | 38-40 |
# | Operations | plan a deployment with costs and secrets handled, monitor it, tell drift from degradation? | 41-44 |
# | Communication | write a README, a report and a model card whose claims match the evidence? | 45-47 |
#
# Pick the two areas with the lowest level and plan one small project or exercise for each in the next month. The
# advanced track (`advanced/notebooks/`) goes deeper on all of them.

# %%
my_levels = {
    # "SQL": 3,
    # "Validation": 2,
}

# %% [markdown]
# ## What to show in your portfolio
#
# - The capstone repository: README, technical report and model card (notebook 46), the code and tests, and the
#   container and CI workflow (Week 10).
# - One or two notebooks that show your reasoning, for example the leak hunt (24) or the error analysis (27).
# - Not the graded exercises themselves: they show you followed a course, not what you can build.
#
# ## Going further
#
# - Revisit the notebooks listed next to any exercise you found hard, then redo the exercise without hints.
# - The advanced track's final assessment (`advanced/notebooks/48_final_assessment.ipynb`) is longer and less
#   guided.
# - Keep building: a second small project in a different domain (a public tabular dataset, a time series) is the best
#   test of whether these skills transfer.

# %%
# Record your progress (optional; stored in progress/progress.json):
from mlcourse.progress import mark
# mark("48", "reading")
# mark("48", "guided")
