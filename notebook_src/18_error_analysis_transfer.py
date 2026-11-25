# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/18_error_analysis_transfer.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 18 · Error analysis and timed transfer exercise
#
# **Week 3 · day 6 · 2 h essential path + up to 1 h optional** · lab files: [`labs/w3d6_error_analysis_transfer/`](../labs/w3d6_error_analysis_transfer/)
#
# **Objective.** Turn errors into a ranked failure taxonomy with slices; then run a complete leak-free evaluation on the unfamiliar business table, unassisted, in 90 minutes.

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
# Unit id `w3d6_error_analysis_transfer` · Week 3, day 6 · Handbook: [H6.7](../docs/handbook/ch06_evaluation_leakage_uncertainty/h6_7_error_analysis.md)
# (uses [H6.6](../docs/handbook/ch06_evaluation_leakage_uncertainty/h6_6_bootstrap_and_paired_comparisons.md) for slice intervals)
# · Content status: see [STATUS.md](../docs/guides/status.md)
#
# This session has two halves with different rules. The first is a short guided lab: turn one
# detector's errors on SKAB into a ranked failure list. The second is the course's **transfer
# exercise, part 2**: a complete, leak-free evaluation of an unfamiliar business problem, unassisted
# and timed at 90 minutes.

# %% [markdown]
# ## 1. Purpose
#
# **Objective.** Turn a model's errors into a ranked failure taxonomy with sized slices, and then,
# independently and under time pressure, carry out a complete evaluation on a tabular business problem
# you have not seen.
#
# **Why an applied ML engineer needs it.** After the first model, the job is choosing the next piece
# of work. "Recall is 0.67" does not say what to change; "half of all wrong rows are the alarm dropping
# out after the first detection, on 26 of 27 experiments" does. In interviews and in design reviews you
# will be asked "what does your model get wrong?", and an answer with sizes and a next experiment is
# what separates analysis from anecdote. The timed half measures whether the Week 2-3 habits (framing,
# leak audit, a split that matches deployment, a decision metric, an interval, a baseline) hold when
# nobody prompts them.
#
# **Deliverables.**
#
# 1. A tested `flowguard.erroranalysis` module and `lab/ERROR_ANALYSIS.md`: a one-page error analysis of
#    the w2d6 flow-rate baseline on the SKAB development experiments.
# 2. `challenge/evaluate.py` and `challenge/REPORT.md` for the LedgerLine late-payment problem
#    (SYNTHETIC data), produced in one 90-minute sitting.
#
# **Completion criteria.**
#
# * `python wb.py check w3d6` passes (guided practice) and `ERROR_ANALYSIS.md` is written from your run.
# * `python wb.py check w3d6 --challenge` passes *and* the sitting was unassisted and timed (independent
#   skill). The report is then read against the scoring guidance in the solutions tree.
#
# **Prerequisites.** [w2d6](12_baselines_metrics.ipynb) (the flow-rate baseline, point
# metrics; its challenge was transfer part 1), w3d1 ([leak audit](13_leakage.ipynb)),
# [w3d2](14_group_temporal_validation.ipynb) (splits that match deployment),
# [w3d5](17_uncertainty.ipynb) (cluster intervals). Event matching from
# [w3d4](16_point_vs_event_evaluation.ipynb) helps but is not required: the lab classifies
# error *runs* itself. If some Week 3 lessons are not finished yet, the lab still runs (it ships its own
# `flowguard` snapshot).
#
# **Time budget.** This session deliberately uses most of the optional extension: the transfer
# exercise needs one unbroken 90-minute block.
#
# | Activity | Minutes |
# |---|---|
# | Read sections 2-3, run the two worked examples | 20 |
# | Guided lab: implement three functions, run the report, write `ERROR_ANALYSIS.md` | 40 |
# | Break | 10 |
# | **Transfer exercise, timed, unassisted** | **90** |
# | Assessment and reflection | move to the review day (w3d7) |
#
# If you have only two hours today, do the guided half now and the 90-minute sitting as its own session
# before w3d7. Do not split the sitting.
#
# Data: `python project/get_skab.py` (once) for the lab's real-data run. Checks and the challenge need
# no download.

