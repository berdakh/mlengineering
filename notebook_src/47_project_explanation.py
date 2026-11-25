# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/47_project_explanation.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 47 · Explaining the project and defending tradeoffs
#
# **Week 8 · day 5 · 2 h essential path + up to 1 h optional** · lab files: [`labs/w8d5_project_explanation/`](../labs/w8d5_project_explanation/)
#
# **Objective.** Deliver 5-minute and 20-minute walkthroughs and answer adversarial questions on evaluation, limitations and alternatives.

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
# Unit id `w8d5_project_explanation` · Week 8, day 5 · Content status: see [STATUS.md](../docs/guides/status.md)

# %% [markdown]
# ## 1. Purpose
#
# **Objective.** Deliver 30-second, 5-minute and 20-minute walkthroughs of flowguard, and answer
# adversarial questions about evaluation, limitations and alternatives with evidence rather than with
# reassurance.
#
# **Why an applied ML engineer needs it.** In most interview loops the project discussion is where a
# candidate with research experience wins or loses. Interviewers rarely ask "what is a z-score?"; they
# ask "why didn't you ship the model with the best test score?" and listen for whether you know where
# your evidence ends. At work the same skill decides whether your recommendation is adopted. You have
# given many conference talks; the difference here is the listener: an engineer or manager who wants
# the decision, the cost and the risk in five minutes, then pushes on the weakest point.
#
# **Deliverable.** In `lab/`: written answers to twenty hard questions (`ANSWERS.md`), a 30-second
# version, a 5-minute script, a 20-minute outline, a slide outline, and one recorded 5-minute run
# scored in `SELF_SCORE.md`.
#
# **Completion criteria.**
#
# * `python wb.py check w8d5` passes (structure: all answers present, spoken length, cited artifacts exist).
# * One recording of the 5-minute walkthrough, self-scored against the rubric in assessment.md (section 7 of this notebook).
# * Independent skill: `python wb.py check w8d5 --challenge` passes for a walkthrough of one of *your
#   own* research projects and five adversarial answers, written without opening the hints.
#
# **Prerequisites.** [w8d2](44_report_limitations.ipynb) (technical report and limitations) and
# the project milestones; the numbers you quote must come from your own runs. Assumed: you can present;
# this session is about structure, priorities and honesty under pressure.
#
# **Time budget (2 h essential).**
#
# | Activity | Minutes |
# |---|---|
# | Read section 2, run the worked example (the script linter) | 20 |
# | Guided lab: 30-second and 5-minute versions, first 10 answers | 55 |
# | Record the 5-minute version once, watch it, self-score | 20 |
# | Independent challenge: start the research walkthrough | 15 |
# | Assessment and reflection | 10 |
# | *Optional extension: remaining 10 answers, 20-minute outline and slides, a second recording* | *up to 60* |

