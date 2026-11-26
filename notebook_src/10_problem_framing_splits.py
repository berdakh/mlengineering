# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/10_problem_framing_splits.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 10 · Problem framing and versioned split definitions
#
# **Week 2 · day 4 · 2 h essential path + up to 1 h optional** · lab files: [`labs/w2d4_problem_framing_splits/`](../labs/w2d4_problem_framing_splits/)
#
# **Objective.** Translate the stakeholder problem into an ML task: unit of prediction, label definition (point vs event), costs of errors, constraints; freeze splits by experiment and time in a versioned manifest.

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
# **Unit id:** `w2d4` · **Week 2, day 4** · **Content status:** Execution verified (see Verification record)
# **Handbook:** [H1.1 From stakeholder need to prediction target](../docs/handbook/ch01_problem_formulation/h1_1_stakeholder_need_to_prediction_target.md) ·
# [H1.2 Units, labels, costs and constraints](../docs/handbook/ch01_problem_formulation/h1_2_units_labels_costs_constraints.md) · H6.1 Leakage taxonomy (planned, w3d1)
# **Data:** the lab uses the real SKAB recordings (`python project/get_skab.py`, GPL-3.0, not redistributed).
# The worked example parts 1–3, all checks and the challenge table are SYNTHETIC and say so where they appear.
#
# ---

# %% [markdown]
# ## 1. Purpose
#
# **Primary objective.** Turn a stakeholder's need into an ML task you can defend, in writing, and
# freeze the evaluation splits for the portfolio project in a versioned manifest that code can validate.
#
# **What you will learn**
#
# - A ten-item framing worksheet: decision, unit, prediction time and horizon, label, error costs,
#   constraints, metric chain, baseline, splits, out of scope.
# - Why the available labels and sampling structure, not model preference, decide between forecasting,
#   classification and anomaly detection on the same sensor stream.
# - How to derive the unit of splitting from the deployment situation, and why a split is *data*
#   (a manifest under version control) and not a seed in code.
# - What must not change once the first result has been computed.
#
# **Why an applied ML engineer needs it.** Most failed ML projects fail before any model is trained:
# the wrong thing is predicted, at a time when it cannot be acted on, measured by a number nobody's
# decision depends on. In interviews, "how would you approach X?" is this lesson; candidates who jump
# to architectures are marked down for it. Coursework and research usually hand you the task
# pre-framed (a benchmark, a label file, a community-standard metric). In industry you write the frame.
#
# **Prerequisites.** [W2D3](09_data_quality_ingestion.ipynb) (ingestion; the lab ships the `flowguard.data`
# snapshot it needs, so you can proceed without it) and the downloaded SKAB files. From Week 1: a
# src-layout package and pytest. Grouped evaluation is introduced here and deepened in Week 3.
#
# **Time budget — essential path 2 h**
#
# | Activity | Time |
# |---|---|
# | Read sections 1–2 | 30 min |
# | Worked example: run both scripts, read the output against section 3 | 15 min |
# | Guided lab, tasks 1–5 (the split) | 45 min |
# | Guided lab, task 6 (problem statement) | 20 min |
# | Assessment Q1–Q5 | 10 min |
#
# **Optional extension — up to 1 h:** independent challenge (40–50 min), interview rep (10–15 min).
#
# ---

