# w1d6 — Independent refactor: an exploratory notebook becomes the project skeleton

**Unit id:** `w1d6` · **Week 1, core day 6** · **Handbook:** [H2.3 Git workflow and refactoring discipline](../../handbook/ch02_maintainable_python/h2_3_git_workflow_refactoring.md)
**Data:** real SKAB recordings for the lab (`python project/get_skab.py`, see [project/README.md](../../project/README.md));
SYNTHETIC SKAB-format files for all checks and for the worked example.

> Commands are run from the course repository root unless a step says otherwise.
> This is an **independent** session. Section 4 is a checklist, not a walkthrough.

---

## 1. Purpose

**Primary objective.** Without step-by-step guidance, turn an exploratory notebook on the project
dataset into the first version of the `flowguard` package, as a sequence of small commits in which
structure changes and behaviour changes never share a commit.

**Why an applied ML engineer needs it.** Almost every model that reaches production started as a
notebook, and the notebook's conclusions were trusted before anyone checked its plumbing. The
valuable skill is not "tidying code". It is the ability to (a) change structure while holding
behaviour fixed, (b) notice where the held behaviour is wrong, and (c) leave a history in which a
reviewer can verify each of those claims separately. This notebook is a fair specimen: it runs
without error, prints plausible numbers, and is wrong in at least five ways that matter to the
project.

**You will practise**

- reading a notebook export for hidden state and order dependence before touching it;
- pinning current behaviour, then extracting functions behind it;
- separating "no behaviour change" commits from "behaviour change" commits, and saying which is which;
- using the staging area to review your own diff before it becomes history;
- keeping data, environments and debris out of the repository.

**Prerequisites.** [w1d3](../w1d3_package_structure/README.md) (package layout, entry point),
[w1d5](../w1d5_testing_ml_code/README.md) (tests on small constructed inputs). w1d4 is helpful, not
required. Git basics (`add`, `commit`, `log`, `diff`) are assumed; H2.3 covers what goes beyond them.
The dataset must be downloaded once: `python project/get_skab.py`.

**Deliverable.** A Git repository `flowguard` (outside the course repository) containing package
v0.1, tests, a README stub, a `.gitignore`, a `NOTES.md` that records every place where the package
disagrees with the notebook and why, and a completed `COMMIT_REVIEW.md`.

**Completion criteria**

- [ ] `WB_TARGET_DIR=<your repo> python -m pytest lessons/w1d6_notebook_to_package/checks -q` passes.
- [ ] `flowguard summary --raw-dir <abs path>/data/raw/skab` run from `/tmp` reports **35** experiments and **46,806** rows.
- [ ] `NOTES.md` lists at least four notebook-versus-package discrepancies, each with both numbers and the mechanism.
- [ ] History has at least six commits; every behaviour change is alone in its commit and says so in its message.
- [ ] `COMMIT_REVIEW.md` is filled in honestly against your own `git log`.
- [ ] No hint beyond hint 1 was opened (otherwise mark `guided`, not `independent`).

**Time budget: essential path, 2 h**

| Activity | Minutes |
|---|---|
| Section 2 and handbook H2.3 quick reference | 20 |
| Section 3: replay the worked example and read its history | 15 |
| Section 4: the refactor | 70 |
| Sections 7-8: commit self-review, assessment, reflection | 15 |

**Optional extension, up to 1 h:** the challenge (about 40 min) and the debugging interview rep (about 15 min).

---

## 2. Conceptual explanation

### 2.1 A notebook is a program whose state you cannot see

A script's state at line *n* is determined by lines 1 to *n* − 1. A notebook's state at a cell is
determined by **the order in which cells were executed in that kernel session**, including cells
that were later edited or deleted. The file on disk records the cell text, not that order. So a
notebook export has two properties a script does not:

- **Hidden state.** A name such as `df` may refer to whatever was last assigned to it by any cell.
  The reader of cell 14 cannot tell which.
- **Order dependence.** Running the cells top to bottom may give a different result from the one the
  author saw, and neither run is "the" result.

You know this from analysis notebooks on recordings: a filter cell re-run twice, a channel list
edited after the epochs were cut. The difference in industry is only that someone else will build on
the numbers without having been in the kernel session.

The practical consequence for refactoring: **the notebook's printed output is a claim about the code,
not a specification.** You pin it so that you can tell when *you* change something, and you expect
to overturn parts of it.

### 2.2 Two kinds of change, never in one commit

Let `f` be the program before a commit and `f'` after it.

