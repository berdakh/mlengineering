# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/14_group_temporal_validation.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 14 · Group-aware and temporal validation
#
# **Week 3 · day 2 · 2 h essential path + up to 1 h optional** · lab files: [`labs/w3d2_group_temporal_validation/`](../labs/w3d2_group_temporal_validation/)
#
# **Objective.** Design validation that matches deployment: grouped, temporal, and combined (experiment x time) schemes with purging/embargo where windows overlap.

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
# Status: see [STATUS.md](../docs/guides/status.md). Handbook:
# [H6.3](../docs/handbook/ch06_evaluation_leakage_uncertainty/h6_3_group_and_temporal_validation.md),
# [H7.2](../docs/handbook/ch07_timeseries_grouped_modeling/h7_2_purging_and_embargo.md).
# Solutions live in `solutions/labs/w3d2_group_temporal_validation/`; open them after your own attempt.

# %% [markdown]
# ## 1. Purpose
#
# **Objective.** Design validation that matches deployment: choose what a validation number is supposed
# to estimate, then build the grouped, temporal or combined scheme that estimates it, with purging and
# embargo where windows overlap a split boundary.
#
# **Why an applied ML engineer needs it.** Splitting by subject or by user is a familiar first step. In a product the question is
# wider and nobody states it for you: will the model meet new machines, the future of known machines, a
# fault type it never saw, or all three? Each has its own validation scheme and each gives a different
# number for the same model. On the project data, in this session, the same random forest scores a
# pooled ROC-AUC of 0.985, 0.818, 0.689 or 0.487 depending only on how the rows were split. Shipping
# decisions are made on whichever of those numbers ends up in the slide, so choosing the scheme is the
# modelling decision with the largest effect on what you believe.
#
# **Deliverable.** `lab/VALIDATION_DESIGN.md`: the validation design memo for `flowguard`, backed by the
# scheme-comparison table you produce on the real data; and (challenge) a splitter for a store-demand
# scenario with a written justification.
#
# **Prerequisites.** [w3d1](13_leakage.ipynb) (leakage taxonomy; the v2 split manifest that
# keeps overlapping experiments together) and [w2d6](12_baselines_metrics.ipynb) (baseline
# scorers, PR-AUC). Neither needs to be finished: snapshots of `flowguard.data`, `flowguard.splits` (v2),
# `flowguard.baselines` and `flowguard.metrics` are in the lab. SKAB downloaded: `python project/get_skab.py`.
#
# **Time budget (2 h essential).**
#
# | Activity | Minutes |
# |---|---|
# | Read section 2, run the two synthetic examples | 30 |
# | Lab tasks 1-2: `required_purge`, `group_kfold_indices` | 20 |
# | Lab tasks 3-4: `grouped_folds`, `leave_one_family_out` | 20 |
# | Lab tasks 5-6: `purged_time_split`, `forward_chaining_split` | 20 |
# | Lab task 7: run the comparison, write `VALIDATION_DESIGN.md` | 20 |
# | Assessment questions 1-3 | 10 |
# | **Optional extension (up to 1 h):** challenge, remaining questions, interview rep | 60 |