# %% [markdown]
# ## 2. Conceptual explanation
#
# ### 2.1 Intuition: a model is an input to somebody's decision
#
# A prediction has no value of its own. It has value when some person or system *does something
# different* because of it. Framing is the act of writing down that causal chain precisely enough that
# each link can be checked:
#
# ```
# need  ->  decision  ->  prediction that would change the decision  ->  label that defines "right"
#       ->  costs of being wrong  ->  metric that tracks those costs  ->  evaluation that mimics deployment
# ```
#
# Read from the left, it is a design procedure. Read from the right, it is an audit: an evaluation that
# does not mimic deployment makes the metric meaningless, a metric that ignores costs makes model
# selection arbitrary, and so on back to "nobody needed this".
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-10-01.svg" alt="Diagram 1 of notebook 10" style="max-width:100%">
#
#
# ### 2.2 The worksheet, with precise terms
#
# | # | Item | The question | Typical failure |
# |---|---|---|---|
# | 1 | **Decision supported** | Who does what differently, compared with today? | "Predict churn" (a model, not a decision) |
# | 2 | **Unit of prediction** | One output per what? | Unit of prediction confused with unit of decision or of generalisation |
# | 3 | **Prediction time and horizon** | At what moment, about which time span, with information up to when? | Features that did not exist at prediction time |
# | 4 | **Label definition** | What exactly is a positive, who says so, how late, how wrong? | Label taken as ground truth; delay ignored |
# | 5 | **Cost of errors** | What does each error type cost, to whom? | "Maximise F1" with no cost argument |
# | 6 | **Constraints** | Latency, compute, cold start, interpretability, data rights | Discovered after the model is built |
# | 7 | **Success metric chain** | Business quantity → operational proxy → development metric | Optimising the last without checking it tracks the first |
# | 8 | **Baseline** | Result of doing nothing; result of the rule an expert would write | Comparing only against other models |
# | 9 | **Splits** | What does a deployed model meet that it has not seen? | Random row split |
# | 10 | **Out of scope** | Which nearby questions will this *not* answer? | Scope creep; over-claiming |
#
# Three units are routinely conflated; keep them apart.
#
# - **Unit of prediction:** what one model output refers to (a timestamp, a window, a customer-month).
# - **Unit of decision:** what the user acts on (an alert, a call list). Often coarser; many predictions
#   feed one decision.
# - **Unit of generalisation:** what is new at deployment (a recording, a patient, a future month). This
#   one determines the split.
#
# ### 2.3 Costs turn into thresholds and metrics
#
# If a score `s` is a calibrated probability of the positive class and acting on a negative costs
# `c_FP` while failing to act on a positive costs `c_FN`, act when the expected cost of acting is lower:
#
# ```
# (1 - s) * c_FP  <  s * c_FN      <=>      s  >  c_FP / (c_FP + c_FN)
# ```
#
# A ten-to-one cost ratio puts the threshold near 0.09, not 0.5. Two consequences: a stated cost ratio,
# however rough, is more useful than a tuned F1 (F1 silently assumes a particular trade-off); and when
# capacity rather than cost binds ("we can make 500 calls"), the decision is a top-k selection and the
# matching metric is precision/recall at k.
#
# Assumptions hidden in that formula: calibrated scores, costs that do not depend on the instance, and
# independent decisions. Alert streams violate the last one (the tenth alert in an hour is worth less
# than the first), which is why detection problems are scored per *event* (w3d4).
#
# ### 2.4 One sensor stream, three framings
#
# The eight SKAB sensors sampled each second admit at least three tasks.
#
# | Framing | Output | Labels needed | Fits when | Fails when |
# |---|---|---|---|---|
# | Forecasting | future sensor values | none beyond the signal | a decision depends on a future *value*; or as a source of residuals | nobody acts on the forecast itself |
# | Supervised classification | P(fault) per window | positives **and** negatives for each fault form expected | faults recur in known forms with enough labelled episodes | new fault mechanisms appear (silent failure) |
# | Anomaly detection | deviation from learned normal | verified-normal data; fault labels only to evaluate | faults are rare, varied, or novel | "normal" changes legitimately (new operating mode) |
#
# What decides is in the data description, not in taste: SKAB has per-sample fault labels (so
# classification is *possible*), one episode per recording and three families with different mechanisms
# (so generalisation across fault types is the open question), and a designated fault-free recording
# (so learning "normal" is supported). There is no future quantity anyone wants (so forecasting is at
# most a means). Protocol B in the split exists precisely to test the classification framing's weak point.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-10-02.svg" alt="Diagram 2 of notebook 10" style="max-width:100%">
#
#
# ### 2.5 From medical event detection to equipment, and where the analogy breaks
#
# A well-studied neighbour is seizure detection in EEG recordings. Comparing the two frames:
#
# | Seizure detection (EEG) | Fault detection on SKAB | Where it breaks |
# |---|---|---|
# | Patient is the unit of generalisation | Experiment (recording) is the unit | All SKAB recordings come from *one* testbed. There is no analogue of "new patient": cross-installation generalisation cannot be tested at all |
# | Expert annotation of onset, with inter-rater disagreement | Label marks when the experimenter applied the cause | The protocol timestamp precedes the visible effect; early "positives" may be undetectable in principle |
# | Event sensitivity, false detections per hour, latency | Event recall, false alerts per hour, detection delay | Same structure. The costs differ: a clinical false alarm burdens staff, an industrial one stops production |
# | Interictal baseline for normalisation | Fault-free recording for reference statistics | One reference recording, from one day; "normal" is narrower than in multi-day EEG |
# | Montage / hardware differences across sites | Sensor recalibration, different installations | Industrial drift is often deliberate and documented outside the data (a set-point change) |
#
# The habit that transfers intact: *never split below the level at which samples are exchangeable.*
# The habit that does not: reaching for the subject-wise split by reflex. In industry the recurring
# entity is often supposed to be in both train and test (the same 200 shops next quarter), and the
# thing that is new is *time*. Derive the unit; do not assume it.
#
# ### 2.6 Splits: why the experiment, and why a file
#
# **Why the experiment.** Consecutive samples in a recording are strongly dependent. With `m` samples
# per group and within-group correlation `ρ`, the information in `n` samples is roughly that of
#
# ```
# n_eff = n / (1 + (m - 1) * ρ)
# ```
#
# independent ones (the design effect). With about 1,100 rows per experiment and `ρ` far from zero,
# 34 recordings are much closer to 34 observations than to 37,401. A row-level split puts
# near-duplicates of every test row in the training set, so it measures interpolation within a
# recording, which deployment never asks for.
#
# **Structure of the manifest** (`splits/v1.json`, [spec](../docs/maintainers/flowguard-spec.md)):
#
# - `test`: whole experiments, stratified by family, opened for final reporting only;
# - `dev_folds`: the rest, in grouped folds, for every modelling choice;
# - `reference_normal`: the fault-free recording; used to learn "normal", never scored for recall;
# - `protocol_b`: hold out the whole `other` family, to estimate behaviour on unseen fault mechanisms.
#
# **Why stratify groups.** With a small family (`valve2`: 4 experiments), an unstratified draw omits it
# from the test set in about 27 % of draws (9 of 34 drawn without regard to family:
# `C(30,9)/C(34,9) = 0.27`), and the headline number then says nothing about it.
#
# **Why a file and not a seed.** `GroupShuffleSplit(random_state=0)` is a function of the seed *and of
# the list of groups*. Add one recording, change the order in which files are listed, or upgrade the
# library, and "the same split" is a different split; experiments that were test become training data
# and old results stop being comparable without anyone deciding so. A manifest is the decision itself:
# it can be diffed, reviewed, hashed, and validated against the data. The seed stays in the manifest as
# provenance, not as the definition.
#
# **What is frozen after the first result.** Membership of the test set; the definition of an event and
# of the metrics; the rule for excluding data. Changing any of them afterwards is legitimate only as a
# new version, with every reported number recomputed and labelled with the version.
#
# **How much the test set can tell you.** Event recall estimated from `n` events has standard error
# `sqrt(p(1-p)/n)`. With the 9 test events of the reference split and true recall 0.8 that is 0.13: a
# 95 % interval of roughly 0.5 to 1.0. This is not a flaw of the split; it is the size of the dataset
# stated honestly, and it is why w3d5 attaches intervals to everything.
#
# The reference manifest drawn as a grid. Each numbered cell is one experiment; its colour is its only role.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/labs/w2d4_problem_framing_splits/figures/split_layout.svg" alt="Grid of the 34 labelled experiments by family: 9 in the test set, the other 25 in four development folds, each family represented in the test set" width="100%">
#
# *Real experiment ids from `splits/v1.json`: 4 + 1 + 4 test experiments, and development folds of
# 7/6/6/6. (This is manifest v1; w3d1 revises it so that experiments sharing duplicated rows stay together.)*
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/labs/w2d4_problem_framing_splits/figures/recall_interval.svg" alt="Interval plot: a 95 percent interval around a true recall of 0.8 is plus or minus 0.26 with 9 test events and plus or minus 0.13 with 34" width="100%">
#
# *What nine test events can tell you. The formula is the one above; the upper ends are clipped at 1.
# No data is involved, only arithmetic.*
#
#
# ### 2.7 A concrete industry example
#
# A logistics company asks for "a model that predicts late deliveries". Framing questions change the
# project: the dispatcher can only re-route *before* a van leaves the depot, so prediction time is
# loading, not en route; GPS features from the journey are unavailable then (they would have produced a
# spectacular offline score); "late" is recorded by drivers pressing a button, often in batches at the
# end of the shift, so label timestamps are unreliable; the depot can re-plan about 30 routes a day, so
# the metric is precision in the top 30, and the baseline is "routes with more than 40 stops". The
# split is by day (future days are new; drivers and postcodes recur). None of this involves choosing a model.
#
# ### 2.8 Limitations and common misconceptions
#
# - **"Framing is a preamble; the real work is modelling."** The frame determines the ceiling. No model
#   recovers from predicting at a time when action is impossible.
# - **"Grouped splitting is always right."** It is right when groups are new at deployment. See 2.5.
# - **"A fixed seed makes the split reproducible."** Only while the group list, its order and the
#   library are unchanged (worked example, part 2).
# - **"The test set shows the true performance."** It shows one estimate with an interval; on 9 events
#   the interval is wide.
# - **"Cost estimates are too uncertain to write down."** An explicit, wrong-by-a-factor-of-two ratio
#   can be argued with and corrected. An unstated one is still there, hidden inside F1 or a 0.5 threshold.
# - **Limits of this lesson's frame for SKAB:** a single laboratory testbed, induced faults, one
#   episode per recording, a role-played stakeholder. The problem statement must say so.
#
# ---