- A **refactoring** is a change for which `f'(x) = f(x)` for every input `x` you care about. Its
  evidence is an unchanged characterization output plus passing tests.
- A **behaviour change** is one for which `f'(x) ≠ f(x)` for some `x`. Its evidence is a test that
  failed before and passes after, plus a sentence saying why the new value is the right one.

A commit that mixes them can be verified by neither kind of evidence: the characterization output
moved, so it no longer shows that the structural part was safe, and the reviewer cannot tell which
lines caused the numbers to move. This is the same discipline as changing one factor per experimental
condition, applied to code history.

The **characterization test** (also called a golden-master or approval test) is the instrument for
the first kind: run the program, store its output, assert the output is unchanged. It encodes no
opinion about correctness. When a behaviour-change commit moves the output, you update the stored
output *in that same commit*, and the diff of the golden file is the reviewable statement of what
changed. The worked example shows exactly this in commit 5.

Characterization has limits you should state rather than discover later: it only covers the inputs
you ran; it is as brittle as the output format; and it cannot be used when the output is known to be
wrong in ways that make it worthless to preserve. In today's lab the notebook's output is of that
last kind for several cells, which is why the lab asks for a discrepancy table instead of a golden
file.

### 2.3 Seams: where to cut

A **seam** is a place where behaviour can be observed or substituted without editing the code around
it. In a notebook export the natural seams are the points where data crosses from one concern to
another:

```
file on disk ──► one experiment as a DataFrame ──► all experiments as one table ──► summaries
             load_experiment(path)              load_raw(raw_dir)                summarize(tidy)
```

Each arrow becomes a function with data in and data out, no printing, no globals, no paths other
than its arguments. The order of extraction that keeps you safe is **from the leaves inward**: first
the function nothing else depends on being a function (one file to one frame), then its callers.

Three questions decide whether a notebook line belongs in the package at all:

1. Does a later step consume its *result* (keep, as a function), or did the author only *look* at it (drop, or keep as a report command)?
2. Is it a fact about the data (belongs in a test or a data-quality check, w2d3) or a transformation (belongs in the package)?
3. Was it an idea that was abandoned? Notebooks are full of these; the z-score cell in today's notebook is one, and it is wrong.

### 2.4 The staging area is a review tool

Git separates three things: the working tree (your files), the index or staging area (the content
of the *next* commit), and history. `git add -p` walks through your changes hunk by hunk and lets you
stage some and leave others; `git diff --staged` shows exactly what the next commit will contain.
Used together they make every commit a deliberate statement:

```bash
git add -p                 # choose hunks; this is where you notice the stray debug print
git diff --staged          # read the commit before it exists
python -m pytest -q        # the staged change should leave the tests passing
git commit -m "Extract load_experiment (no behaviour change)"
```

Commit size is governed by one rule: **a commit should be describable in one sentence without the
word "and"**, and the project should work after it. That makes `git bisect` usable later (every
commit is a valid state to test) and makes review cheap.

### 2.5 What never goes into the repository

| Never commit | Why | Instead |
|---|---|---|
| Datasets, especially third-party ones | size; licence (SKAB is GPL-3.0); history keeps them forever | a download script, checksums, `.gitignore` |
| Model weights, run outputs, caches | size; they are *derived*, so the command that makes them is the source | ignore `runs/`, publish artifacts elsewhere (Week 5) |
| Environments (`.venv/`) and bytecode | machine-specific, large, reproducible from `pyproject.toml` | `.gitignore` |
| Secrets (keys, tokens, `.env`) | a pushed secret must be treated as compromised even if deleted | environment variables; rotate if it ever happens |
| Notebook outputs with data in them | patient or customer data leaks through rendered cells | strip outputs, or keep notebooks out of the package repo |

Two facts about Git make the first row important. Deleting a file in a later commit does not remove
it from history. And `.gitignore` only affects files that are **not yet tracked**: adding a pattern
after the file was committed changes nothing until you also run `git rm --cached <file>`.

### 2.6 An industry example

A team inherits a churn notebook whose final cell reports ROC AUC 0.91. The first engineer rewrites
it as a clean pipeline in one large commit; the pipeline reports 0.78. Nobody can say whether the
rewrite introduced a bug or removed one, and a week is spent re-deriving the notebook's behaviour by
hand. The second approach takes one more day up front: pin the notebook's output; extract loading,
feature and split functions with the output unchanged (four commits); then fix, one commit each, a
join that duplicated customers and a scaler fitted on all rows. The history then reads "0.91 → 0.91
→ 0.91 → 0.84 (deduplicate) → 0.78 (scaler)", and each drop is attributed to a named cause that a
stakeholder can be told about. The final number is the same. What differs is that the second team
can defend it.