# %% [markdown]
# ## 2. Conceptual explanation
#
# ### 2.1 A validation scheme is an estimator; name its estimand first
#
# Cross-validation is usually introduced as a procedure. It is more useful to treat it as an
# **estimator**, and to ask what it estimates. Write the target down before any code:
#
# > *The expected value of metric M, for a model trained the way I will train it, on data drawn the way
# > deployment will draw it.*
#
# "The way deployment will draw it" is the part that varies. Four common answers:
#
# | Deployment question | What must be unseen in validation | Scheme |
# |---|---|---|
# | New units from the same population (new patient, new pump of the same model) | whole groups | grouped K-fold, leave-one-group-out |
# | The future of units already seen (same pump, next month) | later time | forward chaining (rolling or expanding origin) |
# | Another period of a known unit, not necessarily later (gap filling, retrospective scoring) | a contiguous time block, with a buffer | blocked K-fold with purging and embargo |
# | A regime never seen (new fault type, new site, new product line) | a whole category of groups | leave-one-category-out |
#
# and the combination that most industrial systems actually face: **new units, later**. A scheme that
# holds out less than deployment will withhold is optimistic; one that holds out more is pessimistic.
# Neither is "wrong" as arithmetic. It answers a different question from the one you were asked.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/docs/assets/diagrams/mmd-14-01.svg" alt="Diagram 1 of notebook 14" style="max-width:100%">
#
# A second axis is easy to miss. The estimand "performance of *the model I will ship*" differs from
# "performance of *this training procedure* at this sample size". K-fold estimates the second: each fold
# trains on (K-1)/K of the groups. With 27 experiments and 4 folds that is about 20 experiments instead of 27,
# so the estimate is slightly pessimistic for the final model, and its variance is dominated by which
# few experiments landed in which fold.
#
# ### 2.2 Why i.i.d. K-fold fails under dependence
#
# Random K-fold is unbiased for the i.i.d. estimand because a validation row is, by exchangeability, a
# fresh draw: nothing about it is in the training set. Dependence breaks exactly that. If rows come in
# groups that share something (a subject's anatomy, a machine's sensor gain, an experiment's operating
# point), a validation row's group-mates are in training, and a flexible model can use what they reveal.
#
# Two separate effects follow. Keep them apart, they need different remedies.
#
# **(a) Optimism of the point estimate.** Let the label depend on a group-level effect $u_g$ with
# variance $\sigma_u^2$ and on everything else with variance $\sigma_e^2$. The intraclass correlation
#
# $$\rho = \frac{\sigma_u^2}{\sigma_u^2 + \sigma_e^2}$$
#
# is the share of variation that is "which group is this". Under a row split a model that can identify
# the group recovers $u_g$ from the training rows; on a new group it cannot. The gap between the two is
# the optimism, and it grows with $\rho$ and with model flexibility. The worked example measures it.
# The remedy is to split by group. More data does not help: with more rows per group the model
# identifies groups *better*.
#
# **(b) Overconfidence of the interval.** Even with a correct split, $n$ correlated rows are not $n$
# observations. For $G$ groups of $m$ rows and within-group correlation $\rho_e$ of the per-row
# *correctness*, the variance of a mean is inflated by the **design effect**
#
# $$\mathrm{deff} = 1 + (m - 1)\,\rho_e, \qquad n_\text{eff} = \frac{n}{\mathrm{deff}} .$$
#
# With $m = 1000$ rows per experiment and $\rho_e = 0.2$, deff is about 200: 25,000 rows carry the
# information of about 125, and the honest count is closer to the number of experiments. This is why a
# binomial standard error on row-level accuracy is meaningless here. The remedy is to resample groups,
# not rows (w3d5).
#
# **Connection to other domains.** In studies on people (EEG decoding, wearable sensors, speech) this is
# leave-one-subject-out, and within-subject shuffled splits are rightly distrusted. What transfers less
# obviously: (i) in a study the group is given by the recording protocol; in industry you must *find* it
# (customer, device, site, batch, session, firmware version), and there are often several nested ones;
# (ii) within-subject non-stationarity across sessions has an exact counterpart, the recording day, and
# the project data has it (section 4, task 7).
#
# ### 2.3 Grouped schemes
#
# | Scheme | scikit-learn | Use when | Watch for |
# |---|---|---|---|
# | Grouped K-fold | `GroupKFold` | many groups, want every group validated once | folds balanced by rows, not by class or category |
# | Stratified grouped K-fold | `StratifiedGroupKFold` | class or category balance differs across groups | approximate; impossible to balance exactly with few groups |
# | Leave-one-group-out | `LeaveOneGroupOut` | few groups (roughly under 20), each matters | G model fits; per-fold metrics are noisy and may be undefined (one class) |
# | Leave-one-category-out | none; `LeaveOneGroupOut` with the category as group | must generalise to an unseen regime | folds are few and unequal; it is a stress test, not a tuning signal |
# | Repeated grouped shuffle | `GroupShuffleSplit` | want many train/validation draws | validation sets overlap; do not treat repeats as independent |
#
# **Few groups mean a noisy estimate, whatever the scheme.** With $G$ validated groups and a
# between-group standard deviation $s$ of the per-group metric, the standard error of the mean is about
# $s/\sqrt{G}$. For the project: 27 development experiments, per-fold ROC-AUC between 0.63 and 0.94 in
# the table below. Differences of 0.02 between two models are not resolvable, and no scheme fixes that.
#
# **Frozen folds versus fresh folds.** The manifest from w2d4 fixes which experiment is in which fold.
# That makes every later comparison paired (same folds for every model) and keeps overlap groups
# together by construction. Re-drawing folds per experiment adds a noise source that you then have to
# average away.
#
# ### 2.4 Temporal schemes
#
# When the deployment question is about the future, the validation set must be later than the training
# set. Two shapes:
#
# * **Forward chaining (expanding origin).** Cut time into $K+1$ blocks; fold $k$ trains on blocks
#   $0..k$ and validates on block $k+1$. `TimeSeriesSplit` does this; its `max_train_size` turns it into
#   a **rolling origin** (fixed-length training window), which is the right choice when old data stops
#   being representative. Every fold trains on less than the final model will, and early folds on much
#   less.
# * **Blocked K-fold.** Contiguous validation blocks, training on everything else, including later
#   data. It does *not* estimate forecasting performance. It is appropriate when the task is not
#   forecasting (detecting a state from concurrent sensor values) and time matters only because nearby
#   rows are dependent.
#
# Shuffling destroys both. With `shuffle=True` every validation row has training neighbours one step
# away in time.
#
# Forward chaining with four blocks and a gap, drawn as a timeline (each bar is one fold; "gap" rows are
# in neither set):
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/docs/assets/diagrams/mmd-14-02.svg" alt="Diagram 2 of notebook 14" style="max-width:100%">
#
# ### 2.5 Purging and embargo: how many rows to drop
#
# Contiguous blocks are not enough when rows are built from windows. Let row $i$ have features computed
# from a trailing window of $w$ rows, $[i-w+1,\, i]$, and a label that looks $h$ rows ahead, $[i,\, i+h]$
# ($h = 0$ when the label is a property of row $i$). Row $i$ is then a function of the raw samples
#
# $$S_i = [\,i - w + 1,\; i + h\,].$$
#
# Two rows share raw samples iff their spans intersect, i.e. iff
#
# $$|i - j| \le w - 1 + h .$$
#
# So for a validation block $[a, b]$:
#
# * **purge** the training rows in $[a - (w-1+h),\; a-1]$: their labels and features reach into the block;
# * **embargo** the training rows in $[b+1,\; b + (w-1+h)]$: their feature windows reach back into it.
#
# ```text
# row index  ......|<- purge w-1+h ->|<====== validation block [a, b] ======>|<- embargo w-1+h ->|......
# training   ######|      dropped    |                                       |      dropped      |######
#            a training row here has a label        a training row here has a feature window
#            window reaching into the block         reaching back into the block
# ```
#
# Dropping $w - 1 + h$ rows on each side guarantees that no raw sample is shared, without any argument
# about what the model could exploit. It is a sufficient condition for independence *if the raw samples
# themselves are independent*. They usually are not (sensor signals are autocorrelated), so the buffer
# is a floor: extend it by the correlation length of the signal when you can estimate one. In forward
# chaining there is nothing after the block to embargo, and the purge is the `gap` argument of
# `TimeSeriesSplit`.
#
# What the buffer costs: $2(w-1+h)$ rows per block. With short series and long windows that is most of
# the data, which is itself a finding (the windows are too long for the amount of data).
#
# ### 2.6 Combined schemes and nesting
#
# "New machines, later" needs both conditions at once: validation rows come from groups absent from
# training *and* from a later period, with the label purge applied at the cut-off. The challenge builds
# exactly this. The estimate has two parts worth reporting separately (known units later; new units
# later), because they fail for different reasons and call for different fixes.
#
# Any choice made by looking at validation scores (hyperparameters, thresholds, features, the model
# family) makes those scores optimistic for that choice. The remedy is an outer split that the choice
# never sees: here the manifest's test experiments. [w3d3](15_hyperparameter_selection.ipynb)
# quantifies the size of that optimism.
#
# ### 2.7 A concrete industry example
#
# *Illustrative composite, not a documented incident.* A lender trains a default model on three years
# of loans and validates with shuffled 5-fold: AUC 0.81. Six months after launch the monitored AUC is
# 0.72. Three things were wrong with the scheme, none with the model code: (1) a customer with several
# loans appeared on both sides, and the model had learned customers; (2) the label "defaulted within 12
# months" for loans issued in the last year of data used outcomes that post-dated the validation loans'
# issue dates; (3) underwriting policy changed in year three, so the population the model would score
# was the newest one, which random folds dilute. A scheme that held out the last year, purged twelve
# months of labels before it, and grouped by customer reported 0.73 beforehand.
#
# ### 2.8 Limits and misconceptions
#
# * **"Grouped CV is conservative, so it is safe."** It is unbiased for *new groups from the same
#   population*. If deployment brings a new regime it is still optimistic (table below: 0.818 against
#   0.689 with a family held out).
# * **"TimeSeriesSplit handles time series."** It orders the folds. It does not purge unless you set
#   `gap`, it knows nothing about groups, and it assumes equally spaced rows of one series.
# * **"More folds give a better estimate."** More folds give more training data per fit and more
#   correlated fits. They do not create more independent groups.
# * **"Purging removes temporal leakage."** It removes shared raw samples. Slow drift, a protocol in
#   which the anomaly always starts near row 570 (w2d6), or a recording-day offset are untouched by it.
# * **"The pessimistic number is the true one."** Each scheme estimates a different thing. Report the
#   one that matches the deployment question and say which question that is.

