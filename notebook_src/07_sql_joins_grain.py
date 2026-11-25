# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/07_sql_joins_grain.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 07 · SQL I: grain, joins, aggregation and NULL semantics
#
# **Week 2 · day 1 · 2 h essential path + up to 1 h optional** · lab files: [`labs/w2d1_sql_joins_grain/`](../labs/w2d1_sql_joins_grain/)
#
# **Objective.** Write correct multi-table queries by reasoning about table grain first; recognise fan-out, NULL and anti-join traps.

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
    if not Path("/content/mlengineering-").exists():
        subprocess.run(["git", "clone", "--depth", "1",
                        "https://github.com/berdakh/mlengineering-.git",
                        "/content/mlengineering-"], check=True)
    os.chdir("/content/mlengineering-")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                    "-r", "requirements.txt"], check=True)

REPO_ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents]
                 if (p / "src" / "mlcourse").is_dir())
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT / "src"))
print("repo root:", REPO_ROOT)

# %% [markdown]
# **Unit id:** `w2d1` · **Week 2, day 1** · **Content status:** Execution verified (see Verification record)
# **Handbook:** [H3.1 Grain, joins, aggregation and NULLs](../docs/handbook/ch03_sql_data_pipelines/h3_1_grain_joins_aggregation_nulls.md)
# **Data:** `data/maintenance.db` — SYNTHETIC ([schema](../labs/w2d1_sql_joins_grain/data/README.md)). Totals in this lesson are properties of a generator; they say nothing about real maintenance operations.
#
# ---

# %% [markdown]
# ## 1. Purpose
#
# **Primary objective.** Write multi-table queries that are *correct by construction*: decide the
# grain of the result first, bring every input to that grain before joining, and prove the result with
# invariants instead of by looking at it.
#
# **What you will learn**
#
# - Stating the grain (what one row means) and key of every table and of every intermediate result.
# - Predicting the row count of a join from the cardinality of the relationship.
# - Recognising fan-out (double counting) and fixing it by pre-aggregating to the join grain.
# - SQL's three-valued logic: what NULL does to comparisons, `WHERE`, aggregates, `NOT IN`, `COUNT`.
# - Where a filter belongs with a `LEFT JOIN` (`ON` versus `WHERE`), and `WHERE` versus `HAVING`.
# - Verifying a query with row-count and reconciliation checks.
#
# **Why an applied ML engineer needs it.** Training tables in industry are assembled by joins, usually
# by you. A fan-out join does not raise an error; it duplicates rows, inflates sums, duplicates labels
# and puts copies of one entity on both sides of a split. A filter in the wrong clause silently removes
# exactly the entities with no activity, which are often the negative class. These bugs survive code
# review because the query runs and the numbers look plausible. SQL rounds in interviews for ML roles
# are mostly this: joins, aggregation, NULLs, and whether you check your own result.
#
# **Prerequisites.** Diagnostic `a2_sql` attempted (its review tells you how much of section 2 to skim).
# `SELECT … FROM … WHERE … GROUP BY` is assumed. Nothing from Week 1 is required except a working
# environment; SQLite ships with Python.
#
# **Time budget — essential path 2 h**
#
# | Activity | Time |
# |---|---|
# | Read sections 1–2 (2.2, 2.3 and 2.5 are the core) | 25 min |
# | Worked example: run it, predict each output before reading it | 15 min |
# | Guided lab, tasks 1–8 | 60 min |
# | Assessment questions (written) | 15 min |
# | Reflection and progress flags | 5 min |
#
# **Optional extension — up to 1 h:** independent challenge (40 min), interview rep (15 min), DuckDB
# comparison (5 min). The `independent` flag for this unit stays unset until the challenge is done
# without hints.
#
# ---