# %% [markdown]
# ## 2. Conceptual explanation
#
# The handbook section [H6.7](../docs/handbook/ch06_evaluation_leakage_uncertainty/h6_7_error_analysis.md)
# is the full treatment. This section gives what the lab and the challenge need.
#
# ### 2.1 Error analysis generates hypotheses
#
# The output of error analysis is a short ranked list of failure modes, each with a **size**, a
# **suspected cause**, and a **falsifiable next experiment**, plus an explicit list of what was examined
# and found unremarkable. Three rules make it analysis rather than storytelling:
#
# 1. **Fix the object.** One model, one threshold, one split, written down.
# 2. **Work on development data.** Reading test errors and then changing the model converts the test
#    set into a second development set.
# 3. **Quantify, and stay at the unit of independence.** Slices are compared by per-experiment
#    (per-customer) values with their sizes, not by pooled rows.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/docs/assets/diagrams/mmd-18-01.svg" alt="Diagram 1 of notebook 18" style="max-width:100%">
#
# ### 2.2 The unit table and the two kinds of average
#
# The **unit table** has one row per experiment: counts (rows, positives, flagged, TP, FP, FN) and the
# metrics computed inside the experiment. Every later step is a group-by on it.
#
# A slice value can be the **mean of per-unit metrics** or a **row-pooled** metric:
#
# $$
# \text{mean recall}_S = \frac{1}{|S|}\sum_{u \in S} \frac{TP_u}{TP_u + FN_u}
# \qquad\text{vs}\qquad
# \text{pooled recall}_S = \frac{\sum_{u\in S} TP_u}{\sum_{u\in S}(TP_u + FN_u)} .
# $$
#
# They agree when units are of similar size and behave alike, and diverge when one large unit dominates
# the pooled figure. The reliability engineer asks "on a typical experiment, how much of the fault is
# flagged?" (mean over units); someone sizing alert storage asks "what share of anomalous rows is
# flagged?" (pooled). Report the one that matches the question, with sizes, and the other if they differ.
#
# **Undefined is not zero.** Recall on an experiment with no anomalous rows, or precision when nothing is
# flagged, cannot be computed. Store `NaN` and keep it out of means; report how many units were defined.
# Writing 0.0 turns "not measurable" into "measured as terrible" and silently drags slice means down.
#
# **Uncertainty of a slice.** A slice of `k` experiments has a standard error of about `s/√k` for its mean;
# with between-experiment standard deviation 0.3, ten experiments give a 95 % half-width near 0.19. The
# lab bootstraps experiments within a slice and refuses an interval below five defined experiments.
#
# ### 2.3 Slice hunting is multiple testing
#
# Search enough slices and one will look bad by chance. The worked example simulates 24 machines with
# *identical* true recall 0.80 and 40 arbitrary binary attributes (80 slices): the worst slice found
# averages 0.729, and 45 % of searches with no real effect find one at least that bad. The same slice
# re-measured on fresh machines gives 0.764 against 0.800 for the rest.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/labs/w3d6_error_analysis_transfer/figures/slice_hunting.svg" alt="SYNTHETIC: distribution of the worst slice recall found by searching 80 slices when no slice effect exists; the observed worst slice 0.729 sits in the middle of it" width="100%">
#
# *SYNTHETIC simulation, 2,000 searches (`example/slice_traps.py`, part 2). A "worst slice" at 0.73 is
# what chance produces here; it is not a finding.*
#
# Discipline: write the slicing variables before looking; prefer variables computable without labels;
# count how many slices you examined; and treat a surprising slice as a hypothesis to test on other
# units. Slices *defined using the labels* (for example "experiments where the fault barely moves the
# flow") usually restate the failure rather than explain it.
#
# **Simpson's paradox** is the other trap: a detector can be better in every regime and worse pooled when
# the regimes are mixed differently. In the worked example detector B has higher recall in both steady
# and variable load (0.990 vs 0.882 and 0.537 vs 0.480) and lower pooled recall (0.628 vs 0.802), because
# B was tested mostly under variable load. Standardised to the same 50/50 mix, B leads 0.764 to 0.681.
#
# ### 2.4 Label noise versus model error
#
# Some errors no model can avoid. In SKAB, 235 distinct measurements occur in two files with opposite
# labels (`other/12`/`other/13`: 178; `other/3`/`other/4`: 57). A detector that is a function of the
# sensors alone must be wrong on one copy of each, so 235 of those 470 rows are irreducible errors. With
# burn-in normalisation the two copies can get different scores, so the observed baseline error on
# contradictory rows (24) is not that floor. Report such units separately, with and without, so later
# comparisons are not driven by rows nobody can get right.
#
# ### 2.5 Error kinds for detectors
#
# Per-row errors in event detection are not independent: they come in runs, and the run's position
# relative to the labelled event says what went wrong. The lab classifies each run of wrong rows:
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/docs/assets/diagrams/mmd-18-02.svg" alt="Diagram 2 of notebook 18" style="max-width:100%">
#
# Each kind has a different cause and fix: *misses* and *late* detections need a more sensitive signal;
# *fragments* point at threshold noise (hysteresis or a hold time) or a transient response; *pre-onset*
# runs are threshold noise, genuine precursors, or label timing; *post-event* runs suggest the reference
# no longer describes normal after a fault. This is the same vocabulary you use for HFO or seizure
# detectors (detection latency, fragmented detections, false detections per hour); the difference in
# industry is that the cost of each kind comes from an operator's alert queue, not a reviewer.
#
# ### 2.6 Ranking: frequency × cost × fixability
#
# Frequency caps the gain: fixing a mode that causes 5 % of wrong rows can improve the metric by at
# most 5 %. Cost is the stakeholder's, not the metric's (a late detection may cost more than a hundred
# post-event alarms). Fixability is your honest estimate of the chance a cheap change works. The product
# is a ranking heuristic, not a measurement; state the assumptions so someone can disagree with them.
#
# ### 2.7 An industry example
#
# A payments team's fraud model loses recall in one quarter. Error analysis by merchant category finds the
# loss concentrated in 3 of 40 categories, all onboarded the same month, all using a new payment
# processor whose transaction timestamps arrive in UTC instead of local time; the "hour of day" feature
# was shifted. The fix was a data-contract check at ingestion, not a new model. (Illustrative composite,
# not a cited incident.) The pattern generalises: the top failure mode is often in the data, and slicing
# by *how the data was produced* (source, firmware, site, onboarding cohort) finds it more often than
# slicing by model internals.
#
# ### 2.8 Misconceptions
#
# * *"Look at the 20 worst examples."* They over-represent label errors and corrupted inputs; sample
#   errors systematically instead.
# * *"The slice with the lowest metric is the problem."* With small slices, the lowest is mostly noise.
# * *"An undefined metric is a zero."* It is a missing measurement.
# * *"Error analysis on the test set is fine if we don't retrain."* Any decision informed by it is a
#   selection on test.
# * *"A bigger model will fix it."* Only if the failure mode is capacity. Here the top mode is a
#   threshold policy and the second involves label timing.