# %% [markdown]
# ## 3. Worked example
#
# Two scripts in [`example/`](../labs/w2d4_problem_framing_splits/example). Run from the repository root.
#
# ### 3.1 Synthetic: what a split estimates, and why a seed is not a split

# %%
!python labs/w2d4_problem_framing_splits/example/split_unit_demo.py

# %% [markdown]
# **Data (SYNTHETIC, generated in the script).** 24 machines × 200 windows, 6 features. Each machine has
# a sensor *fingerprint* (a constant offset on every feature, visible to the model) and an unobserved
# *fault propensity*. The label depends on a genuinely transferable signal mixed into feature 0 and on
# the machine's propensity. Schema: `X` (float, 6 columns), `y` (0/1), `g` (machine id).
#
# **Output of the authoring run**
#
# ```
# Part 1: what does each split estimate?  (ROC AUC, 5 split seeds)
#   row-level split      mean 0.784   range 0.771-0.795
#   machine-level split  mean 0.536   range 0.383-0.669
#   truth: 200 new machines   0.525
#
# Part 2: same code, same random_state=0, one extra machine in the list
#   test set before: 6 machines; after: 7 machines
#   machines that were test and are now training data: 4 -> ['M01', 'M10', 'M14', 'M20']
#
# Part 3: a manifest is data
#   sha256 of the manifest text: 5394bc4a85016a70
#   adding machine M24 to the fleet changes this file by: nothing (M24 is simply unassigned,
#   and validation fails loudly until someone decides where it goes)
# ```
#
# **Key code decisions.** The "truth" is computed on 200 freshly simulated machines, which is possible
# only because the data is synthetic; that is the one thing simulation is good for here. The random
# forest is deliberately flexible enough to memorise fingerprints. Five split seeds are shown because
# one seed would hide the spread.
#
# **Interpretation.**
# *Part 1.* The row-level split reports 0.78; the model in fact barely transfers (0.53 on new
# machines), because it has learned which machine a window comes from and that machine's fault rate.
# The machine-level split is centred on the truth but ranges from 0.38 to 0.67 with six test machines:
# an honest estimate from few groups is *noisy*, and a single grouped split can mislead in either
# direction. The size of the gap is a property of this simulation (strong fingerprints, weak signal);
# the mechanism is general.
# *Part 2.* Identical code and seed; one machine added to the fleet; four of the six former test
# machines are now training data. Nothing warned anyone.
# *Part 3.* The manifest does not move when the fleet changes, and a validator can refuse to proceed
# until the new machine is assigned.
#
# ### 3.2 Real data: the same comparison on SKAB (development experiments only)

