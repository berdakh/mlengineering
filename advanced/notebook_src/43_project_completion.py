# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/advanced/notebooks/43_project_completion.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 43 · Project completion audit: reproduce from a clean clone
#
# **Week 8 · day 1 · 2 h essential path + up to 1 h optional** · lab files: [`labs/w8d1_project_completion/`](../../labs/w8d1_project_completion/)
#
# **Objective.** Audit the project against the deliverables checklist and reproduce every headline number from a fresh clone.

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
# Unit id `w8d1_project_completion` · Week 8, day 1 · Handbook:
# [H8.3 Clean-clone reproduction](../../docs/handbook/ch08_reproducible_experiments/h8_3_clean_clone_reproduction.md) ·
# Content status: see [STATUS.md](../../docs/guides/status.md)
#
# **This is an independent integration session.** Like the milestones ([w4d6](24_project_milestone_1.ipynb),
# [w5d6](30_project_milestone_2.ipynb), [w7d6](42_project_milestone_4.ipynb)), the lab is a
# contract and a checklist, not a walkthrough. Today you stop adding features and find out what your project can
# actually show.

# %% [markdown]
# ## 1. Purpose
#
# **Objective.** Audit the flowguard project against its deliverables checklist and reproduce every headline
# number from a fresh clone: new directory, new virtual environment, pinned dependencies, data downloaded and
# verified by hash, one command per artifact, numbers compared with the committed report within stated
# tolerances. You build the audit tool, run it on your repository, and write down what is missing and what you
# will deliberately leave out.
#
# **Why an applied ML engineer needs it.** "Can you rerun that?" is the first question a reviewer, a new
# teammate or an interviewer asks about a result. A number that only exists on the author's laptop is an
# anecdote. The audit turns "I think it is reproducible" into a log anyone can check, and it is the cheapest
# way to find the hidden state that every project accumulates: a file that was never committed, a dependency
# installed months ago, a number pasted into a report by hand.
#
# **Deliverables.**
# * `audit/clean_clone_check.py` (lab), passing `python wb.py check w8d1`.
# * In your repository: `REPRODUCE.toml`, a fully pinned `requirements.lock`, `expected/results.json`, and
#   `audit/REPRODUCTION_LOG.md` produced by the tool against your latest commit.
# * `DELIVERABLES.md` (lab) for your project and `challenge/SCOPING_MEMO.md`.
#
# **Completion criteria.**
# * `python wb.py check w8d1`: the tool passes a reproducible SYNTHETIC project and fails six defective ones for
#   the right reason; your `DELIVERABLES.md` accounts for every item in the project checklist.
# * Your own repository's audit log, committed. A FAIL is acceptable if the memo says what you will do about it.
# * `python wb.py check w8d1 --challenge` passes.
#
# **Prerequisites.** All four milestones ([w4d6](24_project_milestone_1.ipynb), [w5d6](30_project_milestone_2.ipynb),
# w6d6, [w7d6](42_project_milestone_4.ipynb)); [w1d4](04_config_logging.ipynb) (run directories and
# provenance); [w6d2](32_docker_reproducibility.ipynb) (lockfiles and pinning).
#
# **Time budget (2 h essential).**
#
# | Activity | Minutes |
# |---|---|
# | Read section 2; run the worked example | 20 |
# | Lab: implement the seven functions of the audit tool until the checks pass | 45 |
# | Lab: `REPRODUCE.toml`, lockfile and expected results in your repository; run the audit on it | 25 |
# | Lab: `DELIVERABLES.md` | 10 |
# | Challenge: gap list and scoping memo | 20 |
# | *Optional extension: run the audit on Python 3.11 too (CI matrix or a second interpreter); add `repeat = 2`; audit a classmate's repository* | *up to 60* |

