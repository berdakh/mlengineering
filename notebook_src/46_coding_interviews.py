# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/46_coding_interviews.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 46 · Coding and SQL interviews, timed
#
# **Week 8 · day 4 · 2 h essential path + up to 1 h optional** · lab files: [`labs/w8d4_coding_interviews/`](../labs/w8d4_coding_interviews/)
#
# **Objective.** Solve Python data-structure and SQL problems under time pressure while explaining aloud.

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
# **Status:** Execution verified (see the verification record at the end).
# **Handbook:** [H16.4 Interview problem patterns](../docs/handbook/ch16_system_design_communication/h16_4_interview_problem_patterns.md)
# **Prerequisites:** the interview reps so far ([interview/README.md](../docs/guides/interview-practice.md), sets 1-6),
# [w2d1](07_sql_joins_grain.ipynb) and [w2d2](08_sql_windows_timeseries.ipynb) (SQL grain,
# joins, window functions, gaps and islands), [w1d5](05_testing_ml_code.ipynb) (writing your own tests).
#
# ---

# %% [markdown]
# ## 1. Purpose
#
# **What you will learn.** The small set of problem patterns that most data and ML coding rounds draw from,
# a talk-aloud protocol that makes your reasoning visible, and how to test your own solution under time
# pressure. Then you solve a timed set of six Python and three SQL problems and a 45-minute mock.
#
# **Why an applied ML engineer needs it.** Almost every Machine Learning Engineer and Applied Scientist loop
# has at least one coding round and often a SQL round. They are pass/fail gates that research experience
# does not exempt you from, and they reward a specific skill: producing correct, efficient, tested code
# while explaining it, in 20-45 minutes. The problems here are flavoured by ML and data work (labels,
# alarms, sensors, pipelines, trips) so the practice transfers to the job as well.
#
# **Primary objective.** Solve the essential subset of the timed set within the time boxes, talking aloud,
# and log an error pattern for every miss.
#
# **Deliverable.** Your solutions in `lab/python/` and `lab/sql/` passing the checks; recordings scored with
# the talk-aloud rubric; an error log by pattern in `progress/notes.md`; the mock in `challenge/`.
#
# **Completion criteria.**
# - `python wb.py check w8d4` passes for the problems you attempted (guided practice is the essential
#   subset: P1, P2, P3, Q1, Q2; the rest are the extension).
# - Each attempted problem has a row in your error log: time, pass/fail, pattern, mistake.
# - `python wb.py check w8d4 --challenge` passes on a single 45-minute attempt (independent skill).
#
# | Activity | Essential (2 h) | Optional (≤ 1 h) |
# |---|---|---|
# | Read section 2, run the worked example | 25 min | |
# | Timed: P1, P2, P3 (10 + 12 + 15 min) | 40 min | |
# | Timed: Q1, Q2 (12 + 12 min) | 25 min | |
# | Score recordings, error log, assessment Q1-Q7 | 30 min | |
# | P4, P5, P6, Q3 | | 60+ min (or the review day) |
# | Challenge: 45-minute mock | on the review day | |
#
# ---