# %% [markdown]
# ## 2. Conceptual explanation
#
# ### 2.1 One story arc, three lengths
#
# A technical project story that survives questioning has six beats, always in this order:
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/docs/assets/diagrams/mmd-47-01.svg" alt="Diagram 1 of notebook 47" style="max-width:100%">
#
# *The arc. Interviewers probe Evidence and Limitation; a script without them invites the question
# you least want.*
#
# The three lengths are the same arc at different resolution, not three different stories:
#
# | Length | Words (at about 140 per minute) | What each beat gets |
# |---|---|---|
# | 30 seconds | 40-90 | one clause per beat; no numbers except the one that matters |
# | 5 minutes | 550-800 | 40-130 words per beat; one number with its interval; one limitation |
# | 20 minutes | an outline, not a script | each beat becomes 2-4 minutes with one visual; leave time for questions |
#
# A spoken 5-minute slot holds about 550-650 words once pauses and a diagram are counted; the reference
# script is 556 words, about four minutes of speech.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/labs/w8d5_project_explanation/figures/speaking_time.svg" alt="Six bars of speaking time for the reference script: Problem 41 s, Constraint 42 s, Decision 49 s, Evidence 53 s, Limitation 30 s, Next step 23 s; all well under 90 s" width="100%">
#
# *Speaking time per beat of the reference 5-minute script, from `example/script_lint.py`. No beat
# exceeds 90 seconds; Evidence is the longest, Next step the shortest.*
#
# ### 2.2 What to show: one diagram, one table, one failure
#
# Three visuals carry a project discussion; more becomes a tour.
#
# 1. **One architecture diagram** - data to monitored service, ten boxes at most. It answers "what did
#    you actually build?" and lets the interviewer point at the part they want to probe.
# 2. **One results table with intervals** - candidates, the decision metric with its interval, cost
#    columns (latency, size). It answers "why this model?" without a word of defence.
# 3. **One failure example** - a fault you missed, with what the scores and logs showed. Nothing signals
#    seniority faster than choosing to show your own miss and explaining it.
#
# ![Four development PR-AUC intervals: logistic 0.83 [0.76, 0.89], flow-rate z (chosen) 0.76 [0.68, 0.84], Mahalanobis 0.71 [0.60, 0.80], isolation forest 0.56 [0.49, 0.64]; test faults caught and model size next to each](figures/results_slide.svg)
#
# *The results slide as a picture (REAL SKAB, w4d5 decision table). The chosen model is not the top
# point estimate; the overlapping intervals and the cost columns are the argument.*
#
# ### 2.3 Answering adversarial questions: concede, quantify, redirect
#
# Hard questions usually target a real weakness. Three moves, in order, keep the answer honest and short:
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/docs/assets/diagrams/mmd-47-02.svg" alt="Diagram 2 of notebook 47" style="max-width:100%">
#
# *The three moves. Skipping "concede" sounds defensive; skipping "quantify" sounds vague; skipping
# "redirect" leaves the weakness as the last thing said.*
#
# Example. *"Your test set has seven experiments - why believe anything?"* Concede: "It is small; I don't
# claim precise numbers." Quantify: "Five of seven faults caught has an interval of roughly 0.36 to 0.92."
# Redirect: "So my claims are relative and protocol-based: every decision was made on 27 development
# experiments, the test set was looked at once, and the chosen model is clearly above the clock baseline."
#
# ### 2.4 Precise terms
#
# * **Walkthrough** - a spoken explanation with a fixed structure and length, not a demo.
# * **Headline number** - the one result you would keep if you could keep only one; always with its
#   interval and its comparison.
# * **Artifact** - something a listener could open: a report, a table, a commit, a test. Every claim in
#   an answer should point at one.
# * **Adversarial question** - one aimed at a real weakness; distinct from a clarifying question, which
#   you answer directly.
#
# ### 2.5 Connection to what you know
#
# Your conference talks follow a related arc (motivation, methods, results, discussion), but reviewers
# reward novelty and a significant result, while an engineering audience rewards a correct decision
# under constraints and a clear account of risk. Two habits transfer directly: stating the unit of
# analysis (patients there, experiments here) and reporting per-unit results. One habit must be
# dropped: leading with the method. In industry the method is the third thing you mention, after the
# problem and the constraint.
#
# ### 2.6 Industry example (an illustrative composite, not a cited case)
#
# A team proposes replacing a rule-based fraud screen with a model. The engineer who gets the decision
# through does not open with model architecture. They say: the screen blocks 2 % of good customers
# (problem); labels arrive after 60 days (constraint); we chose the model that keeps good-customer
# blocks flat while catching more fraud (decision); on the last two months it catches 9 [6, 12] more
# fraud cases per 10,000 at equal blocking (evidence); we have not seen a holiday season (limitation);
# so we shadow it until January (next step). Every question that follows has a slot to land in.
#
# ### 2.7 Limitations and misconceptions
#
# * **"More detail shows more competence."** It shows less judgement. Depth is for the follow-up question.
# * **"Never mention weaknesses."** Interviewers find them in 30 seconds; mentioning them first moves
#   the conversation to how you handled them.
# * **"Numbers are always better than words."** A number without its comparison and interval is a
#   liability under questioning ("0.88 compared with what?").
# * **"A script makes you sound rehearsed."** Scripts are for preparation; deliver from the six beats.
#   The recording will show whether you are reading.
# * **This lesson does not make a weak project strong.** It makes your evidence audible. If an answer
#   needs a number you do not have, that is a finding for the project, not a wording problem.

# %% [markdown]
# ## 3. Worked example: linting a walkthrough
#
# `example/ledgerline_2min.md` is a 2-minute walkthrough of the w3d6 transfer exercise (SYNTHETIC
# data), chosen because its honest result is unflattering: the model did *not* beat the rule.
# `example/script_lint.py` makes the structure visible: speaking time per section, missing beats,
# numbers in the Evidence section without an interval, and jargon.

