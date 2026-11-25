# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/15_hyperparameter_selection.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 15 · Hyperparameter and threshold selection without fooling yourself
#
# **Week 3 · day 3 · 2 h essential path + up to 1 h optional** · lab files: [`labs/w3d3_hyperparameter_selection/`](../labs/w3d3_hyperparameter_selection/)
#
# **Objective.** Select hyperparameters and decision thresholds using only training/validation data; quantify selection optimism with nested validation.

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
# Status: see [STATUS.md](../docs/guides/status.md). Handbook: [H6.4](../docs/handbook/ch06_evaluation_leakage_uncertainty/h6_4_selection_and_nested_validation.md).
# Solutions live in `solutions/labs/w3d3_hyperparameter_selection/`; open them after your own attempt.

# %% [markdown]
# ## 1. Purpose
#
# **Objective.** Select hyperparameters and decision thresholds using only training and validation data,
# and quantify the optimism of selection with nested validation.
#
# **Why an applied ML engineer needs it.** Every model that ships was chosen: among families, settings,
# feature sets, thresholds, seeds, "the run that worked". Each choice is a small fit to the data used to
# compare candidates, and the score of the winner on that data is too high. In research the cost is an
# inflated table; in a product it is a launch decision made on a number that will not be met, and a
# threshold that pages people at a rate nobody predicted. Today you will see a real search on SKAB in which
# the best trial's own score is 0.891, the honest estimate of the procedure is 0.850, and the four outer
# folds do not agree on a model family or a feature window.
#
# **Deliverable.** `flowguard.selection` (tested), and `lab/SELECTION.md`: protocol, the three dev-side
# numbers, one test evaluation at frozen thresholds, and your reading.
#
# **Prerequisites.** [w3d2](14_group_temporal_validation.ipynb) (grouped folds, the split manifest);
# [w2d6](12_baselines_metrics.ipynb) (PR-AUC, thresholds from dev). The lab ships snapshots of
# `flowguard.data`, `splits` (manifest v2, overlap groups kept together), `features` (causal, burn-in
# normalised, no clock features) and `metrics`. SKAB downloaded: `python project/get_skab.py`.
#
# **Time budget (2 h essential).**
#
# | Activity | Minutes |
# |---|---|
# | Read section 2, run the worked example | 30 |
# | Lab tasks 1-3: candidates, grouped search, selection rules | 30 |
# | Lab task 4: nested estimate | 20 |
# | Lab task 5: thresholds | 15 |
# | Lab task 6: run on SKAB (about 3-8 min of compute), write `SELECTION.md` | 15 |
# | Assessment questions 1-3 | 10 |
# | **Optional extension (up to 1 h):** challenge (60 recorded trials, one test look); interview rep | 60 |

