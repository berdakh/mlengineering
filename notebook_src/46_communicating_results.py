# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/46_communicating_results.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 46 · Communicating results: README, report, model card
#
# **Week 12 · lesson · about 90 minutes**
#
# Most people will never run your code. They will read the first screen of your README, skim the results, and
# decide whether to trust you. This lesson is about writing the three documents that carry a project: a **README**,
# a short **technical report** and a **model card**, so that every number is honest and every claim stays inside
# the evidence.
#
# **What you will learn**
#
# - who reads which document, and what each reader needs first;
# - to write numbers with their uncertainty, in one consistent format;
# - to check documents automatically: required sections, numbers without intervals, claims you cannot support;
# - to write a README, a technical report and a model card for the SKAB project.
#
# **What you need:** notebook 45 (the capstone numbers). Basic Markdown: `#` headings, `-` bullets, and code blocks
# between three backticks (all shown below).
#
# **How grading works:** exercises 1-5 are small text-processing functions tested on example documents.
# Exercises 6-8 are your own documents, checked **structurally** by the course's versions of those functions. A
# structural check cannot tell whether your writing is good; it can tell whether a required part is missing.

# %%
# --- Setup: works in Google Colab AND on your own computer. Safe to re-run. ---
# In Colab this downloads the course (about 30 s) and installs what it needs (about a minute, once
# per session). On your computer it just finds the course folder.
import os, sys, subprocess
from pathlib import Path

if "google.colab" in sys.modules and not Path("/content/mlengineering").exists():
    subprocess.run(["git", "clone", "--depth", "1",
                    "https://github.com/berdakh/mlengineering.git", "/content/mlengineering"], check=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r",
                    "/content/mlengineering/requirements.txt"], check=True)
REPO_ROOT = Path("/content/mlengineering") if "google.colab" in sys.modules else next(
    p for p in [Path.cwd(), *Path.cwd().parents] if (p / "src" / "mlcourse").is_dir())
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT / "src"))
from mlcourse.grader import grade, quiz
print("Ready. Course folder:", REPO_ROOT)

# %%
import re
from IPython.display import Markdown, display

# %% [markdown]
# ## 1 · Three documents, three readers
#
# **Why.** A document that tries to serve everyone serves no one. A hiring manager, a reviewer and a team deciding
# whether to use your detector ask different questions.
#
# **Idea.**
#
# | Document | Reader | Their first question |
# |---|---|---|
# | README | a visitor to the repository | What is this, does it work, how do I run it? |
# | Technical report | a reviewer or colleague | What exactly did you do, and how sure are you? |
# | Model card | someone deciding whether to use the model | What is it for, where does it fail, what are the risks? |
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-c46-01.svg" alt="One project with one set of numbers feeds three documents: a README for visitors, a technical report for reviewers and a model card for would-be users; all three share the rules that every number has an interval and every claim stays inside the evidence" style="max-width:100%">
#
# All three share one set of numbers, copied from the code that produced them (notebook 45 stored them in
# `detector.json`), and two rules: **every estimate comes with its uncertainty**, and **no claim goes beyond what was
# tested**.
#
# **See it.** The capstone's headline numbers, as they came out of notebook 45:

# %%
CAPSTONE = {
    "pr_auc": (0.884, 0.811, 0.927),          # pooled over 7 test experiments, bootstrap over experiments
    "prevalence": 0.338,                      # PR-AUC of a constant score
    "events_detected": (7, 7),                # detected, out of
    "event_recall_ci": (0.59, 1.00),          # exact (Clopper-Pearson) 95% interval for 7/7
    "delay_median": 56, "delay_range": (11, 118),   # readings (about 1 per second)
}
CAPSTONE

# %% [markdown]
# ### Exercise 1 · one format for every estimate
#
# Write `format_result(point, low, high, digits=2)` returning text like `"0.88 (95% CI 0.81 to 0.93)"`: each number
# with `digits` decimals (use an f-string such as `f"{x:.{digits}f}"`). If the point is outside its own interval
# (`low <= point <= high` fails), raise `ValueError`: that is a bug upstream, not something to print.

