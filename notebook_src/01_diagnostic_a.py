# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/01_diagnostic_a.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 01 · Diagnostic A: Python, SQL, data cleaning
#
# **Week 1 · day 1 · about 2 h, time-boxed, unassisted** · your files: [`diagnostic/`](../diagnostic/)
#
# **Objective.** Produce time-boxed, unassisted evidence of current skill in Python refactoring/debugging, SQL joins and aggregation, and pandas data cleaning.

# %%
# --- Setup: works on your laptop AND in Google Colab ----------------------------
# In Colab this clones the course repository and installs the requirements (about a
# minute, first run only). On your own machine it just finds the repository. Every
# command in this notebook runs from the repository root. Safe to re-run.
import os
import subprocess
import sys
from pathlib import Path

if "google.colab" in sys.modules:
    if not Path("/content/mlengineering").exists():
        subprocess.run(["git", "clone", "--depth", "1",
                        "https://github.com/berdakh/mlengineering.git",
                        "/content/mlengineering"], check=True)
    os.chdir("/content/mlengineering")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                    "-r", "requirements.txt"], check=True)

REPO_ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents]
                 if (p / "src" / "mlcourse").is_dir())
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT / "src"))
print("repo root:", REPO_ROOT)

# %% [markdown]
# Purpose: find out what you can already do **independently**, so the first weeks spend time where it
# is needed and skip what you have demonstrated. It is not an exam and produces no score - only a
# per-skill evidence level (see `solutions/diagnostic/SCORING.md` *after* you finish).
#
# Nothing about your results is known until you submit. The roadmap is adapted only after your actual
# submissions are reviewed.

# %% [markdown]
# ## Structure: two sessions, about two hours each
#
# | Session | Section | Probes | Time box |
# |---|---|---|---|
# | A (W1D1) | [a1_python](../diagnostic/a1_python/README.md) | debugging, refactoring, Python semantics | 40 min |
# | A | [a2_sql](../diagnostic/a2_sql/README.md) | joins, aggregation, NULLs, fan-out, window functions | 35 min |
# | A | [a3_cleaning](../diagnostic/a3_cleaning/README.md) | pandas data cleaning, date/time-zone handling, judgment | 35 min |
# | B (W1D2) | [b1_baseline](../diagnostic/b1_baseline/README.md) | problem framing, baselines, metrics under imbalance | 35 min |
# | B | [b2_leakage](../diagnostic/b2_leakage/README.md) | leakage, validation design | 35 min |
# | B | [b3_testing_api](../diagnostic/b3_testing_api/README.md) | writing tests, request validation, API concepts | 25 min |
# | B | [b4_explain](../diagnostic/b4_explain/README.md) | explaining and defending an ML decision | 20 min |
#
# Session A totals 110 minutes, session B 115. Use the remaining minutes of each session to fill in
# [`SUBMISSION.md`](../diagnostic/SUBMISSION.md).
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-01-01.svg" alt="Diagram 1 of notebook 01" style="max-width:100%">
#
# *The path through the diagnostic. Nothing is adapted until the submission has been reviewed.*

# %% [markdown]
# ## Rules (they make the result useful to you)
#
# 1. **Time-box each section.** When the time is up, stop, note where you were, move on. An unfinished
#    section is information; an untimed finished one is not.
# 2. **No AI assistants, no searching for the answer.** Official documentation of Python, SQLite,
#    pandas, scikit-learn, pytest and pydantic is allowed - looking up an API is normal work.
#    If you do use other help, record it in `SUBMISSION.md`; that section then counts as guided.
# 3. **Do not open `solutions/`** (or `b3_testing_api/checks/impls/`) until you have submitted.
# 4. You may run the checks as often as you like - they are your feedback loop, as tests are at work.
# 5. Work in each section's `lab/` directory. Commit after each section if you use Git:
#    `git add -A && git commit -m "diagnostic a1"`.

# %% [markdown]
# ## Commands
#
# From the repository root:

# %%
!python wb.py check diagnostic/a1_python
!python -m pytest diagnostic/a1_python/checks -q

# %% [markdown]
# The starter code **fails** its checks in every section. That is the intended starting state.
# Passing checks shows that the objectively checkable behaviour is right; the written parts and the
# quality of the code are reviewed by reading your submission.
#
# Requirements: Python >= 3.11 with numpy, pandas, scikit-learn, pytest and pydantic >= 2 (see the
# repository `README.md` for environment setup).