# %% [markdown]
# ## 2. Conceptual explanation
#
# ### 2.1 Intuition: you already do this, with different names
#
# In your EEG work the same recording exists at several resolutions: one row per **sample**, per
# **window**, per **channel × window**, per **recording**, per **subject**. You would never average
# subject age over windows and call it the cohort's mean age, because subjects with longer recordings
# would count more. You would also never let windows from one subject fall on both sides of a split.
# Both instincts are statements about *grain*: what one row represents, and what the independent unit is.
#
# SQL bugs in industry are the same mistake made with a join. A per-recording metadata table joined to
# a per-channel table yields one row per channel; any per-recording quantity (duration, age, label) is
# now repeated once per channel, and `SUM` or `AVG` over it is wrong. Nothing warns you. The discipline
# of this lesson is to make the grain explicit before writing the `SELECT`.
#
# ### 2.2 Precise terms
#
# - **Grain** of a table or result: the real-world thing one row stands for ("one work order",
#   "one part line of a work order").
# - **Key**: a set of columns whose values are unique per row. A *minimal* key has no removable column.
#   The grain and the minimal key are two descriptions of the same fact. `parts_used` has grain "part
#   line" and key `(wo_id, part_id)`.
# - **Measure**: a numeric column you aggregate. Every measure is *defined at a grain*:
#   `labor_hours` at the work-order grain, `quantity` at the part-line grain. **A measure may only be
#   summed over rows that are at its own grain** (or after being deliberately allocated to a finer one).
# - **Cardinality** of a relationship: one-to-one, one-to-many, many-to-many. It determines what a
#   join does to the row count.
#
# **The lesson database at a glance** (SYNTHETIC; full schema in [`data/README.md`](../labs/w2d1_sql_joins_grain/data/README.md)).
# Read each line as "one parent row has zero or more child rows"; the grain of a table is its primary key.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/docs/assets/diagrams/mmd-07-01.svg" alt="Diagram 1 of notebook 07" style="max-width:100%">
#
# `machines` has two independent children (`work_orders`, `downtime_events`), and `work_orders` has a
# child of its own (`parts_used`). Those two shapes are where every fan-out in this lesson comes from.
#
#
# ### 2.3 Joins as row-set operations, and the row-count rule
#
# A join of `A` and `B` on a predicate produces one output row for every *pair* `(a, b)` that satisfies
# the predicate. Everything else follows from that.
#
# | Join | Rows produced |
# |---|---|
# | `A INNER JOIN B` | matching pairs only |
# | `A LEFT JOIN B` | matching pairs, plus each unmatched `a` once with NULLs for `B`'s columns |
# | `A FULL OUTER JOIN B` | matching pairs, plus unmatched rows of both sides |
# | `A CROSS JOIN B` | all `|A|·|B|` pairs |
#
# Let `m(a)` be the number of rows of `B` that match row `a`. Then
#
# ```
# |A INNER JOIN B| = Σ_a m(a)              |A LEFT JOIN B| = Σ_a max(m(a), 1)
# ```
#
# So joining *towards the "one" side* (work order → its machine, `m(a) = 1`) preserves the row count
# and the grain of `A`. Joining *towards the "many" side* (work order → its part lines) changes the
# grain to that of the child. This is not a problem in itself. It becomes a bug in two situations:
#
# 1. **A measure from the parent is aggregated after the join.** Each work order's `labor_hours`
#    appears `m(a)` times.
# 2. **Two independent children are joined to the same parent.** A machine with `a` work orders and
#    `b` downtime events yields `a·b` rows, so labour is multiplied by `b` and downtime by `a`:
#
#    ```
#    Σ_rows labor = b · (true labor)        Σ_rows downtime = a · (true downtime)
#    ```
#
#    On the lesson database machine 1 has 4 work orders (18.4 h) and 5 downtime events (63.5 h); the
#    naive join reports 92.0 h and 254.0 h. Over all machines it reports 1,218.1 labour hours against
#    a true 633.8.
#
# **The fix is always the same: aggregate each child to the grain you are joining at, then join.**
# After pre-aggregation every join is one-to-(zero or one), `m(a) ≤ 1`, and the row count cannot grow.
#
# ```sql
# WITH wo AS (SELECT machine_id, SUM(labor_hours) AS labor_hours FROM work_orders GROUP BY machine_id),
#      dt AS (SELECT machine_id, SUM(hours) AS downtime_hours FROM downtime_events GROUP BY machine_id)
# SELECT m.machine_id, COALESCE(wo.labor_hours, 0), COALESCE(dt.downtime_hours, 0)
# FROM machines m LEFT JOIN wo USING (machine_id) LEFT JOIN dt USING (machine_id);
# ```
#
# `COUNT(DISTINCT …)` and `SELECT DISTINCT` are not fixes. They repair counts of identifiers and leave
# sums wrong, and `SUM(DISTINCT labor_hours)` is wrong in a new way (two orders of 4.0 h count once).
#
# What the naive join does to one machine with 2 work orders and 3 downtime events:
#
# ```text
# work_orders (machine 7)        downtime_events (machine 7)        machines ⋈ work_orders ⋈ downtime_events
#  wo_id  labor_hours             event_id  hours                    wo_id  labor  event_id  hours
#   101       4.0                    901     2.0                      101    4.0     901      2.0
#   102       6.0                    902     5.0                      101    4.0     902      5.0
#         ─────────                  903     1.0                      101    4.0     903      1.0
#  true labour 10.0                      ─────────                    102    6.0     901      2.0
#                                 true downtime 8.0                   102    6.0     902      5.0
#                                                                     102    6.0     903      1.0
#                                                                    ───────────────────────────────
#                                                     2 x 3 = 6 rows:  SUM(labor) 30.0   SUM(hours) 16.0
#                                                                      = 3 x 10.0        = 2 x 8.0
# ```
#
# (The six-row block is illustrative, not rows of the lesson database.) On the lesson database the same
# mechanism produces these totals:
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/labs/w2d1_sql_joins_grain/figures/fanout_totals.svg" alt="Bar chart: true labour hours 633.8 against 1,218.1 from the naive join; true downtime hours 793.5 against 2,523.8" width="100%">
#
# *Both sums are inflated, by different factors, because each child is multiplied by the row count of the
# other. SYNTHETIC data; regenerate with `python labs/w2d1_sql_joins_grain/figures/make_figures.py`.*
#
#
# ### 2.4 NULL and three-valued logic
#
# NULL means "no value here", and SQL does not know *why*. Predicates evaluate to TRUE, FALSE or
# UNKNOWN (which SQLite displays as NULL):
#
# | Expression | Result |
# |---|---|
# | `NULL = NULL`, `NULL <> 1`, `NOT NULL` | UNKNOWN |
# | `NULL AND FALSE` | FALSE |
# | `NULL OR TRUE` | TRUE |
# | `NULL AND TRUE`, `NULL OR FALSE` | UNKNOWN |
# | `NULL IS NULL` | TRUE |
#
# Consequences, all executed in the worked example:
#
# - **`WHERE`, `HAVING` and join `ON` keep a row only when the predicate is TRUE.** UNKNOWN is dropped
#   like FALSE. `WHERE criticality <> 'high'` does not return the machines whose criticality was never
#   assessed: on the lesson database 7 machines are `high`, 12 are returned by `<> 'high'`, and 13 are
#   NULL and appear in neither.
# - **Aggregates skip NULL.** `COUNT(*)` counts rows; `COUNT(col)` counts non-NULL values; `SUM` and
#   `AVG` ignore NULLs, so `AVG(labor_hours)` is the mean over orders *with recorded hours*, a different
#   estimand from "mean hours per order". Over zero rows `COUNT` is 0 while `SUM` and `AVG` are NULL,
#   which is why outer-joined sums need `COALESCE(…, 0)`.
# - **`x NOT IN (subquery)` returns no rows if the subquery yields any NULL.** `x NOT IN (1, NULL)` is
#   `x <> 1 AND x <> NULL`, which is never TRUE. Use `NOT EXISTS` (or `LEFT JOIN … WHERE b.key IS NULL`).
# - **`GROUP BY` treats NULLs as one group**, and `DISTINCT` treats them as equal, unlike `=`.
#
# Decide what each NULL *means* before choosing how to treat it. "Labour not recorded" must not be
# turned into 0 inside an average; "no work orders" should become 0 in a count.
#
# ### 2.5 Filters and outer joins: `ON` versus `WHERE`
#
# Logical evaluation order: `FROM`/`JOIN … ON` → `WHERE` → `GROUP BY` → `HAVING` → `SELECT` →
# `ORDER BY`. For an inner join a condition gives the same result in `ON` or `WHERE`. For a `LEFT JOIN`
# it does not:
#
# - a condition on the **right** table in `ON` restricts which right rows may match; unmatched left
#   rows are still kept, NULL-extended;
# - the same condition in `WHERE` is evaluated after the join; on NULL-extended rows it is UNKNOWN,
#   they are dropped, and the outer join has become an inner join.
#
# "All sites with their number of corrective orders in 2025, including zero" therefore needs the type
# and date conditions in `ON`. `WHERE` filters rows before grouping; `HAVING` filters groups after
# aggregation and is the only place an aggregate may appear as a filter.
#
# A subtler version of the same trap: on a NULL-extended row *every* right-hand column is NULL, so
# `CASE WHEN m.decommissioned_date IS NULL THEN 1 END` counts a phantom "active machine" for a site
# that has no machines at all.
#
# Where a condition on the outer-joined table goes decides which rows survive:
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/docs/assets/diagrams/mmd-07-02.svg" alt="Diagram 2 of notebook 07" style="max-width:100%">
#
#
# ### 2.6 Verifying a query
#
# Treat a query like code under test (W1D5). Useful oracles:
#
# - **Key uniqueness.** `SELECT key, COUNT(*) FROM result GROUP BY key HAVING COUNT(*) > 1` returns
#   nothing. Do this for inputs as well: an assumed one-to-one relationship that is really one-to-many
#   is the commonest root cause.
# - **Row-count invariants.** "One row per site" means exactly `SELECT COUNT(*) FROM sites` rows. Count
#   rows after each join while building the query.
# - **Reconciliation totals.** The grand total of a measure in the result equals the total computed
#   from the single table at whose grain the measure is defined. This catches fan-out *and* dropped rows.
# - **Known small cases.** Check one entity by hand, preferably one with zero children and one with many.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/docs/assets/diagrams/mmd-07-03.svg" alt="Diagram 3 of notebook 07" style="max-width:100%">
#
#
# ### 2.7 A concrete industry example
#
# A subscription company's dashboard showed monthly revenue 18 % above the finance ledger. The query
# joined `orders` to `order_items` (to show product categories) and to `shipments` (to show delivery
# status), then summed `orders.total`. Orders with two items and two shipments were counted four times.
# Marketing dashboards built on the same view had been used to set acquisition budgets. The fix was
# three CTEs at the order grain and a reconciliation test against the ledger total in CI. The ML
# variant is identical: a churn training table built by joining customers to tickets and to payments
# duplicates customers in proportion to their activity, so heavy users are over-weighted and a random
# row split leaks customers across train and test.
#
# ### 2.8 Limits and common misconceptions
#
# - *"The query ran and the numbers look reasonable."* Fan-out errors are often modest (here +32 % in
#   total) and can coexist with dropped rows that pull the other way; site 2 in the lab is *under*-reported
#   by the same query that over-reports the total.
# - *"`DISTINCT` fixes duplicates."* It hides the symptom for identifiers and leaves measures wrong.
# - *"`LEFT JOIN` guarantees all left rows."* Only until a `WHERE` condition touches the right table.
# - *"NULL is like 0 / empty string / False."* It is none of these; `NULL = NULL` is not TRUE.
# - *"`COUNT(*)` and `COUNT(col)` are interchangeable."* Only when `col` is never NULL, which an outer
#   join can change.
# - **Engine differences.** SQLite is permissive: it accepts a selected column that is neither grouped
#   nor aggregated and returns the value from an arbitrary row of the group; PostgreSQL, DuckDB and
#   BigQuery reject that. SQLite also has dynamic typing and no date type. The reasoning in this lesson
#   is standard SQL; the leniency is not.
# - **What this lesson does not cover:** window functions, as-of joins and gaps-and-islands (W2D2),
#   query performance and indexing, and transactions.
#
# ---