# %% [markdown]
# ## 2. Conceptual explanation
#
# ### 2.1 Selection is a second fit
#
# Training fits parameters to training rows. Selection fits *choices* to validation scores. The two have
# the same failure: the fitted object is adapted to the noise in the data it was fitted on, so its score on
# that data is optimistic. The difference is only one of scale: a threshold is a one-parameter model fitted
# to dev scores; choosing among 24 configurations is a model with 24 discrete options.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/docs/assets/diagrams/mmd-15-01.svg" alt="Diagram 1 of notebook 15" width="100%">
#
# The quantity worth reporting is the performance of the **procedure** (search, select, refit, threshold)
# on new experiments, not the dev score of the configuration it happened to pick.
#
# ### 2.2 The optimism of the maximum
#
# Let K candidates have true scores `μ_i` and CV estimates `μ̂_i = μ_i + ε_i`. Choosing the largest
# estimate and reporting it overstates the chosen candidate by `E[ε_winner] > 0`.
#
# * If all candidates are equally good and the errors are independent `N(0, σ²)`, the optimism is
#   `σ · E[max of K standard normals]`: 0.56σ for K=2, 1.54σ for K=10, 2.25σ for K=50, growing like
#   `σ√(2 ln K)`.
# * Candidates scored on the same folds share part of their error (correlation ρ). The shared part moves
#   all candidates together and does not change the winner, so the optimism shrinks by `√(1−ρ)`.
# * When candidates differ, the winner is good *and* lucky (the winner's curse): selection still helps, but
#   the reported score is too high.
#
# These are not exotic. With σ = 0.02 (a typical SE of a 4-fold PR-AUC) and 50 candidates, the winner looks
# 0.045 better than it is.
#
# ### 2.3 Nested validation
#
# Wrap the procedure in an outer loop. For each outer fold k: run the whole search on the other folds only,
# select, refit the selected candidate on those folds, and score fold k. Fold k never fitted a model, never
# scored a candidate, never moved a threshold.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/docs/assets/diagrams/mmd-15-02.svg" alt="Diagram 2 of notebook 15" width="100%">
#
# What it estimates is a property of the procedure. Different outer folds may pick different candidates;
# that is information, not a malfunction: it says the search cannot separate the candidates with this data.
#
# Two broken versions look nested and are not: (a) search once on all folds, then "cross-validate the
# tuned model" (each outer fold has already voted for its winner); (b) inner folds split by rows (every
# experiment on both sides of every inner split). Both are mutants in this lab.
#
# ### 2.4 Searching
#
# * **Random beats grid** when few hyperparameters matter: with a budget of B trials, a grid over d
#   dimensions tries `B^{1/d}` values of each, random search tries B. In the worked example (16 trials, one
#   relevant hyperparameter) random search finds a better value than a 4×4 grid in 90 % of runs.
# * **Log scales** for strengths and rates (`C`, learning rate).
# * **Record every trial.** The lab's `grouped_search` returns all of them; selecting from a list you did not
#   keep is how researcher degrees of freedom become invisible.
# * **Budgets.** Successive halving and Hyperband (concept only) spend less on poor candidates; early stopping
#   is a hyperparameter chosen on validation data. None changes the need to nest the estimate.
#
# ### 2.5 The one-standard-error rule
#
# Among candidates whose mean is within one SE (of the best candidate) of the best mean, choose the
# simplest. When the SEs exceed the gaps between the top means, the ordering among them is noise, and
# simplicity (variance, latency, maintenance) is a better tiebreak than noise. It needs an explicit
# complexity ordering; it does **not** remove optimism from the number attached to the choice.
#
# ### 2.6 Thresholds are hyperparameters
#
# A decision threshold is fitted on development scores and frozen:
#
# * the development scores must be **out-of-fold** (each row scored by a model that never saw its experiment);
# * the test result is reported **at the frozen threshold**, never at the test-optimal one;
# * an alert-budget threshold (lowest threshold whose false-alarm fraction on normal dev rows is within a
#   budget) obeys the same rule.
#
# ### 2.7 How many times may you look at test?
#
# Once per question. Every look that can change a decision is a selection on test. A bug discovered after a
# test look is fixed, and the new test number is reported as obtained after a second look. The challenge
# logs your looks.
#
# ### 2.8 Connection to what you know
#
# EEG decoding papers often tune hyperparameters, channel sets or frequency bands with cross-validation that
# includes the test subjects, or tune per-subject thresholds on the subject being scored. You will recognise
# both as the broken versions of section 2.3. Leave-one-subject-out with an inner leave-one-subject-out for
# tuning is nested validation; it is expensive, which is why it is often skipped, and the skipped version is
# optimistic in exactly the way quantified here.
#
# ### 2.9 Industry example
#
# A fraud team runs 300 trials of gradient-boosting hyperparameters on last quarter's data and reports the
# best validation AUC, 0.912, to justify a launch. A nested estimate would have given about 0.89; live AUC
# after a month is 0.887. The launch was still right, but the business case, which promised a 12 % reduction in
# losses based on 0.912, was not met, and the next model's (honest) evaluation looked like a regression.
# (Illustrative composite.)
#
# ### 2.10 Limits and misconceptions
#
# * "CV is unbiased" - for a fixed configuration, approximately; not for the configuration CV selected.
# * "Nested CV gives the performance of the final model" - it estimates the procedure; the final model is
#   one draw from it.
# * "If test beats the nested estimate, the nested estimate was pessimistic" - with 7 test experiments and
#   4 outer folds both numbers are noisy; one comparison says little (see the lab).
# * "The one-SE rule corrects optimism" - it changes the choice, not the bias of the attached number.
# * "A threshold is post-processing, not a parameter" - it is fitted, so it must be fitted on dev.