# %% [markdown]
# ## 3. Worked example
#
# Three scripts. The first two are SYNTHETIC and isolate one mechanism each; nothing about real
# equipment can be concluded from them. Outputs below are copied from runs on Python 3.13.18,
# scikit-learn 1.9.1.
#
# ### 3.1 Group dependence: optimism and effective sample size

# %%
!python labs/w3d2_group_temporal_validation/example/group_dependence.py

# %% [markdown]
# **Data.** 20 machines x 100 rows. Columns: `x_signal` (truly predictive everywhere), four
# `fingerprint` features that identify the machine and nothing else, and a binary label that depends on
# `x_signal`, on a machine-level offset $u_g$ and on noise. The ICC of the latent label is set by
# $\sigma_u$. Truth is the accuracy on 300 machines generated afterwards and never seen in any form.
#
# ```
# Part A - optimism of row-wise K-fold as within-machine correlation grows (mean of 5 repetitions)
# | ICC rho | row 5-fold | machine 5-fold | truth: new machines | row optimism |
# |---|---|---|---|---|
# | 0.0 | 0.841 | 0.849 | 0.847 | -0.005 |
# | 0.2 | 0.862 | 0.780 | 0.769 | +0.093 |
# | 0.5 | 0.887 | 0.692 | 0.669 | +0.218 |
# | 0.8 | 0.921 | 0.536 | 0.574 | +0.347 |
# ```
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/labs/w3d2_group_temporal_validation/figures/optimism_vs_icc.svg" alt="Row-wise K-fold accuracy rises with the intraclass correlation while accuracy on new machines falls; machine-wise K-fold follows the truth" width="100%">
#
# *SYNTHETIC. The gap between the orange line and the dashed truth is what a row split would have
# promised and not delivered.*
#
# **Reading it.** With no group effect the two schemes agree and both are right. As $\rho$ grows the
# row-wise number goes *up* while the truth goes *down*: the group effect that makes new machines hard
# is the same thing the model memorises from group-mates. The machine-level estimate tracks the truth
# within a few points; at $\rho = 0.8$ it is 0.04 below it. That direction is expected (each fold trains
# on 16 machines, the final model on 20) but five repetitions do not establish its size.
#
# **Key code decision.** The model is a random forest because the effect needs a learner that can use
# the fingerprint. A linear model on `x_signal` alone would show no optimism, which is the practical
# lesson in reverse: the more flexible your model, the more a row split flatters it.
#
# ```
# Part B - effective sample size: spread of a per-row accuracy over 2,000 simulated test sets
# of 20 machines x 100 rows, when correctness is correlated within a machine (rho_e)
# | rho_e | naive SE sqrt(p(1-p)/n) | simulated SE | ratio^2 (design effect) | 1 + (m-1) rho_e |
# |---|---|---|---|---|
# | 0.00 | 0.0089 | 0.0089 | 1.0 | 1.0 |
# | 0.05 | 0.0089 | 0.0224 | 6.3 | 6.0 |
# | 0.20 | 0.0089 | 0.0405 | 20.5 | 20.8 |
# ```
#
# The simulated inflation matches $1 + (m-1)\rho_e$. A correlation of 0.05, which nobody would notice
# in a plot, makes the naive standard error too small by a factor of 2.5.
#
# ### 3.2 Overlapping windows across a boundary

