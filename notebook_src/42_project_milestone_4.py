# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/42_project_milestone_4.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 42 · Project milestone 4: monitoring demonstration and runbook
#
# **Week 7 · day 6 · 2 h essential path + up to 1 h optional** · lab files: [`labs/w7d6_project_milestone_4/`](../labs/w7d6_project_milestone_4/)
#
# **Objective.** Demonstrate monitoring on a replay of held-out experiments and document operating procedures.

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
# Unit id `w7d6_project_milestone_4` · Week 7, day 6 · Handbook:
# [H15.6 Reliability patterns](../docs/handbook/ch15_logging_monitoring_updates/h15_6_reliability_patterns.md),
# [H15.2 Operational debugging](../docs/handbook/ch15_logging_monitoring_updates/h15_2_operational_debugging.md);
# H15.1 service logs and metrics, H15.3 drift, H15.4 delayed labels and H15.5 updates and rollback come with
# w7d1-w7d4 · Content status: see [STATUS.md](../docs/guides/status.md)
#
# **This is an independent integration session.** Like [w4d6](24_project_milestone_1.ipynb) and
# [w5d6](30_project_milestone_2.ipynb), the lab is a checklist and a contract, not a walkthrough.
# You integrate this week's pieces (reliable service, input monitoring, drift, delayed labels, registry and
# rollback) into one reproducible demonstration and write the runbook an on-call engineer would use.

# %% [markdown]
# ## 1. Purpose
#
# **Objective.** One command replays a scripted scenario of real held-out SKAB experiments through the
# running service. The scenario covers normal operation, a units bug, input drift, two real faults,
# delayed labels, a bad promotion and its rollback. The command writes a report in which every number
# comes from a machine-readable results file. Your runbook tells an on-call engineer what each alert
# means and what to do first.
#
# **Why an applied ML engineer needs it.** "How would you know the model is failing in production?" is the
# question that separates a demo from a service. The honest answer is never "accuracy". Labels arrive
# late or never, so you watch a set of proxies: inputs outside what the model has seen, input
# distributions that have moved, alarm rates that exceed what the business accepts, degraded answers, and
# the readiness of the process. Then you reconcile with labels when they come. A monitoring demo proves you
# have wired those signals and that each fires for the problem it is meant to catch. A runbook proves
# someone other than you can act on them.
#
# **Deliverables (milestone 4).**
# * In your flowguard repository: `make monitor-demo` (or the `python -m flowguard monitor-demo` command)
#   producing `reports/monitoring_demo.md` and `reports/results.json` from raw data, the frozen manifest and
#   `scenarios/demo.toml`; `RUNBOOK.md` covering every alert in `configs/alerts.toml`.
# * `challenge/SUBMISSION.md` filled in and pushed for review.
#
# **Completion criteria.**
# * `python wb.py check w7d6`: on a SYNTHETIC copy of your project, the demo runs twice with identical numbers.
#   Every scripted event appears in the timeline with its detection stated, each scripted problem raises
#   its signal, the report's numbers equal `results.json`, every service process is stopped, and the
#   runbook has the required sections and an entry for every alert.
# * The same command on the real data in your repository.
# * `python wb.py check w7d6 --challenge` passes and the submission is pushed.
#
# **Prerequisites.** [w7d5](41_reliability.ipynb) (guards, degradation, drills), w7d1-w7d4
# (structured logs and golden signals; drift; delayed labels; registry, promotion and rollback),
# [w6d6](36_cd_ops_debugging.ipynb) (rollback by digest, debugging logs), [w4d6](24_project_milestone_1.ipynb)
# (a report generated by a command). The lab ships a complete snapshot (flowguard 0.9.0) with minimal
# versions of the w7d1-w7d4 modules, so you can work from it or port the checklist to your own repository.
#
# **Time budget (2 h essential).**
#
# | Activity | Minutes |
# |---|---|
# | Read section 2; run the starter once and read its report critically | 25 |
# | Lab: find and fix the three planted problems (checks guide you) | 35 |
# | Lab: write the runbook | 35 |
# | Real data: run the demo, read the report as a reviewer, compare with the reference | 15 |
# | Submission and self-review (the challenge) | 10 |
# | *Optional extension: add an injected model fault (`FLOWGUARD_FAULTS`) as a scenario event; alert on the degraded rate; a drift monitor on normalised values* | *up to 60* |