# %% [markdown]
# ## 3. Worked example: what selection does to the number you report
#
# [`example/selection_demo.py`](../labs/w3d3_hyperparameter_selection/example/selection_demo.py) is a SYNTHETIC simulation (NumPy only).

# %%
!python labs/w3d3_hyperparameter_selection/example/selection_demo.py

# %% [markdown]
# Output (run 2026-11-22, last four parts):
#
# ```
# A/B. All K candidates have true score 0.70; each estimate has standard error 0.02.
#      Mean amount by which the BEST estimate exceeds the truth:
#         K   independent   correlated(rho=0.7)   sigma*sqrt(2 ln K)
#         1      -0.0000          -0.0001              0.0000
#         2      0.0114          0.0063              0.0235
#         5      0.0234          0.0129              0.0359
#        10      0.0308          0.0167              0.0429
#        20      0.0374          0.0204              0.0490
#        50      0.0450          0.0246              0.0559
#       100      0.0501          0.0273              0.0607
#       500      0.0607          0.0334              0.0705
#
# C. 60 candidates whose true scores differ (s.d. 0.01), selected by a dev estimate with s.e. 0.02:
#      dev estimate of the winner   0.7518
#      true score of the winner     0.7104   (optimism 0.0415)
#      true score of the true best  0.7232   (regret   0.0128)
#      true score of a random one   0.6999
#      the winner is the truly best candidate in 11.2% of repetitions
#
# D. Budget 16 trials, score depends only on C (optimum 0.800):
#      4x4 grid:  4 distinct values of C, best score found 0.7920
#      random:   16 distinct values of C, best score found 0.7970 on average; beats the grid in 89.7% of runs
# ```
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/labs/w3d3_hyperparameter_selection/figures/optimism_of_max.svg" alt="Optimism of the best of K equally good candidates against K, for independent and correlated estimates, with the sigma sqrt(2 ln K) bound" width="100%">
#
# *Figure 1 (SYNTHETIC, σ = 0.02).* The optimism grows slowly with K (like √ln K) and is smaller when
# candidates share noise, as they do when scored on the same folds. The bound is loose at small K.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/labs/w3d3_hyperparameter_selection/figures/grid_vs_random.svg" alt="Grid versus random search with sixteen trials when only one of two hyperparameters affects the score" width="100%">
#
# *Figure 2 (SYNTHETIC).* A 4×4 grid spends its 16 trials on 4 values of the hyperparameter that matters;
# random search tries 16.
#
# Interpretation. Part C is the realistic case: the winner is better than a random candidate (0.710 vs
# 0.700), so selection helps, but its dev estimate (0.752) overstates it by 0.04, and it is the truly best
# candidate only 11 % of the time. Selection is worth doing; its score is not worth reporting.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/labs/w3d3_hyperparameter_selection/figures/threshold_frozen.svg" alt="F1 against threshold on development and on shifted test scores, marking the frozen dev threshold and the test-optimal F1" width="100%">
#
# *Figure 3 (SYNTHETIC, test scores shifted by +0.5).* The circled test-optimal F1 belongs to no deployable
# detector. The reportable number is test F1 at the threshold frozen on dev.

# %% [markdown]
# ## 4. Guided lab: `flowguard.selection` on SKAB
#
# Work in `labs/w3d3_hyperparameter_selection/lab/`. Given and complete: `data.py`, `splits.py`,
# `features.py`, `metrics.py`, `selection_report.py`. Yours: every function in `src/flowguard/selection.py`
# and `SELECTION.md`.
#
# Check at any time (offline, synthetic data, a few seconds):

# %%
!python wb.py check w3d3