# %% [markdown]
# ## 2. Conceptual explanation
#
# ### 2.1 Intuition
#
# A coding round tests three things at once: whether you can find an algorithm with the right complexity,
# whether your code is correct at the edges, and whether the interviewer can follow your reasoning. Most
# interview problems for data roles are variations of about a dozen patterns. Recognising the pattern is
# most of the work; the rest is careful code and your own tests.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/docs/assets/diagrams/mmd-46-01.svg" alt="Diagram 1 of notebook 46" style="max-width:100%">
#
# ### 2.2 Precise terms
#
# * **Time complexity:** how the running time grows with input size, in big-O, for the worst case unless
#   stated otherwise. **Amortised:** average per operation over a sequence (a deque push and pop are O(1)
#   amortised in a monotonic-deque window even though one step can pop many items).
# * **Invariant:** a statement that holds before and after every loop iteration (e.g. "every alarm before
#   index `i` is earlier than the current fault or already used"). Saying the invariant is how you argue
#   correctness aloud.
# * **Grain (SQL):** what one row of a table or intermediate result represents. Fan-out is a join that
#   silently changes the grain.
# * **Brute force:** the simplest correct algorithm, stated first so you have a baseline and a test oracle.
#
# ### 2.3 The talk-aloud protocol
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/docs/assets/diagrams/mmd-46-02.svg" alt="Diagram 2 of notebook 46" style="max-width:100%">
#
# Spend about two minutes on the first three boxes even when you think you know the answer: interviewers
# score them, and it is where misunderstandings are caught cheaply. When stuck, say what is blocking you and
# work a smaller example by hand.
#
# ### 2.4 The mathematics you need
#
# Complexity arithmetic: an O(n²) algorithm on n = 200,000 is 4 × 10¹⁰ elementary steps, minutes to hours in
# Python; O(n log n) is about 3.5 × 10⁶, well under a second. Doubling n doubles O(n), quadruples O(n²) and
# slightly more than doubles O(n log n). A log-log plot of time against n has slope 1 for linear and 2 for
# quadratic algorithms:
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/labs/w8d4_coding_interviews/figures/scaling.svg" alt="Log-log plot of run time against input size: the brute force rises with slope about 2 and the hash-map version with slope about 1" width="100%">
#
# *Figure 1 (measured on the authoring machine; your times will differ, the slopes should not).* The worked
# example's brute force against its hash-map version, k = n/10.
#
# For numerical code, know one stability fact: the variance via E[x²] − E[x]² loses all precision when the
# mean is large relative to the spread (catastrophic cancellation); use Welford's update or two passes.
#
# ### 2.5 Connection to what you already know
#
# You have written these patterns in research code without naming them: event extraction from a binary
# detector output is gaps and islands; matching detections to annotated events within a tolerance is two
# pointers over sorted times; a running mean and variance for artefact thresholds is Welford; top-k channels
# by power is a heap. The interview difference is the time box and the need to say why it is correct.
#
# ### 2.6 SQL rounds: grain first
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/docs/assets/diagrams/mmd-46-03.svg" alt="Diagram 3 of notebook 46" style="max-width:100%">
#
# The schema of today's database is in [`data/README.md`](../labs/w8d4_coding_interviews/data/README.md) (an ER diagram and the grain of each
# table).
#
# ### 2.7 Limitations and common misconceptions
#
# * *"Optimal complexity is all that counts."* A correct brute force with tests beats an unfinished optimal
#   solution. Get a baseline, then improve.
# * *"The checks passed, so I am done."* Checks verify outputs. The rubric scores the reasoning and the
#   communication, which is half the interview.
# * *"LeetCode-style practice is irrelevant to ML jobs."* The patterns appear constantly in data code
#   (deduplication, windows, joins); the time pressure is what is artificial.
# * Practising only easy problems feels productive and transfers poorly; the medium problems are the bar.
#
# ---

# %% [markdown]
# ## 3. Worked example: a repeated reading within k
#
# **Problem (not in the lab).** Flag every index whose value already appeared among the previous `k`
# readings. Code: [`example/repeat_within_k.py`](../labs/w8d4_coding_interviews/example/repeat_within_k.py).
#
# **Talk-aloud transcript (abridged).**
# 1. *Restate:* "Index i is flagged if some j with i − k ≤ j < i has the same value. Example `[1, 2, 1]`,
#    k = 2: index 2 is flagged."
# 2. *Edges:* empty list; k = 0 flags nothing; a repeat exactly k back counts, k + 1 back does not.
# 3. *Brute force:* "Look back over the previous k values for every index: O(n k), which is O(n²) when k is
#    proportional to n."
# 4. *Improve:* "Only the most recent index of each value matters, because if the most recent occurrence is
#    more than k back, all earlier ones are too. A dict from value to last index gives O(n) time, O(distinct
#    values) space." That sentence is the invariant.
# 5. *Tests:* the five asserts in `own_tests()`, then agreement with the brute force on 500 random cases.