# %% [markdown]
# ## 2. Conceptual explanation
#
# ### 2.1 What the demonstration must show
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/docs/assets/diagrams/mmd-42-01.svg" alt="Diagram 1 of notebook 42" style="max-width:100%">
#
# Each event in the scenario tests one link between a problem and the signal that should catch it:
#
# | Event | Problem | Signal expected | Why that signal and not another |
# |---|---|---|---|
# | E1-normal | none | none | an alarm here is a false alarm; a monitor that cries wolf is ignored |
# | E2-units-bug | client sends L/h (×60) | `out_of_support` | the z-score is scale invariant (w7d5), so the model cannot see it |
# | E3-input-drift | pump at 80 % flow | `drift` | in range, so no support alert; burn-in adapts, so no alarms |
# | E4-fault, E5-fault | real valve faults | `detector` | the product working; E5 is a fault the model is known to miss |
# | E6-labels | inspection results arrive | `delayed_eval` | the only measurement of actual performance |
# | E7-bad-promotion | threshold typed as 1.5 | `alarm_rate` | no labels yet, but an alarm share far above budget on normal data |
# | E8-rollback | recovery | `version_restored` | the registry pointer is not enough: `/version` must change |
#
# **Drift is not degradation.** E3 shows inputs moving with no change in alarms. E2 shows a broken input
# with no change in alarms either. Labels (E6) are the only direct evidence of performance, and they
# cover only the traffic that was inspected.
#
# ### 2.2 The reference run on real data
#
# `make monitor-demo` on the 7 held-out test experiments of the frozen v2 manifest. It ran in 3.3 s
# end to end, with three service processes started and stopped:
#
# | # | Event | Model version | Signals fired | Result |
# |---|---|---|---|---|
# | 1 | E1-normal | flowrate-z-2026.11 | none | as expected |
# | 2 | E2-units-bug | flowrate-z-2026.11 | out_of_support, drift | as expected |
# | 3 | E3-input-drift | flowrate-z-2026.11 | drift | as expected |
# | 4 | E4-fault (valve1/13) | flowrate-z-2026.11 | alarm_rate, detector | as expected |
# | 5 | E5-fault (valve1/8) | flowrate-z-2026.11 | none | **not detected** (expected detector) |
# | 6 | E6-labels | flowrate-z-2026.11 | delayed_eval | as expected |
# | 7 | E7-bad-promotion | flowrate-z-2026.12-rc1 | alarm_rate, detector | as expected |
# | 8 | E8-rollback | flowrate-z-2026.11 | version_restored | as expected |
#
# Summary from `results.json`: 7 of 8 events as expected; 5,084 values scored; 560 out-of-support values (all of
# E2); drift threshold 7.5253; delayed labels covered 3 replays with 2 labelled faults, 1 detected, 0 false
# alarm events (event recall 0.5 from 2 faults, which says almost nothing about the true rate); 2 service
# restarts. A second run produced identical numbers. The full generated report is
# `solutions/labs/w7d6_project_milestone_4/example_demo/monitoring_demo.md`.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/labs/w7d6_project_milestone_4/figures/demo_signals.svg" alt="Alarm rate is above budget only for the real fault and the bad promotion; drift PSI crosses its threshold for the units bug and the 80 % flow replay; only the units bug is out of support" width="100%">
#
# *Figure 1. Signals per replayed event in the reference demo (REAL data). Orange bars are above their
# alert line. The missed fault E5 looks exactly like normal operation, which is why the report must say
# "not detected" rather than leave it out.*
#
# ### 2.3 Calibrating an alert, and what calibration cannot fix
#
# An alert threshold must come from data where the answer is known to be "no alert": here, the normal rows
# of the 27 development experiments. The demo sets the drift threshold at the *largest* PSI observed among
# them, 7.53. With 27 exchangeable healthy windows, a new healthy window exceeds the maximum with
# probability about 1/28. That is the false-alarm rate the choice implies.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/labs/w7d6_project_milestone_4/figures/drift_calibration.svg" alt="Calibration PSI of 27 development experiments lies between 3.26 and 7.53; a healthy test experiment reaches 7.38, just under the threshold; the 80 % flow replay reaches 9.62" width="100%">
#
# *Figure 2. The calibration set (REAL). Single healthy experiments already sit far from the pooled
# reference, because SKAB experiments run at different, nearly constant flow levels. The healthy part of
# test experiment `other/1` reaches 7.38, a hair under the threshold.*
#
# The figure is the most important result of the milestone. The monitor "works" in the demo, but its margin
# is thin: one healthy test experiment came within 2 % of alerting. A raw-value PSI against a pooled
# reference is a coarse signal when the population of machines is heterogeneous. Better options exist
# (per-machine references, monitoring normalised values or burn-in statistics, w7d2), and the runbook's
# known limitations must say so. A milestone that shows only green ticks without this caveat would be
# less trustworthy, not more.
#
# ### 2.4 Promotion and rollback are process events, not file events
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/docs/assets/diagrams/mmd-42-02.svg" alt="Diagram 2 of notebook 42" style="max-width:100%">
#
# A running process loaded its bundle at startup. Changing the pointer changes nothing until the process is
# replaced, and replacing it means stopping the old one. Two of the three planted problems in the starter
# live exactly here.
#
# ### 2.5 A report you can trust
#
# Every number in `monitoring_demo.md` is rendered from `results.json`, and `results.json` is written by
# the same run. Nothing is pasted. The report states, for every scripted event, whether it went as
# expected, including "not detected" and "UNEXPECTED ALERT". Hiding a miss is worse than having one.
#
# ### 2.6 The runbook
#
# A runbook entry answers three questions in the order an on-call engineer needs them:
#
# * **Meaning:** what is true when this fires?
# * **First actions:** what do I check or do in the next ten minutes, with exact commands?
# * **Escalate:** when, and to whom?
#
# The required sections are service overview, dashboards and queries, alerts (one `### <AlertName>` per alert
# in `configs/alerts.toml`), common incidents, rollback, escalation and known limitations. Known
# limitations carry the measured weaknesses: the fallback detects 2 of 7 test faults, the drift margin is
# thin, and the labelled set is tiny.
#
# ### 2.7 An industry example
#
# A team ships a demand-forecasting model for a grocery chain. Its "monitoring" is a weekly accuracy
# report, which arrives eight days after the fact because sales are reconciled weekly. A supplier changes
# the unit of one product feed from items to cases. Forecasts for 300 products drop by a factor of 12. A
# scale-invariant model would not even notice; this one does, but nothing alerts until the weekly report.
# The fix teams converge on is this milestone in miniature: input guards per feature, drift on inputs
# against a calibrated threshold, an output-rate monitor (share of forecasts that changed by more than
# 50 % week on week), a scripted replay that proves each alert fires, and a runbook entry per alert. An
# illustrative composite, not a documented single incident.
#
# ### 2.8 Limitations and misconceptions
#
# * *"All green means healthy."* E5 was quiet and wrong. Proxies catch some failures; only labels measure
#   performance, and late.
# * *"Drift means retrain."* E3 drifted with unchanged alarms. Drift is a reason to look, not a decision.
# * *"The rollback is done when the registry says so."* It is done when `/version` says so on every instance.
# * *"A demo on synthetic data proves the monitors work."* The checks use synthetic data to test that your
#   code wires signals correctly. Only the real-data run shows the thin drift margin.
# * Not covered: multi-instance rollouts, alert routing and paging tools, dashboards beyond queries,
#   long-term storage of logs.