# %%
!python labs/w8d5_project_explanation/example/script_lint.py labs/w8d5_project_explanation/example/ledgerline_2min.md

# %% [markdown]
# Output from the authoring run (2026-11-25):
#
# ```text
# section           words  seconds
# Problem              68       29
# Constraint           62       27
# Decision             54       23
# Evidence             39       17
# Limitation           48       21
# Next step            45       19
# total               316      135
#
# WARN 'Evidence' uses 'bootstrap': explain it or replace it for a non-specialist
# WARN Evidence: number without uncertainty -> "The rule reached a weekly top-fifteen precision of 0.727...."
# 2 warning(s)
# ```
#
# Interpretation. The structure is complete and balanced. Both warnings are real. "Bootstrap" needs
# three words of translation ("resampling customers"). And the rule's 0.727 has no interval because the
# reference evaluation never computed one: the linter exposes that the comparison "model 0.722
# [0.651, 0.783] vs rule 0.727" mixes an interval with a bare number. The honest wording is "the rule
# falls inside the model's interval, so the model is not shown to be better". Run the linter on the
# reference 5-minute script in the solutions tree and it flags several numbers too: the linter is a
# heuristic that asks "is the uncertainty stated nearby?", not a judge. Read each warning and decide.
#
# Reproduce with any Python >= 3.11; the linter uses only the standard library.

# %% [markdown]
# ## 4. Guided lab
#
# Work in `lab/`. Use your own project's numbers and artifact paths; set `WB_PROJECT_DIR` to your
# flowguard repository if the artifacts you cite live there (`export WB_PROJECT_DIR=~/projects/flowguard`).
#
# 1. **30 seconds (10 min).** Write `WALKTHROUGH_30S.md`: one clause per beat, 40-90 words. Read it aloud
#    with a timer. *Checkpoint:* under 35 seconds spoken.
# 2. **5 minutes (30 min).** Write `WALKTHROUGH_5MIN.md` with the six headings. Put one number with its
#    interval in Evidence and one real limitation in Limitation. Run the linter on it and fix or
#    consciously accept each warning. *Checkpoint:* `python wb.py check w8d5` passes the two
#    walkthrough checks.
# 3. **Twenty answers (25 min essential for the first ten).** Open `QUESTIONS.md`. For each question,
#    find the artifact that answers it *before* writing - if none exists, write that down as a gap
#    rather than inventing a confident answer. Use concede-quantify-redirect where the question targets
#    a weakness. Keep each to 40-130 words. *Checkpoint:* the answer checks for Q01-Q10 pass.
# 4. **Record (20 min).** Record the 5-minute version (phone or `ffmpeg`/OBS), watch it once, fill in
#    `SELF_SCORE.md` against the rubric in assessment.md (section 7 of this notebook). One change only for the next take.
# 5. **Extension.** Remaining answers; `OUTLINE_20MIN.md` (timed parts, 18-22 min); `SLIDES.md` with the
#    three visuals of section 2.2.
#
# **Debugging the checks.** "cited artifact(s) not found": the path is relative to the course root or to
# `WB_PROJECT_DIR`; no leading `./` or `~`. "words" counts tokens with a letter or digit; code blocks
# are not counted. "placeholder": remove every `TODO`.

# %%
# Run the automated checks on your guided lab.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w8d5")

