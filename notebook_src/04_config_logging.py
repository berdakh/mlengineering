# %% [markdown]
# [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/04_config_logging.ipynb)
#
# *Click the badge to run this notebook in Google Colab - no install required. The first code cell sets everything up.*

# %% [markdown]
# # 04 · Configuration, logging and reproducible runs
#
# **Week 1 · day 4 · 2 h essential path + up to 1 h optional** · lab files: [`labs/w1d4_config_logging/`](../labs/w1d4_config_logging/)
#
# **Objective.** Make a training run reproducible and inspectable: typed validated config with overrides, logging configured once, explicit seeds, and a run directory with config snapshot, metrics and provenance.

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
# **Unit id:** `w1d4` · **Week 1, day 4** · **Content status:** Execution verified (see Verification record)
# **Handbook:** [H2.2 Configuration, logging and reproducible runs](../docs/handbook/ch02_maintainable_python/h2_2_configuration_logging_runs.md)
# **Data:** `data/synthetic/pump_vibration.csv` — SYNTHETIC. Metric values in this lesson illustrate mechanics only; they say nothing about real equipment.
#
# ---

# %% [markdown]
# ## 1. Purpose
#
# **Primary objective.** Make a training run *reproducible and inspectable*: every value that
# influenced the result is declared in one validated configuration, every run writes a
# self-describing directory, and diagnostics go through `logging` rather than `print`.
#
# **What you will learn**
#
# - Treating configuration as typed, validated, immutable data with an explicit precedence order.
# - Configuring the standard `logging` module once, at the application entry point, and writing
#   library code that only *emits* records.
# - Threading a seed explicitly, and stating which nondeterminism you have *not* removed.
# - Recording provenance (resolved config, code version, library versions, data hash) per run.
#
# **Why an applied ML engineer needs it.** In research the question after a run is "what number did
# I get?". In a team the questions arrive weeks later and from other people: *which settings produced
# the model in production, can we regenerate it, what changed between Tuesday's run and today's, why
# did the nightly job fail at 03:00?* All four are answered from configuration snapshots and logs or
# they are not answered at all. Interviewers probe this directly ("how would you reproduce a model you
# trained six months ago?").
#
# **Prerequisites.** [W1D3](03_package_structure.ipynb): the `pumpwatch` package in a `src/`
# layout with a `train` command. You have used `argparse` and `print`-debugging for years; no prior
# use of `logging` or TOML is assumed.
#
# **Time budget — essential path 2 h**
#
# | Activity | Time |
# |---|---|
# | Read sections 1–2 (skim what you know; do not skip 2.3 and 2.5) | 25 min |
# | Worked example: run, modify, read the code | 20 min |
# | Guided lab, tasks 1–5 | 60 min |
# | Assessment questions (written answers) | 15 min |
#
# **Optional extension — up to 1 h:** independent challenge (40 min), interview rep (15 min).
# If you only have two hours, do the challenge on the review day; the independent-skill flag for
# this unit stays unset until it is done without the hints.
#
# ---