# %%
!python labs/w3d2_group_temporal_validation/example/purge_demo.py

# %% [markdown]
# **Data.** One series of 6,000 rows. Features are trailing means ($W = 40$) of three slow "context"
# series that are independent of the target; the label is the sign of the mean of white noise over the
# next $H = 30$ rows. The features carry no information, so the true ROC-AUC is exactly 0.5. The model
# is 5-nearest-neighbours, which can match a row to its temporal neighbours through the context features.
#
# ```
# true ROC-AUC = 0.500. W = 40, H = 30, n = 6000; mean and s.d. over 10 seeds
# | scheme | pooled out-of-fold ROC-AUC |
# |---|---|
# | shuffled 5-fold | 0.661 +- 0.010 |
# | blocked, 5 blocks of 1200 rows, no buffer | 0.500 +- 0.016 |
# | blocked, 300 blocks of 20 rows, no buffer | 0.533 +- 0.012 |
# | blocked, 300 blocks, purge = embargo = 10 | 0.504 +- 0.014 |
# | blocked, 300 blocks, purge = 69, embargo = 0 | 0.518 +- 0.013 |
# | blocked, 300 blocks, purge = embargo = 30 (label horizon only) | 0.503 +- 0.015 |
# | blocked, 300 blocks, purge = embargo = 69 (W - 1 + H) | 0.503 +- 0.014 |
# ```
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/labs/w3d2_group_temporal_validation/figures/purge_demo.svg" alt="Dot plot of pooled ROC-AUC per scheme on unpredictable labels: shuffled 0.66, short blocks without buffer 0.53, one-sided purge 0.52, two-sided buffers about 0.50" width="100%">
#
# *SYNTHETIC; the truth is 0.5, so every orange point is leakage. Whiskers: one s.d. over 10 seeds.*
#
# **Reading it, including what it does not show.**
#
# * Shuffling manufactures an AUC of 0.66 from nothing.
# * Blocking alone fixes it when blocks are long (0.500): boundary rows are a negligible share of 1,200.
#   With blocks of 20 rows, as in day-by-day walk-forward evaluation, the boundary is most of the block
#   and the leak is back (0.533).
# * A one-sided buffer leaves half of it (0.518): the embargo is not optional in blocked K-fold.
# * In this construction a buffer of 10 already brings the number within noise of 0.5, and the three
#   two-sided buffers cannot be told apart. The measurable leak here needs similar features *and*
#   similar labels, which decays within a few rows. $W - 1 + H = 69$ is the buffer that guarantees no
#   shared samples regardless of the model; this demo does not show that the full length is *necessary*,
#   and for a specific model it may not be.
#
# ### 3.3 The same question on the real data
#
# This is lab task 7; the table is in section 4 so that you produce it yourself first.

# %% [markdown]
# ## 4. Guided lab
#
# Work in `labs/w3d2_group_temporal_validation/lab/`. Given: `flowguard.data`, `flowguard.splits`
# (v2: `find_overlap_groups`, `make_splits(..., keep_together=...)`), `flowguard.baselines`,
# `flowguard.metrics`, the complete script `compare_schemes.py`, and `splits/v2.json`, the manifest
# repaired and frozen in w3d1 (7 test, 27 development experiments; replace it with your own if you wrote one). You write
# `src/flowguard/validation.py`. You may use scikit-learn splitters inside your functions or write them
# by hand; the checks look only at what the functions return.

# %%
!python wb.py check w3d2