# %%
def format_result(point, low, high, digits=2):
    ### BEGIN SOLUTION
    if not (low <= point <= high):
        raise ValueError(f"point {point} is outside its interval [{low}, {high}]")
    return f"{point:.{digits}f} (95% CI {low:.{digits}f} to {high:.{digits}f})"
    ### END SOLUTION
    ### STARTER
    # YOUR CODE HERE
    raise NotImplementedError


# %%
grade("w12.format_result", format_result)

# %% [markdown]
# **Try it.** Format the PR-AUC with 3 decimals, then with 1. Which one would you put in a README? (Two decimals is
# usually right: with 7 test experiments the third decimal is noise.)

# %%
from mlcourse.graders.w12 import use

print(use(format_result, *CAPSTONE["pr_auc"]))
print(use(format_result, *CAPSTONE["pr_auc"], digits=3))

# %% [markdown]
# ## 2 · Structure you can check
#
# **Why.** Readers scan headings first. A README without a "how to run" section loses most visitors in seconds; a
# model card without "limitations" is not a model card.
#
# **Idea.** Markdown headings are lines that start with one to six `#` characters and a space: `# Title` is level 1,
# `## Results` is level 2. Inside a **code block** (between lines that start with three backticks) a `#` line is code
# (often a shell comment), not a heading. With a list of headings, checking for required sections is one line.
#
# **See it.** A small document and its headings, found the naive way:

# %%
DOC = '''# flowguard

## Quickstart

```bash
# install first
pip install -e .
```

## Results
'''
[line for line in DOC.splitlines() if line.startswith("#")]

# %% [markdown]
# The naive version thinks `# install first` is a heading. Your version will not.
#
# ### Exercise 2 · find the headings
#
# Write `headings(md)` returning a list of `(level, text)` tuples, in order. A heading line matches the regular
# expression `^(#{1,6})\s+(.*\S)\s*$` (one to six `#`, whitespace, then text); `level` is the number of `#` and `text`
# is the rest, stripped. Skip lines inside code blocks: keep a flag that flips on every line whose stripped text
# starts with three backticks.

# %%
def headings(md):
    ### BEGIN SOLUTION
    found, in_code = [], False
    for line in md.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        match = re.match(r"^(#{1,6})\s+(.*\S)\s*$", line)
        if match and not in_code:
            found.append((len(match.group(1)), match.group(2).strip()))
    return found
    ### END SOLUTION
    ### STARTER
    # YOUR CODE HERE
    raise NotImplementedError


# %%
grade("w12.headings", headings)

# %% [markdown]
# ### Exercise 3 · missing sections
#
# Write `missing_sections(md, required)` returning the names in `required` (keep their order) that do not appear in
# any heading. Compare in lower case and accept a name **inside** a longer heading: `"Results"` is present if there is
# a heading `## Results (test set)`. Use your `headings` function.

# %%
def missing_sections(md, required):
    ### BEGIN SOLUTION
    texts = [text.lower() for _, text in headings(md)]
    return [name for name in required if not any(name.lower() in text for text in texts)]
    ### END SOLUTION
    ### STARTER
    # YOUR CODE HERE
    raise NotImplementedError


# %%
grade("w12.missing_sections", missing_sections)

# %% [markdown]
# ## 3 · Claims that match the evidence
#
# **Why.** Two habits destroy trust faster than a weak result: a number given as if it were exact, and a claim the
# project never tested ("production-ready", "never misses a fault").
#
# **Idea.** Both can be caught with blunt rules:
#
# - in the **Results** section, every line with a decimal number (like `0.88`) should also carry its uncertainty:
#   the letters `CI`, the word `interval`, or `±`. Whole numbers (`7/7`, `56 readings`) are counts and pass;
# - a short list of **overclaims** should never appear. The rule is blunt on purpose: even "not production-ready" is
#   flagged, because the better sentence says what *was* tested ("evaluated on 7 laboratory experiments only").
#
# A *section* runs from its heading to the next heading of the same or a higher level (fewer `#`), so a `### Notes`
# inside `## Results` still belongs to Results. The helper below returns a section's lines:

# %%
def section_lines(md, name):
    """Lines under the first heading whose text contains `name` (any case), up to the next heading of the same or a
    higher level. Headings inside code blocks are ignored."""
    lines, inside, level, in_code = [], False, 0, False
    for line in md.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            if inside:
                lines.append(line)
            continue
        match = None if in_code else re.match(r"^(#{1,6})\s+(.*\S)\s*$", line)
        if match:
            if inside and len(match.group(1)) <= level:
                break
            if not inside and name.lower() in match.group(2).lower():
                inside, level = True, len(match.group(1))
                continue
        if inside:
            lines.append(line)
    return lines


section_lines("# A\n## Results\n- x 0.5\n### Notes\n- y\n## Limitations\n- z", "Results")

# %% [markdown]
# ### Exercise 4 · numbers without an interval
#
# Write `unqualified_numbers(md, section="Results")` returning the stripped lines of that section (use
# `section_lines`) that contain a decimal number (regular expression `\d+\.\d+`) and contain none of: `±`, `CI`
# (exactly these capital letters), `interval` (any case). Skip lines inside code blocks. A section that does not
# exist gives `[]`.

# %%
def unqualified_numbers(md, section="Results"):
    ### BEGIN SOLUTION
    found, in_code = [], False
    for line in section_lines(md, section):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        has_number = re.search(r"\d+\.\d+", line)
        qualified = "±" in line or "CI" in line or "interval" in line.lower()
        if has_number and not qualified:
            found.append(line.strip())
    return found
    ### END SOLUTION
    ### STARTER
    # YOUR CODE HERE
    raise NotImplementedError


# %%
grade("w12.unqualified_numbers", unqualified_numbers)

# %% [markdown]
# ### Exercise 5 · overclaims
#
# Write `overclaims(md)` returning the phrases from `OVERCLAIMS` that appear in the text, ignoring case, sorted, each
# once.

# %%
OVERCLAIMS = ("production-ready", "production ready", "guarantee", "100% accurate", "never misses",
              "always detects", "state-of-the-art")


def overclaims(md):
    ### BEGIN SOLUTION
    text = md.lower()
    return sorted({phrase for phrase in OVERCLAIMS if phrase in text})
    ### END SOLUTION
    ### STARTER
    # YOUR CODE HERE
    raise NotImplementedError


# %%
grade("w12.overclaims", overclaims)

# %% [markdown]
# **See it.** A README that a tired engineer might write on a Friday, run through your checks:

# %%
BAD_README = '''# flowguard

A production-ready fault detector that never misses a fault.

## Results

PR-AUC 0.884, precision 0.91.

## Limitations

None known.
'''
print("missing:", use(missing_sections, BAD_README, ["Overview", "Quickstart", "Results", "Limitations"]))
print("no interval:", use(unqualified_numbers, BAD_README))
print("overclaims:", use(overclaims, BAD_README))

# %% [markdown]
# Every problem is visible in three lines of output. (And "precision 0.91" appears nowhere in the capstone: a number
# with no source is worse than a number with no interval. Copy numbers from code, never from memory.)
#
# **Try it.** Fix `BAD_README` in the cell above until all three lists are empty. You will need two new sections,
# an interval, and a different first sentence.
#
# ## 4 · The README
#
# **Why.** The README is the front door of your portfolio. A reviewer gives it about a minute.
#
# **Idea.** Five sections, in this order:
#
# 1. **Overview**: what it is, for whom, and its status (an *educational prototype* on laboratory data) in 2-4
#    sentences;
# 2. **Quickstart**: the exact commands, in a code block, that take a fresh clone to a result;
# 3. **Results**: the headline numbers with intervals, and what they were measured on;
# 4. **Limitations**: at least two specific ones, as bullets;
# 5. **Data and licence**: where the data comes from, its licence (SKAB is GPL-3.0) and a citation.
#
# Specific beats humble. "More data would help" is true of every project and tells the reader nothing. "The window
# must start in normal operation; a window that starts mid-fault raises no alarm" tells them exactly when not to
# trust the detector.
#
# ### Exercise 6 · write the project README
#
# Write `README_MD` for the SKAB project with the five headings above (level-2 headings under a level-1 title).
# Use the numbers in `CAPSTONE` (via `format_result` if you like), describe the project as an educational prototype,
# and put the commands in a code block. The grader checks: all five sections, a code block in Quickstart, an
# interval in Results and none of its decimal numbers without one, at least two limitation bullets, the licence named,
# the word "educational", and no overclaims.