# %% [markdown]
# ## 3. Worked example: recordings, channels, annotations
#
# **Data.** A toy in-memory database in a shape you know (SYNTHETIC, created inside the script):
#
# | Table | Grain | Columns |
# |---|---|---|
# | `recordings` (4 rows) | recording | `recording_id`, `subject_id`, `duration_s` |
# | `channels` (9 rows) | (recording, channel) | `recording_id`, `channel`, `is_bad` (NULL = not reviewed) |
# | `annotations` (5 rows) | annotated event | `annotation_id`, `recording_id`, `kind`, `duration_s` |
#
# Recording 2 has no annotations; recording 4 has neither channels nor annotations.
#
# **Run it** (reproducible: no randomness, no files):

# %%
!python labs/w2d1_sql_joins_grain/example/fanout_demo.py

# %% [markdown]
# **Predict before you read each block.** The script prints seven blocks; the important ones:
#
# ```
# -- truth, from the table whose grain matches the measure
#    total_recorded_s
#    2250.0
#
# -- WRONG: duration summed after joining channels (one row per channel)
#    total_recorded_s | rows_summed
#    6000.0 | 9
#
# -- WRONG: two one-to-many children joined to the same parent
#    recording_id | intermediate_rows | n_channels_reported | event_s_reported
#    1 | 6 | 6 | 135.0
#    2 | 2 | 2 | NULL
#    3 | 12 | 12 | 420.0
#    4 | 1 | 0 | NULL
#
# -- RIGHT: each child aggregated to the parent grain, then joined
#    recording_id | n_channels | event_s
#    1 | 3 | 45.0
#    2 | 2 | 0
#    3 | 4 | 105.0
#    4 | 0 | 0
# ```
#
# **Interpretation.** Recording 3 has 4 channels and 3 annotations, so the naive join has 12 rows;
# channels are reported as 12 (each counted 3 times) and event seconds as 420 = 4 × 105. Recording 2
# shows the other face of the problem: its channel count happens to be right (no annotations, so the
# LEFT JOIN added one NULL-extended row per channel) and its event time is NULL instead of 0. A
# spot-check on recording 2 would have passed. The row-count block makes the mechanism visible:
#
# ```
# -- how many rows after each step?
#    recordings | after_inner_channels | after_left_channels | after_both
#    4 | 9 | 10 | 21
# ```
#
# 4 → 10 → 21: each step that increases the count is a change of grain that you must be able to name.
#
# **Code decisions worth noticing.** Each child is reduced in its own CTE whose `GROUP BY` column is
# the join key, so the join is provably at most one row per parent. `COALESCE` is applied *after* the
# outer join, where "no children" has become NULL and should read as 0. The NULL block shows the
# difference between two estimands:
#
# ```
# -- aggregates: COUNT(*) counts rows, COUNT(col)/SUM/AVG skip NULL
#    n_rows | n_reviewed | n_bad | bad_rate_of_reviewed | bad_rate_of_all
#    9 | 7 | 1 | 0.14285714285714285 | 0.1111111111111111
# ```
#
# `AVG(is_bad)` is the bad-channel rate among *reviewed* channels (1/7). Dividing by `COUNT(*)` (1/9)
# silently assumes unreviewed channels are good. Neither is "the" answer; you must choose and say which.
#
# The anti-join block shows `NOT IN` returning no rows when the list contains a NULL, while
# `NOT EXISTS` and `LEFT JOIN … IS NULL` both return recordings 2 and 4. The last block shows SQLite
# accepting `SELECT subject_id, recording_id, SUM(…) … GROUP BY subject_id`; the `recording_id` it
# prints is one arbitrary member of each group.
#
# ---