# %% [markdown]
# All 40 checks fail on the starter.
#
# **Task 1 - candidates (10 min).** `param_grid` (full product, deterministic order) and `sample_params`
# (`loguniform`, `uniform`, `int`, `choice`; same seed, same list).
#
# *Checkpoint.* `checks/test_candidates.py` passes 5 tests; one checks that log-uniform draws are uniform in
# the exponent.
#
# **Task 2 - grouped search (15 min).** `grouped_search`: for every candidate and fold k, fit a fresh
# estimator on the rows of the *other folds* and score fold k. Rows outside the folds (test experiments,
# the reference recording) are never fitted or scored.
#
# *Checkpoint.* `test_search.py` passes 7 tests, including an independent oracle and a test that plants
# rows outside the folds and detects any use of them.
#
# *Debugging.* Oracle mismatch only on some folds: you build the training mask as "not in fold k", which
# includes test rows. Non-determinism: you reused one estimator object across fits.
#
# **Task 3 - selection rules (5 min).** `select_best` with `"max"` and `"one_se"` and the documented
# tie-breaks.
#
# *Checkpoint.* `test_select_best.py` passes 7 tests.
#
# **Task 4 - nested estimate (20 min).** `nested_estimate`: outer loop over folds; inner search on the
# others; select; refit on all inner folds; score the outer fold. Return the outer scores, their mean and SE,
# the chosen params and the inner best score per fold.
#
# *Checkpoint.* `test_nested.py` passes 9 tests. The one to read: on pure-noise data the best inner score is
# visibly optimistic while the nested estimate stays near chance; the poisoned-fold test plants an outer fold
# that would change the inner choice if it were used.
#
# **Task 5 - thresholds (15 min).** `evaluate_at_threshold`, `select_threshold` (`best_f1`, `alert_budget`),
# `frozen_threshold_evaluation`.
#
# *Checkpoint.* `test_threshold.py` passes 12 tests (some parametrised). Two of them change only the test
# data and require the threshold not to move.
#
# **Task 6 - run on SKAB and read (15 min).**

# %%
!python labs/w3d3_hyperparameter_selection/lab/selection_report.py
!python labs/w3d3_hyperparameter_selection/lab/selection_report.py --n-candidates 6

# %% [markdown]
# The report searches two families (logistic regression and histogram gradient boosting, each with a
# feature-window hyperparameter) with grouped 4-fold CV on the 27 development experiments, computes the
# nested estimate with the one-SE rule, chooses thresholds on out-of-fold dev scores, and evaluates once on
# the 7 test experiments. The split is read from `lab/splits/v2.json`, the manifest repaired and frozen in
# [w3d1](13_leakage.ipynb): the test set is never redrawn once results have been seen, so every
# Week 3 lesson reports on the same seven experiments. The search plus nesting took about 4.5 minutes on
# the last authoring run; expect 2-8 minutes.
#
# Expected with the reference implementation (yours must match to three decimals; all randomness is seeded):
#
# ```
# dev experiments 27 in 4 folds, test 7; 24 candidates; metric = point-level PR-AUC
#
# search: dev CV PR-AUC over candidates: min 0.794, median 0.828, max 0.891
#   best trial    #17: 0.891 +/- 0.015 (SE over folds)  hgb, window 10, max_depth 4, learning_rate 0.045, max_iter 200
#   one-SE choice #12: 0.878 +/- 0.012                   hgb, window 10, max_depth 4, learning_rate 0.262, max_iter 50
#
# nested estimate of search + one-SE selection + refit: 0.850 +/- 0.032
#   outer fold 0: inner selected mean 0.899 -> outer score 0.852  hgb, window 10
#   outer fold 1: inner selected mean 0.861 -> outer score 0.759  logreg, window 10, C 0.0015
#   outer fold 2: inner selected mean 0.854 -> outer score 0.886  hgb, window 0
#   outer fold 3: inner selected mean 0.869 -> outer score 0.904  hgb, window 60
#
# TEST (looked at once), selected candidate refitted on all dev experiments:
#   test PR-AUC 0.922   (dev CV of the selected trial 0.878, best dev CV of any trial 0.891, nested 0.850)
#   threshold [best_f1] = 0.262:        dev P 0.768 R 0.791 F1 0.779 FAR 0.151 | test P 0.774 R 0.907 F1 0.835 FAR 0.158
#   threshold [alert_budget 5%] = 0.920: dev P 0.868 R 0.523 F1 0.653 FAR 0.050 | test P 0.941 R 0.637 F1 0.759 FAR 0.024
#
# for scale: elapsed time alone (no sensors) has test PR-AUC 0.524; test prevalence 0.373
# ```
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/labs/w3d3_hyperparameter_selection/figures/skab_trials.svg" alt="Twenty-four recorded SKAB trials sorted by dev score with SE bars, and horizontal lines for the best trial's dev score, the nested estimate with its band, and the single test score" width="100%">
#
# *Figure 4 (real SKAB, 27 development and 7 test experiments).* The SE bars of the top trials overlap
# heavily; the best trial's own score (dashed) sits far above the nested estimate of the procedure (solid,
# band ±1 SE). The single test look (dotted) lands above both.
#
# Things to see for yourself before reading the reference interpretation:
#
# * why 0.891 is not "expected performance", and which number is;
# * what it means that one outer fold chose logistic regression and three chose boosting, with three
#   different feature windows;
# * whether test 0.922 against nested 0.850 is evidence that nesting was pessimistic. Count the independent
#   units on each side (4 outer folds of 6-8 experiments; 7 test experiments) and look at the spread of the
#   four outer scores (0.759 to 0.904) before answering;
# * what the alert-budget threshold buys (test false-alarm rate 2.4 % of normal rows) and costs (recall 0.64).
#
# **Completion criteria.** All 40 lab checks pass; `SELECTION.md` is filled from your own run, states the
# protocol (including the number of test looks: one), and gives the nested estimate, not the best trial's
# score, as the expected performance, with its limitations.