# %% [markdown]
# ## 2. Conceptual explanation
#
# ### 2.1 Intuition: a run is a function, and you must be able to name its arguments
#
# A training run computes
#
# ```
# result = f(code, config, data, environment, seed) + ε
# ```
#
# where `ε` is whatever nondeterminism is left (thread scheduling, GPU kernels, hash ordering).
# A notebook hides most of these arguments: `config` is scattered over cells and edited in place,
# `code` is "whatever the kernel executed, in whatever order", `data` is "the file that was at that
# path that day". Engineering a run means making each argument *explicit and recorded*:
#
# | Argument | Made explicit by | Recorded as |
# |---|---|---|
# | code | a package under version control | git commit (+ "dirty" flag) |
# | config | one typed object built at start-up | resolved config snapshot |
# | data | a path in the config | content hash of the file |
# | environment | pinned dependencies | interpreter + library versions |
# | seed | a config value passed down as an argument | part of the config snapshot |
# | ε | — | a written statement of what is not controlled |
#
# You already do the scientific version of this in a methods section. The difference is that a
# methods section is written once by a human; a run directory is written every time by the program.
#
# ### 2.2 Terminology
#
# - **Configuration** — values that select *what* to compute and may differ between runs or
#   deployments (paths, hyperparameters, seeds, log level). Distinct from **constants** of the method
#   (the definition of RMS) and from **secrets** (credentials).
# - **Resolved configuration** — the final values after all layers are merged. This, not the file, is
#   what ran.
# - **Precedence** — the fixed order in which layers override each other:
#   `defaults < config file < environment variables < command-line flags` (most specific wins).
# - **Repeatability / reproducibility / replicability.** Usage is inconsistent across fields — two
#   widely cited sources assign *reproducible* and *replicable* opposite meanings (see H2.2). This
#   course uses: **repeatable** = same code, config, data, environment → same numbers;
#   **reproducible** = someone else obtains the same result from your recorded artefacts;
#   **replicable** = the *finding* holds on new data. Today's lab buys repeatability and the records
#   needed for reproducibility. It buys no replicability at all.
# - **Logger / handler / formatter** — a *logger* is a named entry point that code emits records to;
#   a *handler* delivers records somewhere (stderr, file); a *formatter* renders a record as text.
# - **Provenance** — the recorded origin of an artefact: which code, data and settings produced it.
#
# ### 2.3 Configuration as data
#
# Three rules do most of the work.
#
# **(a) One object, built once, passed down.** `load_config()` runs at start-up and returns a frozen
# dataclass. Functions take the *values* they need (`train_and_evaluate(features, test_fraction, seed, C)`),
# not the config object and never a global. This keeps `features.py` and `model.py` importable and
# testable without any file on disk — which you will rely on tomorrow in W1D5.
#
# **(b) Reject what you do not understand.** The idiom `cfg.get("seed", 7)` turns a typo
# (`sed = 3`) into a silently wrong experiment that still completes and still produces a
# plausible number. A config loader should fail on unknown keys, wrong types and out-of-range values,
# and its error should name the key (`split.sed`), because the person reading the error is usually
# not the person who wrote the loader.
#
# **(c) Snapshot what was resolved, not what was requested.** With layers, no single input file
# describes the run. Write the merged result into the run directory *before* training starts, so a
# crashed run is still explained.
#
# Why TOML and frozen dataclasses here? `tomllib` is in the standard library (Python ≥ 3.11), the
# format has real types (ints, floats, strings, booleans, tables) and no implicit conversions, and you
# already maintain a `pyproject.toml`. Dataclasses give named, typed fields and immutability
# (`frozen=True`) with no dependency. Two limits to know: `tomllib` only *reads* TOML — hence the
# JSON snapshot — and dataclasses do **not** validate types at run time; annotations are documentation
# unless you check them, which is what the lab's loader does. The handbook discusses YAML, pydantic and
# Hydra; we do not adopt Hydra yet because config *composition* and sweep launching solve problems you
# do not have in a seven-key config, and they hide exactly the merge logic this lesson asks you to
# understand. In W5 the API layer brings in pydantic, at which point revisiting this choice is cheap
# because the rest of the package only sees a `Config` object.
#
# **Where secrets go.** Never in the repository and never in a snapshot. The Twelve-Factor App
# formulation is the useful test: could the codebase be made public at any moment without leaking a
# credential? Credentials are supplied by the environment (environment variables, or a secrets manager
# that populates them) and read at the point of use. Note that Twelve-Factor defines "config" as what
# varies *between deploys* and puts all of it in environment variables; ML training configuration
# (hyperparameters, feature settings) varies between *experiments* and must be versioned and reviewed,
# so it belongs in files under version control. Deployment settings of the future service (W5–W6) will
# follow the environment-variable rule.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/docs/assets/diagrams/mmd-04-01.svg" alt="Diagram 1 of notebook 04" style="max-width:100%">
#
# *Precedence is defaults, then file, then command line: later sources override earlier ones, and the snapshot records the result after all of them.*
#
# ### 2.4 Logging architecture
#
# ```
# logger "pumpwatch.features" ──┐                     ┌─ StreamHandler(stderr)  level=config
# logger "pumpwatch.split"    ──┼─► logger "pumpwatch" ┤
# logger "pumpwatch.cli"      ──┘   (handlers here)    └─ FileHandler(train.log) level=DEBUG
# ```
#
# - Loggers form a hierarchy by dotted name. A record emitted on `pumpwatch.features` is offered to
#   that logger's handlers, then **propagates** to the handlers of each ancestor
#   (`pumpwatch`, then the root logger) unless a logger on the way has `propagate = False`.
# - A logger's **level** decides whether a record is created at all; each handler's level filters
#   again on delivery. That is how one run can show INFO on the console and keep DEBUG in a file.
# - **Library code** does exactly one thing: `logger = logging.getLogger(__name__)` at module top, then
#   `logger.info(...)`. It never adds handlers, never calls `basicConfig`. The Python logging HOWTO is
#   explicit that configuring handlers is the application developer's prerogative.
# - **The application** (here: `cli.main`) configures handlers once.
# - With no configuration at all, records of WARNING and above still reach stderr through a
#   "handler of last resort"; INFO and DEBUG vanish. That is why un-configured code "logs nothing".
#
# Levels, as a working convention: **DEBUG** — detail for diagnosing (coefficients, shapes);
# **INFO** — milestones of a healthy run (rows loaded, split sizes, metrics); **WARNING** — the run
# continues but something deserves a human look (38 samples interpolated); **ERROR** — the run cannot
# produce its result.
#
# **Structured context.** Write `logger.info("loaded data path=%s rows=%d", path, n)`: an event name
# followed by `key=value` pairs, with arguments passed separately (the string is only formatted if the
# record is actually emitted). Such lines can be grepped and parsed; prose sentences cannot. W7 turns
# this into JSON logs for the service; the habit is the same.
#
# **stdout is an interface.** The program's *result* goes to stdout, diagnostics to stderr.
# `pumpwatch train ... | jq .metrics.auc` must work at any log level.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/docs/assets/diagrams/mmd-04-02.svg" alt="Diagram 2 of notebook 04" style="max-width:100%">
#
# *Library modules only obtain loggers and emit records. Where records go is decided in one place. Standard output stays free for the JSON result.*
#
# ### 2.5 Seeds, and the mathematics of what a seed does *not* give you
#
# Fixing a seed fixes one draw of a random variable. For a metric $M$ computed on a random
# group split $S$,
#
# $$\operatorname{Var}(M) = \underbrace{\operatorname{Var}_S\big(\mathbb{E}[M \mid S]\big)}_{\text{which units are held out}} + \underbrace{\mathbb{E}_S\big[\operatorname{Var}(M \mid S)\big]}_{\text{optimiser, initialisation, } \varepsilon}$$
#
# Logistic regression with a fixed solver has no second term; a neural network has both. A seeded run
# reports a single value from this distribution. On the synthetic pump data (10 units, 3 held out),
# seeds 0–9 give F1 from **0.778 to 0.930** (mean 0.879, sample s.d. 0.044) with *identical* code and
# hyperparameters — executed for this lesson with the reference solution. So:
#
# - A seed makes a run **repeatable**. It does not make the estimate **precise**.
# - A difference between two configurations that is smaller than the seed-to-seed spread is not
#   evidence. Compare over several seeds (W3 treats this properly; the seed in your config is what
#   makes that comparison scriptable).
# - Choosing the seed that gives the best number is hyperparameter tuning on the test set.
#
# This is the same phenomenon as the fold-to-fold spread you know from leave-subjects-out EEG
# evaluation: with few groups, *which* subjects are held out dominates the variance.
#
# **Practical rules.** (1) No global seeding in library code — pass `seed` (or a
# `numpy.random.Generator`) as an argument; scikit-learn's own guidance is that an integer
# `random_state` gives the same results across calls. (2) One seed per *purpose* if purposes should
# vary independently (split vs. initialisation). (3) Record library versions: NumPy only promises the
# same random stream for the same seed *on the same build and machine*, and allows the default
# generator's streams to change in feature releases.
#
# **PyTorch, for when it enters in W4** (conceptual; no torch in this lab). The PyTorch
# reproducibility notes state that completely reproducible results are not guaranteed across releases,
# commits or platforms, nor between CPU and GPU. Within one platform you can narrow `ε`:
# `torch.manual_seed`, `torch.backends.cudnn.benchmark = False` (the auto-tuner may otherwise select
# different convolution algorithms per run), `torch.use_deterministic_algorithms(True)` (errors on
# operations with no deterministic implementation), and seeding DataLoader workers via
# `worker_init_fn` plus an explicit `generator`. Each costs speed or convenience — which is why they
# are configuration, and why the honest deliverable is a *statement of residual nondeterminism*
# rather than a claim of determinism.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/labs/w1d4_config_logging/figures/seed_spread.svg" alt="SYNTHETIC pump data: test F1 for split seeds 0 to 9 with identical code and data ranges from 0.778 to 0.930, mean 0.879, sample standard deviation 0.044" width="100%">
#
# *SYNTHETIC data, reference solution. The ten points share code and data and differ only in which three units are held out (numbers above each point). A 0.04 difference between two single runs is inside this spread. Regenerate with `python labs/w1d4_config_logging/figures/make_figures.py`.*
#
# | seed | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
# |---|---|---|---|---|---|---|---|---|---|---|
# | test F1 | 0.914 | 0.914 | 0.870 | 0.870 | 0.778 | 0.930 | 0.882 | 0.909 | 0.853 | 0.873 |
#
# ### 2.6 Connection to what you already know
#
# Your experiments already have configs — they live in argparse defaults, notebook cells and file
# names like `run_lr1e-3_seed2_FINAL`. Encoding settings in file names is a run directory without a
# schema. The subject-level bookkeeping you do for cross-patient evaluation (which patients were in
# which fold) is provenance; today generalises it to the whole run.
#
# ### 2.7 Industry example
#
# A team retrains a fraud-scoring model nightly. One morning precision at the alert threshold is down
# four points. With run directories the on-call engineer runs a diff of last night's and the previous
# night's runs: the config is identical, the code commit is identical, the *data hash differs and the
# row count in the log dropped 30 %*. An upstream export truncated. Time to diagnosis: minutes, and no
# model was at fault. Without the snapshot, hash and logged row counts, the same investigation starts
# with "did anyone change anything?" in a chat channel. Your independent challenge builds exactly that
# diff tool.
#
# ### 2.8 Limitations and common misconceptions
#
# - *"I set the seed, so it is reproducible."* The seed is one of five arguments. Change the data file
#   or a library version and the same seed gives a different result.
# - *"The config file in git is the record."* Not if command-line overrides exist, and not if the file
#   was edited after the run. The snapshot is the record.
# - *"Logging is print with timestamps."* The value is separation: code decides *what* happened,
#   the application decides *where it goes and how much*. `print` cannot be silenced, filtered or
#   redirected per component.
# - *"More logging is better."* A log that reports every window is not read. Log state changes and
#   counts.
# - *A run directory is not an experiment tracker.* It has no search, no comparison UI, no access
#   control. It is the minimal mechanism; W4 introduces a tracker once you can say what it automates.
# - *Recording the environment is not pinning it.* `environment.json` tells you what was installed;
#   it does not recreate it. Lock files and containers (W6) do.
#
# ---