# %% [markdown]
# ## 2. Conceptual explanation
#
# ### 2.1 What "reproducible from a clean clone" requires
#
# A result is reproducible from a clean clone when someone with the repository URL, a commit hash and an
# ordinary machine can regenerate it without asking you anything. Each word excludes a class of hidden state:
#
# | Requirement | Hidden state it excludes | Where the course met it |
# |---|---|---|
# | **Clone**, not copy | files outside git: data, caches, notebook outputs, a local config | w1d6 (`.gitignore`), w2d3 (raw data immutable and downloaded) |
# | **Fresh environment** | packages installed months ago, a different version on your laptop | w1d3 (venv), w6d2 (lockfile with transitive pins) |
# | **Pinned** dependencies | `>=` resolves differently next month | w6d2: 20 of 21 packages changed in a year |
# | **Data by hash** | a silently changed upstream file | `project/get_skab.py` and `MANIFEST.json` |
# | **Frozen split** | a test set redrawn by a seed or a code change | w3d1: `splits/v2.json` |
# | **One command per artifact** | manual steps between commands, notebooks run out of order | w4d6 (`make evaluate`) |
# | **Generated numbers** | a number typed or "rounded up" in a report | w4d6, w7d6: reports built from `results.json` |
# | **Deterministic execution** | unseeded randomness, thread counts, iteration order | w1d4 (seeds), w4d3 and w4d5 (thread pinning), w5d1 (CSV `float_precision`) |
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-43-01.svg" alt="Diagram 1 of notebook 43" style="max-width:100%">
#
# ### 2.2 Precise terms
#
# * **Repeatability**: same person, same machine, same code, same result (a rerun).
# * **Reproducibility** (in this course's sense): same code and data, different machine and environment, same
#   result within a stated tolerance. That is what the clean clone tests.
# * **Replicability**: a new implementation or new data reaching the same conclusion. Out of scope today;
#   protocol B in w4d2 was a small step towards it (a held-out fault family).
# * **Headline number**: a value a reader would quote from your report. Not every number in `results.json` needs
#   to be audited, but every headline number must be.
# * **Tolerance**: the largest difference you accept, stated before running. For deterministic CPU code
#   `abs_tol = 1e-9` (or exact equality) is realistic; for GPU training or BLAS reductions across machines you
#   may need a tolerance, and then you must say why and how big.
#
# ### 2.3 Tolerances, and why exact is the right default
#
# Floating-point arithmetic is deterministic on one machine for one sequence of operations. Differences across
# machines come from a different order of operations: multi-threaded reductions, vectorised kernels with
# different widths, different library versions. Summing $n$ numbers in a different order changes the result by
# at most about $n\,\varepsilon \sum_i |x_i|$ with $\varepsilon \approx 2.2 \times 10^{-16}$ for double precision, which
# for the metrics in this project is far below $10^{-9}$. So a difference of $0.03$ in a PR-AUC is never
# "floating-point noise": it is a different computation, different data or a number that was not produced by
# the code. Start with exact comparison and relax a tolerance only with a stated reason.
#
# ### 2.4 The failures you will meet, and their signature in an audit
#
# | Failure | What the audit sees | Fix |
# |---|---|---|
# | Absolute path (`/home/you/...`) | static scan hit; then a missing file in the clone | paths relative to the repository root, or configuration |
# | Unpinned or missing dependency | `>=` in the lockfile; `ModuleNotFoundError` in the fresh venv | `pip freeze` in a clean venv, commit the full lock |
# | Data not under version control and not downloaded | `FileNotFoundError` in the clone | a download step with hashes, or commit small data |
# | Number edited by hand | headline mismatch, everything else fine | regenerate; never type numbers |
# | Unseeded randomness or thread-dependent results | different numbers on a repeat of the same commit | seeds in config; `OMP_NUM_THREADS=1` where it matters |
# | Results committed but code changed after | mismatch | regenerate and commit together; record the commit in provenance |
#
# ### 2.5 Connection to other domains
#
# Many published results cannot be rerun. In lab research the hidden state is usually a preprocessed data file
# made by a script that no longer exists, or a cleaning step done by eye. The industry version is the same, but the cost is paid by a colleague
# three months later instead of a reader. The cure is identical: make the raw-to-result path a command, then
# prove it runs somewhere else.
#
# ### 2.6 An industry example
#
# A team ships a demand model whose offline evaluation shows a 4 % error reduction. Six months later the model
# degrades and someone tries to retrain it: the training notebook depends on a feature table that was rebuilt
# since, the original environment used a pandas version with different groupby defaults, and nobody can
# reproduce the 4 %. The team cannot tell whether the model degraded or never was as good as reported. A
# clean-clone audit at release time, with the log archived next to the model, would have answered that
# question in a minute.
#
# ### 2.7 Gap lists and scoping
#
# An audit always finds gaps. The professional move is to decide, in writing, what to fix now, what to defer and
# what to drop, with the time you actually have. A deliberate "out of scope, because..." reads as judgement; a
# silent half-finished deliverable reads as a mistake.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/docs/assets/diagrams/mmd-43-02.svg" alt="Diagram 2 of notebook 43" style="max-width:100%">
#
# ### 2.8 Limitations and misconceptions
#
# * "It runs on my machine in a fresh venv" is not a clean clone: your working tree still has untracked files.
# * A Docker image is not a substitute: an image built from a dirty tree is reproducible only for that image.
#   The audit should start from the commit.
# * A PASS shows the numbers can be regenerated; it does not show they are right. Validity was the job of
#   Weeks 2-4.
# * Downloading data from a third party makes the audit depend on that party. The hash manifest tells you
#   when the upstream changed; it cannot bring the old file back. Keep an archived copy where the licence allows.
# * Matching the committed number exactly after a code change can hide a bug that did not move the headline.
#   The audit is a floor, not a test suite.