# %%
!python labs/w8d4_coding_interviews/example/repeat_within_k.py

# %% [markdown]
# Output on the authoring machine (times vary between runs and machines):
#
# ```text
# own tests pass; brute force and hash map agree on 500 random cases
#        n       k  brute (s)  hash map (s)
#     2000     200     0.0026       0.00024
#     4000     400     0.0107       0.00058
#     8000     800     0.0518       0.00408
#    16000    1600     0.1593       0.00205
#    32000    3200     0.6205       0.00442
# ```
#
# **Interpretation.** Each doubling of n multiplies the brute force's time by about four, as O(n k) with
# k = n/10 predicts; the hash map grows roughly linearly (single timings below a millisecond are noisy). At
# n = 200,000 the brute force would need about 25 seconds, the hash map a few hundredths of a second.
#
# **Reproducibility.** The random inputs are seeded; timings are not reproducible by nature. Figures are
# regenerated with `python labs/w8d4_coding_interviews/figures/make_figures.py`.
#
# ---

# %% [markdown]
# ## 4. Guided lab — the timed set
#
# All problem statements are in [`PROBLEMS.md`](../labs/w8d4_coding_interviews/PROBLEMS.md). Starters are in `lab/python/` (one function each;
# the docstring is the specification) and `lab/sql/` (one query each).
#
# **Task 1 — set up.** Read the conditions at the top of `PROBLEMS.md`. Start recording. Create a table in
# `progress/notes.md` with columns: problem, minutes, passed, pattern, mistake, pattern of the mistake.
#
# **Task 2 — P1, P2, P3** (10, 12 and 15 minutes). For each: restate, edge cases, brute force, improvement,
# code, your own tests, then

# %%
!python -m pytest labs/w8d4_coding_interviews/checks -q -k p1

# %% [markdown]
# *Checkpoint.* Each problem has known-answer checks, a comparison with a slow brute force on hundreds of
# random inputs, and a large-input check stopped after 4 seconds. If only the large-input check fails, your
# answer is right and your complexity is not: look for a loop inside a loop or a repeated scan.
#
# **Task 3 — Q1 and Q2** (12 minutes each). Write the grain comment first. The checks run your query on the
# shipped database, on a database regenerated with another seed (a hard-coded answer fails there), and on
# tiny hand-built databases with the trap the problem is about (several payment attempts per trip; tied
# drivers).
#
# *Debugging guidance.* If Q1's counts are too large, compare `SELECT COUNT(*)` of your intermediate result
# with the number of March completed trips: a larger number is fan-out. If a city is missing, a `WHERE`
# filter on the right-hand table has turned your `LEFT JOIN` into an inner join.
#
# **Task 4 — score and log.** Score each recording with the rubric in `assessment.md` (section 7 of this notebook). Fill
# your error log. Then read only the "Notes on the timed set" table in
# `solutions/labs/w8d4_coding_interviews/assessment_answers.md` for the problems you finished.
#
# **Optional extension — P4, P5, P6, Q3.** Same procedure. P4 has a numerical trap; P6 has a
# recursion-depth trap; Q3 is the gaps-and-islands pattern.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/labs/w8d4_coding_interviews/figures/streak.svg" alt="Daily activity of one driver over February to April 2026 with the longest run of consecutive active days highlighted" width="100%">
#
# *Figure 2 (SYNTHETIC rides database).* Q3 on one driver: 13 consecutive days from 28 February. The query
# has to see days, not trips: this driver often completes several trips a day.
#
# ---

# %%
# Run the automated checks on your guided lab.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w8d4")