# %% [markdown]
# ## Data
#
# All sections use one synthetic dataset, documented in [`data/README.md`](../diagnostic/data/README.md). It is not
# real; see that file for what cannot be concluded from it.

# %% [markdown]
# ## After you finish
#
# Fill in `SUBMISSION.md`, commit, and send back what it lists. Then (and only then) read
# `solutions/diagnostic/` to compare. Feedback and any change to the roadmap follow from the submission.

# %% [markdown]
# ## a1 - Python: debug and refactor
#
# **Time box: 40 minutes.** Session A, section 1 of 3. No hints; standard-library docs are fine.

# %% [markdown]
# ## Situation
#
# You inherit `lab/usage_report.py`, a small module that turns raw viewing-event lines into a usage
# report. It "works on the sample file". It also has several defects, and `build_report` is hard to change.

# %% [markdown]
# ## Task
#
# 1. **Debug.** Make every function satisfy the specification below. Do not change function names or
#    the meaning of their arguments (you may add type hints, helpers, classes).
# 2. **Refactor.** Leave the module in a state you would be content to have reviewed: no duplicated
#    logic in `build_report`, clear names, errors handled deliberately rather than swallowed.
# 3. **Write down** what you found in `lab/NOTES.md` (one line per bug; 3-6 lines on the refactor).

# %% [markdown]
# ## Specification
#
# An event line is `customer_id,ISO-8601 timestamp,minutes`, e.g. `C00017,2025-03-02T21:15:00,42.5`.
#
# * `parse_line(line)` returns `(customer_id, datetime, minutes)` (a tuple or anything that unpacks like
#   one). `minutes` may be fractional. Returns `None` for malformed lines: wrong number of fields,
#   unparseable timestamp or number, negative minutes.
# * `load_events(lines)` parses an iterable of lines, skipping malformed lines and exact duplicate lines
#   *within that call*. Two calls with the same lines return the same result.
# * `sessionize(events, gap_minutes=30)` returns `{customer_id: [session, ...]}` with sessions in
#   chronological order. A session is a dict with `start`, `end` (datetimes of first/last event),
#   `minutes` (sum) and `n_events`. A new session starts when the gap since the customer's previous
#   event is **strictly greater** than `gap_minutes`. Events may arrive in any order. The input is not modified.
# * `rolling_mean(values, window)` returns a list as long as `values`; element *i* is the mean of the
#   last `window` values up to **and including** *i* (fewer at the start, where fewer exist).
# * `top_customers(totals, k=3)` returns up to `k` `(customer_id, total)` pairs, largest total first,
#   ties broken by `customer_id` ascending.
# * `build_report(lines, gap_minutes=30, k=3)` returns a dict with keys `n_events`, `n_customers`,
#   `total_minutes`, `n_sessions`, `longest_session_minutes` (each a dict by customer) and `top_customers`.

# %% [markdown]
# ## Check your work

# %%
!python wb.py check diagnostic/a1_python
!python -m pytest diagnostic/a1_python/checks -q

# %% [markdown]
# The shipped starter fails several checks; that is expected.

# %% [markdown]
# ## Acceptance criteria
#
# * All checks pass (behaviour).
# * `NOTES.md` names each defect and its cause - not just "fixed test X".
# * The refactor is judged by reading your code (see `SUBMISSION.md`); checks cannot grade it.

# %% [markdown]
# ## Submit
#
# `lab/usage_report.py`, `lab/NOTES.md`, and the time you actually used.

# %%
# Run the automated checks on your guided lab.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("diagnostic/a1_python")

# %% [markdown]
# ## a2 - SQL: joins, aggregation, window functions
#
# **Time box: 35 minutes.** Session A, section 2 of 3. No hints; SQLite documentation is fine.
#
# Database: `diagnostic/data/streambox.db` (SQLite, **synthetic**). Schema and column meanings are in
# [`../data/README.md`](../diagnostic/data/README.md). Dates are ISO-8601 text (`YYYY-MM-DD`), so string comparison
# orders them correctly.
#
# Write **one `SELECT` statement per file** (CTEs are fine) in `lab/q1.sql` ... `lab/q5.sql`. Return the
# columns in the order given. Column names and row order are not checked; amounts are compared to 2 decimals.
#
# | File | Question | Columns |
# |---|---|---|
# | `q1.sql` | For invoices dated in 2025 with status `paid`: per customer country, how many distinct customers paid and how much revenue. Customers with no recorded country are reported as `UNKNOWN`. | country, n_paying_customers, revenue |
# | `q2.sql` | Customers who signed up in 2025 and have never opened a support ticket. | customer_id |
# | `q3.sql` | For every customer on the `premium` plan: total amount of their `paid` invoices (all time) and number of support tickets (all time). Customers with none of either appear with 0. | customer_id, total_paid, n_tickets |
# | `q4.sql` | Customers whose **most recent** invoice has status `failed`. Most recent = latest `invoice_date`; if several share that date, the one with the highest `invoice_id`. | customer_id, invoice_id, invoice_date |
# | `q5.sql` | Monthly `paid` revenue for 2025 and the change versus the previous month (NULL for the first month). | month (`YYYY-MM`), revenue, change_vs_prev |
#
# Before trusting a query, look at the data: at least two of these questions have an obvious query that
# runs without error and returns a wrong answer.

