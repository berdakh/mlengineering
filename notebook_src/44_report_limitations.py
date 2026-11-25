# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/44_report_limitations.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 44 · Technical report and model limitations
#
# **Week 8 · day 2 · 2 h essential path + up to 1 h optional** · lab files: [`labs/w8d2_report_limitations/`](../labs/w8d2_report_limitations/)
#
# **Objective.** Write a short technical report and a limitations section that a sceptical reviewer would accept.

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
# Unit id `w8d2_report_limitations` · Week 8, day 2 · Handbook:
# [H16.2 Reports and limitations](../docs/handbook/ch16_system_design_communication/h16_2_reports_and_limitations.md),
# [H16.1 Decision memos](../docs/handbook/ch16_system_design_communication/h16_1_decision_memos.md) ·
# Content status: see [STATUS.md](../docs/guides/status.md)
#
# **This is an integration and communication session.** The writing is graded with a rubric; a small tool you
# build grades the parts of a report that can be checked mechanically.

# %% [markdown]
# ## 1. Purpose
#
# **Objective.** Write a four-page technical report and a model card for flowguard in which every number is
# traceable to a results file, every estimate carries an interval and says how it was obtained, and the
# limitations say what a reader must not conclude. Build `report/check_report.py`, which enforces the mechanical
# part of that standard.
#
# **Why an applied ML engineer needs it.** Most of the value of an evaluation is lost between the results file and
# the reader. Reviewers, managers and interviewers read the report, not the code. The habits that make a report
# trustworthy (generated numbers, intervals with their unit, claims no stronger than the evidence, limitations with
# consequences) are also the ones that are easiest to drop under time pressure. Peer review teaches the same
# habits; the industry difference is that the reader often cannot ask a follow-up question before acting.
#
# **Deliverables.**
# * `report/check_report.py` (lab), passing `python wb.py check w8d2`.
# * In your repository: `reports/TECHNICAL_REPORT.md` (from `lab/report/TEMPLATE.md`), `reports/MODEL_CARD.md`,
#   and a results file the report is checked against; the checker passes on them.
# * `challenge/REVIEW.md`: a peer review of a flawed SYNTHETIC report.
#
# **Completion criteria.**
# * `python wb.py check w8d2`: the checker passes a sound SYNTHETIC report and fails each of six broken ones for
#   the right reason only.
# * Your report passes the checker and is scored against the rubric in assessment.md (section 7 of this notebook).
# * `python wb.py check w8d2 --challenge` passes.
#
# **Prerequisites.** [w8d1](43_project_completion.ipynb) (the numbers are reproducible);
# [w4d5](23_model_choice.ipynb) (decision memo); [w3d5](17_uncertainty.ipynb) (cluster bootstrap,
# Wilson intervals, paired comparisons); the milestone reports of w4d6, w5d6 and w7d6.
#
# **Time budget (2 h essential).**
#
# | Activity | Minutes |
# |---|---|
# | Read section 2; run the worked example | 20 |
# | Lab: implement the checker | 35 |
# | Write your report and model card from the template; run the checker on them | 45 |
# | Challenge: peer review | 20 (the rest in the extension) |
# | *Optional extension: finish the review (40 min box); add the report's figures to its `make` target; ask someone to read only your limitations section and say what they would not do with the model* | *up to 60* |