# %% [markdown]
# ## 4. Guided lab
#
# **Result to produce:** seven correct queries in `lab/queries/`, each with its grain stated, and a
# short bug report on a broken dashboard query. You work in `labs/w2d1_sql_joins_grain/lab/`.
#
# Run a query file, or an ad-hoc statement, with the helper:

# %%
!python labs/w2d1_sql_joins_grain/lab/run.py labs/w2d1_sql_joins_grain/lab/queries/q1_machines_per_site.sql
!python labs/w2d1_sql_joins_grain/lab/run.py -c "SELECT COUNT(*) FROM work_orders"
!python wb.py check w2d1

# %% [markdown]
# Rules for every file: one `SELECT` statement (CTEs allowed); the column names given in the file's
# header; replace the `-- grain: TODO` line **before** writing the query. Column order is free; row
# order is free unless the header requires one. The checks run each query on `data/maintenance.db` and
# on a second database with different rows, so reason about the schema, not about the values you see.
#
# ### Task 1 — Orient: write down grains and prove the keys (8 min)
#
# Read [data/README.md](../labs/w2d1_sql_joins_grain/data/README.md). For `work_orders`, `parts_used` and `downtime_events` run a
# uniqueness check of the key you believe in, for example:
#
# ```sql
# SELECT wo_id, part_id, COUNT(*) FROM parts_used GROUP BY wo_id, part_id HAVING COUNT(*) > 1;
# ```
#
# *Checkpoint:* each returns no rows. Then answer for yourself: is `wo_id` alone a key of `parts_used`?
# (`SELECT COUNT(*), COUNT(DISTINCT wo_id) FROM parts_used` gives 121 and 57.)
#
# ### Task 2 — `q1_machines_per_site`: outer join and what `COUNT` counts (7 min)
#
# Every site, with its number of machines and of machines still in service.
# *Checkpoint:* 6 rows; `Fenwick Yard` shows 0 and 0; `Aldermoor` shows 9 and 7.
# *If Fenwick Yard shows 1:* you are counting rows, and the NULL-extended row is a row. *If it shows 0
# machines but 1 active:* reread the last paragraph of 2.5.
#
# ### Task 3 — `q2_unassigned_technicians`: anti-join (5 min)
#
# *Checkpoint:* 3 technicians. *If you get no rows at all:* your subquery returns a NULL (section 2.4).
# Run `SELECT COUNT(*), COUNT(tech_id) FROM work_orders` to see how many.
#
# ### Task 4 — `q3_machine_hours`: two children of one parent (12 min)
#
# All machines with number of work orders, labour hours and downtime hours.
# *Checkpoints:* 32 rows; machine 1 → 4 orders, 18.4 labour hours, 63.5 downtime hours; machine 2 has
# downtime 0. Then reconcile: the sum of your `labor_hours` column must equal
# `SELECT SUM(labor_hours) FROM work_orders` (633.8) and the downtime column must sum to 793.5.
# *If machine 1 shows 92.0 and 254.0:* that is 18.4 × 5 and 63.5 × 4. Apply 2.3.
#
# ### Task 5 — `q4_corrective_2025_per_site`: filter placement (8 min)
#
# *Checkpoint:* 6 rows, two of them with 0. *If you get 4 rows:* a condition on `work_orders` is in
# `WHERE`. Note that the dates are text; `opened_date >= '2025-01-01' AND opened_date < '2026-01-01'`
# is the robust form of "in 2025".
#
# ### Task 6 — `q5_type_summary`: conditional aggregation and NULL-aware averages (7 min)
#
# One row per `wo_type` with four different counts/averages from a single pass over `work_orders`.
# *Checkpoint:* `n_orders` sums to 93; `corrective` has 38 orders, 8 open, 8 unassigned.
# Decide deliberately what the average is over, and say so in a comment.
#
# ### Task 7 — `q6_expensive_orders`: `WHERE` versus `HAVING`, required order (5 min)
#
# *Checkpoint:* first row is work order 1 with 6 part lines and a parts cost of 4,064.36. Here joining
# to the part-line grain is correct, because cost is defined there. Say why in your grain comment.
#
# ### Task 8 — Diagnose `broken/dashboard_site_costs.sql` (15 min)
#
# Finance reports that the tile's labour hours are too high and that work orders seem to be missing.
#
# 1. Run the broken query. Compare its totals with totals taken from single tables.
# 2. Count rows along the join chain (after `work_orders`, after `parts_used`). Name each grain.
# 3. Find how many work orders the query drops, and which site is *under*-reported and why.
# 4. Write the corrected query in `queries/q7_site_costs_fixed.sql` (all sites; zeros where nothing).
# 5. Fill in `FANOUT_REPORT.md`: the three numbers at the top and four short sections.
#
# *Checkpoint:* your fixed query has 6 rows and passes all three reconciliations (work-order count,
# labour hours, parts cost). Parts cost is identical in the broken and fixed queries; be able to
# explain why that column was right all along.
#
# **Debugging guidance**
#
# | Symptom | Likely cause |
# |---|---|
# | `…sql must be a single SELECT` | a second statement, or text before `SELECT`/`WITH` |
# | `result columns … do not match` | alias missing or misspelled; names are compared case-insensitively |
# | passes on `committed`, fails on `reseeded` | a literal id or value from the data is in the query |
# | right row count, wrong sums | fan-out upstream of the `SUM` |
# | right sums for some rows, rows missing | inner join or `WHERE` on an outer-joined table |
# | `NULL` where 0 is expected | missing `COALESCE` after an outer join |
#
# When all checks pass: `python wb.py mark w2d1 guided`.
#
# ---