# %% [markdown]
# The starter fails all 29 checks.
#
# **Task 1 - `required_purge(window, horizon=0)`.** Return the number of rows to drop on each side of a
# test block (section 2.5). *Checkpoint:* `required_purge(30) == 29`, `required_purge(40, 30) == 69`.
# *If the property test fails with "a buffer one row shorter should leave shared samples"*, your buffer
# is too long: adjacent means $|i-j| = 1$, and with $w = 1, h = 0$ no buffer is needed.
#
# **Task 2 - `group_kfold_indices(groups, n_splits, seed=0)`.** Row-position folds in which no group is
# split and every group is validated once; the assignment depends on `seed`. *Checkpoint:* the planted
# check prints nothing when it passes; to see the numbers, run the body of
# `test_grouped_estimate_recovers_truth_where_row_kfold_is_optimistic` in a REPL: row-wise about 0.89,
# truth about 0.63, yours between 0.60 and 0.70. *Debugging:* if yours is near 0.89 you are folding
# rows; `np.unique(groups[train])` and `np.unique(groups[val])` must be disjoint.
#
# **Task 3 - `grouped_folds(manifest)`.** `(train_ids, val_ids)` per development fold, and a
# `ValueError` for a manifest that is unsafe: a test or reference experiment inside a fold, or an
# overlap group whose members sit in different folds. *Why raise instead of repair:* a splitter that
# silently "fixes" a manifest hides the fact that the frozen file is wrong. *Checkpoint:*
#
# ```python
# from flowguard.data import load_raw
# from flowguard.splits import load_splits
# from flowguard.validation import grouped_folds
# m = load_splits("splits/v2.json")                     # from the lab directory: the w3d1 manifest
# print([(len(tr), len(va)) for tr, va in grouped_folds(m)])      # [(20, 7), (19, 8), (21, 6), (21, 6)]
# ```
#
# **Task 4 - `leave_one_family_out(tidy, keep_together=None)`.** One fold per labelled family. An
# experiment that shares an overlap group with a held-out experiment is *dropped* from training, not
# moved: moving it would put a different family into validation. *Checkpoint (real data, all 34
# labelled experiments):* `other` 20 train / 14 val, `valve1` 18 / 16, `valve2` 30 / 4.
#
# **Task 5 - `purged_time_split(n, n_splits, purge=0, embargo=0)`.** Contiguous test blocks in time
# order that cover `range(n)` once; training excludes the block, `purge` rows before it and `embargo`
# rows after it. *Checkpoint:* `purged_time_split(20, 4, 2, 1)[1]` trains on `[0, 1, 2, 11, ..., 19]`
# and tests on `[5, ..., 9]`. *Debugging:* off-by-one errors live at the block edges; write the expected
# training set for one block by hand before reading the assertion message.
#
# **Task 6 - `forward_chaining_split(n, n_splits, gap=0)`.** `n_splits + 1` contiguous blocks; fold k
# tests on block k+1 and trains on rows `0 .. start - gap - 1`. Raise if the gap leaves nothing to
# train on. *Checkpoint:* `forward_chaining_split(20, 3, 2)` gives training sizes 3, 8, 13.
#
# **Task 7 - run the comparison and write the memo.**

# %%
!python labs/w3d2_group_temporal_validation/lab/compare_schemes.py

# %% [markdown]
# Expected output (reference run; yours should match to the third decimal on the same library versions):
#
# ```
# development pool: 27 experiments, 27342 usable rows, positive fraction 0.387; test experiments not opened
#
# ### random forest on raw sensor values
#
# | scheme | folds | pooled PR-AUC | pooled ROC-AUC | ROC-AUC per fold |
# |---|---|---|---|---|
# | 1 rows, shuffled 4-fold | 4 | 0.981 | 0.985 | 0: 0.985, 1: 0.984, 2: 0.986, 3: 0.985 |
# | 2 time blocks within experiment, no buffer | 4 | 0.915 | 0.922 | block 0: 0.949, block 1: 0.862, block 2: 0.865, block 3: 0.886 |
# | 3 time blocks within experiment, purge = embargo = 29 | 4 | 0.890 | 0.896 | block 0: 0.951, block 1: 0.859, block 2: 0.821, block 3: 0.881 |
# | 4 experiments held out (manifest folds) | 4 | 0.820 | 0.818 | fold 0: 0.856, fold 1: 0.626, fold 2: 0.938, fold 3: 0.862 |
# | 5 one family held out | 3 | 0.685 | 0.689 | other: 0.529, valve1: 0.875, valve2: 0.910 |
# | 6 forward by recording day | 2 | 0.382 | 0.487 | train 1 day(s) -> 2020-03-01: 0.485, train 2 day(s) -> 2020-03-09: 0.497 |
#
# ### logistic regression on burn-in z + rolling mean
#
# | scheme | folds | pooled PR-AUC | pooled ROC-AUC | ROC-AUC per fold |
# |---|---|---|---|---|
# | 1 rows, shuffled 4-fold | 4 | 0.837 | 0.867 | 0: 0.870, 1: 0.859, 2: 0.871, 3: 0.866 |
# | 2 time blocks within experiment, no buffer | 4 | 0.720 | 0.746 | block 0: 0.915, block 1: 0.725, block 2: 0.906, block 3: 0.849 |
# | 3 time blocks within experiment, purge = embargo = 29 | 4 | 0.687 | 0.704 | block 0: 0.913, block 1: 0.723, block 2: 0.894, block 3: 0.851 |
# | 4 experiments held out (manifest folds) | 4 | 0.787 | 0.814 | fold 0: 0.813, fold 1: 0.758, fold 2: 0.879, fold 3: 0.883 |
# | 5 one family held out | 3 | 0.689 | 0.743 | other: 0.653, valve1: 0.814, valve2: 0.902 |
# | 6 forward by recording day | 2 | 0.637 | 0.727 | train 1 day(s) -> 2020-03-01: 0.478, train 2 day(s) -> 2020-03-09: 0.789 |
# ```
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/labs/w3d2_group_temporal_validation/figures/skab_schemes.svg" alt="Two panels, one per model: pooled ROC-AUC under six schemes with per-fold dots; the forest falls from 0.985 (rows shuffled) to 0.818 (experiments held out) and 0.689 (family held out)" width="100%">
#
# *Real SKAB development experiments. Small grey dots are folds; their spread is the honest size of the
# uncertainty you are working with.*
#
# Facts you need to read the table. The experiments were recorded on three days: 2020-02-08 (`other/5`
# to `other/14` and the fault-free run), 2020-03-01 (`other/1` to `other/4`), 2020-03-09 (all of
# `valve1` and `valve2`). So **family and recording day are confounded**: scheme 5 and scheme 6 both mix
# "new fault mechanism" with "another day". Block 0 (the first quarter of each experiment) contains
# anomalous rows in one development experiment only, `other/2`, whose anomaly starts at row 104; block 0's
# per-fold value therefore rests on one experiment. In the development pool 2020-03-01 is three
# experiments, `other/2`, `other/3`, `other/4`, which form one overlap group: scheme 6's first fold
# validates on what is effectively one recording, and a per-fold value on one recording is an anecdote.
#
# Then fill in `lab/VALIDATION_DESIGN.md`. It asks for: the deployment question in one sentence, the
# estimand, the primary scheme and why the others are rejected or kept as stress tests, what each number
# in your table does and does not support, the purge you would apply and its derivation, and the known
# weaknesses of the design. It is graded with the rubric at the end of the template. Things to work out
# yourself before reading the reference memo:
#
# * Why does the raw-sensor forest lose 0.17 between scheme 1 and scheme 4, and the burn-in logistic
#   regression only 0.05?
# * For the logistic regression the pooled ROC-AUC of scheme 3 (0.704) is *below every per-fold value*,
#   and that of scheme 2 below all but one.
#   What does that say about scores from different folds, and why would time blocks cause it here?
# * Which rows of the table can be compared with each other at all?
#
# **Completion criteria.** All 29 checks pass; `compare_schemes.py` runs; the memo is filled in and
# names one primary scheme, with the evidence for it and at least two stated limitations.