# %% [markdown]
# ## 5. Independent challenge
#
# Translate one of **your own** research projects (a study you led; EEG/iEEG or other) into the same
# structure, plus a translation to industry, and answer five adversarial questions about it. Details
# and acceptance criteria: [challenge/README.md](../labs/w8d5_project_explanation/challenge/README.md). Do not use numbers you cannot
# source; where your paper reported no interval, say so.
#
#
# ### The challenge brief
#
#
# **Independent. No hints, no solutions until you have finished.**
#
# Pick one research project you led (an EEG/iEEG or BCI study is ideal). In `challenge/`:
#
# 1. `RESEARCH_WALKTHROUGH.md` - a 5-minute walkthrough with the six beats (Problem, Constraint,
#    Decision, Evidence, Limitation, Next step; 550-800 words in those six sections, each at least 40),
#    plus two further sections:
#    * `## Translation to industry` (at least 60 words): the same structure in an industrial setting,
#      and what an engineering role would add that the study never needed.
#    * `## What was not established` (at least 40 words): claims your evidence does not support.
# 2. `ADVERSARIAL.md` - five questions a sceptical interviewer would ask about that project (`## A1` ...
#    `## A5`), each answered with lines starting `Question:`, `Concede:`, `Quantify:`, `Redirect:`;
#    each answer at most 120 words.
#
# Rules: use only numbers you can source from your paper or data. If the study reported no interval,
# write "no interval" and why, rather than inventing one. Do not include unpublished or confidential
# details you would not say in an interview.
#
# #### Acceptance criteria
#
# * `python wb.py check w8d5 --challenge` passes (structure only).
# * Rubric in `../assessment.md` ("Research walkthrough" rows): the translation names concrete
#   counterparts (unit, event, error costs) and at least two engineering concerns absent from the study.
# * Recorded once; `python wb.py mark w8d5 independent` only if written without hints.

# %%
# Run the automated checks on your independent challenge.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w8d5", challenge=True)

# %% [markdown]
# ## 6. Progressive hints
#
# [Hint 1 - concept](../labs/w8d5_project_explanation/hints/hint1_concept.md) · [Hint 2 - approach](../labs/w8d5_project_explanation/hints/hint2_approach.md) ·
# [Hint 3 - partial](../labs/w8d5_project_explanation/hints/hint3_partial.md)
#
#
# Open one hint at a time, only after a real attempt.
#
# <details>
# <summary><b>Hint 1 concept</b></summary>
#
#
# The walkthrough is an argument for a decision, not a summary of work. Before writing a word, answer
# in one line each: what decision did the project support, what made it hard, what rule did you choose
# by, what is the single number that supports the choice (with its comparison and interval), and what
# does that number not cover. Those five lines are your skeleton; everything else is optional.
#
# For adversarial questions, the weakness the interviewer targets is usually real. Agreeing with the
# true part first is not weakness - it is what makes the rest of your answer credible.
#
# </details>
#
# <details>
# <summary><b>Hint 2 approach</b></summary>
#
#
# 1. List your artifacts first (`project/README.md`, your report, decision table, test outputs). For each
#    of the twenty questions, write the artifact path before the answer. A question with no artifact is
#    a gap: say what you would need, do not fill it with confidence.
# 2. Draft the 5-minute script at about 100 words per beat, then cut to fit 550-800 words. Run
#    `example/script_lint.py` and look at the Evidence warnings: every number needs its comparison and
#    uncertainty nearby.
# 3. For the research challenge, map the study onto flowguard's vocabulary: unit of independence,
#    event, error costs, decision. Then list what an engineering role adds: packaging, serving,
#    monitoring, updates, rollback, on-call.
# 4. Record before polishing. The first recording shows where you hesitate; those are the beats to
#    rewrite.
#
# </details>
#
# <details>
# <summary><b>Hint 3 partial</b></summary>
#
#
# A complete answer to Q03 ("seven test experiments") in the expected shape:
#
# > It is small, and I do not claim precise numbers from it. Event recall of 5 of 7 has an interval of
# > roughly 0.36 to 0.92. What makes the result interpretable is the protocol: every choice was made on 27
# > development experiments, the test set was looked at once, and the chosen detector is compared with
# > the clock baseline and chance, where the gap is large. So my claims are relative, not precise.
# >
# > Evidence: `labs/w4d5_model_choice/figures/test_look.csv` `labs/w3d5_uncertainty/README.md`
#
# And the Evidence beat of a 5-minute script:
#
# > On the seven test experiments the detector caught 5 of 7 faults, interval 0.36 to 0.92, with no
# > false-alarm events; on development data its PR-AUC was 0.76 [0.68, 0.84], level with the supervised
# > alternative within the interval, at a fraction of the cost.
#
# For the research challenge, the Translation section starts like this:
#
# > The same structure is equipment monitoring with few machines: the machine is the patient, a fault
# > is a seizure, the allowed detection delay is the onset tolerance ...
#
# </details>