# %% [markdown]
# ## 3. Worked example
#
# Two scripts. The first is SYNTHETIC and shows the slice arithmetic; the second uses REAL SKAB files
# and measures label conflicts.
#
# ### 3.1 Two slice traps

# %%
!python labs/w3d6_error_analysis_transfer/example/slice_traps.py

# %% [markdown]
# Output of the run on 2026-11-22:
#
# ```
# Part 1: recall of two detectors, by regime and overall
# detector        regime  events  detected  recall
#        A   steady load     400       353   0.882
#        A variable load     100        48   0.480
#        B   steady load     100        99   0.990
#        B variable load     400       215   0.537
#
# pooled over regimes:
#           events  detected  recall
# A            500       401   0.802
# B            500       314   0.628
#
# standardised to the same regime mix (50/50):
# A   0.681
# B   0.764
#
# Part 2: 24 machines, identical true recall 0.80, 10 events each, 40 arbitrary binary attributes
# overall mean recall 0.804
# three 'worst' slices found by searching:
#    slice  n_machines  recall
# attr21=1           7   0.729
# attr06=1          13   0.731
# attr13=1          15   0.753
#
# minimum slice recall under 'no real slice effect': median 0.733, 5th percentile 0.675
# observed minimum 0.729 -> fraction of null searches at least this low: 0.45
# same slice definition on 24 fresh machines: recall 0.764 vs rest 0.800
# ```
#
# Reading it: in part 1 the pooled comparison is dominated by *where* each detector was tested, not how
# well it detects; standardising to a common mix reverses the conclusion. In part 2 the "worst slice"
# is exactly what the null distribution predicts, and it partly regresses on fresh machines. Key code
# decision: the null distribution is simulated with the *same* search procedure (same number of slices,
# same machines), because the multiplicity is a property of the search, not of any single slice.
#
# ### 3.2 Label conflicts in SKAB

# %%
!python project/get_skab.py
!python labs/w3d6_error_analysis_transfer/example/label_conflicts_skab.py

# %% [markdown]
# ```
# labelled rows: 37401
# rows that also occur in another labelled file: 1436
# of those, rows whose copies carry contradictory labels: 470 (235 distinct measurements)
#
# by experiment:
#                rows  labelled_anomalous
# other/12        178                 178
# other/13        178                   0
# other/3          57                  57
# other/4          57                   0
#
# baseline errors in the affected experiments ['other/12', 'other/13', 'other/3', 'other/4']: 1028
#   of which on contradictory rows: 24
# ...
#   irreducible errors = 235 of 470 contradictory rows
# ```
#
# Interpretation: `other/12` and `other/13` contain 178 identical measurements labelled anomalous in one
# file and normal in the other. Any error analysis that ranks `other/13` as "the detector's worst
# false-alarm experiment" must say this first. Data schema: the tidy SKAB table of
# [docs/maintainers/flowguard-spec.md](../docs/maintainers/flowguard-spec.md) (`experiment_id, family, t, datetime`, eight
# sensors, `anomaly`). Rows are compared on all eight sensor values plus timestamp.
#
# **Reproducibility.** Part 2 of `slice_traps.py` is seeded; `label_conflicts_skab.py` is deterministic
# given SKAB at commit `b2c0d46` (`project/get_skab.py --verify`).