# %%
# Run the automated checks on your guided lab.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w3d2")

# %% [markdown]
# ## 5. Independent challenge
#
# A retail chain that keeps opening stores retrains a demand model every quarter and uses it for the
# following eight weeks, for existing stores and for stores opened since. Design and implement the
# validation splitter that answers that question, on a SYNTHETIC store x week panel, and justify it in
# writing. Task, data schema and acceptance criteria:
# [challenge/README.md](../labs/w3d2_group_temporal_validation/challenge/README.md). No solution is given there.

# %%
!python wb.py check w3d2 --challenge

# %% [markdown]
# ### The challenge brief
#
#
# **Time:** about 45 minutes (optional extension). Work without opening `solutions/`.
#
# #### Situation
#
# A retail chain retrains its demand model at the end of every quarter and uses it for the next
# **eight weeks**: for stores that already exist and for stores that open during that time. The model
# predicts, for a store in week *t*, the total demand over weeks *t+1 .. t+4* (`demand_next4`).
#
# The data team validated with a random 80/20 split of store-weeks and reports an error that the
# business finds too good to be true. Design the validation that answers the deployment question, and
# implement it.
#
# #### Data (SYNTHETIC)
#
# `data/store_panel.csv`, generated by `data/make_panel.py` (seeded). One row per store and week; row
# order carries no meaning. Nothing about real retail demand can be concluded from it; it isolates two
# mechanisms (overlapping label windows and store identity).
#
# | Column | Meaning |
# |---|---|
# | `store_id` | `S000` ... |
# | `week` | 0 ... 103 |
# | `opened_week` | first week of the store |
# | `fp_1`, `fp_2`, `fp_3` | store attributes (location, size, format); constant per store, so they identify it |
# | `demand` | demand in the week |
# | `demand_next4` | label: demand summed over the next four weeks; empty when those weeks do not all exist |
#
# #### Task
#
# 1. Write the deployment question as one sentence and derive what must be unseen at validation time:
#    which rows may train a model that is retrained at the end of week *c*, which rows it will be used on,
#    and what distinguishes a "known" from a "new" store **from the model's point of view**.
# 2. Implement `deployment_folds(panel, cutoffs, horizon_weeks=8, label_weeks=4)` in
#    `store_validation.py` (signature fixed; contract in its docstring). One fold per cut-off, with three
#    sorted arrays of row positions: `train`, `val_known`, `val_new`. Raise `ValueError` for a cut-off that
#    leaves no training or no validation rows.
# 3. Write `JUSTIFICATION.md` next to the code (half a page): the deployment sentence, the rule for each
#    of the three sets, the buffer you applied and why it has that size, and why the random split's number
#    was too good. Report errors for known and new stores separately; say why one pooled number would
#    mislead.
#
# #### Acceptance criteria (checked by `python wb.py check w3d2 --challenge`, on re-seeded panels)
#
# * One fold per cut-off, in order; integer row positions, sorted, disjoint; all three sets non-empty for
#   the given cut-offs.
# * No training label uses demand from after the cut-off, and *every* label that was fully observed at the
#   cut-off is used for training (the model is retrained on all available history).
# * Validation is exactly the labelled store-weeks of the eight weeks after the cut-off.
# * `val_known` contains only stores with training rows; `val_new` only stores without.
# * A planted chain-wide weekly shock is not predictable from training labels (detects label windows that
#   overlap the validation period).
# * A store-memorising model has a clearly larger error on `val_new` than on `val_known` (detects "new"
#   defined by something other than what the model has seen).
# * Impossible cut-offs raise `ValueError`.
# * `JUSTIFICATION.md` is graded with the rubric in the solutions after you have written it.