# %% [markdown]
# ## 3. Worked example: reading the starter's report
#
# Run the starter once on the real data before changing anything:
#
# ```bash
# cd labs/w7d6_project_milestone_4/lab
# make monitor-demo RAW=../../../data/raw/skab OUT=reports        # or the python -m form in the Makefile
# ```
#
# The command finishes, and the report looks plausible. Read it as a reviewer would and ask three
# questions. They are the method of this session, and the checks ask the same ones.
#
# 1. **Does the version column follow the registry history at the bottom of the report?** Look at the
#    rollback row.
# 2. **Is every number in the report in `results.json`?** Compare the Summary table with
#    `python -c "import json; print(json.load(open('reports/results.json'))['summary'])"`.
# 3. **Did every process the demo started stop?** The report prints `all stopped:`. Then check for
#    yourself: `pgrep -af flowguard.api` should print nothing.
#
# Each "no" is one planted problem. In the reference run the answers are: the rollback row shows
# `flowrate-z-2026.11`; the drift threshold is 7.5253 in both files; three processes were started and
# `pgrep` finds none.
#
# **If `pgrep` finds leftover servers**, stop them before anything else: `pkill -f flowguard.api:app_from_env`.

# %% [markdown]
# ## 4. Lab: the milestone checklist
#
# The starter (`lab/`) is a complete project: `src/flowguard/` (service, guards, monitoring, registry, demo
# runner, CLI), `configs/` (model, service settings, alerts), `scenarios/demo.toml`, `splits/v2.json`, a
# Makefile and four unit tests. It runs, but its report cannot be trusted yet.