# %% [markdown]
# ## 3. Worked example
#
# **Files:** [`example/run_detector.py`](../labs/w1d4_config_logging/example/run_detector.py), [`example/detector.toml`](../labs/w1d4_config_logging/example/detector.toml).
# A deliberately different problem from the lab so that you see the pattern, not the solution: a
# rolling z-score spike detector on a simulated sensor trace.
#
# **Dataset.** Simulated in the script (SYNTHETIC): `n_samples` standard-normal values with `n_spikes`
# additive spikes of ±`spike_size` at random positions after index 200. "Schema": a 1-D float array
# and an integer array of true spike indices. Nothing about detector quality on real sensors follows
# from it.
#
# **Run it** (from the repository root):
#
# ```bash
# python labs/w1d4_config_logging/example/run_detector.py
# python labs/w1d4_config_logging/example/run_detector.py --set detector.threshold=3.0
# python labs/w1d4_config_logging/example/run_detector.py --set detector.threshold=2.0
# python labs/w1d4_config_logging/example/run_detector.py --set detector.treshold=3.0
# python labs/w1d4_config_logging/example/run_detector.py 2>/dev/null
# ```
#
# **Expected output** (obtained with NumPy 2.5.3; other NumPy versions may simulate a different trace
# and therefore different counts — see 2.5):
#
# | Command | stdout |
# |---|---|
# | defaults (threshold 4.0) | `{"n_true": 25, "n_detected": 23, "precision": 0.9565…, "recall": 0.88}` |
# | `detector.threshold=3.0` | `{"n_true": 25, "n_detected": 41, "precision": 0.6097…, "recall": 1.0}` |
# | `detector.threshold=2.0` | `{"n_true": 25, "n_detected": 249, "precision": 0.1004…, "recall": 1.0}` plus a WARNING on stderr |
# | `detector.treshold=3.0` | nothing on stdout; `config error: …unexpected keyword argument 'treshold'…` on stderr; exit code 2 |
# | defaults, `2>/dev/null` | only the JSON line |
#
# Each successful run creates `runs_example/<timestamp>/` with `config.json`, `metrics.json`, `run.log`
# (delete the directory when done; do not commit run directories).
#
# **Decisions worth reading in the code**
#
# 1. `SignalConfig(**raw["signal"])` — passing the parsed table as keyword arguments makes the
#    dataclass constructor itself reject unknown keys. This is the cheapest strict loader there is. Its
#    weakness is visible in the typo case: the message names the *class and argument*, not the config
#    key, and nothing checks types (`threshold = "high"` would be accepted and fail later, inside
#    NumPy). The lab's loader fixes both.
# 2. `__post_init__` holds range checks, because a frozen dataclass has no other hook.
# 3. `simulate` creates `np.random.default_rng(cfg.seed)` locally. No `np.random.seed` at module level,
#    so calling order elsewhere cannot change the trace.
# 4. `detect` uses `sliding_window_view(x, window)[:-1]` so the baseline for sample *t* uses only
#    samples before *t* — no future information. (You will meet this again as temporal leakage in W3.)
# 5. `logging.basicConfig(...)` is called inside `main()`, not at import. In a single-file script the
#    script *is* the application, so `basicConfig` on the root logger is appropriate; in the lab's
#    package you attach handlers to the package logger instead.
# 6. Only `print(json.dumps(metrics))` writes to stdout.
#
# **Interpretation.** Lowering the threshold trades precision for recall, as it must; the point here is
# that each of those three numbers is attached to a directory that says which threshold, window and
# seed produced it, and that the mistyped run produced no number at all instead of a wrong one.
#
# ---