# %%
# Run the automated checks on your independent challenge.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w3d2", challenge=True)

# %% [markdown]
# ## 6. Progressive hints
#
# Open in order, and only after a real attempt.
#
# 1. [Concept](../labs/w3d2_group_temporal_validation/hints/hint1_concept.md) - what each part of the deployment sentence withholds.
# 2. [Approach](../labs/w3d2_group_temporal_validation/hints/hint2_approach.md) - the order in which to build the masks, and how to test them.
# 3. [Partial implementation](../labs/w3d2_group_temporal_validation/hints/hint3_partial.md) - the skeleton with the two decisive lines left out.
#
# The full reference is in `solutions/labs/w3d2_group_temporal_validation/`.
#
#
# Open one hint at a time, only after a real attempt.
#
# <details>
# <summary><b>Hint 1 concept</b></summary>
#
#
# Each phrase of a deployment sentence withholds something:
#
# | Phrase | What validation must withhold |
# |---|---|
# | "new pumps / new stores / new patients" | every row of the validation units from training (grouping) |
# | "next month / the following eight weeks" | everything after the cut-off from training (time) |
# | "retrained at the end of the quarter" | labels not yet *observed* at the cut-off, even if the row's own date is earlier |
# | "a fault type it never saw" | a whole category of units (leave-one-category-out) |
#
# For the lab: the project's deployment question is about new experiments (new pumps or runs) of known
# fault families, with a stress test for an unseen family. Rows from one experiment share its operating
# point and sensor offsets, so they are not independent.
#
# For buffers: a row's information comes from a span of raw samples, $[i-w+1, i+h]$. Two rows are
# dependent through shared samples when their spans intersect. Count the rows you must drop so that no
# training span touches a validation span.
#
# For the challenge: a "known" store is one the *model* has seen, not one the *business* considers old.
#
# </details>
#
# <details>
# <summary><b>Hint 2 approach</b></summary>
#
#
# **Lab.**
#
# 1. `required_purge`: spans intersect iff $|i-j| \le w - 1 + h$, so drop that many rows on each side.
# 2. `group_kfold_indices`: shuffle the *unique groups* with the seed, deal them into folds, then map back
#    to rows. Assert in a REPL that the group sets of train and validation are disjoint.
# 3. `grouped_folds`: read the folds from the manifest; before returning, raise if any test or reference
#    experiment appears in a fold, or if an overlap group's members are spread over folds.
# 4. `leave_one_family_out`: for each family, validation = its experiments; training = the other
#    labelled experiments *minus* any that share an overlap group with a validation experiment.
# 5. `purged_time_split`: `np.array_split(np.arange(n), n_splits)` gives the blocks; training is
#    everything outside `[start - purge, end + embargo]`.
# 6. `forward_chaining_split`: `n_splits + 1` blocks; fold k validates block k+1 and trains on
#    `0 .. start - gap - 1`.
#
# Write one property test per function before running the checks: blocks cover `range(n)` exactly once;
# no training index within the buffer; group sets disjoint.
#
# **Challenge.** Three boolean masks per cut-off *c*, on rows with a label:
# `train = week + label_weeks <= c`; validation = `c < week <= c + horizon_weeks`; split validation by
# whether the store appears in `train`. Then check the planted-shock property yourself: if training
# labels end at week *c* rather than *c - 4*, the last training labels share weeks with the first
# validation labels.
#
# </details>
#
# <details>
# <summary><b>Hint 3 partial</b></summary>
#
#
# ```python
# def required_purge(window, horizon=0):
#     return window - 1 + horizon
#
#
# def purged_time_split(n, n_splits, purge=0, embargo=0):
#     folds = []
#     for block in np.array_split(np.arange(n), n_splits):
#         start, end = int(block[0]), int(block[-1])
#         keep = np.ones(n, dtype=bool)
#         keep[max(0, start - purge): end + embargo + 1] = False
#         folds.append((np.flatnonzero(keep), block))
#     return folds
#
#
# def leave_one_family_out(tidy, keep_together=None, ...):
#     labelled = ...                                     # experiments with family != "anomaly-free"
#     for family in sorted(...):
#         val = [e for e in labelled if family_of[e] == family]
#         blocked = set()                                # experiments sharing a group with val
#         for group in keep_together or []:
#             if group & set(val):
#                 blocked |= set(group)
#         train = [e for e in labelled if e not in val and e not in blocked]
#         ...
# ```
#
# Challenge skeleton:
#
# ```python
# for c in cutoffs:
#     train = has_label & (week + label_weeks <= c)
#     val = has_label & (week > c) & (week <= c + horizon_weeks)
#     if not train.any() or not val.any():
#         raise ValueError(...)
#     known = np.isin(store, ...)                        # stores with at least one TRAINING row
#     folds.append({"cutoff": int(c), "train": position[train],
#                   "val_known": ..., "val_new": ...})
# ```
#
# </details>