### 2.7 Misconceptions

- *"The notebook ran, so its numbers are the baseline to reproduce."* It ran in an unknown cell order. Reproduce it once, then audit it.
- *"Refactoring means improving the code."* Refactoring means **not** changing behaviour. Improvement of behaviour is a separate, tested step.
- *"Small commits are bureaucracy."* They are what makes a behaviour change attributable. One large commit destroys that information permanently.
- *"`.gitignore` will keep the data out."* Only if the pattern exists before the first `git add`, and only for untracked files.
- *"I will squash it later."* Squashing after review is fine. Squashing a refactor together with a fix removes the evidence that the refactor was safe.
- *"Linting is about style."* The useful part of a linter finds real defects (unused variables that reveal a forgotten step, shadowed names, mutable defaults). Formatting is the unimportant part, which is why it should be automatic and never discussed.

---

## 3. Worked example: a meters notebook, commit by commit

A different, much smaller notebook is refactored in six commits. The data is SYNTHETIC (three
electricity meters, twelve readings each); it demonstrates the mechanics only.

```
example/
  steps/01_notebook_as_found/     explore_meters.py, meters.csv
  steps/02_characterization/      tests/test_characterization.py, tests/golden.txt, .gitignore
  steps/03_extract_loading/       meterkit.py, explore_meters.py
  steps/04_remove_hidden_state/   meterkit.py, explore_meters.py
  steps/05_fix_fleet_mean/        explore_meters.py, tests/test_meterkit.py, tests/golden.txt, ...
  steps/06_readme/                README.md
  replay_history.py               rebuilds these six commits in a scratch repository
```

Each `steps/` directory holds only the files that commit adds or changes. Rebuild the history and
read it:

```bash
python lessons/w1d6_notebook_to_package/example/replay_history.py /tmp/meters-demo
cd /tmp/meters-demo
git log --oneline
git show HEAD~1            # the one behaviour-changing commit
git diff HEAD~3 HEAD~2     # a pure extraction
```

Output of the replay in the authoring session (hashes differ on every run, since they depend on time):

```
01_notebook_as_found       tests: no tests ran in 0.00s
02_characterization        tests: 1 passed in 0.39s
03_extract_loading         tests: 1 passed in 0.37s
04_remove_hidden_state     tests: 1 passed in 0.39s
05_fix_fleet_mean          tests: 3 passed in 0.70s
06_readme                  tests: 3 passed in 0.75s

32751cd Add README
611efe5 Fix fleet mean: it used M2 rows only (BEHAVIOUR CHANGE)
d991c63 Extract mean_kwh and peak_days, replace cells with main() (no behaviour change)
653497f Extract load_readings and daily_totals (no behaviour change)
47f30b4 Pin current output with a characterization test
c6808c8 Add notebook export and sample data as found
```

**The flaw.** The notebook has a cell `df = df[df.meter_id == "M2"]` ("look at the big one"), and a
later cell prints `"fleet mean kwh per reading"` from `df`. The "fleet" mean is the mean of one meter.

**Decisions worth noticing**

1. **Commit 1 adds the notebook untouched.** History then contains the thing being refactored, and every later diff is measured against it.
2. **Commit 2 pins the output, wrong value included** (`fleet mean ... 3.603`). The test docstring says it is scaffolding, not a claim of correctness.
3. **Commits 3 and 4 move code and leave `golden.txt` untouched.** That untouched file is the evidence that they are refactorings. Commit 4 has to keep the bug alive to stay honest, so it does so explicitly: `mean_kwh(m2)` with a comment `BUG PRESERVED ON PURPOSE`. Hidden state became a visible, named argument. That is the whole trick: once the wrong input has a name, the bug is one line.
4. **Commit 5 is the only one that changes behaviour**, and its diff shows it three ways: one line of code, one line of golden output, and a new unit test that states the correct behaviour on a hand-checkable frame.

   ```
   611efe5 Fix fleet mean: it used M2 rows only (BEHAVIOUR CHANGE)

    explore_meters.py      |  4 +---
    tests/conftest.py      |  4 ++++
    tests/golden.txt       |  2 +-
    tests/test_meterkit.py | 23 +++++++++++++++++++++++
    4 files changed, 29 insertions(+), 4 deletions(-)

   -fleet mean kwh per reading: 3.603
   +fleet mean kwh per reading: 1.949
   ```
5. **The example keeps a flat layout** (`meterkit.py` beside the script) to stay small. Your project uses the `src` layout from w1d3.