# %% [markdown]
# ## 4. Guided lab
#
# **Goal.** Take `pumpwatch` from v0.1.0 (flags and `print`) to v0.2.0: `pumpwatch train --config
# configs/base.toml [--set section.key=value ...] [--run-dir runs]` producing a run directory.
#
# **Starter:** `labs/w1d4_config_logging/lab/` — the W1D3 reference package plus
# `configs/base.toml`. If you prefer to continue from your own W1D3 package, copy it over the starter
# (keep `configs/`); the checks only use the contract below.
#
# **The contract the checks grade** (nothing else about your implementation is prescribed):
#
# | Aspect | Requirement |
# |---|---|
# | Entry point | `pumpwatch.cli.main(argv=None) -> int`; `train --config PATH [--set SECTION.KEY=VALUE]... [--run-dir DIR]` |
# | Config API | `pumpwatch.config.load_config(path, overrides=None)` returns an immutable object with `cfg.data.path`, `cfg.data.fs`, `cfg.split.test_fraction`, `cfg.split.seed`, `cfg.model.C`, `cfg.logging.level`; invalid input raises a `ValueError` (or subclass) |
# | Defaults | `data.fs=256.0`, `split.test_fraction=0.3`, `split.seed=7`, `model.C=1.0`, `logging.level="INFO"`; `data.path` is required |
# | Precedence | defaults < file < `--set` |
# | Validation | unknown key, wrong type, out-of-range value, missing `data.path` → non-zero exit, message containing the dotted key (e.g. `split.sed`) on stderr, no traceback, empty stdout |
# | Run directory | each run creates a new sub-directory of `--run-dir` containing `config.json` (resolved, nested by section), `metrics.json`, `environment.json` (keys `python`, `packages`, `git_commit`, `data_sha256`), and a non-empty `*.log` |
# | stdout | exactly one JSON object with keys `run_dir` and `metrics` |
# | Logging | importing any `pumpwatch` module configures nothing and prints nothing; console verbosity follows `logging.level` and goes to stderr; the log file keeps the run's steps even when the console is at ERROR |
# | Determinism | same config → identical `metrics.json`; `split.seed` changes the held-out units |
#
# Run the checks at any time (they take about half a minute):

# %%
!python -m pytest labs/w1d4_config_logging/checks -q