# %% [markdown]
# ## 7. Assessment
#
# assessment.md (section 7 of this notebook): six reasoning questions, a design-choice explanation, a rubric, and
# an interview rep (validation and leakage). Model answers and common incorrect answers are in
# `solutions/labs/w3d2_group_temporal_validation/assessment_answers.md`.
#
#
# ### Assessment questions
#
#
# Answer in writing before opening `solutions/labs/w3d2_group_temporal_validation/assessment_answers.md`.
# Questions 1-3 are on the essential path (10 minutes).
#
# #### Reasoning questions
#
# 1. A model will score sensor windows from *new* machines next quarter. Name the scheme you would use and
#    what it must withhold. Which single scheme would you add as a stress test, and what would a large drop
#    on it mean?
# 2. Features use a 60-row trailing window; the label is "a fault occurs within the next 15 rows". You use
#    blocked K-fold within each machine. How many rows do you purge and embargo on each side, and what does
#    that buffer *not* protect against?
# 3. On SKAB, scheme 1 gives 0.985 and scheme 4 gives 0.818 for the forest. A colleague says "the forest
#    overfits; use stronger regularisation". What is the better explanation, and which experiment would
#    distinguish the two?
# 4. 25,000 rows from 25 experiments, row-level accuracy 0.90. Someone reports a 95 % interval of
#    ±0.004. With within-experiment correlation of correctness $\rho_e = 0.1$ and about 1,000 rows per
#    experiment, what is the design effect, and roughly how wide should the interval be?
# 5. Why does `TimeSeriesSplit(gap=0)` not solve the label-overlap problem, and what does `gap` correspond
#    to in section 2.5's notation?
# 6. In the challenge, why is "opened within the last 26 weeks" the wrong definition of a new store, even
#    though it is what the business calls a new store?
#
# #### Design-choice explanation (graded)
#
# 7. Your validation memo picked scheme 4 as primary and scheme 5 as a stress test. A manager asks you to
#    report "the most conservative number" (scheme 6, 0.487 for the forest) in the product review. Write
#    the reply (5-8 sentences).
#
# ##### Rubric for question 7
#
# | Level | Description |
# |---|---|
# | Strong | Explains that schemes estimate different quantities and that "conservative" is not a criterion; shows why scheme 6 is uninformative here (two folds, day confounded with family, first fold on one overlap group); offers what the review needs: the primary estimate with its uncertainty and the stress-test result as a stated risk |
# | Adequate | Correct that scheme 6 answers a different question, without the specific reasons it is unreliable |
# | Weak | Agrees to report the lowest number "to be safe", or dismisses scheme 6 because it is low |
#
# #### Interview rep (validation and leakage, 15 minutes, spoken)
#
# > "We forecast hourly electricity demand per building for the next 24 hours. Our data science team
# > reports MAPE 3 % with 5-fold cross-validation on two years of hourly data from 400 buildings. We plan
# > to roll the model out to 2,000 new buildings next month. How would you validate it?"
#
# Cover: the deployment sentence, what must be withheld (time *and* buildings), the gap or purge for a
# 24-hour horizon and lagged features, seasonality in fold design, what you would report and in how many
# numbers. Self-score with the rubric in the answers file.

# %% [markdown]
# ## 8. Reflection and review
#
# **You should now be able to, without help:**
#
# * state the estimand of a validation scheme and pick the scheme from a deployment sentence;
# * explain with $\rho$ and the design effect why row-wise K-fold is optimistic and why its error bars are too narrow;
# * derive the purge and embargo for a given feature window and label horizon;
# * implement grouped, family-held-out, purged-block and forward-chaining splitters and test them;
# * read a table of schemes and say which differences are leakage, which are distribution shift, and which are noise.
#
# **Reflection prompt (5 minutes, in `progress/notes.md`).** In your own published cross-subject
# results, was there a second grouping variable (session, site, amplifier, recording day) that the
# validation did not hold out? What would the deployment sentence for that work have been?
#
# **Retrieval question for later (answer from memory on the light day).** A row uses a 60-row trailing
# feature window and a label defined over the next 15 rows. How many training rows do you drop on each
# side of a validation block, and what does that buffer *not* protect against?
#
# **Next.** [w3d3 - hyperparameter and threshold selection without fooling yourself](15_hyperparameter_selection.ipynb):
# the folds built here become the inner loop, and the question is how much choosing on them inflates them.

# %% [markdown]
# ## Verification record
#
# Executed 2026-11-22 on Python 3.13.18, NumPy 2.5.3, pandas 3.0.5, scikit-learn 1.9.1: both example
# scripts; `compare_schemes.py` on the 35 downloaded SKAB files with the repaired v2 manifest from w3d1
# (development experiments only); `figures/make_figures.py`;
# `python tools/verify_checks.py labs/w3d2_group_temporal_validation` for both parts. Not verified:
# Python 3.11/3.12 (CI only), time boxes, and the explanations offered for the real-data table beyond
# the checks described in the reference memo.

# %% [markdown]
# ## Record your progress
#
# Tick only what is true. Passing the supplied checks is *guided practice*; mark *independent* only for work done without hints or solutions.

# %%
from mlcourse.progress import mark, note

# mark("w3d2", "reading")
# mark("w3d2", "guided")
# mark("w3d2", "independent")
# note("w3d2", "what tripped me up today")