# %% [markdown]
# ## 3. Worked example: an audit by hand
#
# `example/manual_audit.sh` builds a tiny SYNTHETIC project whose data folder is git-ignored, runs it in the
# author's tree, then does by hand what your tool will automate.
#
# ```bash
# bash labs/w8d1_project_completion/example/manual_audit.sh
# ```
#
# Output (copied from a run on 2026-11-25):
#
# ```text
# == 1. the author's project (data/ is git-ignored)
# mean = 4.0
# tracked files: .gitignore summarise.py
# == 2. clean clone + fresh venv, run the same command
# FAILED in the clone: FileNotFoundError: [Errno 2] No such file or directory: 'data/values.csv'
# == 3. fix: commit the (small) data file, then audit again
# mean = 4.0
# author and clone agree
# ```
#
# What to notice: step 1 succeeds, and `git ls-files` already tells you why it should not be trusted (the data
# is not tracked). Step 2 is the audit: clone, fresh venv (`--without-pip`, so nothing from your system leaks
# in), same command. Step 3 fixes the cause, not the symptom. For SKAB the fix is not committing the data (the
# licence is GPL-3.0 and the files are 4 MB) but a download step that checks hashes.
#
# The same procedure, automated and run for real against the reference flowguard evaluation (the w4d6 lab
# solution, a fully pinned lock from `pip freeze`, the SKAB download script, and the committed
# `results.json` as the expected file) passed: 18 headline values, maximum difference 0, 75 s in total.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/labs/w8d1_project_completion/figures/audit_timeline.svg" alt="Real clean-clone audit of the reference evaluation: about 5 s to clone and install, 7 s to download the data, 63 s to evaluate; verdict PASS" width="100%">
#
# *Real run (2026-11-22, Python 3.13.18); values in `figures/figure_data.csv`. Most of the time is the
# evaluation itself, with 2000 bootstrap replicates; the environment and data steps are cheap enough to run on
# every release.*