**Interpretation.** The number moved from 3.603 to 1.949, a factor of 1.8, and the history attributes
all of it to one named cause. Nothing here says the new number is "good"; it says the new number is
what the label on the print statement claims.

**A real incident from building this example.** The first version of `replay_history.py` copied
files with their modification times preserved. Both versions of `golden.txt` had the same size and
the same timestamp, Git's change detection (which checks size and time before content) concluded
the file had not changed, and commit 5 silently omitted it while the tests passed. `git show --stat`
on the supposedly behaviour-changing commit is what revealed it. Reading your own commit before
moving on is not a formality.

---

## 4. Lab (independent): refactor `explore_skab.py`

The notebook export is [`lab/explore_skab.py`](lab/explore_skab.py). It loads the SKAB files,
renames columns, concatenates experiments and prints summaries. It runs without error:

```bash
python project/get_skab.py                                       # once; data/raw/skab/ is git-ignored
python lessons/w1d6_notebook_to_package/lab/explore_skab.py | tee /tmp/notebook_output.txt
```

Its first lines of output in the authoring session:

```
valve1 16
valve2 4
other 14
(46806, 13)
(37401, 14)
experiments: 34
```

**Target.** `flowguard` v0.1 as specified in [docs/FLOWGUARD_SPEC.md](../../docs/FLOWGUARD_SPEC.md):

- `flowguard.data.SENSOR_COLUMNS`, `load_experiment(path) -> DataFrame`, `load_raw(raw_dir) -> DataFrame` (the tidy table defined in the spec);
- a console command `flowguard summary --raw-dir <dir>` that prints **one JSON document** on stdout:
  `{"n_experiments": ..., "n_rows": ..., "experiments": [{"experiment_id", "family", "n_rows", "anomaly_fraction", ...}, ...]}`;
- user errors (missing directory, no experiment files) give a one-line message on stderr and a non-zero exit code;
- `load_experiment` raises `FileNotFoundError` for a missing file and `ValueError` naming any missing column;
- tests that build their own tiny SKAB-format files, a README stub, a `.gitignore`.

**Where to work.** In a new repository **outside** the course repository, because this becomes your
portfolio project with its own history:

```bash
mkdir -p ~/projects/flowguard && cd ~/projects/flowguard && git init -b main
```

Grade it from the course repository with:

```bash
WB_TARGET_DIR=~/projects/flowguard python -m pytest lessons/w1d6_notebook_to_package/checks -q
```

(`python wb.py check w1d6` honours the same variable.) The checks use synthetic files only. They do
not look at your Git history; that is what `COMMIT_REVIEW.md` is for.

### Checklist

Work through these in order. How you do each one is up to you.

1. **Read before running.** Read the export once and write down, per cell: what it needs from earlier cells, and what it leaves behind. Predict two numbers you expect to be wrong. (10 min)
2. **Record the notebook's claims.** Commit the export untouched and its captured output (`notes/notebook_output.txt`) as the first commit. (5 min)
3. **Skeleton.** `pyproject.toml`, `src/flowguard/`, `.gitignore` **before** any data can be added by accident, an empty test that runs. One commit. (10 min)
4. **Extract leaf to root.** `load_experiment`, then `load_raw`, then the summary. Write each function's test on a constructed file *first or alongside*; make at least one constructed case hostile (a two-digit file name, shuffled rows, a file without label columns, reordered columns). (30 min)
5. **Confront the notebook.** For every number where package and notebook disagree, add a row to `NOTES.md`: notebook value, package value, mechanism, which is right and how you know. Fix-commits are separate from extraction-commits. (10 min)
6. **Command and README.** `flowguard summary`, then a README stub that says what this is, where the data comes from, and the two commands a stranger needs. (10 min)
7. **Review your history** with [`lab/COMMIT_REVIEW.md`](lab/COMMIT_REVIEW.md). Copy it into your repository, fill it in, commit it. (5 min)

### Checkpoints

| When | You should be able to show |
|---|---|
| After step 2 | `git log --oneline` has one commit; `git status` is clean; the data directory is not in the repository |
| After step 4 | `python -m pytest -q` passes in your repo **without** the dataset present and from another directory |
| After step 5 | The package reports a different number of experiments and of rows than the notebook, and you can say why in one sentence each |
| After step 6 | `cd /tmp && flowguard summary --raw-dir <abs path> \| python -m json.tool > /dev/null` succeeds |

### When something goes wrong