# %%
# Run the automated checks on your guided lab.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w3d3")

# %% [markdown]
# ## 5. Independent challenge
#
# [`challenge/README.md`](../labs/w3d3_hyperparameter_selection/challenge/README.md). Sixty recorded trials (SYNTHETIC) with five fold scores
# each; choose one, attach an honest estimate, look at its sealed test score exactly once, and design a
# simulation of the optimism of the maximum. Graded on 200 freshly generated tables: your estimate must be
# unbiased for the trial you choose.

# %%
!python wb.py check w3d3 --challenge

# %% [markdown]
# ### The challenge brief
#
#
# Work without the hints first. About 60 minutes. Nothing here needs the lab to be finished.
#
# #### Scenario
#
# A colleague ran a search before going on leave and left you `trials.csv`: **60 trials** (SYNTHETIC,
# generated by `checks_challenge/gen.py`), one row each, with the model family, the parameter count, a
# learning rate, and the trial's score on the **same five development folds** (`fold_0` ... `fold_4`,
# higher is better). The test scores of all 60 trials exist, sealed in `sealed_test_scores.b64`. Your
# manager wants one model and one number: "how good will it be on new data?"
#
# You may look at the test score of **one** trial, once: the one your procedure chooses.
#
# ```bash
# python labs/w3d3_hyperparameter_selection/challenge/reveal_test.py --trial <id>   # logs every call
# ```
#
# Every call is appended to `test_looks.json`, which is part of your submission.
#
# #### Tasks
#
# 1. **Selection procedure.** Implement `choose(trials)` in `selection_rule.py`: return the trial id you
#    would ship and an **honest estimate** of its test score. "Honest" means: averaged over many tables
#    like this one, your estimate equals the true score of the trial you chose. Think about what the
#    chosen trial's own dev mean is, before using it.
# 2. **One look.** Run `reveal_test.py` once for the trial `choose` returns on the shipped table.
# 3. **Optimism simulation.** Implement `simulate_max(k, sigma, n_rep, seed, rho)` in `optimism.py`
#    (docstring there). Then design a small experiment of your own in its `__main__` block: write down
#    what you expect *before* running it, run it, and tabulate the result.
# 4. **Report.** Replace every TODO in `REPORT.md` (one page): your rule and why it suits this table,
#    your pre-look estimate and how it was computed, the look and whether the gap is surprising (in
#    numbers), the simulation, and at least two things you would not conclude.
#
# #### Acceptance criteria