# %% [markdown]
# ## Work and check
#
# ```bash
# python diagnostic/a2_sql/lab/explore.py                      # list tables
# python diagnostic/a2_sql/lab/explore.py "SELECT * FROM tickets LIMIT 5"
# python diagnostic/a2_sql/lab/explore.py q3.sql               # run your file, print first rows
#
# python wb.py check diagnostic/a2_sql                         # or:
# python -m pytest diagnostic/a2_sql/checks -q
# ```
#
# The starter files fail all checks; that is expected.

# %% [markdown]
# ## Acceptance criteria
#
# * Each query returns exactly the expected set of rows.
# * You can say, for each query, what a wrong-but-plausible version would have returned and why
#   (one line each in `SUBMISSION.md`).

# %% [markdown]
# ## Submit
#
# The five `.sql` files and time used.

# %%
# Run the automated checks on your guided lab.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("diagnostic/a2_sql")

# %% [markdown]
# ## a3 - Data cleaning with pandas
#
# **Time box: 35 minutes.** Session A, section 3 of 3. No hints; pandas documentation is fine.

# %% [markdown]
# ## Situation
#
# `diagnostic/data/signups_dirty.csv` (**synthetic**) is a CRM export of customer signups. It was
# assembled from several regional systems and has not been cleaned. Raw columns (all read as text):
#
# | Column | Meaning as documented by the source team |
# |---|---|
# | `customer_id` | Customer key. The export may contain several rows per customer. |
# | `signup_date` | Signup date. Regional systems export it as an ISO date, as `DD/MM/YYYY`, or as a local timestamp with UTC offset. The business definition of the signup date is the **UTC calendar date**. |
# | `country` | ISO 3166-1 alpha-2 code, entered by hand. |
# | `plan` | One of `basic`, `standard`, `premium`. |
# | `monthly_price` | Monthly price. See `price_unit`. |
# | `price_unit` | `usd` or `cents`. |
# | `age` | Age in years. Legacy systems used sentinel codes for "not provided". |
# | `updated_at` | When this row was last written (`YYYY-MM-DD HH:MM:SS`, UTC). |

# %% [markdown]
# ## Task
#
# Implement `clean(raw)` in `lab/clean.py`. Look at the data first; the list above does not tell you
# everything that is wrong. Output contract:
#
# * Exactly these columns: `customer_id, signup_date, country, plan, monthly_price_usd, age`.
# * One row per `customer_id`; when a customer has several rows, the most recently updated one is kept.
# * `signup_date`: timezone-naive datetime at midnight, the UTC calendar date.
# * `country`: upper-case two-letter code, or missing.
# * `plan`: `basic` / `standard` / `premium`, or missing for anything else.
# * `monthly_price_usd`: numeric, US dollars.
# * `age`: numeric; "not provided" codes and values outside 13-110 are missing.
# * Missing means a real missing value (`None`/`NaN`/`NaT`/`pd.NA`), never a placeholder string or number.
# * `raw` is not modified.
#
# Then fill in `lab/NOTES.md`: each defect, how many rows, how you detected it, what you decided.

# %% [markdown]
# ## Check your work

# %%
!python diagnostic/a3_cleaning/lab/clean.py
!python wb.py check diagnostic/a3_cleaning
!python -m pytest diagnostic/a3_cleaning/checks -q

# %% [markdown]
# The starter raises `NotImplementedError`, so every check fails until you implement `clean`.

# %% [markdown]
# ## Acceptance criteria
#
# * All checks pass, including the comparison of the full file with the generator's ground truth.
# * `NOTES.md` shows the defects were *found by inspection* (counts, examples), not inferred from test names.

# %% [markdown]
# ## Submit
#
# `lab/clean.py`, `lab/NOTES.md`, time used.

# %%
# Run the automated checks on your guided lab.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("diagnostic/a3_cleaning")