# %%
!python wb.py check w7d6

# %% [markdown]
# Work through the checklist. The checks tell you which items fail; hints 1-3 narrow it down.
#
# 1. **Fix the three planted problems** in `src/flowguard/demo.py`. They are in the promotion/rollback
#    branch and in `render_report`; section 3 tells you how to find them by reading the output.
# 2. **Write `RUNBOOK.md`** from the template: every alert in `configs/alerts.toml`, with Meaning, First
#    actions (exact commands) and Escalate, plus the seven required sections. Use the real numbers from
#    your run in the overview and known limitations.
# 3. **Run on the real data** and read your report against section 2.2. Commit `reports/monitoring_demo.md`,
#    `reports/results.json` and the figure. Do not commit `reports/registry/` or `reports/service.log` if
#    your `.gitignore` policy excludes artifacts and logs; say which in the submission.
# 4. **Confirm reproducibility**: run twice, compare `summary` in both `results.json` files.
#
# *Checkpoints.* `test_versions_follow_the_registry` and `test_every_server_was_stopped` pass after the
# first fix; `test_report_summary_matches_results` after the second; the two runbook checks after task 2.
# *Debugging.* If the demo hangs at startup, a previous run left a server on the port; `pkill` it. If the
# checks report `results.json` missing, run the command from the lab directory and read its stderr. Most
# often `PYTHONPATH` does not include `src`.

# %%
# Run the automated checks on your guided lab.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w7d6")

# %% [markdown]
# ## 5. Independent challenge: submit milestone 4
#
# [challenge/README.md](../labs/w7d6_project_milestone_4/challenge/README.md): fill in `SUBMISSION.md` for your own repository, with the demo
# results copied from your `results.json`, every checklist item ticked or justified, a self-review with
# evidence, and a question for the reviewer.
#
#
# ### The challenge brief
#
#
# Run the demo on the **real** data in your own flowguard repository, read the report as a reviewer would,
# and fill in SUBMISSION.md. Tick only what is true; mark anything you did not do as `n/a`
# with a reason. Score yourself against the rubric in ../assessment.md with evidence a
# reviewer can check (a file, a number, a command). Commit the generated report and your runbook, tag the
# commit (`git tag v0.9.0-m4`), push, and push the submission.
#
# The "Demo results" fields are copied from your generated `results.json` (summary). If an event was not as
# expected (in the reference run, `E5-fault`: the model misses the fault in `valve1/8`), say so: a demo
# that shows a known miss honestly is stronger than one that hides it.
#
# **Acceptance criteria.** `python wb.py check w7d6 --challenge` passes (structure only: no TODO left, header
# and result fields well formed, every checklist item ticked or justified, every self-review row scored
# with evidence, at least one specific question). Quality is judged by the reviewer, not by the checks.