# %% [markdown]
# ## 4. Guided lab
#
# Work in `labs/w3d6_error_analysis_transfer/lab/`. It ships `flowguard` with snapshots of `data`,
# `splits` (v2, overlap groups kept together), `metrics`, `baselines`, and a stub
# `erroranalysis.py` whose docstrings are the specification. `error_report.py` is complete; it runs the
# w2d6 bar baseline (`|z|` of `flow_rate` against each experiment's first 100 rows) on the **27
# development experiments** with the best-F1 development threshold, and prints the tables. The split is
# read from `lab/splits/v2.json`, the manifest repaired and frozen in [w3d1](13_leakage.ipynb):
# the test set is never redrawn once results have been seen, so every Week 3 lesson uses the same seven
# test experiments, and they are never scored here.
#
# ### Task 1 — `per_experiment_table` (10 min)
#
# One row per experiment with counts, precision, recall, false-alarm rate (FP over normal rows), onset,
# first detection, detection delay. A flag before onset is a false alarm, not an early detection.
#
# *Checkpoint:* `python -m pytest labs/w3d6_error_analysis_transfer/checks/test_per_experiment_table.py -q`
# (each function has its own check file). *Debugging:* if delays are negative you counted pre-onset flags as detections; if a
# recall is 0.0 on an experiment without anomalies, it should be `NaN`.
#
# ### Task 2 — `slice_metrics` (10 min)
#
# Mean over experiments within each slice, with `n_experiments`, `n_defined`, `n_rows`, min, max and a
# percentile bootstrap over experiments (seeded; `NaN` below five defined experiments). Levels requested
# but absent appear with `n_experiments == 0`.
#
# *Debugging:* the checks plant a slice where one large bad experiment and several small good ones give a
# row-pooled value of 0.87 and a per-experiment mean of 0.25. If you get 0.87, you pooled rows.
#
# ### Task 3 — `error_segments` (15 min)
#
# Classify every run of wrong rows using the tree in section 2.5. *Invariant to test yourself:* the
# segments' `n_rows` must sum to the number of wrong rows, and no segment crosses experiments.
#
# ### Task 4 — run it on SKAB and write the note (5 min run + writing)

# %%
!python labs/w3d6_error_analysis_transfer/lab/error_report.py

# %% [markdown]
# Checkpoint values from the reference run (2026-11-22, SKAB `b2c0d46`, frozen manifest v2): threshold
# 2.404 (development F1 0.700); row-pooled recall 0.674, mean of per-experiment recalls 0.674; failure
# kinds
#
# ```
#       kind  n_segments  n_rows  n_experiments
#   fragment         698    3039             26
#  pre_onset         730    1433             24
# post_event         432    1212             23
#       late           5     243              5
#   boundary          26     192             19
# ```
#
# No event is missed outright. If your numbers differ, check the threshold convention (`score >=
# threshold` is flagged) and that `burn_in=100` rows are excluded.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/labs/w3d6_error_analysis_transfer/figures/recall_per_experiment.svg" alt="Per-experiment recall of the flow-rate baseline on 27 real SKAB development experiments ranges from 0.01 to 0.99 around a mean of 0.67, with no family clustering" width="100%">
#
# *REAL SKAB, development experiments only. The mean describes almost no experiment; the families are
# interleaved, which is the first hint that "family" will not be the explanation.*
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/labs/w3d6_error_analysis_transfer/figures/failure_kinds.svg" alt="Failure kinds of the flow-rate baseline: fragments account for 3,039 of the wrong rows, pre-onset 1,433 and post-event 1,212; no event is missed" width="100%">
#
# *REAL SKAB, same run. Left: wrong rows by kind; right: number of segments. Rows and segments rank the
# kinds differently for `late`: few segments, each long.*
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/labs/w3d6_error_analysis_transfer/figures/alarm_strips.svg" alt="Score traces for four real SKAB experiments showing a held detection, a dropout after onset, an 80-row late detection, and alarms before the labelled onset" width="100%">
#
# *REAL SKAB, development experiments. One experiment per failure kind: `valve1/12` (detected and held), `other/5` (fragment),
# `other/7` (late), `other/13` (pre-onset, the experiment with contradictory labels). Look at the
# shaded label and the alarm ticks, not the score scale.*
#
# Now fill in `lab/ERROR_ANALYSIS.md` from your own run: object, headline, the ranked failure-mode table
# (size, evidence, suspected cause, cost, fixability), slices examined and found unremarkable, label
# issues, one next experiment per top mode with the result that would falsify it, and limits. One page.
# Figures regenerate with `python labs/w3d6_error_analysis_transfer/figures/make_figures.py`.
#
# **If the lab runs long:** finish the note on the review day. Do not let it eat into the 90-minute
# sitting.