# %% [markdown]
# ## 5. Independent challenge — a 45-minute mock
#
# [`challenge/README.md`](../labs/w8d4_coding_interviews/challenge/README.md): two unseen problems (one Python, one SQL) in one 45-minute
# sitting, recorded, scored with the same rubric. No solution in this directory.
#
#
# ### The challenge brief
#
#
# **Conditions.** One 45-minute timer for both problems, talking aloud and recording, exactly as in a
# technical screen. Do not open `checks_challenge/` or `solutions/` first. Spend the first two minutes
# reading both problems and deciding the order. Write your own tests; run the checks at the end only.

# %%
!python wb.py check w8d4 --challenge

# %% [markdown]
# #### C1 — The longest stable stretch (Python, `python/c1_longest_stable_run.py`)
#
# A sensor produces `values`. Return `(start, length)` of the longest contiguous run whose maximum minus
# minimum is at most `tolerance`; the earliest run wins ties; empty input gives `(0, 0)`; a negative
# tolerance raises `ValueError`. Must handle 300,000 values within a few seconds (O(n) is expected).
#
# #### C2 — March driver cohort (SQL, `sql/c2_driver_cohorts.sql`)
#
# On the rides database: a driver belongs to the **March 2026 cohort** if their first **completed** trip was
# requested in March 2026. A cohort driver is **active** if they completed at least 25 trips in the 30 days
# starting at the timestamp of that first completed trip (from the first trip's `requested_at`, inclusive, to
# 30 days later, exclusive). For each city with at least one cohort driver (city from `drivers.city_id`):
# `city, cohort_size, active_drivers, active_share` (active / cohort, rounded to 3 decimals), ordered by city.
#
# #### Acceptance criteria
#
# 1. Both check suites pass, including the large-input time limit for C1.
# 2. Your recording shows: restating each problem with an example, a stated brute force and its complexity,
#    the improvement, your own tests (including an edge case), and the final complexity.
# 3. Score yourself with the talk-aloud rubric in `../assessment.md` before reading the reference notes in
#    `solutions/labs/w8d4_coding_interviews/assessment_answers.md`.

# %%
# Run the automated checks on your independent challenge.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w8d4", challenge=True)