# %%
# Run the automated checks on your guided lab.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w2d1")

# %% [markdown]
# ## 5. Independent challenge
#
# [challenge/README.md](../labs/w2d1_sql_joins_grain/challenge/README.md): five unseen questions on the same schema. For each you
# declare the grain and the minimal key of the result; the checks verify the result on both databases
# and that your declared key is unique and minimal. No step-by-step guidance. Aim for 40 minutes
# without hints.

# %%
!python wb.py check w2d1 --challenge

# %% [markdown]
# ### The challenge brief
#
#
# **Conditions:** 40 minutes, no hints, no solutions, same database (`../data/maintenance.db`, SYNTHETIC).
# Record in `progress/notes.md` how long you took and whether you opened a hint; set the `independent`
# flag only if you did not.
#
# Write one query per file in `challenge/queries/`. Each file already states the question and the
# required column names. Before writing SQL, replace two header lines:
#
# ```sql
# -- grain: one row per <what a row of YOUR result represents, and which entities are included>
# -- key: <comma-separated column names forming the MINIMAL key of the result>
# ```
#
# | File | Question |
# |---|---|
# | `c1_site_type_costs.sql` | Per site and work-order type: number of work orders and their total parts cost |
# | `c2_machine_parts.sql` | For every machine: number of distinct parts ever used on it and total quantity |
# | `c3_technician_load.sql` | For every technician: orders assigned, recorded labour hours, distinct machines serviced |
# | `c4_site_scorecard.sql` | For every site: machines, downtime hours, labour hours, parts cost |
# | `c5_parts_never_corrective.sql` | Parts never used on a corrective work order |
#
# The exact wording, including which entities must appear with zeros, is in each file's header.
#
# #### Acceptance criteria
#
# 1. Each file contains a single `SELECT` (CTEs allowed) returning exactly the required columns.
# 2. Results are correct on the committed database **and** on a re-seeded database you have not seen.
# 3. The declared key is unique in the result on both databases and is minimal (no measures in it).
# 4. "Every …" means every row of that table appears, with 0 (not NULL) where there is nothing to count or sum.
# 5. For `c4`, you can state three reconciliation checks your result satisfies, and you have run them.