# %% [markdown]
# ## 7. Assessment
#
# assessment.md (section 7 of this notebook): reasoning questions, the walkthrough rubric, and the interview rep
# (a recorded 5-minute walkthrough followed by three questions drawn at random from the bank).
#
#
# ### Assessment questions
#
#
# #### Reasoning questions (answer in 2-4 sentences)
#
# 1. Why does the Limitation beat come *before* Next step, and what happens to a talk that ends on Evidence?
# 2. Your best test number is 0.92 for a model you did not ship. Should it appear on your results
#    slide? Explain your choice (design-choice question).
# 3. An interviewer asks "is 0.88 good?". Give the two comparisons that make the number interpretable.
# 4. Why is showing a failure example a stronger move than showing a second success?
# 5. A question targets a weakness you had not thought of. What do you say in the first ten seconds?
# 6. Which of your twenty answers had no artifact behind it, and what does that tell you about the project?
#
# #### Rubric for the recorded 5-minute walkthrough
#
# | Row | Meets | Partly | Not yet |
# |---|---|---|---|
# | Structure | six beats in order, each audible; under 5:30 | one beat missing or merged | no discernible structure |
# | Decision | the choice and the rule it was made by are explicit | choice stated, rule implicit | method described, no decision |
# | Evidence | one headline number with its comparison and interval | numbers without comparison or interval | no numbers, or a list of many |
# | Limitation | names a limitation that matters for the decision | generic caveat ("more data") | none |
# | Delivery | speaks to a non-specialist; jargon explained; not read verbatim | some jargon unexplained | reads the script |
#
# #### Rubric for the twenty answers and the research walkthrough
#
# | Row | Meets | Partly | Not yet |
# |---|---|---|---|
# | Honesty | concedes real weaknesses; states what is not established | hedges without specifics | defends everything |
# | Grounding | each claim points to an artifact; numbers match it | some unsupported claims | invented or unsourced numbers |
# | Brevity | 40-130 words, answer first | answer buried in context | over 150 words |
# | Research translation (challenge) | concrete counterparts (unit, event, error costs) and two engineering concerns the study lacked | analogy without specifics | none |
#
# #### Common incorrect answers and why they fail
#
# * **"The test score was best, so we shipped it."** Ignores the protocol-B result and the cost columns.
# * **"Seven experiments is enough because they have 9,000 samples."** Confuses samples with
#   independent units - the core error the course is built against.
# * **"The drift monitor detects faults."** It detects input change; conflating the two is a red flag.
# * **Answers that list everything** ("we also tried X, Y, Z...") instead of answering first.
#
# #### Interview rep (10-15 min, reduced assistance)
#
# Record the 5-minute walkthrough without notes. Then draw three question numbers at random
# (`python -c "import random; print(sorted(random.sample(range(1, 21), 3)))"`) and answer them aloud,
# 45 seconds each, before reading your written answers. Score with the rubric above, then compare with
# `solutions/labs/w8d5_project_explanation/QUESTION_BANK.md`.

# %% [markdown]
# ## 8. Reflection and review
#
# * **You should now be able to:** give flowguard in 30 seconds, 5 minutes and 20 minutes from the same
#   six beats; answer the twenty questions with an artifact behind each; and show your own failure case
#   without defensiveness.
# * **Reflection prompt:** which question did you most want to avoid, and what does that say about the
#   project's weakest evidence?
# * **Later retrieval question:** without notes, give the three moves for an adversarial question and
#   apply them to "why only seven test experiments?".
# * **Next:** [w8d6 final assessment](48_final_assessment.ipynb) - an independent sample to
#   set next to the Week 1 diagnostic.

# %% [markdown]
# ## Verification record
#
# Executed 2026-11-25 on Python 3.13: `python tools/verify_checks.py labs/w8d5_project_explanation`
# (lab: reference passes, 5 mutants rejected; challenge: reference passes, 4 mutants rejected); shipped
# starters fail; worked example and figure script run, outputs quoted above. Every number in the
# reference answers was checked against the cited lesson's text or committed result files. The research
# walkthrough reference is **fictional** and labelled so. Not verified: speaking rates (140 words per
# minute is a planning value; measure yours), Python 3.11/3.12.

# %% [markdown]
# ## Record your progress
#
# Tick only what is true. Passing the supplied checks is *guided practice*; mark *independent* only for work done without hints or solutions.

# %%
from mlcourse.progress import mark, note

# mark("w8d5", "reading")
# mark("w8d5", "guided")
# mark("w8d5", "independent")
# note("w8d5", "what tripped me up today")