# %%
# Run the automated checks on your independent challenge.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w7d6", challenge=True)

# %% [markdown]
# ## 6. Progressive hints
#
# [Hint 1 — concept](../labs/w7d6_project_milestone_4/hints/hint1_concept.md) · [Hint 2 — approach](../labs/w7d6_project_milestone_4/hints/hint2_approach.md) ·
# [Hint 3 — partial implementation](../labs/w7d6_project_milestone_4/hints/hint3_partial.md)
#
#
# Open one hint at a time, only after a real attempt.
#
# <details>
# <summary><b>Hint 1 concept</b></summary>
#
#
# * A registry pointer and a running process are two different things. After you move `CURRENT`, which
#   process answers the next request, and which model did it load?
# * "Restart" means stop *and* start. If only the start happens, how many processes exist afterwards, and
#   which one is in `pids`?
# * A generated report has one source of truth. Search `render_report` for any number that does not come
#   from `results`.
# * For the runbook: write each alert entry for a colleague woken at 3 a.m. who has never seen this repository.
#
# </details>
#
# <details>
# <summary><b>Hint 2 approach</b></summary>
#
#
# 1. Run `python wb.py check w7d6` and read the first failing check's message; then open the matching part
#    of `src/flowguard/demo.py`:
#    * versions and servers → the `if kind in ("promote", "rollback"):` block in `run_demo`;
#    * summary mismatch → the Summary table in `render_report`, and the module constants at the top.
# 2. The reference structure of the block: switch the pointer (promote *or* rollback), then for both
#    kinds: stop the current service, start a new one from `registry.path()`, record its pid.
# 3. Delete the constant the report uses and render every summary value from `results["summary"]`.
# 4. Runbook: start from `configs/alerts.toml`. Copy each `condition` into the Meaning line and add what is
#    true when it fires; write First actions as numbered commands from the "Dashboards and queries" table.
#
# </details>
#
# <details>
# <summary><b>Hint 3 partial</b></summary>
#
#
# ```python
# # demo.py, inside the event loop of run_demo
# if kind in ("promote", "rollback"):
#     if kind == "promote":
#         registry.promote(bad.model_version if ev["version"] == "bad" else good.model_version,
#                          ev.get("reason", ""))
#     else:
#         registry.rollback(ev.get("reason", ""))
#     service.stop()
#     service = Service(registry.path(), settings_path, log_file, src_dir)
#     pids.append(service.proc.pid)
# ```
#
# ```python
# # demo.py, render_report: the Summary table comes from results only
# lines += [f"| {k} | {_fmt(v)} |" for k, v in results["summary"].items()]
# ```
#
# One runbook entry, as a shape to copy (fill in your own commands and numbers):
#
# ```markdown
# ### InputOutOfSupport
#
# **Meaning:** values outside the range seen in development data (...). Scores for them are extrapolation;
# the z-score is scale invariant, so a units error does not change alarms.
# **First actions:** 1) find the machine in `predict` log events with `out_of_support > 0`; 2) ...; 3) ...
# **Escalate:** gateway team the same day (SEV2); ...
# ```
#
# </details>