# %%
!python wb.py check w2d1 --challenge

# %% [markdown]
# #### Deliverable
#
# The five query files, plus three or four sentences in `progress/notes.md`: which question had a trap
# you did not see at first, and which invariant exposed it.
#
# #### Optional extension
#
# Run your queries on a second engine and look for differences (DuckDB is not a course dependency):
#
# ```bash
# python -m pip install duckdb
# python labs/w2d1_sql_joins_grain/example/run_on_duckdb.py labs/w2d1_sql_joins_grain/challenge/queries
# ```

# %%
# Run the automated checks on your independent challenge.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w2d1", challenge=True)

# %% [markdown]
# ## 6. Progressive hints
#
# Open only as far as you need, and record which level you used.
#
# 1. [Concept](../labs/w2d1_sql_joins_grain/hints/hint1_concept.md) — the question to ask of every join.
# 2. [Approach](../labs/w2d1_sql_joins_grain/hints/hint2_approach.md) — a query-building routine and which trap each question hides.
# 3. [Partial implementation](../labs/w2d1_sql_joins_grain/hints/hint3_partial.md) — CTE skeletons with the aggregations left out.
#
# The full reference queries are in `solutions/labs/w2d1_sql_joins_grain/` (open after attempting).
#
#
# Open one hint at a time, only after a real attempt.
#
# <details>
# <summary><b>Hint 1 concept</b></summary>
#
#
# Ask one question of every join before you write it:
#
# > **For one row on the left, how many rows on the right can match: at most one, or many?**
#
# If the answer is "many", the result is now at the child's grain. From that point on you may only
# aggregate measures that are defined at that grain. A measure that came from the parent, or from a
# *different* child, is repeated and must not be summed, counted or averaged there.
#
# Second question, for every condition that mentions a table reached through a `LEFT JOIN`:
#
# > **Should entities with no matching child still appear?** If yes, the condition cannot be in `WHERE`.
#
# Third, for every anti-join ("never", "without", "no …"):
#
# > **Can the column I compare against be NULL?** If yes, `NOT IN` will return nothing.
#
# For the challenge: the phrase "for every X" fixes the driving table (X) and the grain (one row per X).
# "Distinct parts ever used on a machine" is a statement about a set across several work orders, not
# about part lines.
#
# </details>
#
# <details>
# <summary><b>Hint 2 approach</b></summary>
#
#
# A routine that prevents most mistakes:
#
# 1. **Write the grain of the result** and its key. Count how many rows that implies
#    (`SELECT COUNT(*) FROM <driving table>`).
# 2. **List the measures and the grain at which each is defined.**
#    `labor_hours` → work order. `quantity`, cost → part line. `hours` → downtime event.
# 3. **One CTE per measure source**, each grouped to the result's grain (or to the grain of the join
#    key you will use). Join tables *upwards* (towards the "one" side) inside the CTE to obtain the
#    grouping column; that direction never duplicates rows.
# 4. **Start the final `SELECT` from the driving table and `LEFT JOIN` each CTE.** Each CTE has at most
#    one row per key, so the row count stays at the number from step 1.
# 5. **`COALESCE(…, 0)`** the measures that come from an outer-joined CTE.
# 6. **Verify:** row count equals step 1; grand totals equal single-table totals.
#
# Which trap each lab or challenge question hides:
#
# | Question | Trap |
# |---|---|
# | q1 | `COUNT(*)` and `IS NULL` tests on a NULL-extended row |
# | q2, c5 | `NOT IN` with NULLs; for c5 the "corrective" condition belongs *inside* the anti-join |
# | q3, c4 | several independent children under one parent |
# | q4 | condition on the outer-joined table placed in `WHERE` |
# | q5 | which rows the average is over; counting NULLs |
# | q6 | row filter versus group filter; here the child grain is the right one |
# | q7 | parent measure summed at child grain, plus rows lost to an inner join |
# | c1 | counting orders after joining part lines |
# | c2 | part lines versus distinct parts across a machine's orders |
# | c3 | "every technician", including those who never appear in `work_orders` |
#
# For the challenge key: a set of columns that is unique is not automatically the key you want.
# Remove columns while it stays unique; what remains should read like the grain sentence.
#
# </details>
#
# <details>
# <summary><b>Hint 3 partial</b></summary>
#
#
# Skeletons with the aggregations and conditions left out. They show shape, not answers.
#
# ##### Two children under one parent (q3; the pattern for c4)
#
# ```sql
# WITH wo AS (
#     SELECT machine_id, /* aggregates of work_orders */ 
#     FROM work_orders
#     GROUP BY machine_id
# ),
# dt AS (
#     SELECT machine_id, /* aggregate of downtime_events */
#     FROM downtime_events
#     GROUP BY machine_id
# )
# SELECT m.machine_id, /* COALESCE each measure */
# FROM machines AS m
# LEFT JOIN wo ON wo.machine_id = m.machine_id
# LEFT JOIN dt ON dt.machine_id = m.machine_id;
# ```
#
# For `c4` the result grain is the site, so each CTE must be grouped by `site_id`. A child table that has
# no `site_id` gets it by joining *up* to `machines` inside the CTE (many-to-one, no duplication).
# Parts cost needs two upward steps: part line → work order → machine.
#
# ##### Parent measure plus child measure (q7; the pattern for c1)
#
# ```sql
# WITH wo_parts AS (                       -- one row per work order that used parts
#     SELECT pu.wo_id, /* cost */ AS parts_cost
#     FROM parts_used AS pu JOIN parts AS p ON p.part_id = pu.part_id
#     GROUP BY pu.wo_id
# )
# SELECT /* grouping columns */, COUNT(w.wo_id), SUM(w.labor_hours), SUM(wp.parts_cost)
# FROM /* driving table and joins down to work_orders: which join type keeps every site? */
# LEFT JOIN wo_parts AS wp ON wp.wo_id = w.wo_id
# GROUP BY /* ... */;
# ```
#
# After the join to `wo_parts` each work order still appears once, so `COUNT` and `SUM(labor_hours)` are safe.
#
# ##### Filter that must not remove left rows (q4)
#
# ```sql
# FROM sites AS s
# LEFT JOIN machines AS m    ON m.site_id = s.site_id
# LEFT JOIN work_orders AS w ON w.machine_id = m.machine_id
#                           AND /* conditions on w go HERE */
# GROUP BY s.site_id
# ```
#
# Count a column of `w` that is never NULL in the base table, not `*`.
#
# ##### Anti-join with a condition (q2, c5)
#
# ```sql
# SELECT p.part_id, p.part_name
# FROM parts AS p
# WHERE NOT EXISTS (
#     SELECT 1
#     FROM parts_used AS pu
#     JOIN /* the table that knows the order type */ 
#     WHERE pu.part_id = p.part_id
#       AND /* the condition that defines a disqualifying use */
# );
# ```
#
# ##### Distinct across a path (c2)
#
# `COUNT(DISTINCT pu.part_id)` over the rows of one machine counts each part once however many orders
# used it; `SUM(pu.quantity)` over the same rows is safe because every part line appears exactly once on
# the path machine → work order → part line (a chain, not two sibling branches).
#
# </details>