# %% [markdown]
# ## 2. Conceptual explanation
#
# ### 2.1 The structure of a short technical report
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/docs/assets/diagrams/mmd-44-01.svg" alt="Diagram 1 of notebook 44" style="max-width:100%">
#
# Each section answers a question a sceptical reader will ask, in the order they will ask it: what is this for, what
# data, how could the evaluation have fooled you, what did you find, where does it fail, what did you decide, how
# does it run, what must I not conclude, and can I check it. Four pages is enough for a system like flowguard if
# tables carry the numbers and prose carries the reasoning.
#
# ### 2.2 Writing results honestly
#
# * **Every number is generated.** The report is read from the results file (or written by a script that reads
#   it). A typed number drifts the first time the analysis is rerun. The w4d6 and w7d6 milestones already did this
#   for tables; the checker extends it to prose.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/docs/assets/diagrams/mmd-44-02.svg" alt="Diagram 2 of notebook 44" style="max-width:100%">
# * **Every estimate has an interval and its unit.** "0.884 [0.811, 0.928]" means little until the reader knows
#   the interval came from a cluster bootstrap over 7 test recordings. The unit of resampling is the claim about
#   what generalises.
# * **Differences are estimated directly.** Two separate intervals that overlap do not show that two models are
#   equivalent, and two that do not overlap are a conservative test; the paired interval of the difference is the
#   object of interest (figure below).
# * **"Significant" is a technical word.** Use it only with the test that produced it, and prefer the interval:
#   it says how large the effect could be, which is what the decision needs.
# * **Report what did not work.** The neural model that did not beat the classical one, the detector that fell on
#   an unseen fault family, the missed fault. Omitting them makes every remaining claim less credible.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/labs/w8d2_report_limitations/figures/overlap_vs_paired.svg" alt="Left: test PR-AUC intervals of the two best detectors overlap; right: on development data the paired difference is +0.069 with interval 0.022 to 0.128, which excludes zero but not the 0.05 practical threshold" width="100%">
#
# *Real SKAB results from the w4d6 reference (`figures/make_figures.py`). The left panel is the single test look,
# the right panel the development comparison on which the decision was made. Neither "the intervals overlap, so
# no difference" nor "the interval excludes zero, so the bigger model is better" is the right reading.*
#
# ### 2.3 How wide is "5 of 7"?
#
# With few events, the uncertainty is the result. The Wilson interval for a proportion $\hat p = k/n$ is
#
# $$\frac{\hat p + \frac{z^2}{2n} \pm z\sqrt{\frac{\hat p(1-\hat p)}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}, \qquad z = 1.96 \text{ for } 95\,\%.$$
#
# For 5 of 7 it is [0.36, 0.92]: the detector might catch a third of faults or nine in ten. Even all 34 SKAB
# events would give an interval about 0.29 wide.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/labs/w8d2_report_limitations/figures/wilson_width.svg" alt="Width of the 95 % Wilson interval for a recall of 5/7 against the number of events: 0.56 at 7 events, 0.29 at 34, still 0.12 at 200" width="100%">
#
# *Computed (no data). A limitation is honest when it is quantified like this rather than called "small sample".*
#
# ### 2.4 Limitations that matter
#
# A limitation is useful when it tells the reader what not to do with the model. Write each one as: the fact, its
# impact (what conclusion or use it rules out), and the mitigation (what you did, or what would be needed). For
# flowguard the list writes itself from the course's own findings: 7 test recordings and 34 faults in total; 1,290
# duplicated rows with 235 conflicting labels; a laboratory testbed rather than a plant; detectors losing about a
# quarter of their PR-AUC on an unseen fault family; a drift monitor that flags few fault windows and fires on a
# harmless recalibration; degradation without drift; a weak fallback; a thin drift-alert margin.
#
# What does *not* belong: generic disclaimers ("more data could help"), limitations of methods you did not use, and
# apologies. What reviewers reject outright: claims of real-world or clinical validity from a benchmark, causal
# statements from a predictive model, "state of the art" without the comparison, and accuracy on imbalanced data.
#
# ### 2.5 The model card
#
# A model card is a one-page summary for people deciding whether to use the model: what it does, intended and
# out-of-scope uses, data, performance with intervals, inputs and outputs, known failure modes, monitoring and
# update policy, and ethical or practical considerations. It is a projection of the report, not a separate
# analysis, so its numbers come from the same results file.
#
# ### 2.6 What the checker can and cannot do
#
# | Rule | Catches | Cannot catch |
# |---|---|---|
# | required sections | a missing limitations or reproducibility section | a section that says nothing |
# | number trace | typed, stale or edited numbers | a number traced to the wrong field (the value 0.143 also matches "14 %") |
# | interval method | intervals with no stated unit or method | the wrong unit (row bootstrap with clustered data) |
# | "significant" needs a test | the bare word | a test that does not fit the design |
# | limitation items need impact and mitigation | lists of bare caveats | trivial or misleading limitations |
#
# The checker is a linter. The rubric and a human reviewer judge the rest; the challenge practises being that reviewer.
#
# ### 2.7 Connection to other domains
#
# The structure is a paper's, compressed: problem, data, methods, results, discussion. The differences are the
# reader (a decision-maker, not a referee), the decision section (what to do now), the serving and monitoring
# section (the model keeps running after the report), and the expectation that a reader can regenerate every number.
# The limitations sections of clinical and scientific papers transfer directly: "evaluated on 7 recordings from one
# testbed" is the same sentence as "evaluated on 9 patients from one centre".
#
# ### 2.8 An industry example
#
# A fraud team reports that a new model "reduces losses by 12 %". Finance budgets on it. The number came from one
# month of replayed transactions with the threshold tuned on that month, and the interval, never computed, would
# have spanned zero. The model under-delivers, and the team's next report is read with suspicion. The same work
# written as "+12 % [-3 %, +25 %] on one replayed month, threshold tuned on the same month; a shadow period is needed
# before budgeting" would have led to the right decision and protected the team's credibility.