# %% [markdown]
# Work with the package importable, either `pip install -e labs/w1d4_config_logging/lab` in your
# course virtual environment (then re-install your own W1D3 package later if you use both) or, without
# installing, `export PYTHONPATH=labs/w1d4_config_logging/lab/src` for this shell.
#
# ### Task 1 — Typed configuration (20 min)
#
# Create `src/pumpwatch/config.py` with frozen dataclasses for the four sections and
# `load_config(path, overrides=None)`. For this task ignore `overrides`.
#
# ```python
# # starter sketch - complete it
# @dataclass(frozen=True)
# class SplitConfig:
#     test_fraction: float = 0.3
#     seed: int = 7
#
# def load_config(path, overrides=None) -> Config:
#     with open(path, "rb") as fh:          # tomllib needs binary mode
#         raw = tomllib.load(fh)
#     ...
# ```
#
# Required behaviour: unknown section or key → error naming `section.key`; wrong type → error
# (an `int` where a `float` is expected is fine; a `str` is not; `True` is not an integer here even
# though `isinstance(True, int)` is true in Python); ranges: `fs > 0`, `0 < test_fraction < 1`,
# `C > 0`, level in `DEBUG/INFO/WARNING/ERROR`.
#
# **Checkpoint 1**
#
# ```bash
# python -c "from pumpwatch.config import load_config; print(load_config('labs/w1d4_config_logging/lab/configs/base.toml'))"
# ```
#
# prints a nested `Config(...)` showing `seed=7`. Then edit a copy of the TOML to contain `sed = 7`
# and confirm you get your own error naming `split.sed`, not a `TypeError` from a constructor.
#
# ### Task 2 — Overrides and precedence (10 min)
#
# Implement `overrides`: a list of strings `"section.key=value"`. Decide how the value text becomes a
# typed value *before* you write code, and write your rule in the module docstring. Apply overrides to
# the raw nested dict **before** building and validating the dataclasses, so that an override passes
# through exactly the same checks as a file value.
#
# **Checkpoint 2.** `load_config(path, ["split.seed=11"]).split.seed == 11`;
# `load_config(path, ["split.seed=1.5"])` and `["model.depth=3"]` raise your error.
#
# ### Task 3 — Run directory and CLI (15 min)
#
# Rewrite `cli.py`: `--config`, repeatable `--set`, `--run-dir` (default `runs`). On each run:
# create `RUN_DIR/<run_id>/` (design the id so that two runs never share a directory — think about two
# runs started in the same second), write `config.json` *before* doing any work, then compute, then
# write `metrics.json` and `environment.json`, then print `{"run_dir": ..., "metrics": ...}`.
#
# `environment.json` needs: `python` (`platform.python_version()`), `packages` (a dict with at least
# `numpy`, `pandas`, `scikit-learn` from `importlib.metadata.version`), `git_commit` (hash or `null`
# when not in a git checkout or git is absent), `data_sha256` (hash of the data file's bytes).
#
# **Checkpoint 3**
#
# ```bash
# python -m pumpwatch.cli train --config labs/w1d4_config_logging/lab/configs/base.toml --run-dir /tmp/pw_runs
# ls /tmp/pw_runs/*/
# ```
#
# Expected metrics for the base config, from the reference solution on the tested versions:
# `auc ≈ 0.9992`, `f1 ≈ 0.909`, `test_units = ["P01", "P06", "P09"]`. If your numbers differ at the
# second decimal, something other than the config changed — find out what before continuing.
#
# <img src="https://raw.githubusercontent.com/berdakh/mlengineering-/main/docs/assets/diagrams/mmd-04-03.svg" alt="Diagram 3 of notebook 04" style="max-width:100%">
#
# *Anatomy of a run directory: four files, four questions.*
#
# ### Task 4 — Logging (10 min)
#
# Add `logger = logging.getLogger(__name__)` to `io`, `features`, `split`, `model` and log, with
# `key=value` context: rows and units loaded (INFO), number of interpolated samples if any (WARNING),
# windows and positive rate (INFO), seed and held-out units (INFO), fitted coefficients (DEBUG). Write
# a `setup_logging(level, log_file)` function, call it once from the CLI after the run directory
# exists, and send console output to **stderr**.
#
# **Checkpoint 4**
#
# ```bash
# python -m pumpwatch.cli train --config labs/w1d4_config_logging/lab/configs/base.toml --run-dir /tmp/pw_runs 2>/dev/null | python -m json.tool
# python -m pumpwatch.cli train --config labs/w1d4_config_logging/lab/configs/base.toml --run-dir /tmp/pw_runs --set 'logging.level="ERROR"' >/dev/null
# ```
#
# The first prints valid JSON only. The second prints nothing, and the newest `*.log` still lists the
# steps.
#
# ### Task 5 — Determinism and the residual-nondeterminism note (5 min)
#
# Run the base config twice and `diff` the two `metrics.json` files (no output expected). Run with
# `--set split.seed=3` and confirm `test_units` changes. Then add a section "Reproducibility" to
# `lab/README.md` (create it) stating, in your own words, (a) what is fixed by the config, (b) what is
# recorded but not fixed, (c) what is neither. Three to six sentences. This note is part of the
# deliverable and is graded by the rubric, not by the checks.
#
# ### Debugging guidance
#
# | Symptom | Likely cause |
# |---|---|
# | `TypeError: a bytes-like object is required` / `File must be opened in binary mode` | `tomllib.load` needs `open(path, "rb")` |
# | Your INFO lines from `cli.py` are missing but other modules log | under `python -m pumpwatch.cli` the module's `__name__` is `"__main__"`, so `getLogger(__name__)` is not below `pumpwatch`. Name that logger explicitly, or attach handlers to the root logger and accept third-party noise |
# | Every log line appears twice | handlers on both your package logger and the root logger (propagation), or `setup_logging` called twice without removing old handlers |
# | Nothing is logged at all | no handler configured: only WARNING+ reaches the last-resort handler |
# | `--set 'logging.level=ERROR'` fails to parse | decide whether bare words are strings in your override rule; the checks pass the TOML-quoted form `logging.level="ERROR"` |
# | `--set data.path=/x/y.csv` rejected | same decision: an unquoted path is not valid TOML |
# | Checks report "expected exactly one run directory" | you write files directly into `--run-dir` instead of a per-run sub-directory |
# | `git_commit` raises outside a repository | catch the failure and store `null`; provenance collection must never crash a run |
# | Checks fail only with `Traceback` in stderr | a config mistake escaped as an exception; catch your config error in `main` and return a non-zero code |
#
# **Deliverable.** The v0.2.0 package in `lab/` passing the checks, one run directory you produced,
# and the reproducibility note. Completion criteria: all checks pass **and** you can explain, without
# looking, the path of one INFO record from `pumpwatch.split` to the log file.
#
# ---

# %%
# Run the automated checks on your guided lab.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w1d4")

# %% [markdown]
# ## 5. Independent challenge
#
# [`challenge/README.md`](../labs/w1d4_config_logging/challenge/README.md) — add `pumpwatch compare-runs RUN_A RUN_B`, the tool
# from the industry example in 2.7. It transfers today's ideas to *reading* run directories and
# forces a decision about what "the same data" means. Acceptance criteria are in that file; there is
# no solution in this directory. Checks: `python -m pytest labs/w1d4_config_logging/checks_challenge -q`.
#
#
# ### The challenge brief
#
#
# **Time:** about 40 minutes · **Assistance:** none intended (hints exist; using them changes how you
# record this unit) · **Solution:** not in this directory.
#
# #### Situation
#
# Two training runs disagree. Before anyone discusses models, you want a tool that answers, from the
# run directories alone: *what was configured differently, how did the metrics move, and was it even
# the same data?*
#
# #### Task
#
# Copy your finished lab package into this directory and extend it:
#
# ```bash
# cp -r labs/w1d4_config_logging/lab/. labs/w1d4_config_logging/challenge/
# ```
#
# Add a second sub-command:
#
# ```
# pumpwatch compare-runs RUN_A RUN_B
# ```
#
# which reads the two run directories written by `pumpwatch train` and prints one JSON object to
# stdout:
#
# ```json
# {
#   "config_diff": {"split.seed": {"a": 7, "b": 3}},
#   "metric_diff": {"auc": {"a": 0.9992, "b": 1.0, "delta": 0.0008}},
#   "same_data": true
# }
# ```
#
# #### Acceptance criteria
#
# 1. `config_diff` contains exactly the configuration values that differ, keyed by **dotted name**
#    (`section.key`), each with the value in run A (`a`) and in run B (`b`). Identical configs give `{}`.
# 2. `metric_diff` has one entry per **numeric** metric present in both runs, with `a`, `b` and
#    `delta`. You must decide and document the sign convention; the checks expect the convention under
#    which a positive `delta` means the metric is higher in RUN_B. Non-numeric metrics
#    (e.g. `test_units`) are not differenced.
# 3. `same_data` is `true` exactly when both runs read byte-identical data — regardless of where the
#    file was located — and `false` otherwise.
# 4. If either argument is not a complete run directory, the command exits non-zero with a one-line
#    message on stderr, no traceback, and nothing on stdout.
# 5. `pumpwatch train` still passes the lab checks.
# 6. In `challenge/README_NOTES.md`, answer in 3–5 sentences: *under which values of `config_diff` and
#    `same_data` is it legitimate to attribute a metric delta to a modelling change, and what would
#    you still want to know?* (Graded with the assessment rubric, not by the checks.)
#
# #### Checks