# %%
# Run the automated checks on your guided lab.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w3d6")

# %% [markdown]
# ## 5. Independent challenge: transfer exercise, part 2 (90 minutes, timed)
#
# [`challenge/README.md`](../labs/w3d6_error_analysis_transfer/challenge/README.md). LedgerLine, an invented B2B software vendor (SYNTHETIC
# data, schema in [`data/README.md`](../labs/w3d6_error_analysis_transfer/data/README.md)), wants to know whether a model could choose its
# 15 weekly collection calls better than a simple rule. You implement the evaluation in
# `challenge/evaluate.py` (fixed signatures) and write a one-page `challenge/REPORT.md`: framing, leak
# audit, split, baseline and model, decision metric, interval, one error slice, limitations.
#
# Rules: one unbroken sitting, timer on, no hints, no solutions, no assistant. Record start and stop time
# and anything you looked up in the report's conditions box. An unfinished honest evaluation is worth
# more than a finished one with a leak.

# %%
!python labs/w3d6_error_analysis_transfer/challenge/evaluate.py
!python wb.py check w3d6 --challenge

# %% [markdown]
# The checks grade what the model may see, how the data is split, what the metric computes, and whether
# the reported performance is possible at all. They do not reward a higher score. The report is read
# against `solutions/labs/w3d6_error_analysis_transfer/challenge/SCORING.md` after you stop.
#
#
# ### The challenge brief
#
#
# **Independent and timed. 90 minutes, one sitting, no hints, no solutions, no assistant.**
# Set a timer. When it rings, stop, commit what you have, and write down what is missing. An unfinished
# honest evaluation scores higher than a finished one with a leak.
#
# This is the second sitting of the course's transfer exercise (part 1 was the w2d6 challenge). The
# data is **SYNTHETIC**: an invented B2B vendor, "LedgerLine". Schema and limits:
# `../data/README.md`. It replaces a public business dataset whose access and
# licence could not be verified from the authoring environment (see the w2d6 challenge). Being
# simulated, it tells you nothing about real customers; it does let the checks compare your estimate
# with the generator's ground truth.
#
# #### Situation
#
# LedgerLine's collections team can make **15 proactive calls per week**. A call to a customer whose
# invoice would have been paid late tends to bring payment forward; a call about an invoice that would
# have been paid on time is wasted and mildly annoying. Each Monday they choose 15 of the invoices
# issued in the previous seven days. They currently choose by gut feeling.
#
# They ask: *if a model picked the 15, what share of our calls would land on invoices that really go
# late, and is that better than a simple rule we could apply ourselves?* The model would be trained
# once, on everything known on 2024-09-30, and used from 2024-10-01.
#
# You receive one export, `../data/invoices.csv`, with a data dictionary.
#
# #### What to produce
#
# 1. `challenge/evaluate.py`: implement the five pieces whose signatures are fixed in the file
#    (`FEATURES`, `split_train_test`, `weekly_topk_precision`, `fit_and_score`, `run`).
# 2. `challenge/REPORT.md` (template provided, one page): framing, leak audit, split, baseline and
#    model, metric, interval, one error slice, limitations.
#
# Suggested use of the 90 minutes: 10 framing and reading the dictionary, 15 leak audit, 15 split and
# metric, 25 baseline and model, 10 interval and slice, 15 writing.
#
# #### Acceptance criteria
#
# * `python wb.py check w3d6 --challenge` passes (19 checks, about 15 s). The checks grade the
#   *evaluation*: what the model may see, how the data is split, what the metric computes, and whether
#   the reported performance is possible at all. They do not reward a higher score.
# * Every column of the table is classified in the report as usable or not at issue time, with the reason.
# * The split matches the deployment described above, including what is and is not known on 2024-09-30.
# * The reported number is the decision metric, compared with a rule that needs no model, with an
#   interval whose resampling unit you justify.
# * One slice of the model's behaviour is reported with its size, and the report says what you would
#   check next.
# * Limitations name at least: what the synthetic data cannot show, what the interval does not cover,
#   and one way the deployment could differ from the test period.
#
# #### Recording the sitting
#
# In `REPORT.md`, fill in the conditions box: start and stop time, anything you looked up, whether you
# finished. Then `python wb.py mark w3d6 independent` only if the sitting was unassisted and the checks
# pass; otherwise `python wb.py mark w3d6 review`.
#
# Scoring guidance and a reference report are in
# `solutions/labs/w3d6_error_analysis_transfer/challenge/`. Open them after you have stopped.