# %% [markdown]
# ## 3. Worked example: a paragraph generated, not typed

# %%
!python labs/w8d2_report_limitations/example/write_results_paragraph.py

# %% [markdown]
# Output (copied from a run on 2026-11-25; real SKAB results from the w4d6 reference):
#
# ```text
# == Written by hand (what reviewers reject)
# The supervised model is better (0.90 vs 0.88 PR-AUC), and our detector is highly reliable (5/7 faults detected).
#
# == Generated from the results file
# On the 27 development recordings the supervised model's PR-AUC was +0.069 [0.022, 0.128] higher than the
# flow-rate z-score (paired cluster bootstrap over 23 overlap groups, 2000 replicates); inconclusive: the interval
# excludes zero but not differences below the 0.05 we fixed in advance. On the single test look (7 recordings) the
# chosen detector found 5 of 7 faults (Wilson 95 % interval [0.36, 0.92]) with a median delay of 100 s and no
# false alarm in 1.2 hours of normal operation, too little time to confirm the budget of one per 8 hours.
# ```
#
# What changed: the comparison is the paired difference on development data (the data the decision used), not two
# test numbers; each interval says how it was obtained; "highly reliable" became a count with its interval; and the
# last clause states what the data cannot show (1.2 hours of normal operation cannot confirm a one-per-8-hours
# budget). The script reads the numbers; rerunning the evaluation updates the paragraph.

# %% [markdown]
# ## 4. Lab: the report checker, then your report
#
# The checks run your checker on SYNTHETIC reports (`checks/synthetic_reports.py`): a sound one that contains every
# number format a checker must handle (thousands separators, percentages, negative values, a number ending a
# sentence, code spans, dates, versions, identifiers) and six that each break exactly one rule.
#
# 1. Read the module docstring of `lab/report/check_report.py`: the five rules and their finding codes.
# 2. Implement `strip_markup` and `traced`. *Checkpoint:* the sound report produces no `untraced_number` finding.
#    If it does, print the token: rounding (`round(v, d)` with `d` the decimals written), the percent rule
#    (`35 %` matches 0.349) and thousands separators are the usual culprits.
# 3. Implement `check`: sections, numbers line by line (skip headings, code blocks and images), intervals and
#    "significant" per block, limitation items. *Checkpoint:* `python wb.py check w8d2` passes all 9 checks.
# 4. Copy `lab/report/TEMPLATE.md` to your repository, write your report and model card from your results files
#    (the w4d6, w5d6 and w7d6 outputs, plus the w8d1 audit log), and run the checker until it passes. Put
#    identifiers, commands and versions in backticks.
# 5. Read your limitations section as the reliability engineer would. Could they tell what not to do with the model?
#
# **Debugging guidance.**
# * *"0.042 does not appear":* the stored value may round the other way (0.0425 rounds to 0.043 in binary floating
#   point). Fix the report or the stored precision, not the checker.
# * *A heading number is flagged:* skip lines starting with `#`.
# * *A sentence-final number is never checked:* your number pattern refuses a trailing full stop; refuse only a
#   full stop followed by a digit (a decimal).
# * *The interval rule fires on a table with a caption:* the caption must be in the same block (no blank line
#   between table and caption).

# %%
# Run the automated checks on your guided lab.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w8d2")

# %% [markdown]
# ## 5. Independent challenge: peer review
#
# See [challenge/README.md](../labs/w8d2_report_limitations/challenge/README.md). Review [challenge/FLAWED_REPORT.md](../labs/w8d2_report_limitations/challenge/FLAWED_REPORT.md)
# (SYNTHETIC late-payment prediction) in 40 minutes, without hints.
#
#
# ### The challenge brief
#
#
# FLAWED_REPORT.md is a short SYNTHETIC report on late-payment prediction, written for a
# finance team. Review it as a sceptical colleague: find what is wrong, explain why it matters, and request a
# concrete change. Write the review in REVIEW.md. Time box: 40 minutes, no hints.
#
# This is the other side of today's lab: the rules your checker enforces catch some problems mechanically;
# most of the serious ones in this report need judgement.
#
# **Acceptance criteria** (`python wb.py check w8d2 --challenge`, structure plus coverage):
# * at least six issues, each with a line number in `FLAWED_REPORT.md`, a problem, why it matters, a requested
#   change of six or more words, and a severity (`major` or `minor`); at least three are `major`;
# * the issues point at (by line number) at least five of the problems the report was written to contain;
# * the summary and recommendation sections are written; no placeholders left.
#
# The model answer, with every planted problem explained, is in the solutions folder.