# %%
!python wb.py check w3d3 --challenge

# %% [markdown]
# * Over 200 freshly generated tables, your estimate's average error for the chosen trial is within
#   ±0.008, and your choices are better than picking a trial at random.
# * `choose` is deterministic, does not modify its input and does not depend on row order.
# * `test_looks.json` shows exactly one look, at the trial `choose` selects.
# * `simulate_max` reproduces known expected maxima of normal samples, scales with `sigma`, and responds
#   to `rho` as theory predicts.
# * `REPORT.md` is written (no TODO), with numbers. The written parts are self-assessed with the rubric in
#   `solutions/labs/w3d3_hyperparameter_selection/assessment_answers.md`, after you finish.
#
# If you looked more than once, do not delete the log. Write down what you did and why it invalidates
# the number; that is the more valuable learning outcome.

# %%
# Run the automated checks on your independent challenge.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w3d3", challenge=True)

# %% [markdown]
# ## 6. Progressive hints (open in order, only when stuck)
#
# 1. [Concept](../labs/w3d3_hyperparameter_selection/hints/hint1_concept.md)
# 2. [Approach](../labs/w3d3_hyperparameter_selection/hints/hint2_approach.md)
# 3. [Partial implementation](../labs/w3d3_hyperparameter_selection/hints/hint3_partial.md)
#
# If you open a hint, the work counts as guided, not independent.
#
#
# Open one hint at a time, only after a real attempt.
#
# <details>
# <summary><b>Hint 1 concept</b></summary>
#
#
# * Selection is fitting. Whatever data chose the hyperparameters, the threshold or the winning trial
#   has been *used*, and the score on that data is biased upward for the thing chosen.
# * The number to report is the performance of the **procedure** (search + select + refit), estimated on
#   data the procedure never saw. Nested validation does exactly that: the outer loop wraps the whole
#   procedure, the inner loop is the procedure.
# * "Never saw" has two levels here: rows of the outer fold must not be fitted by any inner model, and
#   they must not be *scored* by any inner model either (scoring is how they would vote for a candidate).
# * Rows outside the folds (test experiments, the reference recording) are never touched by any of this.
# * A threshold is a parameter with one dimension. Choose it on development scores that are themselves
#   out-of-fold, freeze it, apply it once to test.
# * Challenge: the chosen trial's dev mean is the maximum (or near-maximum) of 60 noisy numbers. Ask what
#   you would get if you re-ran your *whole rule* without one fold and scored its choice on that fold.
#
# </details>
#
# <details>
# <summary><b>Hint 2 approach</b></summary>
#
#
# **`param_grid`** - `itertools.product` over the values, in key order; one dict per combination.
# **`sample_params`** - one `np.random.default_rng(seed)`; for each candidate, for each key in a fixed
# order, draw according to the spec. Log-uniform: `exp(uniform(log low, log high))`.
#
# **`grouped_search`** - for candidate i and fold k: training groups = union of the *other folds*
# (not "everything except fold k": the table also holds test rows); build masks with
# `tidy[group_column].isin(...)`; fit a **fresh** estimator from the factory; score fold k with the metric.
# Record `fold_scores`, their mean and SE = sd(ddof=1)/sqrt(n_folds).
#
# **`select_best`** - "max": argmax of means, earliest on ties. "one_se": band = best mean minus the
# best trial's SE; among trials in the band, minimise `complexity(params)`, then maximise the mean.
#
# **`nested_estimate`** - for each outer fold k: `inner = [f for j, f in enumerate(folds) if j != k]`;
# `trials = grouped_search(..., inner, ...)`; `chosen = select_best(trials, rule, complexity)`; refit
# `chosen["params"]` on all rows of the inner folds; score fold k. Report the mean and SE of the outer
# scores, and keep the chosen params and inner best score per fold (they are the interesting part).
#
# **Thresholds** - candidate thresholds are the observed dev scores. For best F1, evaluate each (vectorise
# by sorting); for the alert budget, compute the fraction of normal rows flagged at each candidate and
# take the lowest that satisfies the budget.
#
# **Challenge `choose`** - write a private `_pick(scores, n_params)` that applies your rule to a matrix of
# fold scores. The estimate: for each fold k, `_pick` on the matrix without column k, read that trial's
# score in column k; average.
#
# </details>
#
# <details>
# <summary><b>Hint 3 partial</b></summary>
#
#
# ```python
# def nested_estimate(estimator_factory, candidates, tidy, folds, metric, feature_columns,
#                     label_column="anomaly", group_column="experiment_id", rule="max", complexity=None):
#     if len(folds) < 3:
#         raise ValueError("nested validation needs at least three folds")   # inner search needs two
#     outer_scores, chosen_params, inner_best = [], [], []
#     for k, outer in enumerate(folds):
#         inner_folds = [f for j, f in enumerate(folds) if j != k]
#         trials = grouped_search(estimator_factory, candidates, tidy, inner_folds, metric,
#                                 feature_columns, label_column, group_column)
#         chosen = select_best(trials, rule, complexity)
#         train_groups = [g for f in inner_folds for g in f]
#         score = ...        # refit chosen["params"] on train_groups, score the outer fold
#         outer_scores.append(score)
#         chosen_params.append(chosen["params"])
#         inner_best.append(chosen["mean"])
#     return {...}           # which fields does the docstring promise?
# ```
#
# ```python
# def frozen_threshold_evaluation(dev_scores, dev_labels, test_scores, test_labels, rule="best_f1", budget=None):
#     threshold = select_threshold(dev_scores, dev_labels, rule, budget)   # dev only
#     return {"threshold": threshold, "rule": rule,
#             "dev": evaluate_at_threshold(dev_scores, dev_labels, threshold),
#             "test": evaluate_at_threshold(test_scores, test_labels, threshold)}
# ```
#
# Still yours: the search loop, both selection rules with their tie-breaks, the two threshold rules, and
# in the challenge, the selection rule itself and the nested estimate over the recorded folds.
#
# </details>