# %%
### BEGIN SOLUTION
README_MD = f'''# flowguard: fault detection on a water-circulation testbed

## Overview

flowguard flags abnormal operation in recordings from a laboratory water-circulation testbed (the SKAB benchmark).
It scores each flow-rate reading against the first 100 readings of the same recording (a burn-in z-score) and raises
an alarm after 5 consecutive readings more than 3 standard deviations away. It is an educational prototype, built to
practise the full engineering workflow; it has only been evaluated on laboratory data.

## Quickstart

```bash
git clone https://github.com/<you>/flowguard && cd flowguard
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python project/get_skab.py          # downloads SKAB (about 4 MB, GPL-3.0)
pytest -q                           # unit and API tests
python -m flowguard.evaluate        # test-set evaluation with intervals
```

## Results

Measured on the 7 held-out test experiments of the frozen split (v2); intervals are 95%.

- Point level: pooled PR-AUC {format_result(*CAPSTONE["pr_auc"])}; a constant score gets 0.34 (no interval needed: it
  is the share of anomalous readings).
- Events: 7 of 7 test faults detected, none early (95% CI 0.59 to 1.00, exact binomial interval).
- Detection delay: median 56 readings (about one minute), range 11 to 118.

## Limitations

- Seven test experiments: the event recall interval is wide, and small differences between detectors cannot be
  resolved.
- The window must start in normal operation. A window that starts during a fault raises no alarm, because the
  baseline is already faulty.
- Only the flow-rate sensor is used; faults that barely change the flow rate are missed (on the 27 development
  recordings, 6 faults were missed and 4 alarms came before the fault).
- Laboratory recordings only; nothing here was evaluated on a real plant.

## Data and licence

Skoltech Anomaly Benchmark (SKAB) v0.9, licensed GPL-3.0, downloaded by `project/get_skab.py` and not stored in this
repository. Citation: Katser, I. D., Kozitsin, V. O. (2020). Skoltech Anomaly Benchmark (SKAB). Kaggle.
DOI 10.34740/KAGGLE/DSV/1693952.
'''
### STARTER
README_MD = """YOUR README HERE"""
### END SOLUTION

# %%
grade("w12.project_readme", README_MD)

# %% [markdown]
# **See it.** Render it the way GitHub would:

# %%
display(Markdown(README_MD))

# %% [markdown]
# ## 5 · The technical report
#
# **Why.** A reviewer wants to be able to repeat or challenge your work. The README says *what*; the report says
# *how* and *how sure*.
#
# **Idea.** One or two pages (250-1,500 words), six sections:
#
# | Section | Answers |
# |---|---|
# | Question | What decision does this support, for whom? |
# | Data | Which data, how split, what was excluded and why (overlap groups, the reference recording)? |
# | Method | The detector and its parameters, and the baselines it was compared with. |
# | Results | Point and event metrics with intervals, on the test set only. |
# | Limitations | What the evidence does not support. |
# | Next steps | The two or three most useful things to do next, concretely. |
#
# In *Learning from Data* terms, the report is where you are honest about the gap between what you measured (a test
# estimate on 7 experiments) and what a reader wants to know (performance on the next, unseen recording).
#
# ### Exercise 7 · write the technical report
#
# Write `REPORT_MD` with the six headings above. The grader checks: all six sections, 250-1,500 words, an interval in
# Results and no decimal number there without one, at least two limitation bullets, at least one next step as a
# bullet, and no overclaims.