# %%
# Run the automated checks on your independent challenge.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w8d2", challenge=True)

# %% [markdown]
# ## 6. Progressive hints
#
# 1. [Concept](../labs/w8d2_report_limitations/hints/hint1_concept.md)
# 2. [Approach](../labs/w8d2_report_limitations/hints/hint2_approach.md)
# 3. [Partial implementation](../labs/w8d2_report_limitations/hints/hint3_partial.md)
#
#
# Open one hint at a time, only after a real attempt.
#
# <details>
# <summary><b>Hint 1 concept</b></summary>
#
#
# The checker is a linter for claims. Each rule turns a reviewer's habit into a test:
#
# * "Where does this number come from?" → every number must equal some value in the results file *at the precision
#   written*. Rounding is the point: the report says 0.884, the file says 0.8842514; they agree to three decimals.
# * "Bootstrap over what?" → an interval and its method live in the same block of text, so the reader never has to
#   search for them.
# * "Which test?" → the word "significant" carries a test name or p value with it.
# * "So what?" → each limitation says its impact and its mitigation.
#
# Work line by line for numbers and block by block (text between blank lines) for intervals and significance.
#
# </details>
#
# <details>
# <summary><b>Hint 2 approach</b></summary>
#
#
# * `strip_markup(line)`: a few `re.sub` calls in order: inline code (text between backticks), link targets (the parenthesised part after a closing bracket), URLs,
#   dates `\d{4}-\d{2}-\d{2}`, version strings `\d+(\.\d+){2,}`, and a leading list marker. Replace with a space,
#   not with nothing, so neighbouring tokens do not merge.
# * `traced(token, percent, leaves)`: parse the token (drop thousands commas), count the decimals written, and look
#   for any leaf with `round(leaf * (100 if percent else 1), d) == round(value, d)`.
# * `check`:
#   1. `sections(lines)` gives titles; each required name must start one of them (case-insensitive).
#   2. For each line outside code blocks that is not a heading or an image: `NUMBER.finditer(strip_markup(line))`;
#      group 1 is the number, group 2 the optional `%`.
#   3. For each `blocks(lines)` block: `INTERVAL` without `METHOD` → `interval_without_unit`; `SIGNIFICANT` without
#      `TEST_REF` → `significance_without_test`.
#   4. Limitations: collect list items (a line starting with `*`, `-` or `1.`, plus indented continuation lines);
#      count them and the ones containing both `Impact:` and `Mitigation:`.
#
# </details>
#
# <details>
# <summary><b>Hint 3 partial</b></summary>
#
#
# ~~~python
# def traced(token: str, percent: bool, leaves: list[float]) -> bool:
#     value = float(token.replace(",", ""))
#     decimals = len(token.split(".")[1]) if "." in token else 0
#     return any(round((v * 100 if percent else v), decimals) == round(value, decimals) for v in leaves)
#
#
# def check(report, results, min_limitations=5):
#     lines = report.splitlines()
#     found = []
#     secs = sections(lines)
#     for req in REQUIRED_SECTIONS:
#         if not any(t.lower().startswith(req.lower()) for t in secs):
#             found.append(finding("missing_section", 0, f"no '## {req}...' section"))
#     leaves = numeric_leaves(results)
#     in_code = False
#     for i, raw in enumerate(lines, 1):
#         if raw.strip().startswith("```"):
#             in_code = not in_code
#             continue
#         if in_code or raw.lstrip().startswith(("#", "![")):
#             continue
#         for m in NUMBER.finditer(strip_markup(raw)):
#             ...  # untraced_number with line i
#     for start, block in blocks(lines):
#         ...  # interval_without_unit, significance_without_test
#     ...      # limitations_incomplete
#     return found
# ~~~
#
# </details>