# %% [markdown]
# ## 6. Progressive hints
#
# [Hint 1 — which pattern](../labs/w8d4_coding_interviews/hints/hint1_concept.md) · [Hint 2 — approach](../labs/w8d4_coding_interviews/hints/hint2_approach.md) ·
# [Hint 3 — partial implementations](../labs/w8d4_coding_interviews/hints/hint3_partial.md). Each hint is split by problem, so reading the
# line for one problem does not spoil the others.
#
#
# Open one hint at a time, only after a real attempt.
#
# <details>
# <summary><b>Hint 1 concept</b></summary>
#
#
# Read only the line for the problem you are stuck on.
#
# * **P1** What do you need to remember per sample, and per annotator within a sample?
# * **P2** Both lists are sorted. Can a pointer into `alarms` ever need to move backwards?
# * **P3** What is the only fact about the past you need for a key?
# * **P4** Variance needs count, mean and spread per sensor. Is there a way to update them one value at a
#   time without the cancellation of "mean of squares minus square of mean"?
# * **P5** If someone gave you a candidate answer `X`, could you check quickly whether `X` is achievable?
# * **P6** Which steps can run first? After one runs, which become available? How do you always pick the
#   smallest available one cheaply?
# * **Q1** What is the grain of `payments`? What happens to a trip row when it meets three payment rows?
# * **Q2** A window function that numbers rows within each city, never giving two rows the same number.
# * **Q3** For consecutive days, `day - (its position in the sorted list)` is constant.
#
# </details>
#
# <details>
# <summary><b>Hint 2 approach</b></summary>
#
#
# * **P1** `dict[sample] -> dict[annotator] -> latest label`; then compare the set of values.
# * **P2** One pass over faults; advance the alarm index past alarms earlier than the fault; if the next
#   alarm is within tolerance, record the delay and consume it.
# * **P3** `last_kept[key]`; update it only when you keep an event.
# * **P4** Welford: `n += 1; d = x - mean; mean += d / n; m2 += d * (x - mean)`; variance `m2 / n`.
#   Then sort `(-variance, id)` (or `heapq.nsmallest`), rounding variances to 12 significant digits.
# * **P5** Binary search the answer between `max(costs)` and `sum(costs)`; the check is a greedy pass that
#   starts a new batch when adding the next cost would exceed `X`.
# * **P6** Kahn's algorithm: in-degree counts, a min-heap of ready steps. If you emit fewer steps than
#   exist, the rest are on (or behind) a cycle.
# * **Q1** Aggregate payments to one row per trip first (a CTE), then `cities LEFT JOIN trips LEFT JOIN
#   paid` with filters in the CTEs or `ON`, not in `WHERE`.
# * **Q2** Count per `(city, driver)` in a CTE; `ROW_NUMBER() OVER (PARTITION BY city ORDER BY count DESC,
#   driver_id)`; keep `<= 2`.
# * **Q3** `SELECT DISTINCT driver_id, DATE(requested_at)`; `JULIANDAY(day) - ROW_NUMBER() OVER (...)` as
#   the island key; group; pick the longest per driver with another `ROW_NUMBER`.
#
# </details>
#
# <details>
# <summary><b>Hint 3 partial</b></summary>
#
#
# ```python
# # P5: the feasibility check and the search skeleton
# def batches_needed(costs, limit):
#     count, running = 1, 0
#     for c in costs:
#         if running + c > limit:
#             count, running = count + 1, 0
#         running += c
#     return count
#
# lo, hi = max(costs), sum(costs)
# while lo < hi:
#     mid = (lo + hi) // 2
#     if batches_needed(costs, mid) <= max_batches:
#         hi = mid          # mid works: try smaller
#     else:
#         lo = mid + 1      # mid too small
# ```
#
# ```python
# # P6: the loop of Kahn's algorithm with a heap
# ready = [s for s in steps if indeg[s] == 0]
# heapq.heapify(ready)
# while ready:
#     s = heapq.heappop(ready)
#     order.append(s)
#     for nxt in succ[s]:
#         indeg[nxt] -= 1
#         if indeg[nxt] == 0:
#             heapq.heappush(ready, nxt)
# ```
#
# ```sql
# -- Q3: the island key
# WITH days AS (SELECT DISTINCT driver_id, DATE(requested_at) AS day FROM trips WHERE status = 'completed')
# SELECT driver_id, day,
#        JULIANDAY(day) - ROW_NUMBER() OVER (PARTITION BY driver_id ORDER BY day) AS grp
# FROM days;
# -- next: GROUP BY driver_id, grp -> MIN(day), COUNT(*); then the longest (earliest on ties) per driver
# ```
#
# </details>

# %% [markdown]
# ## 7. Assessment
#
# `assessment.md` (section 7 of this notebook): seven reasoning questions (complexity of a plausible wrong approach,
# `RANK` vs `ROW_NUMBER`, the variance design choice, binary search on the answer, grain invariants,
# recursion in Python, what to do when stuck) and the talk-aloud rubric used for the interview rep, which
# today is the timed set itself.
#
#
# ### Assessment questions
#
#
# Answer in writing or aloud before opening `solutions/labs/w8d4_coding_interviews/assessment_answers.md`.
#
# **Q1.** P3 asks for O(n). A colleague keeps a list of kept events and scans it backwards for the same key.
# What is the worst-case complexity, and on what input does it happen?
#
# **Q2.** Why does `RANK()` give the wrong answer for Q2 while `ROW_NUMBER()` with a tie-breaker gives the
# right one? When would `DENSE_RANK()` be the right choice instead?
#
# **Q3 (design choice — explain).** In P4 you could store all values per sensor and call
# `statistics.pvariance`, or use a one-pass update. Compare memory, time and numerical behaviour, and say
# which you would choose in an interview and why.
#
# **Q4.** Explain why "binary search on the answer" is valid for P5: what property must the feasibility
# check have?
#
# **Q5.** Q1 joins trips to payments. Write down the grain of each intermediate result in your query, and the
# invariant you would check (a row count or a total) to prove there is no fan-out.
#
# **Q6.** In P6, why does an iterative algorithm matter in Python specifically, and how does Kahn's
# algorithm detect a cycle without a separate search?
#
# **Q7.** You have 25 minutes for a problem and after 10 minutes you have only a brute force. What do you
# say and do?
#
# #### Interview rep: the set itself
#
# The timed problems in [`PROBLEMS.md`](../labs/w8d4_coding_interviews/PROBLEMS.md) and the mock in [`challenge/README.md`](../labs/w8d4_coding_interviews/challenge/README.md),
# talked aloud and recorded. Score each recording with this rubric before reading the reference notes.
#
# | Behaviour | Demonstrated | Partial | Not yet |
# |---|---|---|---|
# | Restates the problem with a small example and edge cases | before coding | after starting | never |
# | States a brute force and its complexity | yes, in under 2 minutes | complexity missing | skips to code |
# | Names the improvement and why it is correct | pattern + invariant | pattern only | trial and error |
# | Writes or says own tests, including an edge case | before running checks | only after a failure | none |
# | States final time and space complexity correctly | both | one | neither |
# | Communicates while stuck | says what is blocking and tries a smaller case | silent stretches > 1 min | silent |
# | Finishes within the time box | yes | within +50 % | no |