# %%
# Run the automated checks on your independent challenge.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w3d6", challenge=True)

# %% [markdown]
# ## 6. Progressive hints
#
# For the **lab** only, open in order and note in `progress/notes.md` which level you used. The hint files
# also contain challenge hints; using them during the sitting makes it a guided attempt, which you then
# record as `review`, not `independent`.
#
# 1. [Conceptual hint](../labs/w3d6_error_analysis_transfer/hints/hint1_concept.md)
# 2. [Suggested approach](../labs/w3d6_error_analysis_transfer/hints/hint2_approach.md)
# 3. [Partial implementation](../labs/w3d6_error_analysis_transfer/hints/hint3_partial.md)
#
# Full reference: `solutions/labs/w3d6_error_analysis_transfer/` (lab, reference error analysis,
# challenge reference, scoring guidance, answers).
#
#
# Open one hint at a time, only after a real attempt.
#
# <details>
# <summary><b>Hint 1 concept</b></summary>
#
#
# Opening this hint means the work is recorded as guided, not independent.
#
# **Lab.** Every function in `flowguard.erroranalysis` is a group-by over experiments followed by
# arithmetic on two aligned 0/1 arrays, `label` and `flag`. The three ideas the checks enforce:
#
# 1. *The experiment is the unit.* A slice value is the mean of per-experiment numbers. If you find
#    yourself summing TP and FN across experiments before dividing, you are computing something else.
# 2. *Undefined is `NaN`.* Ask of every ratio: what is the denominator, and can it be zero? If it can,
#    the answer in that case is "not measurable", and it must stay out of means.
# 3. *A wrong row belongs to a run, and a run belongs to an event (or to none).* Classify the run by
#    where it sits relative to the labelled event and to the event's first detection.
#
# **Challenge.** Three questions settle most of it, and none is about modelling:
#
# * For each column: *on what date does this value come into existence?* Compare that with the issue date.
# * For each training row: *on the day the model is trained, has its label been decided?*
# * For the metric: *what exactly does the team do on a Monday, and with which invoices?*
#
# </details>
#
# <details>
# <summary><b>Hint 2 approach</b></summary>
#
#
# **Lab**
#
# * Write one private helper that validates lengths, builds a frame with `experiment_id, family, t,
#   label, flag`, and drops rows with `t < burn_in`. All three public functions start from it.
# * Write one helper that turns a boolean array into inclusive `(start, end)` runs. Pad with `False` on
#   both sides and look at where consecutive values differ.
# * `per_experiment_table`: inside each experiment sort by `t`, then count. Detection delay uses only
#   flagged rows whose label is 1; a flag before onset is a false alarm, not an early detection.
# * `slice_metrics`: for each level take the metric column, split it into defined and undefined, and
#   report both counts. Bootstrap only if at least `MIN_EXPERIMENTS_FOR_INTERVAL` are defined:
#   draw indices of experiments with replacement, `n_boot` times, and take the 2.5 % and 97.5 % quantiles
#   of the resampled means. Levels passed in `levels` but absent from the data still get a row.
# * `error_segments`: first find the events (runs of label 1). For each event, find the first flagged
#   position. No flag: one `miss` segment spanning the event. Otherwise the missed runs inside the event
#   are `late`/`boundary` (if the run starts at the event's first row) or `fragment` (if not). Then
#   handle the false-alarm runs: does the run touch an event edge and is it short? Is it before the
#   first event, after the last, or is there no event?
# * Check yourself with the invariant: the segments' `n_rows` sum to the number of wrong rows.
#
# **Challenge**
#
# * Leak audit: sort the columns into "printed on the invoice", "customer attribute", "history as of the
#   issue date", "computed later". Two columns come from a master table that is overwritten in place.
#   A quick test for such a column: is it constant within a customer over two years?
# * Split: test is everything issued from the cut-off. Train is not "everything before": compute the date
#   on which each label is decided and compare it with the cut-off.
# * Metric: add a week number to the test frame, sort by score, take the first `k` per week.
# * Sanity bound: an AUC in the high 0.8s or above on this table means a leak. Find it before going on.
# * Interval: decide what the independent unit is among the *called* invoices.
#
# </details>
#
# <details>
# <summary><b>Hint 3 partial</b></summary>
#
#
# **Lab: the two helpers and the core of `error_segments`**
#
# ```python
# def _runs(mask):
#     padded = np.r_[False, mask.astype(bool), False]
#     change = np.flatnonzero(padded[1:] != padded[:-1])
#     return [(int(a), int(b) - 1) for a, b in zip(change[::2], change[1::2])]   # inclusive ends
#
# # inside one experiment, with y (labels), f (flags), t sorted by time:
# events = _runs(y == 1)
# for start, end in events:
#     hits = np.flatnonzero(f[start:end + 1])
#     if len(hits) == 0:
#         add("miss", start, end)
#         continue
#     first_hit = start + int(hits[0])
#     for a, b in _runs(f[start:end + 1] == 0):
#         a, b = a + start, b + start
#         if a == start:
#             ...   # late if (first_hit - start) > late_after, else boundary
#         else:
#             ...   # fragment
# for a, b in _runs((y == 0) & (f == 1)):
#     touches = any(b + 1 == start or a - 1 == end for start, end in events)
#     ...           # no events -> false_alarm; touches and short -> boundary; else pre_onset / post_event / false_alarm
# ```
#
# The bootstrap in `slice_metrics`:
#
# ```python
# rng = np.random.default_rng(seed)
# means = defined[rng.integers(0, len(defined), size=(n_boot, len(defined)))].mean(axis=1)
# ci_low, ci_high = np.quantile(means, [0.025, 0.975])
# ```
#
# **Challenge: split and metric**
#
# ```python
# cutoff = pd.Timestamp(test_start)
# test = df[df["issue_date"] >= cutoff]
# label_known = df["due_date"] + pd.Timedelta(days=30) < cutoff
# train = df[label_known & (df["issue_date"] < cutoff)]
#
# frame = test.assign(_score=scores, _week=(test["issue_date"] - cutoff).dt.days // 7)
# called = frame.sort_values("_score", ascending=False, kind="stable").groupby("_week").head(k)
# ```
#
# What remains yours: which columns go into `FEATURES` and why, the baseline rule, the model, the
# interval, the slice, and the report. The full reference is in
# `solutions/labs/w3d6_error_analysis_transfer/`.
#
# </details>