# %% [markdown]
# ## 7. Assessment
#
# assessment.md (section 7 of this notebook): the report rubric, reasoning questions, a design-choice explanation, and the
# interview rep "explain a limitation to a non-technical stakeholder".
#
#
# ### Assessment questions
#
#
# #### Report rubric (the reviewer uses this; self-score before submitting)
#
# | Criterion | 1 (below) | 2 (meets) | 3 (exceeds) |
# |---|---|---|---|
# | Traceability | numbers typed; checker fails | checker passes; results file and generating command named | figures and tables generated by the same command; provenance block |
# | Uncertainty | point estimates | every estimate with an interval and its unit; differences estimated paired | decision rule fixed in advance and applied in the text |
# | Honesty of claims | "reliable", "significant", "state of the art" without support | claims no stronger than the intervals; negative results reported | states what would change the conclusion |
# | Limitations | generic caveats | each with impact and mitigation, specific to this project | quantified (interval widths, hours of normal data, label coverage) |
# | Usefulness to the stakeholder | written for the author | decision and its conditions clear to the engineer | model card a non-specialist can act on |
#
# #### Reasoning questions
#
# 1. Test PR-AUC intervals of the chosen detector and the logistic model overlap almost entirely. Can you conclude
#    they are equivalent? What would you compute instead, on which data, and why that data?
# 2. The test set had no false alarm in about 1.2 hours of normal operation. What can and cannot be said about the
#    budget of one false alarm per 8 hours? Give the sentence for the report.
# 3. Your checker accepts "14 %" because 0.143 is in the results file, although the sentence refers to a drift
#    alert rate. What does this say about number tracing, and how would you make it stricter?
# 4. **Design choice.** The reference report states that the data come from a laboratory testbed and makes no claim
#    about real plants. A manager asks you to remove that sentence because "it undermines the project". Argue for
#    keeping it, and propose wording that is accurate and not defeatist.
# 5. Which three limitations of flowguard would you keep if the section could hold only three, and why those?
#
# #### Interview rep (15 min, communication)
#
# > "Explain to the plant's operations manager, who has no statistics background, why you cannot promise that the
# > system will catch at least 70 % of faults."
#
# Answer aloud in 2 minutes, without the words "confidence interval" or "bootstrap". Then answer: "So is it any
# good?" and "What would it take to give me a number I can rely on?" Score yourself with the rubric in the answers file.

# %% [markdown]
# ## 8. Reflection and review
#
# **You should now be able to, without notes:** structure a short technical report around a reader's questions;
# state an estimate with its interval and resampling unit; tell an overlap of intervals from a paired comparison;
# quantify a limitation and give its impact and mitigation; recognise the claims a reviewer will reject; and
# automate the mechanical checks.
#
# **Reflection prompt.** Reread the limitations section of your most recent paper. Which items state an impact on
# what a reader may conclude, and which are ritual?
#
# **Retrieval question (for the w8d7 retrospective).** A colleague writes "the new model is significantly better
# (AUC 0.83 vs 0.81)". Write the three questions you ask, and the sentence you would accept instead.
#
# **Next.** [w8d3: ML system design](45_system_design.ipynb).

# %% [markdown]
# ## Verification record
#
# Executed on 2026-11-25 (Python 3.13.18, matplotlib 3.11.2):
#
# * `python tools/verify_checks.py labs/w8d2_report_limitations`: lab reference passes 9 checks and all 7 lab
#   mutants are rejected, each by its intended check; challenge reference passes 6 checks and all 4 challenge
#   mutants are rejected. The shipped starter fails all 9 lab checks; the review template fails all 6.
# * Reference report: `solutions/labs/w8d2_report_limitations/reference/build_results.py` assembles
#   `results.json` from 12 committed files (text sources are matched by pattern and fail loudly if they change);
#   the reference checker passes `TECHNICAL_REPORT.md` against it with 0 findings.
# * Worked example run; output above copied from it. Figures regenerated by `figures/make_figures.py` and viewed.
# * Not verified: Python 3.11/3.12; the time budget; the claim that reviewers in industry reject the listed claims
#   is the author's experience, not a cited study.

# %% [markdown]
# ## Record your progress
#
# Tick only what is true. Passing the supplied checks is *guided practice*; mark *independent* only for work done without hints or solutions.

# %%
from mlcourse.progress import mark, note

# mark("w8d2", "reading")
# mark("w8d2", "guided")
# mark("w8d2", "independent")
# note("w8d2", "what tripped me up today")