# %% [markdown]
# ## 4. Lab: build the audit tool, then audit your project
#
# The checks run your tool against seven SYNTHETIC git repositories (built in a temporary directory by
# `checks/synthetic_repo.py`): one reproducible project and six that each carry one defect.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering/main/labs/w8d1_project_completion/figures/findings_matrix.svg" alt="SYNTHETIC projects: the reference tool flags absolute_path (plus the missing file it causes), unpinned_requirement, missing_dependency, missing_file, headline_mismatch, and nondeterministic (plus a mismatch); the good project passes" width="100%">
#
# *SYNTHETIC repositories; produced by running the reference tool (`figures/make_figures.py`). Two defects
# produce a second, consequential finding: the absolute path also makes the file missing in the clone, and an
# unseeded pipeline also misses its expected value. The checks require the root-cause code to be present.*
#
# **Checklist.**
#
# 1. Read the module docstring of `lab/audit/clean_clone_check.py` and `lab/REPRODUCE.example.toml`.
#    *Checkpoint:* you can say, for each finding code in `lab/README.md`, which function produces it.
# 2. Implement `clone`, `scan_absolute_paths` and `read_requirements`. Run
#    `python wb.py check w8d1`: the `unpinned` and `absolute_path` cases should now pass.
# 3. Implement `make_venv`, `classify_failure` and `run_steps`. The venv must not see system site packages, or
#    the `missing_dependency` case passes when it should fail. Steps run **in the clone**, never in the source.
# 4. Implement `compare_headline`. *Checkpoint:* all 14 audit checks pass (the other 4 grade `DELIVERABLES.md`).
# 5. In your repository: add `REPRODUCE.toml` (adapt the example), generate `requirements.lock` with
#    `pip freeze` inside a fresh venv where you installed only your direct dependencies, copy the results file
#    your report was generated from to `expected/results.json`, commit, and run
#    `python labs/w8d1_project_completion/lab/audit/clean_clone_check.py <your repo> --log <your repo>/audit/REPRODUCTION_LOG.md`.
# 6. Fill in `lab/DELIVERABLES.md` against the checklist in [docs/guides/project.md](../../docs/guides/project.md).
#
# **Debugging guidance.**
# * *`git clone` of a local path fails:* the source must be a git repository with at least one commit; uncommitted
#   changes are (correctly) invisible to the audit.
# * *The good project fails with `missing_dependency` on `encodings` or similar:* you probably set `PYTHONHOME`
#   or `PYTHONPATH` for the step; remove them from the environment you pass.
# * *Everything fails with `install_failed`:* the synthetic projects have an empty lock; create the venv without
#   pip and skip the install when there is nothing to install.
# * *Your own repository fails on the download step:* the audit machine needs network access to the data host;
#   record that in the log rather than committing the data.

# %%
# Run the automated checks on your guided lab.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w8d1")

# %% [markdown]
# ## 5. Independent challenge: gap list and scoping memo
#
# See [challenge/README.md](../../labs/w8d1_project_completion/challenge/README.md). From your audit log and `DELIVERABLES.md`, decide with a stated
# number of hours what you fix now, defer or scope out, and what you will say about it. No hints.
#
#
# ### The challenge brief
#
#
# You have audited your project (lab) and now know what is missing, partial or not reproducible. With a
# fixed amount of time left before you show the project to anyone, decide what to fix, what to defer and
# what to drop **explicitly**, and write it down in SCOPING_MEMO.md.
#
# A half-finished deliverable that is not mentioned reads as a mistake. The same gap, listed with its
# impact and a reason it was scoped out, reads as judgement. Interviewers probe exactly this.
#
# **Inputs.** Your `audit/REPRODUCTION_LOG.md`, your `DELIVERABLES.md`, the limitations recorded in your
# milestone reports, and an honest estimate of the hours you have (the course assumes two sessions: w8d1
# and w8d2, so 4-6 h, minus the time the report will take).
#
# **Acceptance criteria** (`python wb.py check w8d1 --challenge`, structure only):
# * the header states the hours available as a number;
# * at least four gaps, each with evidence (a file, a log line, a number), the impact if left, an effort
#   estimate in hours, a decision (`fix now`, `defer` or `scope out`) and a reason of six or more words;
# * at least one gap is deferred or scoped out, and the `fix now` efforts add up to no more than the hours
#   available;
# * the section on what you will say about scoped-out items has at least 40 words;
# * no placeholders left.
#
# Quality is judged with the rubric in ../assessment.md: are the gaps the ones that
# matter, are the efforts realistic, does each scoped-out item come with what a reviewer should conclude?

# %%
# Run the automated checks on your independent challenge.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w8d1", challenge=True)