# %%
!python project/get_skab.py
!python labs/w2d4_problem_framing_splits/example/skab_row_vs_experiment.py

# %% [markdown]
# **Data.** The 25 development experiments of the reference manifest (27,804 rows); eight raw sensor
# values per timestamp, label `anomaly`. The test set is not read. Schema: [project data dictionary](../docs/guides/project.md).
#
# **Output of the authoring run**
#
# ```
# development pool: 25 experiments, 27804 rows, positive fraction 0.353
# row-level 4-fold         PR-AUC 0.980 (folds 0.975-0.982)   ROC-AUC 0.986 (folds 0.982-0.987)
# experiment-level 4-fold  PR-AUC 0.841 (folds 0.731-0.936)   ROC-AUC 0.849 (folds 0.740-0.936)
# ```
#
# **Interpretation.** A random forest on raw sensor values "achieves" ROC-AUC 0.986 if rows are shuffled
# into folds, and 0.849 when whole experiments are held out. Two things are worth as much attention as
# the drop: the row-level folds agree with each other almost perfectly (0.982–0.987), which looks like
# stability and is in fact four copies of the same leak; and the experiment-level folds range from 0.74
# to 0.94, which is what six held-out recordings can tell you. The experiment-level number is itself
# flattered (point-level metric at 35 % prevalence, raw values rather than causal features, no
# threshold chosen); it is a baseline for the *protocol*, not a model result. Expect small differences
# across library versions.
#
# **Reproducibility.** Both scripts fix their seeds. Versions used: [docs/maintainers/tested-versions.md](../docs/maintainers/tested-versions.md).
#
# The same output as a picture, one dot per fold:
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/labs/w2d4_problem_framing_splits/figures/row_vs_experiment.svg" alt="Dot plot of fold scores: row-level folds cluster at PR-AUC 0.98 and ROC-AUC 0.986, experiment-level folds spread from 0.73 to 0.94 with means 0.841 and 0.849" width="100%">
#
# *Real SKAB, development experiments only. Look at the spread as much as the level: the tight orange
# cluster is four copies of the same leak; the wide blue one is the honest uncertainty of six held-out
# recordings. Regenerate with `python labs/w2d4_problem_framing_splits/figures/make_figures.py`.*
#
#
# ---

# %% [markdown]
# ## 4. Guided lab
#
# Work in [`lab/`](../labs/w2d4_problem_framing_splits/lab). It contains a `flowguard` package (v0.1.0) with a finished `data.py`
# (the loader from the spec), a stub `splits.py`, a minimal `cli.py`, and a `PROBLEM_STATEMENT.md` template.
#
# Use the package without installing it, from the repository root:
#
# ```bash
# export PYTHONPATH=labs/w2d4_problem_framing_splits/lab/src
# python -c "from flowguard.data import load_raw; t = load_raw('data/raw/skab'); print(t.shape, t.experiment_id.nunique())"
# ```
#
# Expected: `(46806, 14) 35`. If you see `FileNotFoundError`, run `python project/get_skab.py` first.
# (An editable install in a virtual environment, as in w1d3, works equally well.)
#
# Run the checks at any time; they use small synthetic tables, never the download:

# %%
!python wb.py check w2d4

# %% [markdown]
# ### Task 1 — Look before you split (10 min)
#
# In a scratch session, answer from the tidy table: how many experiments per family; rows per
# experiment; positive fraction per experiment; how many positive segments per experiment.
#
# **Checkpoint.** 16 / 4 / 14 labelled experiments plus one fault-free recording; exactly one positive
# segment in each labelled experiment. Write down, before coding, how many test experiments per family
# a 25 % stratified split should give.
#
# ### Task 2 — `make_splits` (15 min)
#
# Implement it in `lab/src/flowguard/splits.py` to the contract in the file's docstring.
#
# Requirements the checks enforce: every labelled experiment in the test set or in exactly one dev
# fold; each family with at least two experiments present in both test and development; about
# `test_fraction` of experiments in test; `n_folds` non-empty, reasonably balanced folds; same seed →
# same manifest, independent of row order; the seed actually used; the fault-free recording only under
# `reference_normal`.
#
# **Checkpoint.** `python -m pytest labs/w2d4_problem_framing_splits/checks/test_make_splits.py -q`
# passes.
#
# **Debugging.**
# - *Different result when rows are shuffled:* you are iterating over `unique()` in order of
#   appearance. Sort the experiment ids before drawing.
# - *A family missing from test for some seeds:* you shuffled all experiments as one pool. Draw within
#   each family.
# - *`valve2` entirely in test:* cap the per-family test count at `n - 1`.
#
# ### Task 3 — `validate_splits` (10 min)
#
# Raise `ValueError`, naming the offending ids, for: an experiment on two sides or in two folds;
# an id not in the data; a labelled experiment missing from the manifest; the fault-free recording in
# test or a fold; a labelled experiment listed as reference-normal; a manifest whose `unit` is not
# `experiment_id` or whose entries are not ids.
#
# **Checkpoint.** `test_rejects_broken_manifests` passes for all eight cases. If only the overlap cases
# pass, re-read the list: a validator earns its keep on the failures you did not think of.
#
# ### Task 4 — `save_splits` / `load_splits` (5 min)
#
# Stable, diff-friendly JSON (sorted keys, indentation, trailing newline). `save_splits` raises
# `FileExistsError` if the file exists and `overwrite` is false.
#
# ### Task 5 — `flowguard split` and the real manifest (10 min)
#
# Add the subcommand described in `lab/src/flowguard/cli.py`, then freeze the project split:
#
# ```bash
# python -m flowguard.cli split --raw-dir data/raw/skab --out labs/w2d4_problem_framing_splits/lab/splits/v1.json
# ```
#
# **Checkpoint.** Running it a second time fails with a one-line message and leaves the file
# untouched. The reference implementation prints
#
# ```
# wrote splits/v1.json: test=9 experiments, dev folds=[7, 6, 6, 6], reference_normal=1
# ```
#
# with test = 4 `valve1` (`5, 8, 10, 13`), 1 `valve2` (`0`), 4 `other` (`1, 11, 12, 14`). Your
# membership will differ unless your drawing procedure is identical; that is fine. What must match are
# the properties: 34 experiments assigned once, every family in both test and development, 8–9 in test.
#
# Copy `splits/v1.json` into your own project repository and commit it **now**, before any model exists.
# From here on it changes only by becoming `v2`.
#
# ### Task 6 — The problem statement (20 min)
#
# Fill in `lab/PROBLEM_STATEMENT.md`. One page, ten sections, positions rather than descriptions,
# assumptions marked. The automated check verifies completeness only. Then score yourself with the
# rubric in assessment.md (section 7 of this notebook) and compare with the reference statement in the solutions tree.
#
# **Completion criteria for the lab.** `python wb.py check w2d4` passes; `splits/v1.json` is committed
# in your project repository; your problem statement scores no zero on *Decision*, *Label* or *Splits*.
# Then `python wb.py mark w2d4 guided`.
#
# ---

# %%
# Run the automated checks on your guided lab.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w2d4")

# %% [markdown]
# ## 5. Independent challenge
#
# [challenge/README.md](../labs/w2d4_problem_framing_splits/challenge/README.md): frame a subscription-churn problem from a product
# manager's brief and implement a split that is correct in **time** (a three-month label horizon) and
# in **group** (customers the model has never seen), on a synthetic customer-month table. It transfers
# the lesson to a case where the unit of generalisation is *not* simply "the group", and contains one
# trap that does not exist in SKAB.