# %%
!python -m pytest labs/w1d4_config_logging/checks_challenge -q

# %% [markdown]
# The checks train five small runs (including one on an identical copy of the data at another path and
# one on a file edited in place) and grade only the command's output and exit codes.
#
# #### What this transfers
#
# The lab had you *write* provenance. Here you *consume* it, which is where weaknesses in what you
# recorded become visible. If your lab's `config.json` or `environment.json` lacks something this
# command needs, fix the lab first — that is the intended lesson, not an obstacle.

# %%
# Run the automated checks on your independent challenge.
# A fresh starter is expected to FAIL; passing means guided practice, not mastery.
from mlcourse.checks import check

check("w1d4", challenge=True)

# %% [markdown]
# ## 6. Progressive hints
#
# Open them in order, and only after ten minutes of being stuck. Record which you used in
# your progress notes — a challenge solved with hint 3 counts as guided practice, not as independent
# skill.
#
# 1. [Conceptual hint](../labs/w1d4_config_logging/hints/hint1_concept.md)
# 2. [Suggested approach](../labs/w1d4_config_logging/hints/hint2_approach.md)
# 3. [Partial implementation](../labs/w1d4_config_logging/hints/hint3_partial.md)
# 4. Full reference solutions: `solutions/labs/w1d4_config_logging/` (`lab/`, `challenge/`).
#
#
# Open one hint at a time, only after a real attempt.
#
# <details>
# <summary><b>Hint 1 concept</b></summary>
#
#
# **Lab**
#
# - Think of configuration loading as a pipeline with three separable stages:
#   *collect* (defaults, file, overrides → one raw nested dict), *check* (keys, types, ranges),
#   *freeze* (build immutable objects). Bugs in this lab are almost always two stages tangled
#   together — for example applying overrides after the objects have been built and checked.
# - The snapshot question is "what did the computation receive?", not "what did the user type?".
#   There is exactly one object that answers it.
# - For logging, ask of every line you write: *is this module the application, or a library the
#   application uses?* Only the application may decide where records go.
# - A seed is an argument. If you cannot point at the function parameter through which it travels
#   from the config to the code that draws random numbers, it is not threaded.
#
# **Challenge**
#
# - A nested mapping and a flat mapping with dotted keys carry the same information. Differences are
#   much easier to compute on one of the two.
# - "The same data" is a claim about content. Which field of your run directory is a statement about
#   content, and which is only a statement about location?
# - Decide what a *complete* run directory is before reading any file, and check for it in one place.
#
# </details>
#
# <details>
# <summary><b>Hint 2 approach</b></summary>
#
#
# **Lab**
#
# 1. `load_config`:
#    - read the TOML into `raw` (a dict of dicts);
#    - reject unknown *sections*; make `merged = {section: dict(raw.get(section, {}))}` for all four
#      known sections so later code never needs `.get`;
#    - for each override string: split on the first `=`, split the left side on the first `.`,
#      convert the right side to a typed value, assign into `merged[section][key]`;
#    - per section, compare `set(values)` with the dataclass field names
#      (`dataclasses.fields(cls)`), check each value's type against the field's annotation, then
#      construct the dataclass; a missing required field is the one remaining way construction can fail;
#    - finally run the range checks on the built object.
# 2. Typed override values: the simplest consistent rule is "the right-hand side is a TOML value", which
#    you can parse by handing `tomllib.loads` a one-line document. Decide what happens when that
#    parse fails (reject, or treat as a plain string) and document it.
# 3. CLI order of operations: parse args → load config (on error: message to stderr, return 2) →
#    create run directory → configure logging (now the log file path exists) → write `config.json` →
#    compute → write `metrics.json`, `environment.json` → print JSON → return 0.
# 4. Logging setup: get the logger named after your package, set it to DEBUG, add a
#    `StreamHandler(sys.stderr)` at the configured level and a `FileHandler` at DEBUG, set
#    `propagate = False`. Remove existing handlers first so the function can be called twice.
# 5. Run id: a UTC timestamp alone collides within a second. Either add something that differs
#    (a short hash, a counter) or create with `mkdir(exist_ok=False)` and retry with a suffix.
#
# **Challenge**
#
# 1. `load_run(path)` → dict with the three parsed JSON files, raising one custom exception if the
#    directory or any file is missing.
# 2. `flatten(nested)` → `{"split.seed": 7, ...}`; write it recursively so depth does not matter.
# 3. `config_diff`: iterate over the union of flattened keys; keep those whose values differ.
# 4. `metric_diff`: iterate over the intersection of metric names; keep those where both values are
#    numbers (mind that `bool` is a subclass of `int`); `delta = b - a`.
# 5. `same_data`: compare the content hashes recorded in `environment.json`.
# 6. Wire a second sub-parser; catch your exception in the command function and return 2.
#
# </details>
#
# <details>
# <summary><b>Hint 3 partial</b></summary>
#
#
# Fragments, not a solution: the validation logic, the logging setup body, the environment
# collection and the diff logic are left for you. Opening this hint means the unit counts as guided
# practice for the parts shown.
#
# ##### Lab
#
# ```python
# # config.py
# class ConfigError(ValueError):
#     """A configuration problem the user can fix; the message names the dotted key."""
#
# _SECTIONS = {"data": DataConfig, "split": SplitConfig, "model": ModelConfig, "logging": LoggingConfig}
#
# def parse_override(text: str) -> tuple[str, str, object]:
#     key, sep, raw = text.partition("=")
#     section, dot, name = key.strip().partition(".")
#     if not sep or not dot or not section or not name:
#         raise ConfigError(f"override {text!r} must look like section.key=value")
#     try:
#         value = tomllib.loads(f"v = {raw}")["v"]      # "11" -> 11, "0.5" -> 0.5, '"x"' -> "x"
#     except tomllib.TOMLDecodeError:
#         value = raw.strip()                            # bare words / paths stay strings
#     return section, name, value
#
# def _build_section(name, cls, values):
#     fields = {f.name: f for f in dataclasses.fields(cls)}
#     unknown = sorted(set(values) - set(fields))
#     if unknown:
#         raise ConfigError(f"unknown configuration key: {name}.{unknown[0]}")
#     ...   # type-check each value against fields[key].type, then construct cls(**kwargs)
# ```
#
# Note: with `from __future__ import annotations`, `fields[key].type` is the *string* `"float"`, not
# the class `float`.
#
# ```python
# # cli.py - the order matters
# def run_train(args) -> int:
#     try:
#         cfg = load_config(args.config, args.overrides)
#     except ConfigError as exc:
#         print(f"config error: {exc}", file=sys.stderr)
#         return 2
#     resolved = cfg.to_dict()
#     run_dir = create_run_dir(args.run_dir, resolved)
#     setup_logging(cfg.logging.level, run_dir / "train.log")
#     write_json(run_dir / "config.json", resolved)
#     ...
#     print(json.dumps({"run_dir": str(run_dir), "metrics": metrics}, indent=2))
#     return 0
# ```
#
# ```python
# # runs.py
# def create_run_dir(base, config: dict) -> Path:
#     stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
#     stem = f"{stamp}-{config_fingerprint(config)}"     # fingerprint: short sha256 of sorted-key JSON
#     candidate, n = Path(base) / stem, 1
#     while True:
#         try:
#             candidate.mkdir(parents=True, exist_ok=False)
#             return candidate
#         except FileExistsError:
#             n += 1
#             candidate = Path(base) / f"{stem}-{n}"
# ```
#
# ##### Challenge
#
# ```python
# def flatten(nested: dict, prefix: str = "") -> dict:
#     flat = {}
#     for key, value in nested.items():
#         dotted = f"{prefix}{key}"
#         if isinstance(value, dict):
#             flat.update(flatten(value, prefix=f"{dotted}."))
#         else:
#             flat[dotted] = value
#     return flat
# ```
#
# The remaining pieces (`load_run`, the two diffs, `same_data`, the sub-command) follow hint 2.
# The full reference is in `solutions/labs/w1d4_config_logging/challenge/`.
#
# </details>