# %% [markdown]
# ## 7. Assessment
#
# [`assessment.md`](../labs/w3d3_hyperparameter_selection/assessment.md): six reasoning questions, one design-choice explanation, a rubric, and an
# interview rep (ML fundamentals: regularisation and bias-variance). Automated checks: `checks/` (40 tests)
# and `checks_challenge/` (16 tests), validated against the reference solution and against nine plausible
# wrong submissions.
#
#
# ### Assessment questions
#
#
# Answer in writing before opening `solutions/labs/w3d3_hyperparameter_selection/assessment_answers.md`.
# About 15 minutes for the questions; the interview rep is separate.
#
# #### Reasoning questions
#
# 1. You compare 24 configurations by 4-fold grouped CV; the best scores 0.891 ± 0.015 (SE over folds).
#    Why is 0.891 a biased estimate of that configuration's performance on new experiments, and in which
#    direction? Name two quantities that determine how large the bias is.
# 2. A colleague "does nested CV" like this: run the grid search with grouped 4-fold CV on all development
#    experiments, take the best configuration, then run grouped 4-fold CV of that configuration and report
#    the mean. What is wrong, and what number does this procedure actually estimate?
# 3. In the lab, the four outer folds of the nested estimate chose different model families. Is that a bug?
#    What does it tell you about the search, and about the number you should report?
# 4. Your search space has five hyperparameters and a budget of 32 trials. Argue for random over grid search
#    in two sentences, and say which hyperparameters you would sample on a log scale.
# 5. The decision threshold was chosen as the best-F1 threshold on the *in-sample* scores of the model
#    refitted on all development experiments, then applied to test. What goes wrong, and how does the lab
#    avoid it?
# 6. After seeing the test score, you notice a bug in feature scaling, fix it, rerun, and the test score
#    rises by 0.03. You report the new number. What must the report say, and why?
#
# #### Design-choice explanation (6-10 sentences)
#
# Explain your choice between the "max" and "one-standard-error" selection rules for the project's
# supervised detector. Include: the SE of the top trials relative to the spread of the top means, your
# complexity ordering and why it is the right ordering for a detector that will run online, and what the
# rule does *not* fix about the number you report.
#
# #### Rubric
#
# | Level | Description |
# |---|---|
# | Demonstrated | Separates the estimate of a configuration from the estimate of a procedure; locates every selection step (hyperparameters, family, threshold, post-processing, "best run") and the data it used; quantifies optimism with K, σ and correlation; treats test looks as a budget. |
# | Partial | Correct mechanics of nested CV, but misses one selection step (usually the threshold or the "fix after seeing test") or justifies the one-SE rule only as "simpler is better". |
# | Not yet | Reports the best CV score as expected performance, tunes thresholds on test, or treats nested CV as "CV twice". |
#
# #### Interview rep (ML fundamentals, 12 minutes, spoken)
#
# Answer aloud, then write a 5-line summary:
#
# 1. "Why does L2 regularisation shrink the coefficients of two highly correlated features towards each
#    other, while L1 tends to keep one and zero the other?" Use the geometry of the penalty or the
#    optimality conditions.
# 2. "You increase the regularisation strength and the validation error first falls, then rises. Describe
#    the bias and variance of the estimator along that path, and how you would choose the strength with
#    only 25 independent groups."
#
# Score yourself with the interview rubric in the answers file.