# %% [markdown]
# ## 8. Reflection and review
#
# **You should now be able to, without notes:**
# - name the pattern of a typical data-flavoured coding problem within two minutes and say its complexity;
# - explain correctness with an invariant while coding;
# - write your own tests, including an edge case, before running anything;
# - write SQL that states its grain, avoids fan-out, ranks within groups and finds streaks.
#
# **Reflection prompt (5 minutes, `progress/notes.md`).** Which pattern appeared in more than one of your
# mistakes today, and what will you check first next time?
#
# **Retrieval question for review day.** *Without code: how do you return the longest run of consecutive
# days per user in SQL, and what goes wrong if a user has two events on the same day?*
#
# **Next.** [w8d5 — Explaining the project and defending trade-offs](47_project_explanation.ipynb):
# the remaining interview round, about the work you have built.
#
# ---

# %% [markdown]
# ## Verification record
#
# Executed on 2026-11-25, Python 3.13.18, SQLite 3.53.1, pandas 3.0.5, matplotlib 3.11.2 (figures only).
#
# | What | Command | Outcome |
# |---|---|---|
# | Database | `python labs/w8d4_coding_interviews/data/make_db.py --check` | Regenerated tables identical to the committed file |
# | Worked example | `python labs/w8d4_coding_interviews/example/repeat_within_k.py` | Own tests and 500 random comparisons pass; timings above from one run |
# | Figures | `python labs/w8d4_coding_interviews/figures/make_figures.py` | 2 SVGs + `figure_data.csv`; PNG copies viewed |
# | Lab checks vs reference | `python tools/verify_checks.py labs/w8d4_coding_interviews --part lab` | Reference passes 30 checks; 15 mutants rejected (at least one per problem) |
# | Challenge vs reference | `... --part challenge` | Reference passes 6 checks; 5 mutants rejected |
# | Starters fail | `python -m pytest labs/w8d4_coding_interviews/checks -q` | 30 failed; challenge 6 failed |
# | SQL expected results | pandas oracle in `checks/oracle.py` | Written independently of the reference SQL; agrees on two seeds |
#
# Not verified: the time boxes (not trialled by a learner); behaviour on Windows (the large-input checks use
# `signal.setitimer`, which is Unix-only, as is the course's target platform, Pop!_OS).

# %% [markdown]
# ## Record your progress
#
# Tick only what is true. Passing the supplied checks is *guided practice*; mark *independent* only for work done without hints or solutions.

# %%
from mlcourse.progress import mark, note

# mark("w8d4", "reading")
# mark("w8d4", "guided")
# mark("w8d4", "independent")
# note("w8d4", "what tripped me up today")