# %% [markdown]
# ## 7. Assessment
#
# `assessment.md` (section 7 of this notebook): six reasoning questions, one design-choice explanation, an
# interview coding rep, and the rubric. Write your answers before opening
# `solutions/labs/w1d4_config_logging/assessment_answers.md`, which also lists common incorrect
# answers and why they fail.
#
# Automated checks: `checks/` (lab) and `checks_challenge/` (challenge). They establish that the
# contract holds. They do not establish that you could write this again unaided.
#
#
# ### Assessment questions
#
#
# Write answers in your own words (2–6 sentences each unless stated) **before** opening
# `solutions/labs/w1d4_config_logging/assessment_answers.md`. Suggested location:
# `progress/journal/w1d4_assessment.md`.
#
# #### A. Reasoning questions
#
# **A1.** A config loader is written as `seed = cfg.get("split", {}).get("seed", 7)` for every key.
# Describe a concrete sequence of events in which this produces a wrong *published* number without
# any error or warning. What property of the loader would have prevented it?
#
# **A2.** Your run directory contains `config.json`, and the repository contains
# `configs/base.toml` at the recorded git commit. Give two situations in which these two disagree
# about a value, and say which one you trust and why.
#
# **A3.** A teammate adds `logging.basicConfig(level=logging.INFO)` at the top of
# `pumpwatch/features.py` "so that the logs show up in my notebook". What breaks, for whom, and what
# should they do instead (two acceptable alternatives)?
#
# **A4.** With the base config, ten split seeds give F1 between 0.778 and 0.930 (s.d. 0.044) on the
# synthetic pump data. You change one feature and, with seed 7, F1 moves from 0.909 to 0.930.
# What can you conclude? What is the minimal additional evidence you would collect, and how does
# today's work make collecting it cheap?
#
# **A5.** Two runs have identical `config.json` and identical `git_commit`, yet different
# `metrics.json`. List, in the order you would check them, the remaining explanations, and name the
# recorded field (or the absence of one) relevant to each.
#
# **A6.** Where should each of these live, and why: (i) the regularisation strength `C`;
# (ii) an AWS access key for the bucket holding training data; (iii) the band edges of the
# high-frequency feature (70–110 Hz); (iv) the log level; (v) the URL of the production database
# used by the deployed service?
#
# #### B. Design-choice explanation
#
# **B1.** (8–12 sentences.) In the lab, console logs go to stderr at the configured level, the log
# file is always written at DEBUG, and handlers are attached to the `pumpwatch` logger with
# `propagate = False` rather than to the root logger. Defend or criticise this design. Your answer
# must address: what a user piping the output sees; what a developer embedding `pumpwatch` in a
# FastAPI service (W5) would want instead; and one cost of the chosen design.
#
# #### C. Interview rep (Python, 12 minutes, no assistance, no running code until the end)
#
# You are given log lines in this format:
#
# ```
# 2026-11-21 20:08:55,740 INFO    pumpwatch.io | loaded data path=a.csv rows=38400 duration_ms=41
# 2026-11-21 20:08:55,931 WARNING pumpwatch.features | interpolating missing samples n_missing=38
# 2026-11-21 20:08:55,948 INFO    pumpwatch.split | split seed=7 duration_ms=12
# ```
#
# Write `summarise(lines: list[str], k: int) -> dict` returning
#
# ```python
# {"levels": {"INFO": 2, "WARNING": 1},
#  "slowest": [("pumpwatch.io", 41), ("pumpwatch.split", 12)]}   # up to k (logger, duration_ms), slowest first
# ```
#
# Lines without `duration_ms` do not appear in `slowest`. Malformed lines (no `|`) are skipped and
# counted under `"levels"` as `"MALFORMED"`. State the time complexity in terms of the number of lines
# *n* and *k*, and say what you would change if *n* were 10⁹ lines read from a stream.
#
# Then (and only then) run your function on the three lines above. Self-score with the rubric.
#
# #### D. Rubric
#
# Each open answer is scored 0–3. Record scores honestly; they feed the "review needed" flag, not a grade.
#
# | Score | Meaning |
# |---|---|
# | 0 | Missing, or restates the question |
# | 1 | A correct statement, but no mechanism (says *that*, not *why* or *how it fails*) |
# | 2 | Correct mechanism and a concrete consequence; one relevant aspect missing or one imprecise claim |
# | 3 | Correct mechanism, concrete consequence, the relevant trade-off or limit named, no incorrect claims |
#
# Specific requirements for a 3:
#
# - **A1** — names a silent-typo (or misplaced-section) scenario end to end *and* identifies "reject unknown keys" (not "be more careful").
# - **A2** — both a command-line override and a post-run/uncommitted edit (or dirty tree); trusts the snapshot because it was written by the run from the resolved object.
# - **A3** — root logger reconfigured at import for every host application (and `basicConfig` being a no-op if handlers already exist, so it does not even reliably help); alternatives: configure in the notebook/application, or a documented opt-in helper function.
# - **A4** — "nothing yet"; paired comparison over the same set of seeds/splits; cost is one `--set split.seed=…` loop.
# - **A5** — at least data content (`data_sha256`), library versions/platform (`environment.json`), uncommitted changes (dirty flag), and unrecorded residual nondeterminism; ordered sensibly (cheap, likely first).
# - **A6** — all five placed with a reason; distinguishes experiment config, method constant promoted to config only when it is varied, deploy config, and secrets.
# - **B1** — all three required aspects; at least one genuine cost (e.g. third-party warnings invisible in the file; host applications must re-enable propagation or call their own setup).
# - **C** — correct output on the sample, single pass, `heapq.nlargest` or equivalent bounded heap with O(n log k), streaming answer does not hold all lines; malformed-line handling present. Score 2 if sorted everything (O(n log n)) but correct.
#
# **Review-needed triggers:** any A-question at 0–1, B1 below 2, or C not finished in 15 minutes.