# %% [markdown]
# ## 8. Reflection and review
#
# **You should now be able to do, alone:** identify every selection step in an evaluation and the data it
# used; estimate the optimism of a best-of-K result; implement nested grouped validation and explain what it
# estimates; run a recorded random search; apply the one-SE rule with a justified complexity ordering;
# choose and freeze thresholds on out-of-fold dev scores; keep a test-look budget.
#
# **Reflection prompt** (5 lines, `python wb.py note w3d3 "..."`): in one of your published EEG/iEEG
# results, list every choice that was made after looking at a score (band, channels, window, model,
# threshold, epoch). Which data was each choice made on?
#
# **Retrieval question for later** (w3d7 review and Week 4): you ran 50 configurations, the best has CV
# score 0.81 with SE 0.02 per configuration, and errors are moderately correlated (ρ ≈ 0.5). Roughly how
# much of 0.81 is selection optimism, and what would you compute instead?
#
# **Next.** [w3d4 point versus event evaluation](16_point_vs_event_evaluation.ipynb): the threshold
# you froze today becomes alarms, and the post-processing parameters become two more hyperparameters to
# select on dev.

# %% [markdown]
# ## Verification record
#
# Authored 2026-11-21/22, executed on Python 3.13.18, NumPy 2.5.3, pandas 3.0.5, scikit-learn 1.9.1,
# matplotlib 3.11.2 (figures only), SKAB at commit `b2c0d46`.
#
# * `python tools/verify_checks.py labs/w3d3_hyperparameter_selection`: reference passes lab (40) and
#   challenge (16); 5 lab and 4 challenge mutants rejected.
# * Shipped starter: 40 of 40 lab checks fail; challenge 14 fail, 2 error.
# * Worked example, `selection_report.py` (rerun on the reference solution; numbers above copied from that
#   run), the challenge reference (`selection_rule.py`, `optimism.py`) and `figures/make_figures.py` executed.
# * 2026-11-22: `selection_report.py` switched to the frozen w3d1 manifest (`lab/splits/v2.json`, 7 test
#   experiments) instead of redrawing a split; the search was rerun and every real-SKAB number and the
#   trials figure regenerated from that run.
# * Not verified: time budgets; the industry example is an illustrative composite.

# %% [markdown]
# ## Record your progress
#
# Tick only what is true. Passing the supplied checks is *guided practice*; mark *independent* only for work done without hints or solutions.

# %%
from mlcourse.progress import mark, note

# mark("w3d3", "reading")
# mark("w3d3", "guided")
# mark("w3d3", "independent")
# note("w3d3", "what tripped me up today")