# %% [markdown]
# ## 7. Assessment
#
# assessment.md (section 7 of this notebook): the milestone rubric, reasoning questions and a 15-minute interview rep:
# "how would you know the model is failing in production?" Answers are in
# `solutions/labs/w7d6_project_milestone_4/assessment_answers.md`.
#
#
# ### Assessment questions
#
#
# #### Milestone rubric (the reviewer uses this; you self-score in SUBMISSION.md)
#
# | Criterion | 1 (below) | 2 (meets) | 3 (exceeds) |
# |---|---|---|---|
# | Reproducible demo | manual steps between runs | one command; identical numbers on rerun | plus a clean-clone run recorded |
# | Coverage of failure scenarios | normal and one fault | every event of the reference scenario | plus an injected model fault and a degraded-rate alert |
# | Report integrity | numbers typed or edited | every number from results.json | plus figures generated by the same run and a provenance block |
# | Service lifecycle and rollback | processes leak or rollback unverified | restart on every switch; `/version` checked | plus readiness gating before traffic |
# | Runbook usefulness | headings only | every alert: meaning, commands, escalation | tested by someone else following it |
# | Honesty about limitations | only green results | misses and thin margins reported | quantified (false-alarm rate implied by the threshold, label coverage) |
#
# #### Reasoning questions
#
# 1. The drift threshold is the maximum PSI of 27 healthy development windows. What false-alarm rate per
#    healthy window does that imply, and under which assumption? What would you change if 1 in 28 is too many?
# 2. E2 (units bug) fired both `out_of_support` and `drift`. Why is `out_of_support` the better alert for
#    it, and why does the alarm rate not change?
# 3. E5 is a real fault with no signal. Which signal in this system could ever reveal it, when, and why did
#    the demo list it as "not detected" rather than drop it?
# 4. A colleague's rollback script edits `CURRENT` and exits 0. List what can still be wrong and the check
#    that would catch each.
# 5. The delayed-label report gives event recall 0.5. What is the interval on that number (2 faults), and
#    what does "covers labelled traffic only" warn about? (Hint: which machines get inspected?)
#
# #### Interview rep (15 min, project explanation)
#
# > "Your model is in production. Labels come from maintenance inspections, two to six weeks later. How
# > would you know it is failing?"
#
# Answer aloud in 5 minutes, then take 10 minutes of follow-ups from the list in the answers file (have
# someone read them to you, or answer in writing without looking at the model answer). Score yourself with
# the rubric there.

# %% [markdown]
# ## 8. Reflection and review
#
# **You should now be able to, without notes:** name the production signals that stand in for accuracy
# before labels arrive and the failure each one catches; calibrate an alert threshold on data known to be
# normal and state the false-alarm rate it implies; script a replay that proves each alert fires; generate a
# report whose numbers cannot drift from the results; complete a rollback including the restart and the
# version check; and write a runbook entry someone else can follow.
#
# **Reflection prompt.** Which of your BCI or iEEG pipelines had a "proxy" you trusted in place of a label,
# such as signal quality or a classifier's confidence? When did it mislead you?
#
# **Retrieval question (for the w7d7 review).** The demo showed drift without a change in alarms (E3) and a
# missed fault without any signal (E5). For each, which signal would have revealed the problem, and when?
#
# **Next.** [w7d7 review](../labs/w7d7_review/README.md), then Week 8: [the completion audit](43_project_completion.ipynb) starts by reproducing
# this report and the milestone 1 evaluation from a clean clone.

# %% [markdown]
# ## Verification record
#
# Executed on 2026-11-22 (Python 3.13.18, FastAPI 0.165.0, uvicorn 0.54.0, httpx 0.28.1, matplotlib 3.11.2):
#
# * Reference demo on the real SKAB files: `make monitor-demo` in `solutions/.../lab`, 3.3 s wall, 7 of 8 events
#   as expected (E5 not detected), output committed in `solutions/labs/w7d6_project_milestone_4/example_demo/`;
#   a second run gave identical `summary` and per-event observations; `pgrep` found no service process afterwards.
# * `python tools/verify_checks.py labs/w7d6_project_milestone_4`: lab reference passes 17 checks, all 5 lab
#   mutants rejected; challenge reference passes 6 checks, all 4 challenge mutants rejected. The shipped
#   starter fails 7 of 17 lab checks; the challenge template fails all 6.
# * Figures regenerated by `figures/make_figures.py` (drift calibration recomputed from the raw files) and viewed
#   as PNG.
# * Not verified: Python 3.11/3.12 locally, the time budget, the demo on a machine without `make` (the checks
#   call the `python -m flowguard` form directly).

# %% [markdown]
# ## Record your progress
#
# Tick only what is true. Passing the supplied checks is *guided practice*; mark *independent* only for work done without hints or solutions.

# %%
from mlcourse.progress import mark, note

# mark("w7d6", "reading")
# mark("w7d6", "guided")
# mark("w7d6", "independent")
# note("w7d6", "what tripped me up today")