# %% [markdown]
# ## 7. Assessment
#
# assessment.md (section 7 of this notebook): seven reasoning questions (five on the lab, two on the challenge,
# answer those after your sitting), one design-choice explanation (how to choose a hysteresis rule
# without fooling yourself), a rubric, and an interview rep on the **debugging** strand: a fraud model
# whose AUC drops from 0.97 to 0.71 after launch, narrated aloud. Model answers and common incorrect
# answers: `solutions/labs/w3d6_error_analysis_transfer/assessment_answers.md`.
#
# Automated checks: `python wb.py check w3d6` (32 checks on planted SYNTHETIC frames: the functions must
# recover the planted worst slice, classify constructed segments, keep undefined values undefined) and
# `--challenge` (19 checks). Neither grades the quality of your written analysis; the rubric does.
#
#
# ### Assessment questions
#
#
# Write answers before opening `solutions/labs/w3d6_error_analysis_transfer/assessment_answers.md`.
# Short answers: 3-6 sentences, with a number where one exists.
#
# #### Reasoning questions
#
# 1. In the lab output, row-pooled recall is 0.674 and the mean of per-experiment recalls is 0.674. In
#    the planted check data the same two quantities are 0.87 and 0.25. What property of the data makes
#    them agree in one case and disagree in the other, and which would you report to (a) the reliability
#    engineer and (b) someone sizing compute for alert storage?
# 2. Fragment errors are 698 segments and 3,039 rows; late detections are 5 segments and 243 rows. The
#    stakeholder's stated concern is detection delay. Rank the two with frequency x cost x fixability,
#    making your assumptions explicit, and say what evidence would reverse your ranking.
# 3. You examine recall by family, by gap presence, by row-sharing, by burn-in flow level and by "flow
#    moves less than 1 sd under the fault". Only the last shows a difference (0.355 vs 0.766). Give two
#    distinct reasons why it should not be reported as a discovered failure slice.
# 4. `other/13` has false-alarm rate 0.880 and a 329-row pre-onset alarm. `other/12` and `other/13`
#    share 178 rows with contradictory labels. What can and cannot be concluded about the detector from
#    `other/13`, and how would you present these two experiments in a results table?
# 5. At threshold 2.4044 (the tuned value) `valve1/3` has recall 0.834; at 2.4061, the next distinct score
#    value, it has 0.765.
#    Explain the mechanism, and state which of your error-analysis conclusions survive it.
# 6. (Challenge) The honest model reaches 0.722 and the no-model rule 0.727 on 209 calls. A colleague
#    proposes gradient boosting "to get clearly ahead of the rule". Using the generator ceiling (0.751)
#    and the interval (0.651 to 0.783), say what you expect and what you would do instead.
# 7. (Challenge) The temporal split with and without the label-delay exclusion gives the same AUC
#    (0.763 vs 0.764). Why is the exclusion still required, and in what situation would the two differ a lot?
#
# #### Design-choice explanation (about 150 words)
#
# Your next experiment is hysteresis: raise the alarm at the current threshold, clear it only after the
# score has stayed below a lower threshold for `h` rows. Choose how you will pick `h` and the lower
# threshold, on which data, with which metrics, and how you will prevent the choice from being an
# artefact of the 27 development experiments. State the side effect you expect and the result that
# would make you abandon the idea.
#
# #### Rubric
#
# | Criterion | Not yet | Adequate | Strong |
# |---|---|---|---|
# | Unit of analysis (Q1) | treats the two numbers as interchangeable | explains weighting by rows vs by experiments | ties each to a question someone actually has |
# | Ranking (Q2) | ranks by size only or by cost only | uses all three factors with stated assumptions | names the evidence that would change the ranking |
# | Slice discipline (Q3) | accepts the slice | names multiplicity or label-dependence | both, plus what a legitimate version would look like |
# | Label noise (Q4, Q5) | blames the model or blames the labels wholesale | separates irreducible from model error | proposes reporting with and without, and notes fragility of per-experiment numbers |
# | Evidence versus effort (Q6, Q7) | expects a better model to fix it | uses ceiling and interval to bound the gain | redirects effort to the causal question or to the no-history slice; explains construction over measurement |
# | Design choice | tunes on test, or on all dev at once | grouped cross-validation over experiments, both metrics | also pre-states the abandon criterion and the delay cost |
#
# #### Interview rep (debugging narrative, 10-15 minutes, spoken; Week 3 conditions: timed, rubric only)
#
# > "A fraud model had validation AUC 0.97. Two weeks after launch, on the first labelled production
# > sample, AUC is 0.71. Talk me through how you would investigate. I will answer questions about the
# > system if you ask them."
#
# Speak for five minutes without notes, then write down the ordered list of hypotheses you gave and the
# single query or check you would run for each. Compare with the rubric in `assessment_answers.md`
# only after writing. Per the Week 3 rule, no worked answer is given until you have made a second
# attempt.