# %%
!python wb.py check w2d4 --challenge

# %% [markdown]
# Set `python wb.py mark w2d4 independent` only if the checks pass without hints or the solution.
#
#
# ### The challenge brief
#
#
# **Time:** 40-50 min, unassisted. Hints exist (1, 2,
# 3); using one means the `independent` flag stays unset for this unit.
# **Data:** `customer_months.csv` in this directory - SYNTHETIC (generator:
# `../checks_challenge/customer_months.py`). It supports conclusions about your split logic only.
#
# #### The brief (as a product manager would write it)
#
# > "StreamBox loses subscribers every month. Retention can phone about 5 % of active subscribers a
# > month with an offer. Tell us who to call. We export a snapshot of every active subscriber at the end
# > of each month; a model would be refreshed at month end and used during the following months.
# > Marketing also wants to know whether it works for people who signed up recently."
#
# #### The table
#
# One row per customer per month in which the customer was active (2,386 rows, 300 customers,
# 2024-01 to 2025-06).
#
# | Column | Meaning |
# |---|---|
# | `customer_id` | subscriber |
# | `month` | snapshot month, `YYYY-MM`; features describe the customer at the end of this month |
# | `tenure_months`, `plan`, `usage_hours`, `support_tickets` | features known at the end of `month` |
# | `churn_within_3m` | 1 if the customer cancels during one of the **three months after** `month`, else 0 |
#
# Read this twice: a cancellation is recorded the moment it happens, so a `1` can be known long before
# the three months are over; a `0` can only be known once all three months have passed. In the last
# snapshots the label is therefore either `1` or missing.
#
# #### Part A - framing (written, rubric-graded)
#
# Fill in `FRAMING.md` (same ten headings as the lab's problem statement). One page. Take positions:
# what is the decision, what is the unit, when is the prediction made and about what period, what do
# the two error types cost, what is the business metric and which offline metric stands in for it, what
# is the baseline that needs no model, and what would make you refuse to ship.
#
# #### Part B - the split (automatically checked)
#
# Implement in `churn_splits.py`:
#
# ```python
# split_customer_months(df, test_start, horizon_months=3, new_customer_fraction=0.2, seed=0)
#     -> {"train": [...], "test_known": [...], "test_new": [...]}     # labels from df.index
# ```
#
# The situation to emulate: the model is trained at the end of the month before `test_start` and then
# scores the monthly snapshots from `test_start` onwards.
#
# Acceptance criteria
#
# 1. **Train** contains only rows whose outcome was fully known when the model was trained.
# 2. **Test** rows are snapshots from `test_start` onwards whose outcome is fully observable in the
#    data; every such row is in exactly one of `test_known` / `test_new`. Rows must not be selected by
#    whether the label happens to be filled in.
# 3. `new_customer_fraction` of the customers who *could* have been trained on are withheld from
#    training entirely, chosen reproducibly from `seed`.
# 4. `test_known` = test rows of customers with at least one training row; `test_new` = test rows of
#    customers with none (for whatever reason).
# 5. No usable training row of a training customer is discarded.
# 6. Deterministic for a given seed; the input frame is not modified; works for any `horizon_months`
#    and for a frame whose index is not `0..n-1`.

# %%
!python wb.py check w2d4 --challenge

# %% [markdown]
# #### Part C - one number (put it at the end of `FRAMING.md`)
#
# Compute the churn rate of your test rows, and the churn rate you would have reported had you built
# the test set as "rows from `test_start` on where the label is not missing". Explain the difference
# in two sentences.

# %%
# Run the automated checks on your independent challenge.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w2d4", challenge=True)