# %% [markdown]
# ## 7. Assessment
#
# assessment.md (section 7 of this notebook): six reasoning questions, one design-choice explanation, a rubric, and
# a 15-minute SQL interview rep. Write answers before opening
# `solutions/labs/w2d1_sql_joins_grain/assessment_answers.md`. The automated checks cover the queries;
# the written questions cover whether you can explain *why*.
#
#
# ### Assessment questions
#
#
# Write answers in your own words (2–6 sentences each unless stated) **before** opening
# `solutions/labs/w2d1_sql_joins_grain/assessment_answers.md`. Suggested location:
# `progress/journal/w2d1_assessment.md`. Numbers refer to `data/maintenance.db` (SYNTHETIC).
#
# #### A. Reasoning questions
#
# **A1.** A machine has `a` work orders and `b` downtime events. You `LEFT JOIN` both tables to
# `machines` and compute `SUM(labor_hours)`, `SUM(hours)`, `COUNT(DISTINCT wo_id)` and
# `COUNT(wo_id)` per machine. Give each of the four results in terms of the true values, for
# (i) `a, b ≥ 1` and (ii) `a ≥ 1, b = 0`. Why does case (ii) make spot-checking dangerous?
#
# **A2.** The broken dashboard query reports 838.8 labour hours in total; the true total is 633.8.
# A colleague concludes "the query over-counts by 32 %, so divide by 1.32 until we fix it". Give two
# separate reasons, with evidence from the data, why no single correction factor can be right.
#
# **A3.** In the same broken query the `parts_cost` column is exactly correct. Explain why, using the
# word *grain*. Then state the general rule that tells you, before running anything, which columns of
# a joined result are safe to sum.
#
# **A4.** `SELECT COUNT(*) FROM machines WHERE criticality = 'high'` returns 7 and
# `… WHERE criticality <> 'high'` returns 12, but the table has 32 rows. Explain the missing 13 and
# write a predicate that returns "all machines not known to be high" (25 rows).
#
# **A5.** Someone writes `AVG(COALESCE(labor_hours, 0))` "to handle the NULLs". On this data the
# mean changes from about 7.64 to about 6.82 hours. Which estimand does each expression compute, and
# what would you need to know about *why* the hours are missing to decide which, if either, to report?
#
# **A6.** You are handed this query and told it lists the technicians who have never worked on a
# machine at site 3. It returns no rows, and the author says "so everyone has". Identify the two
# independent defects.
#
# ```sql
# SELECT tech_name FROM technicians
# WHERE tech_id NOT IN (SELECT w.tech_id FROM work_orders w JOIN machines m USING (machine_id)
#                       WHERE m.site_id <> 3);
# ```
#
# #### B. Design-choice explanation (one paragraph, about 150 words)
#
# **B1.** You must build a training table with one row per machine for a "will this machine have a
# corrective work order next quarter?" model, with features from `work_orders`, `parts_used` and
# `downtime_events`. Compare two designs: (1) one query that joins everything and uses
# `COUNT(DISTINCT …)` and `SUM(…)` with care; (2) one CTE per source table, each aggregated to the
# machine grain, joined at the end. Choose one and defend it on correctness, reviewability, the ability
# to test it, and cost. Say what would make you choose the other.
#
# #### C. Rubric for open answers
#
# | Level | A-questions | B1 |
# |---|---|---|
# | **Meets** | Names the mechanism precisely (grain, cardinality, UNKNOWN), gives the right quantities, and ties them to evidence in the data | Chooses with reasons on at least three of the four dimensions, names an invariant that would be tested, and states a condition under which the other design wins |
# | **Partial** | Right conclusion, mechanism vague ("duplicates", "NULLs are weird") or quantities missing | Chooses correctly but argues from style or habit; no test, no counter-condition |
# | **Not yet** | Proposes `DISTINCT`, a correction factor or `COALESCE` everywhere as the fix | Treats the designs as equivalent, or picks (1) because it is shorter |
#
# #### D. Interview rep — SQL (15 minutes, timed)
#
# **Conditions (weeks 1–2 of the fading schedule):** write your answer first, untimed reading of the
# prompt allowed, then compare with the rubric and worked answer in the solutions file. Say your
# reasoning aloud if you can; an interviewer hears the grain statement before they see the query.
#
# > Tables: `users(user_id PK, country)` where `country` may be NULL;
# > `sessions(session_id PK, user_id, started_at)`; `purchases(purchase_id PK, user_id, amount)`.
# > A user may have any number of sessions and purchases, including none.
# >
# > Write one query returning, per country (NULL country reported as `'unknown'`): the number of
# > users, the number of users with at least one purchase, total revenue, and the average number of
# > sessions per user, where users with no sessions count as zero.
# >
# > Then answer: how would you convince a reviewer that the revenue column is right?
#
# Log the rep in `progress/notes.md`: time taken, what went wrong, and the pattern behind the error.