# %% [markdown]
# ## 8. Reflection and review
#
# **You should now be able to, without notes:**
#
# * build a per-unit error table and say which average a stakeholder needs;
# * classify detector errors into runs by kind and size them;
# * say when a slice difference is evidence and when it is the multiplicity of the search;
# * separate irreducible label noise from model error and report both;
# * run a complete, leak-free evaluation of an unfamiliar tabular problem in 90 minutes.
#
# **Reflection prompt** (5 minutes, `progress/notes.md`). In the timed sitting, which step did you
# spend the most time on, and which step did you skip or rush? Was that the step most likely to make
# the number wrong?
#
# **Retrieval question for later** (review day): a slice of 6 experiments has mean recall 0.41 against
# 0.70 for the other 19, and it was the lowest of 12 slices you examined. List three things you must
# check before writing it in a report, and the one-line test you would run on new data.
#
# **Next.** [w3d7 review](../labs/w3d7_review/README.md), then Week 4: time-series models and evidence-based
# model choice. The top failure mode here (fragmentation) and the late detections set up w4d1: a
# detector whose score uses temporal context instead of a per-row threshold.
#
# ---
#
# ### Verification record
#
# Executed on 2026-11-22 with Python 3.13.18, NumPy 2.5.3, pandas 3.0.5, SciPy 1.18.1, scikit-learn
# 1.9.1: both worked examples (outputs above); the reference `error_report.py` on SKAB at `b2c0d46`
# (tables above); `figures/make_figures.py` (four figures, values printed and matching the report);
# the reference challenge (`evaluate.py`: rule 0.727, model 0.722 with customer-bootstrap interval
# 0.651-0.783 on 209 calls); `data/make_invoices.py --check` (byte-identical);
# `python tools/verify_checks.py labs/w3d6_error_analysis_transfer` (reference passes both parts; 4
# lab and 5 challenge mutants rejected); the shipped starters fail (lab 32 of 32; challenge 14 failed,
# 5 errors). Not verified: Python 3.11/3.12; the time boxes, in particular whether 90 minutes suffices.
#
#
# 2026-11-22: real-data scripts switched to the frozen w3d1 manifest (`lab/splits/v2.json`, 7 test
# experiments) instead of redrawing a split with `make_splits`; every real-SKAB number and figure in this
# unit was regenerated from a fresh run.

# %% [markdown]
# ## Record your progress
#
# Tick only what is true. Passing the supplied checks is *guided practice*; mark *independent* only for work done without hints or solutions.

# %%
from mlcourse.progress import mark, note

# mark("w3d6", "reading")
# mark("w3d6", "guided")
# mark("w3d6", "independent")
# note("w3d6", "what tripped me up today")