# %% [markdown]
# ## 6. Progressive hints
#
# For the challenge, in increasing strength: [1 concept](../labs/w2d4_problem_framing_splits/hints/hint1_concept.md) ·
# [2 approach](../labs/w2d4_problem_framing_splits/hints/hint2_approach.md) · [3 partial implementation](../labs/w2d4_problem_framing_splits/hints/hint3_partial.md).
# Full reference: `solutions/labs/w2d4_problem_framing_splits/` (lab, challenge, model answers).
#
#
# Open one hint at a time, only after a real attempt.
#
# <details>
# <summary><b>Hint 1 concept</b></summary>
#
#
# Two different clocks are attached to every row of the churn table:
#
# * the **feature clock**: when the snapshot was taken (`month`);
# * the **label clock**: when the outcome it records became *fully* known.
#
# A split is honest when it could have been carried out by someone standing at the training date with
# no knowledge of later events. Ask of every row: *on the day the model was fitted, had this row's
# label finished happening?* and of every evaluation row: *is its label finished happening now, for
# positives and negatives alike?*
#
# For the lab's SKAB split the two clocks coincide (the label of a timestamp is known with it), which
# is why only the *group* question mattered there. Here both questions matter, and they are independent:
# answer the time question and the customer question separately, then intersect.
#
# For the framing: start from the sentence "Because of the model, ___ will ___ instead of ___." If you
# cannot fill it in, you do not yet have a decision, and nothing else in the document can be right.
# The capacity limit in the brief (5 %) is the strongest clue about which metric matches the decision.
#
# </details>
#
# <details>
# <summary><b>Hint 2 approach</b></summary>
#
#
# Work with integer month numbers so the arithmetic is ordinary subtraction (`year * 12 + month`).
# Let `T` be `test_start`, `H` the horizon, `last` the last month in the table.
#
# 1. **Trainable rows.** The model is fitted at the end of month `T - 1`. A row from month `m` has a
#    label covering `m+1 ... m+H`. Write the inequality that says "that window had closed by then".
#    Check it by hand for `H = 3`, `T = 2025-01`: the latest trainable month should be 2024-09.
# 2. **Evaluable rows.** Month at or after `T`, and the label window must close inside the table.
#    Do not use `notna()` for this: look at which labels are known in the last three months and why.
# 3. **Hold-out customers.** Sample from the customers that have at least one trainable row (sorted,
#    then a seeded generator). Remove *all* their trainable rows from train.
# 4. **Known vs new.** Define these from the result, not from the sample: a test customer is "known"
#    exactly when the final training set contains a row of theirs. Customers who joined after the last
#    trainable month were never sampled, yet the model has not seen them.
# 5. Return `df.index` labels, not positions; the checks use a shuffled, offset index.
#
# Part C: compare `df.loc[test rows, label].mean()` with the mean over
# `df[(month >= T) & label.notna()]`, and look at the months that only the second set contains.
#
# </details>
#
# <details>
# <summary><b>Hint 3 partial</b></summary>
#
#
# The skeleton below is complete except for the three marked expressions.
#
# ```python
# import numpy as np
# import pandas as pd
#
#
# def month_number(months):
#     p = pd.PeriodIndex(months, freq="M")
#     return np.asarray(p.year * 12 + p.month)
#
#
# def split_customer_months(df, test_start, horizon_months=3, new_customer_fraction=0.2, seed=0):
#     m = month_number(df["month"])
#     start = int(month_number([test_start])[0])
#     last = int(m.max())
#     customer = df["customer_id"].to_numpy()
#
#     can_train = ...   # (1) label window closed before `start`
#     can_test = ...    # (2) at/after `start` AND label window closes by `last`
#
#     candidates = np.array(sorted(set(customer[can_train])))
#     n_held = int(round(new_customer_fraction * len(candidates)))
#     held_out = set(np.random.default_rng(seed).choice(candidates, size=n_held, replace=False).tolist())
#
#     in_train = can_train & ~np.isin(customer, list(held_out))
#     seen = ...        # (3) customers that actually have a row in the training set
#     known = can_test & np.isin(customer, list(seen))
#     new = can_test & ~np.isin(customer, list(seen))
#     return {"train": df.index[in_train].tolist(),
#             "test_known": df.index[known].tolist(),
#             "test_new": df.index[new].tolist()}
# ```
#
# Self-check before running the checks: with the supplied file and `test_start="2025-01"` the training
# months should end at 2024-09 and the test months should be 2025-01 to 2025-03.
#
# The full reference is in `solutions/labs/w2d4_problem_framing_splits/challenge/`.
#
# </details>