# %% [markdown]
# ## 8. Reflection and review
#
# **You should now be able to, without notes:**
#
# - write a strict loader for a small typed config with file and command-line layers;
# - set up `logging` so that library modules emit and the entry point configures;
# - say what a seed fixes, what it does not, and how you would report run-to-run variation;
# - list what a run must record for someone else to regenerate it.
#
# **Reflection prompt (5 min, in your journal).** Pick one result from a paper of yours. Which of the
# five arguments of `f` could you recover exactly today, and which only approximately? What is the
# cheapest change to your research workflow that would close the largest gap?
#
# **Retrieval practice (answer on the W1 review day, from memory).** A colleague's `--set split.seed=3`
# run and yours with seed 7 differ by 0.04 F1 and they conclude their feature change helped. State two
# distinct reasons this conclusion is not yet supported, and name the file(s) in a run directory you
# would inspect for each.
#
# **Next lesson.** [W1D5 — Testing ML code with pytest](05_testing_ml_code.ipynb). Because
# the feature and model functions take plain values instead of reading config or files, they can be
# tested in isolation; `load_config`'s rejection rules are your first natural table of test cases.
#
# ---

# %% [markdown]
# ## Verification record
#
# Executed in the authoring session on Python 3.13.18, NumPy 2.5.3, pandas 3.0.5, scikit-learn 1.9.1,
# pytest 9.1.1 (Linux):
#
# - Worked example: all five commands in section 3 executed; outputs in the table are copied from those runs.
# - Reference solution: base config run twice, `metrics.json` identical; `split.seed=3` changes the held-out units.
# - `python tools/verify_checks.py labs/w1d4_config_logging`: reference lab and challenge solutions
#   pass; six lab mutants and three challenge mutants are rejected. The unmodified starter fails 23 of 24 lab checks.
# - Seed-spread figures in 2.5: computed with the reference solution for seeds 0–9.
# - Not verified here: behaviour on Python 3.11/3.12 (the code uses only features available from 3.11);
#   `pip install -e` of the lab package (checks import from `src/` via `PYTHONPATH`).
# - Sources: see the handbook section H2.2 for the list of documents consulted and how.

# %% [markdown]
# ## Record your progress
#
# Tick only what is true. Passing the supplied checks is *guided practice*; mark *independent* only for work done without hints or solutions.

# %%
from mlcourse.progress import mark, note

# mark("w1d4", "reading")
# mark("w1d4", "guided")
# mark("w1d4", "independent")
# note("w1d4", "what tripped me up today")