| Symptom | Likely cause | What to do |
|---|---|---|
| Check says "no pyproject.toml in .../lab" | `WB_TARGET_DIR` not set, or set to a path with `~` inside quotes | `export WB_TARGET_DIR=$HOME/projects/flowguard` |
| Your tests pass, the checks fail on experiment ids | your constructed files never had a name like `10.csv` | add the hostile case to your own tests first, watch it fail, then fix |
| Row count is 37,401 | the fault-free recording was dropped somewhere | find the line that can remove rows; ask what `NaN` labels came from |
| `git status` shows hundreds of data files | `.gitignore` written after `git add`, or pattern does not match | `git rm -r --cached data`, fix the pattern, verify with `git check-ignore -v data/raw/skab/valve1/0.csv` |
| JSON check fails with "stdout must be exactly one JSON document" | a progress `print` shares stdout with the result | diagnostics go to stderr or logging (w1d4) |
| A commit contains both moved code and a changed number | hunks were staged together | `git reset --soft HEAD~1`, then `git add -p` and commit twice |

The reference solution's own notes ([`solutions/.../lab/NOTES.md`](../../solutions/lessons/w1d6_notebook_to_package/lab/NOTES.md))
contain every discrepancy with real numbers. Open them only after your `NOTES.md` is committed.

---

## 5. Independent challenge

[`challenge/README.md`](challenge/README.md): add a sampling-gap report (`flowguard.data.find_gaps`
and `flowguard gaps`) test-first on a branch, and reconcile it with the notebook cell that printed
`n gaps > 5 s: 19`. It transfers today's method to behaviour the notebook only gestured at.

```bash
WB_TARGET_DIR=~/projects/flowguard python -m pytest lessons/w1d6_notebook_to_package/checks_challenge -q
```

## 6. Progressive hints

Open in order, and only when stuck for more than ten minutes. Opening hint 2 or 3 means the unit is
recorded as *guided*.

1. [Concept](hints/hint1_concept.md): what to look for, without saying where.
2. [Approach](hints/hint2_approach.md): an extraction order and the hostile test cases.
3. [Partial implementation](hints/hint3_partial.md): the shape of `load_experiment` and one test.

Full reference: `solutions/lessons/w1d6_notebook_to_package/` (lab, challenge, notes, answers).

## 7. Assessment

[`assessment.md`](assessment.md): five reasoning questions (one asks you to defend a design choice),
the commit-hygiene self-review rubric, and a 10-15 minute **debugging** interview rep. Write your
answers before opening `solutions/lessons/w1d6_notebook_to_package/assessment_answers.md`.

Automated checks cover the package contract and that your tests are self-contained. They cannot
judge your history or your notes; the rubric does.

## 8. Reflection and review

**You should now be able to, alone:**

- take a notebook you did not write and say which of its printed numbers depend on execution order;
- refactor it into tested functions with a history that separates structure from behaviour;
- explain, for each number that changed, what caused the change;
- keep a repository free of data, environments and secrets from the first commit.

**Reflection prompt** (write three or four sentences in `progress/notes.md` via
`python wb.py note w1d6 "..."`): Which of the notebook's errors would you have shipped if you had
simply "cleaned up" the code? What in your process caught it, and what would have caught it earlier?

**Retrieval question for the review day (answer from memory):** A colleague adds `data/` to
`.gitignore` and commits; `git status` still shows the 300 MB file they committed last week as
tracked, and the repository is still large after they delete the file. Explain both observations and
say what has to be done about each.

**Record progress**

```bash
python wb.py mark w1d6 reading
python wb.py mark w1d6 independent      # only if checks pass and no hint beyond hint 1 was used
python wb.py note w1d6 "flowguard repo: ~/projects/flowguard, commit <hash>; hints used: ..."
```

**Next:** `w1d7_review` (light day): Week 1 retrieval sheet and interview set 1. See
[roadmap/SCHEDULE.md](../../roadmap/SCHEDULE.md). The repository you created today is where the
project continues in w2d3 (ingestion and data-quality checks).

---

### Verification record

| What | Result (2026-11-21, Python 3.13.18, pandas 3.0.5, Git 2.43.0) |
|---|---|
| `lab/explore_skab.py` on the real data | runs; output quoted above |
| Reference `flowguard summary` on the real data | 35 experiments, 46,806 rows |
| Worked example replay | six commits, tests pass after each (output quoted above) |
| `python tools/verify_checks.py lessons/w1d6_notebook_to_package` | reference passes both parts; 7 lab mutants and 4 challenge mutants rejected |
| Shipped `lab/` against the checks | fails (no project there by design) |