# %% [markdown]
# ## 7. Assessment
#
# assessment.md (section 7 of this notebook): five reasoning questions (Q5 is the design-choice explanation), the
# rubric for the written problem statement, and one interview rep on validation and leakage. Automated
# checks cover the split code; the rubric covers the writing. Model answers and common incorrect answers:
# `solutions/labs/w2d4_problem_framing_splits/assessment_answers.md`.
#
#
# ### Assessment questions
#
#
# Write your answers in `progress/notes.md` (or a file of your own) **before** opening
# `solutions/labs/w2d4_problem_framing_splits/assessment_answers.md`. About 15 minutes for Q1-Q5.
#
# #### Reasoning questions
#
# **Q1.** A colleague reports "ROC-AUC 0.99 on SKAB with a random forest on the raw sensor values,
# 5-fold cross-validation". State the one question you ask first, and what you expect the number to
# become when it is answered properly. (The lesson's worked example contains the measured answer.)
#
# **Q2.** For each situation name the unit of generalisation and therefore the unit of splitting:
# (a) a seizure detector to be sold to hospitals that are not in your dataset;
# (b) a demand forecast for the same 200 shops next quarter;
# (c) a fraud model scoring card transactions, where one card has many transactions and fraud rings
#     reuse merchants;
# (d) a fault detector for one specific pump that will be retrained monthly on that pump's own data.
#
# **Q3.** Your split manifest was frozen three weeks ago. Since then: (i) you found that two test
# experiments have a 60-second logging gap; (ii) four new experiments were recorded; (iii) the test
# PR-AUC of your favourite model is disappointing and a different seed would "balance the families
# better". For each, say what you do to the manifest and why.
#
# **Q4.** The same eight-sensor stream could be framed as (a) forecasting the next minute of pressure,
# (b) classifying each window as normal or faulty, (c) anomaly detection trained on normal data only.
# For each framing, state what labels it needs, and one condition under which it is the right choice.
#
# **Q5 (design choice).** `make_splits` puts a fixed 25 % of experiments in a test set and uses
# grouped folds on the rest, instead of nested cross-validation over all 34 experiments. Argue for
# this choice, then give the strongest argument against it for a dataset of this size, and say what
# you would report to make the weakness visible.
#
# #### Rubric for the written problem statement (lab Task 6 and challenge Part A)
#
# Score each row 0 / 1 / 2. "2" requires a position a reviewer could disagree with.
#
# | Criterion | 0 | 1 | 2 |
# |---|---|---|---|
# | Decision | describes a model ("predict anomalies") | names a user | names who does what differently, and the status quo |
# | Unit and prediction time | absent or mixes units | unit of prediction given | prediction, decision and generalisation units distinguished; information cut-off explicit |
# | Label | "the label column" | definition given | origin, delay, noise and their consequence for achievable performance |
# | Costs | "both errors matter" | asymmetry stated | rough ratio or budget stated as an assumption, and tied to the threshold or the top-k |
# | Metric chain | a metric named | metric justified | business quantity -> operational proxy -> development metric, with what each can mislead about |
# | Baseline | none | a trivial baseline | do-nothing **and** the expert rule, plus what margin justifies a model |
# | Splits | random or unspecified | grouped or temporal | unit justified from deployment; what is frozen; second protocol or stated blind spot |
# | Limits | none | generic caveat | specific claims the data cannot support |
#
# Interpretation: 13-16 with no zeros is a statement you could defend in a design review. Any zero
# in *Decision*, *Label* or *Splits* means rewrite that section before building anything on it.
#
# #### Interview rep (validation and leakage, 10-15 min, write or speak your answer first)
#
# > "We built a model that predicts, from the first 30 days of a customer's activity, whether they
# > will still be subscribed after 12 months. We took all customers who signed up in the last three
# > years, split them 80/20 at random by customer, tuned on the 80 % with 5-fold CV and got AUC 0.91
# > on the 20 %. Before we ship: what would you check?"
#
# Give a prioritised list of at most five checks. For each: what could be wrong, how you would test
# it with the data they already have, and which direction the reported number would move.

# %% [markdown]
# ## 8. Reflection and review
#
# **You should now be able to, without notes:** fill the ten-item worksheet for an unfamiliar problem
# in 15 minutes; name the unit of generalisation and derive the split from it; explain why a manifest
# beats a seed; say what the test set of your project can and cannot resolve.
#
# **Reflection (3 minutes, in `progress/notes.md`).** Take one study or project you know well. What was the
# decision it supported, and what would a product manager say was missing from its evaluation?
#
# **Retrieval question (answer on the Week 2 review day, from memory).** A recording has 1,100 samples
# with within-recording correlation 0.5. Roughly how many independent observations is that, and what
# does it imply for a confidence interval computed over samples?
#
# **Next:** `w2d5_feature_pipeline` — causal rolling features with train-only statistics. The manifest
# you froze today decides which rows those statistics may see.
#
# ---

# %% [markdown]
# ## Verification record
#
# Executed 2026-11-21 on Python 3.13.18, NumPy 2.5.3, pandas 3.0.5, scikit-learn 1.9.1.
#
# | What | Result |
# |---|---|
# | `example/split_unit_demo.py` | ran; output above copied from the run |
# | `example/skab_row_vs_experiment.py` (real SKAB, dev experiments) | ran; output above copied from the run |
# | Reference `flowguard split` on real SKAB | 9 test / 25 dev (folds 7, 6, 6, 6) / 1 reference; second run exits 2, file unchanged |
# | `python tools/verify_checks.py labs/w2d4_problem_framing_splits` | lab: reference passes, 6 mutants rejected; challenge: reference passes, 5 mutants rejected |
# | Shipped starters | lab checks: 32 failed, 13 errors, 1 passed; challenge checks: 5 failed, 8 errors |
# | Challenge numbers (churn rates 0.163 / 0.199, row counts) | computed from the committed CSV with the reference solution |
#
# Not verified: time boxes (estimates); Python 3.11/3.12 (CI only); the industry example in 2.7 is
# illustrative, not a documented case.

# %% [markdown]
# ## Record your progress
#
# Tick only what is true. Passing the supplied checks is *guided practice*; mark *independent* only for work done without hints or solutions.

# %%
from mlcourse.progress import mark, note

# mark("w2d4", "reading")
# mark("w2d4", "guided")
# mark("w2d4", "independent")
# note("w2d4", "what tripped me up today")