# %% [markdown]
# ## 8. Reflection and review
#
# **You should now be able to do, alone:**
#
# - state the grain and key of any table or intermediate result and predict a join's row count;
# - spot a fan-out from the shape of a query, before running it, and rewrite it with pre-aggregation;
# - choose between `ON`, `WHERE` and `HAVING` for a condition and say what changes;
# - predict what a NULL does in a comparison, an aggregate and `NOT IN`;
# - attach at least two invariants to any aggregate query you hand to someone else.
#
# **Reflection prompt** (3–4 sentences, `python wb.py note w2d1 "…"`): think of a training table you
# built in the past by merging dataframes. What was its grain, what was the independent unit, and is
# there a merge in it whose row count you never checked?
#
# **Retrieval question for a later day** (answer from memory on W2D7): *A parent table has two child
# tables. You join both and sum one measure from each child. By what factor is each sum wrong for a
# given parent row, and what is the general fix? Then: why does `x NOT IN (SELECT y …)` return nothing
# when one `y` is NULL?*
#
# **Next:** [W2D2 — SQL II: CTEs, window functions and time-series queries](08_sql_windows_timeseries.ipynb)
# builds on this. Window functions keep the grain of their input, which is exactly why they are
# the right tool for running statistics and as-of features and the wrong tool for fixing a fan-out.
#
# ---

# %% [markdown]
# ## Verification record
#
# Executed 2026-11-22 on Python 3.13.18, SQLite 3.53.1, pandas 3.0.5, pytest 9.1.1.
#
# | What | Result |
# |---|---|
# | `python labs/w2d1_sql_joins_grain/example/fanout_demo.py` | ran; outputs in section 3 are copied from this run |
# | `python labs/w2d1_sql_joins_grain/data/make_db.py --check` | contents match the committed database |
# | `python tools/verify_checks.py labs/w2d1_sql_joins_grain` | lab: reference passes, 5 mutants rejected; challenge: reference passes, 4 mutants rejected |
# | Shipped starter | fails the lab checks and the challenge checks, as intended |
# | Expected results | computed in pandas (`checks/w2d1_oracle.py`), independently of the reference SQL; both agree on two databases |
# | Optional: reference queries on DuckDB 2.0.1 | all 12 return the same result sets as SQLite; DuckDB rejects the non-grouped column that SQLite accepts |
#
# Not verified: PostgreSQL/BigQuery behaviour is stated from the SQL standard's rules and from memory,
# not executed. The industry example in 2.7 is an illustrative composite, not a cited incident. Time
# boxes are estimates.

# %% [markdown]
# ## Record your progress
#
# Tick only what is true. Passing the supplied checks is *guided practice*; mark *independent* only for work done without hints or solutions.

# %%
from mlcourse.progress import mark, note

# mark("w2d1", "reading")
# mark("w2d1", "guided")
# mark("w2d1", "independent")
# note("w2d1", "what tripped me up today")