# %% [markdown]
# ## 6. Progressive hints
#
# 1. [Concept](../../labs/w8d1_project_completion/hints/hint1_concept.md)
# 2. [Approach](../../labs/w8d1_project_completion/hints/hint2_approach.md)
# 3. [Partial implementation](../../labs/w8d1_project_completion/hints/hint3_partial.md)
#
#
# Open one hint at a time, only after a real attempt.
#
# <details>
# <summary><b>Hint 1 concept</b></summary>
#
#
# The audit has one job: run your project the way a stranger would, with nothing but the commit. Every
# function in the tool removes one way the author's machine could help:
#
# * `clone` removes untracked files (so never copy the working directory);
# * `make_venv` removes installed packages (so system site packages stay off);
# * `read_requirements` removes "whatever version pip picks today" (so only `==` is accepted);
# * `scan_absolute_paths` removes paths that only exist on one machine;
# * `compare_headline` removes "close enough" (so the tolerance is absolute and stated).
#
# A finding is useful only if it names the cause. A crash in the clone is a symptom: read the step's output to
# say *which* module or file was missing.
#
# </details>
#
# <details>
# <summary><b>Hint 2 approach</b></summary>
#
#
# * `clone`: `subprocess.run(["git", "clone", "--quiet", source, str(dest)])`; then `git checkout ref` if the ref
#   is not `HEAD`. Return a `clone_failed` finding on a non-zero exit.
# * `scan_absolute_paths`: iterate over `tracked_files(repo)` (it already calls `git ls-files`), read text files,
#   search each line with `ABS_PATH`, report `path.relative_to(repo)` and the 1-based line number.
# * `read_requirements`: skip blank lines and comments; every other line must `PIN.match`; collect problems.
# * `make_venv`: `venv.EnvBuilder(system_site_packages=False, with_pip=bool(requirements)).create(where)`; install
#   with the venv's own `python -m pip install -r`.
# * `run_steps`: `subprocess.run(step["run"], cwd=repo, env=step_env(bindir), capture_output=True, text=True,
#   timeout=...)`; time it with `time.perf_counter()`; stop at the first non-zero exit and pass the combined output
#   to `classify_failure`.
# * `classify_failure`: two regular expressions, one for `ModuleNotFoundError: No module named '...'` and one for
#   `FileNotFoundError` / `No such file or directory`.
# * `compare_headline`: `get_path` both dictionaries; for numbers compare `abs(got - exp) <= tol`, otherwise `==`.
#
# </details>
#
# <details>
# <summary><b>Hint 3 partial</b></summary>
#
#
# ```python
# def classify_failure(output: str) -> dict:
#     mod = re.search(r"ModuleNotFoundError: No module named '([^']+)'", output)
#     if mod:
#         return finding("missing_dependency",
#                        f"module {mod.group(1)!r} is imported but not installed by the declared requirements")
#     missing = re.search(r"(FileNotFoundError|No such file or directory)[^\n]*", output)
#     if missing:
#         return finding("missing_file", f"a file the pipeline needs is not in the repository: {missing.group(0)[:300]}")
#     return finding("step_failed", output.strip()[-500:])
#
#
# def compare_headline(produced, expected, values):
#     rows, problems = [], []
#     for spec in values:
#         key, tol = spec["key"], float(spec.get("abs_tol", 0.0))
#         exp, got = get_path(expected, key), get_path(produced, key)   # TODO: handle KeyError -> headline_missing
#         if isinstance(exp, (int, float)) and isinstance(got, (int, float)):
#             diff = abs(float(got) - float(exp))
#             ok = diff <= tol
#         else:
#             diff, ok = None, got == exp
#         rows.append({"key": key, "expected": exp, "produced": got, "abs_diff": diff, "abs_tol": tol, "ok": ok})
#         if not ok:
#             problems.append(finding("headline_mismatch", f"{key}: committed {exp!r}, reproduced {got!r}"))
#     return rows, problems
# ```
#
# `make_venv` and `run_steps` are left to you; remember that the steps run in the clone and that the venv's
# `bin` directory goes first on `PATH`, so `python` and `make` inside the steps use it.
#
# </details>

