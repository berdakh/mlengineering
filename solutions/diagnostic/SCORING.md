# Diagnostic scoring guidance

**Read after submitting.** This file is used to review a real submission. Until a submission has
been reviewed, nothing is known about the results and the roadmap stays at its default.

## Principles

* **No numeric proficiency score.** Each skill gets one of three evidence levels, taken from the
  rubric in the section's `NOTES.md`:
  * **Demonstrated independently** - done within the time box, without help beyond official docs,
    and the written explanation shows the mechanism was understood.
  * **Partial** - done with check-driven trial and error, with outside help, over time, or correct
    without being able to explain why.
  * **Not yet demonstrated** - not done or not correct. This says nothing about ability, only that
    this sitting produced no evidence.
* Passing checks is necessary for "Demonstrated" on the behavioural aspects, never sufficient: the
  notes, findings and memo carry the evidence of understanding.
* Help declared in `SUBMISSION.md` caps the affected section at Partial. That is the honest outcome,
  not a penalty.
* One sitting is one sample. A level can be revised in either direction by later independent work
  (lesson challenges, review days).
* Three sources of information are kept apart in the learner record: **demonstrated** (this
  diagnostic and later challenges), **self-reported** (background statement), **unassessed**.
  Existing repositories (for example a research package with tests) are evidence that artifacts
  exist, not of what was produced unaided; the diagnostic is what converts them to "demonstrated".

## How to review a submission

1. Run `python -m pytest diagnostic/<section>/checks -q` on the submitted `lab/` directories and
   record pass counts.
2. Read the code and the written files against the section's `NOTES.md` rubric; assign a level per
   **aspect** (each rubric row), not per section.
3. Compare minutes used with the time box and note declared help.
4. Fill in the evidence table below.
5. Apply the adaptation rules. State each change to the roadmap with the evidence that justifies it.

## Evidence table (to be filled in from a real submission)

| Skill area | Section | Aspect rows in NOTES.md | Level | Evidence (one line) |
|---|---|---|---|---|
| Python debugging and semantics | a1 | Debugging; Python semantics; Error handling | | |
| Refactoring | a1 | Refactoring | | |
| SQL joins/aggregation | a2 | Joins and aggregation; NULL semantics; Fan-out | | |
| SQL window functions | a2 | Window functions | | |
| Data cleaning (pandas) | a3 | Finding defects; pandas fluency; Time zones; Judgment | | |
| Framing and baselines | b1 | Framing; Baselines; Metric under imbalance; Communication | | |
| Leakage and validation | b1, b2 | Leakage hygiene; Target leakage; Validation design; Preprocessing leakage; Scientific honesty | | |
| Test design | b3 | Test design | | |
| Request validation / API concepts | b3 | Validation; API concepts; Validation vs evaluation | | |
| Explaining a decision | b4 | all four rows | | |

## Adaptation rules: what may be compressed or skipped

"Compress" = do the lesson's independent challenge first; if it passes unaided, mark reading and
guided practice as not needed and spend the freed time on the optional extension or the portfolio
project. "Skip" = go straight to the next unit, keeping only the retrieval question on the review day.
Nothing is skipped on the basis of self-report.

| If the diagnostic shows... | Then |
|---|---|
| a1 all aspects Demonstrated | **w1d3 (package structure)**: compress - attempt the challenge directly. **w1d6 (notebook refactor)**: keep, it is the integrative deliverable, but drop its guided steps |
| a1 Refactoring Partial or lower | w1d3 and w1d6 at full length; add the a1 refactor as a repeat exercise on the Week 1 review day |
| a1 Debugging/semantics Partial or lower | add 20 minutes of Python-semantics drills to each Week 1-2 interview-practice slot |
| a1 Error handling Partial or lower | **w1d4 (configuration, logging)** at full length with emphasis on failure paths |
| b3 Test design Demonstrated | **w1d5 (testing ML code)**: compress to the challenge plus the section on statistical checks vs unit tests |
| b3 Test design Partial or lower | w1d5 at full length; re-run b3 part 1 (new function) on the Week 2 review day |
| b3 API concepts / Validation Not yet demonstrated | no change now; Week 5 (FastAPI, request validation) stays at full length. If Demonstrated: compress the first Week 5 API session |
| a2 all aspects Demonstrated | **Week 2 SQL session**: skip the guided lab; keep the SQL-to-feature-table challenge and the recurring SQL interview questions |
| a2 NULL semantics or Fan-out Partial or lower | Week 2 SQL session at full length; one extra SQL question in every weekly interview slot through Week 4 |
| a2 Window functions Not yet demonstrated | add the optional window-function extension of the Week 2 SQL session to the essential path |
| a3 all aspects Demonstrated | **Week 2 pandas / data-quality sessions**: compress the pandas mechanics; keep schema checks and data-quality tests (new material regardless) |
| a3 Time zones or Judgment Partial or lower | Week 2 data-quality session at full length |
| b1 all aspects Demonstrated | **Week 2 baselines-and-metrics session**: compress to the challenge on the transfer dataset |
| b1 Metric under imbalance or Framing Partial or lower | Week 2 baselines session at full length; Week 3 error-analysis session keeps its metric-selection part |
| b2 all aspects Demonstrated | **Week 3 leakage session**: compress to the challenge; keep temporal validation and hyperparameter-selection sessions (nested selection is not probed here) |
| b2 Validation design: grouped split chosen | Week 3 group-aware *and* temporal validation at full length, starting with "which split answers which deployment question" |
| b2 Target leakage Partial (subtle column missed) | Week 3 leakage session at full length, plus a point-in-time feature exercise in Week 2 feature generation |
| b2 Scientific honesty Partial | no session change; reviewers ask for measured-vs-expected separation in every later lab write-up |
| b4 Demonstrated | interview-practice slots start at the "reduced assistance" stage for explanation prompts |
| b4 Partial or lower | a weekly 15-minute written decision memo from Week 2, reviewed against the b4 rubric |

Sections not finished within the time box default to "full length" for the matching sessions; no
inference is drawn beyond that.

## What the diagnostic does not cover

Docker, CI/CD, cloud deployment, monitoring, PyTorch engineering, time-series modelling choices,
hyperparameter selection, live coding under interview conditions and system design are **unassessed**
by this diagnostic. Weeks 4-8 are not adapted from it.

## Verification record for the diagnostic material

See the repository `STATUS.md` for the commands that were executed and their outcomes. Summary: for
each of a1, a2, a3, b1, b2, b3 the reference solution passes the checks, each stored mutant
(a plausible wrong submission) is rejected, and the shipped starter fails. b4 has no automated check.