# %%
### BEGIN SOLUTION
REPORT_MD = '''# flowguard: technical report

## Question

A reliability engineer running the laboratory testbed wants an alert soon after abnormal operation begins, with few
enough false alerts to be trusted. The question is whether a simple, per-recording baseline on one sensor can provide
that, and how precisely seven held-out recordings can tell us. This is an educational prototype.

## Data

SKAB v0.9: 34 labelled recordings of about 750 to 1,330 readings each (about one per second), each with one labelled
anomalous segment, plus one fault-free recording. The split is frozen in a manifest (version 2): 7 test recordings,
27 development recordings. Recordings that share duplicated rows (four overlap groups) stay on the same side, and the
fault-free recording is excluded: it has no labels and shares rows with a labelled recording. Every number below is computed on the
test recordings only, once.

## Method

For each recording, the mean and standard deviation of the flow rate over the first 100 readings form the baseline.
Each later reading is scored by its absolute z-score against that baseline. An alarm is raised when 5 consecutive
readings exceed 3. The parameters were chosen on development data in earlier milestones and frozen before the test
evaluation. The reference point is a constant score, whose PR-AUC equals the share of anomalous readings.

## Results

Intervals are 95%. Point-level metrics pool all test readings; intervals come from a bootstrap that resamples whole
recordings (1,000 resamples), because readings within a recording are dependent.

- Pooled PR-AUC 0.88 (95% CI 0.81 to 0.93), against 0.34 for a constant score (no interval: it is a fixed share).
- 7 of 7 test faults detected and none raised early; the bootstrap cannot express uncertainty for 7/7, so the exact
  binomial interval is reported: event recall 1.00 (95% CI 0.59 to 1.00).
- Median detection delay 56 readings, range 11 to 118 readings.

## Limitations

- Seven test recordings make the event-level interval wide: the data are compatible with a detector that misses
  roughly four faults in ten.
- The detector assumes each window starts in normal operation; windows that start during a fault raise no alarm.
- It uses one sensor. On the 27 development recordings, 6 faults were missed and 4 alarms came before the fault
  started; the test set (7 of 7 detected) looks better than development, a reminder of how small it is.
- All recordings come from one laboratory rig; nothing is known about other equipment or a real plant.

## Next steps

- Add a second sensor (pressure or temperature) and compare on the development folds before touching the test set.
- Monitor inputs against a per-family reference: the pooled reference flow (64.83 ± 42.71 L/min) is too wide to
  reveal anything but large shifts.
- Collect more recordings, or adopt a second held-out family, before claiming any difference between detectors.
'''
### STARTER
REPORT_MD = """YOUR REPORT HERE"""
### END SOLUTION

# %%
grade("w12.technical_report", REPORT_MD)

# %% [markdown]
# ## 6 · The model card
#
# **Why.** Models get reused for things their authors never imagined. A model card, a format proposed by Mitchell
# and colleagues in 2019 and now common on model hubs, tells a would-be user where the model belongs and where it
# does not.
#
# **Idea.** Six sections, each a few sentences:
#
# - **Intended use**: who, for what, in what setting (here: educational use on laboratory recordings);
# - **Out of scope**: uses you advise against, explicitly (safety decisions, other equipment);
# - **Evaluation data**: what it was tested on, and how that data was split;
# - **Metrics**: the numbers, with intervals;
# - **Limitations**: known failure modes;
# - **Ethical considerations**: who could be harmed if it is used wrongly, and how (for example, an operator who
#   trusts a silent detector and skips a manual check).
#
# ### Exercise 8 · write the model card
#
# Write `CARD_MD` with the six headings above. The grader checks: all six sections, at least about 15 words in each,
# "educational" in Intended use, an interval in Metrics and no decimal number there without one, at least two
# limitation bullets, and no overclaims.

# %%
### BEGIN SOLUTION
CARD_MD = '''# Model card: flowguard burn-in z-score detector

## Intended use

Educational use: learning and demonstrating an end-to-end anomaly-detection workflow on the laboratory recordings of
the SKAB benchmark. Suitable for coursework, portfolio demonstrations and as a baseline in further experiments.

## Out of scope

Any safety-related or operational decision on real equipment; recordings from other rigs or sensors; windows that do
not start in normal operation; any use where a missed alarm could cause harm without an independent check.

## Evaluation data

Seven held-out recordings from the frozen SKAB split (version 2), never used to choose parameters. Development used
27 other recordings; recordings sharing duplicated rows were kept on the same side of the split.

## Metrics

- Pooled point-level PR-AUC 0.88 (95% CI 0.81 to 0.93), from a bootstrap over recordings.
- Event recall 7 of 7 test faults (exact 95% CI 0.59 to 1.00), with a median delay of 56 readings.

## Limitations

- Faults that do not change the flow rate are missed; one sensor is used.
- A window that starts during a fault looks normal to the detector and raises no alarm.
- The evidence is seven laboratory recordings, so its estimates are imprecise.

## Ethical considerations

If an operator relied on this detector instead of routine checks, a missed fault could go unnoticed and cause damage
or injury. It must not replace existing safety procedures. It processes sensor readings only and no personal data.
'''
### STARTER
CARD_MD = """YOUR MODEL CARD HERE"""
### END SOLUTION