# %% [markdown]
# ## 7. Assessment
#
# assessment.md (section 7 of this notebook): reasoning questions, a design-choice explanation, the milestone rubric, and the
# interview rep "how do I know your numbers are real?".
#
#
# ### Assessment questions
#
#
# #### Rubric (the reviewer uses this; you self-score in the memo)
#
# | Criterion | 1 (below) | 2 (meets) | 3 (exceeds) |
# |---|---|---|---|
# | Reproduction | audit not run, or run on the working tree | audit log committed for the current commit; FAIL findings explained | PASS, plus a second Python version or machine |
# | Environment | direct dependencies only, or `>=` | full lock from a clean venv | lock plus a container built from it (w6d2) and the same numbers inside |
# | Headline coverage | one or two numbers | every number quoted in the report's summary | plus a repeat run showing determinism |
# | Deliverables audit | statuses without evidence | evidence a reviewer can open for every `done` | partial items quantified (what exactly is missing) |
# | Scoping | a wish list | decisions that fit the stated hours, reasons given | what each scoped-out item means for the claims, stated in the report |
#
# #### Reasoning questions
#
# 1. Your audit passes, but a colleague's identical clone on macOS gives a test PR-AUC that differs in the fourth
#    decimal. Is that a reproducibility failure? What do you check first, and what tolerance would you then set,
#    with what justification?
# 2. Why must the audit clone rather than copy, even if you are sure your working tree is clean?
# 3. The lock lists `numpy==2.5.3` but not `threadpoolctl`. What can go wrong, and why does `pip freeze` in a fresh
#    venv fix it while `pip freeze` in your everyday environment does not?
# 4. **Design choice.** The tool compares only the headline values declared in `REPRODUCE.toml`, not the whole
#    results file. Defend this, and say what risk it leaves and how you would cover it.
# 5. SKAB is downloaded from a third party at a pinned commit with hashes. What does the hash protect against, what
#    does it not protect against, and what would you do if the upstream repository disappeared?
#
# #### Interview rep (15 min, project explanation)
#
# > "How do I know the numbers in your project are real?"
#
# Answer aloud in 3 minutes. Then answer these follow-ups without notes, 1 minute each: "What happens if I clone it
# today?", "Which number would you least trust, and why?", "What did the audit find the first time you ran it?",
# "How long does a full reproduction take, and on what hardware?". Score yourself with the rubric in the answers file.

# %% [markdown]
# ## 8. Reflection and review
#
# **You should now be able to, without notes:** list the hidden state a clean clone excludes and the fix for each;
# write a fully pinned lock; declare a project's reproduction steps and headline values in a file a tool can
# read; read an audit log and tell a root cause from a consequence; and scope the remaining work in writing.
#
# **Reflection prompt.** Pick one of your own projects (a thesis, report or paper). Which step from raw data to figure would fail a
# clean-clone audit today, and what would it take to fix it?
#
# **Retrieval question (for the w8d7 retrospective).** Your audit passes on Python 3.13 and fails on 3.11 with a
# headline mismatch of 0.0004 in one PR-AUC. List three hypotheses in the order you would test them.
#
# **Next.** [w8d2: the technical report and its limitations](44_report_limitations.ipynb), written from the
# numbers you have just shown to be reproducible.

# %% [markdown]
# ## Verification record
#
# Executed on 2026-11-22 and 2026-11-25 (Python 3.13.18, Git 2.43.0):
#
# * `python tools/verify_checks.py labs/w8d1_project_completion`: lab reference passes 18 checks and all 7 lab
#   mutants are rejected, each by its intended check; challenge reference passes 7 checks and all 4 challenge
#   mutants are rejected. The shipped starter fails 15 of 18 lab checks; the memo template fails the challenge.
# * Real audit: `solutions/labs/w8d1_project_completion/real_audit/assemble_reference_repo.py` then the reference
#   tool; PASS, 18 headline values, maximum difference 0, 75 s (log committed next to the script). Dependencies were
#   installed from PyPI into the fresh venv.
# * Worked example run; output above copied from it. Figures regenerated by `figures/make_figures.py` and viewed.
# * Not verified: Python 3.11/3.12; Windows paths (the absolute-path pattern covers `C:\Users\` but was not run on
#   Windows); the time budget.

# %% [markdown]
# ## Record your progress
#
# Tick only what is true. Passing the supplied checks is *guided practice*; mark *independent* only for work done without hints or solutions.

# %%
from mlcourse.progress import mark, note

# mark("w8d1", "reading")
# mark("w8d1", "guided")
# mark("w8d1", "independent")
# note("w8d1", "what tripped me up today")