# %%
grade("w12.model_card", CARD_MD)

# %% [markdown]
# **Try it.** Run your own checks on your three documents. Anything they flag that the grader did not?

# %%
for name, md in [("README", README_MD), ("report", REPORT_MD), ("model card", CARD_MD)]:
    print(f"{name:10s} unqualified: {use(unqualified_numbers, md)} | overclaims: {use(overclaims, md)}")

# %% [markdown]
# ## Quiz
#
# **Q1.** What should the first screen of a README answer?
#
# - a) The history of the project.
# - b) What it is, whether it works (with uncertainty), and how to run it.
# - c) The full source code of the main module.
# - d) Acknowledgements.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w12.46_q1", answer)

# %% [markdown]
# **Q2.** Why report "0.88 (95% CI 0.81 to 0.93)" instead of "0.884"?
#
# - a) Fewer decimals look more professional.
# - b) The interval is a detail most readers skip, so it is optional.
# - c) With 7 test experiments the estimate is imprecise; the interval tells the reader how much weight it can bear.
# - d) Because the best of several runs was 0.93.

# %%
### BEGIN SOLUTION
answer = "c"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w12.46_q2", answer)

# %% [markdown]
# **Q3.** Who is a model card written for?
#
# - a) People deciding whether (and how) to use the model: intended use, limits, data, metrics, risks.
# - b) Engineers who want every hyperparameter.
# - c) Marketing.
# - d) Lawyers checking the licence.

# %%
### BEGIN SOLUTION
answer = "a"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w12.46_q3", answer)

# %% [markdown]
# **Q4.** Which is the most useful limitation?
#
# - a) "More data would improve the model."
# - b) "This is only a student project."
# - c) "The dataset is not perfect."
# - d) "A window that starts during a fault raises no alarm, because the baseline is computed from faulty readings."

# %%
### BEGIN SOLUTION
answer = "d"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w12.46_q4", answer)

# %% [markdown]
# **Q5.** Which sentence belongs in the Overview?
#
# - a) "A production-ready detector for industrial pumps."
# - b) "An educational prototype evaluated on 7 held-out laboratory recordings; not tested on real equipment."
# - c) "Guaranteed 100% detection of valve faults."
# - d) Nothing about scope; let the results speak.

# %%
### BEGIN SOLUTION
answer = "b"
### STARTER
answer = "?"  # put your letter between the quotes
### END SOLUTION
quiz("w12.46_q5", answer)

# %% [markdown]
# ## Recap
#
# - Three documents for three readers: README (visitor), technical report (reviewer), model card (would-be user).
# - One set of numbers, copied from code, each with its uncertainty in one consistent format.
# - Headings are structure you can check: required sections, a code block in Quickstart, bullets in Limitations.
# - Blunt rules catch the two worst habits: decimals without intervals and claims beyond the evidence.
# - Limitations are specific and testable; scope is stated plainly ("educational prototype, laboratory data").
# - A structural check finds what is missing; only a careful reader can judge what is there. Ask a friend to read it.
#
# **On the job.** Teams often put checks like these into CI: a link checker, a spell checker, a script that fails
# the build if a results table in the docs disagrees with the latest evaluation file. The habit you practised here,
# numbers generated by code and checked by code, is what keeps documentation true after the tenth change.
#
# **Going further.** Mitchell et al. (2019), *Model Cards for Model Reporting* (arXiv:1810.03993) for the original
# proposal. The advanced track's notebook 44 (report and limitations, in `advanced/notebooks/`) has a longer worked
# technical report and model card for the same project. Next: notebook 47, interview preparation.

# %%
# Record your progress (optional; stored in progress/progress.json):
from mlcourse.progress import mark
# mark("46", "reading")
# mark("46", "guided")
